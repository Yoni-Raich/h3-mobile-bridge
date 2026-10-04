import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

import backend.db as db_module
from backend.library import init_library_db
from backend.production_db import init_production_db
from backend.main import app, public_health, worker
from backend.workflows import qwen_image_workflow


class ImageGenWorkflowTests(unittest.TestCase):
    def test_text_to_image_workflow(self):
        wf = qwen_image_workflow(
            prompt="A majestic lion on a snowy mountain peak",
            negative_prompt="blurry, low quality",
            width=1024,
            height=1024,
            steps=25,
            cfg=4.0,
            seed=42,
            reference_images=[],
        )
        self.assertIn("1", wf)  # UnetLoaderGGUF
        self.assertIn("2", wf)  # CLIPLoader
        self.assertIn("3", wf)  # VAELoader
        self.assertIn("4", wf)  # TextEncodeQwenImage21 (positive + negative)
        self.assertIn("6", wf)  # EmptyLatentImage
        self.assertIn("8", wf)  # KSampler
        self.assertIn("9", wf)  # VAEDecode
        self.assertIn("10", wf)  # SaveImage

        # Verify UnetLoaderGGUF parameters
        self.assertEqual(wf["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(wf["4"]["class_type"], "TextEncodeQwenImage21")
        self.assertEqual(wf["6"]["inputs"]["width"], 1024)
        self.assertEqual(wf["6"]["inputs"]["height"], 1024)
        self.assertEqual(wf["8"]["inputs"]["steps"], 25)
        self.assertEqual(wf["8"]["inputs"]["cfg"], 4.0)
        self.assertEqual(wf["8"]["inputs"]["seed"], 42)

    def test_image_to_image_with_reference_workflow(self):
        wf = qwen_image_workflow(
            prompt="Turn this character into cyberpunk style",
            negative_prompt="",
            width=1344,
            height=768,
            steps=30,
            cfg=4.5,
            seed=12345,
            reference_images=["ref_character.png", "ref_background.png"],
        )
        self.assertEqual(wf["6"]["inputs"]["width"], 1344)
        self.assertEqual(wf["6"]["inputs"]["height"], 768)
        # Should have LoadImage nodes for references
        load_nodes = [k for k, v in wf.items() if v.get("class_type") == "LoadImage"]
        self.assertEqual(len(load_nodes), 2)
        # Prompt encoder should be TextEncodeQwenImage21 with images.image_1, images.image_2
        self.assertEqual(wf["4"]["class_type"], "TextEncodeQwenImage21")
        self.assertIn("images.image_1", wf["4"]["inputs"])
        self.assertIn("images.image_2", wf["4"]["inputs"])


class ImageGenApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="h3-image-test-")
        self.path = Path(self.temp.name) / "jobs.sqlite3"
        self.original_path = db_module.DB_PATH
        db_module.DB_PATH = self.path
        db_module.init_db()
        init_library_db()
        init_production_db()
        self.notify_patch = patch.object(worker, "notify")
        self.notify_patch.start()
        # Queue/API tests do not require multi-GB model downloads.
        self.health_patch = patch("backend.main.public_health", side_effect=lambda: {
            **public_health(), "qwen_image_ready": True,
        })
        self.health_patch.start()
        self.client = TestClient(app)
        session = self.client.get("/api/session")
        self.token = session.json()["csrf_token"]

    def tearDown(self):
        self.client.close()
        self.notify_patch.stop()
        self.health_patch.stop()
        db_module.DB_PATH = self.original_path
        self.temp.cleanup()

    def test_create_and_list_image_jobs(self):
        # Create image job
        data = {
            "prompt": "A cybernetic futuristic sports car in rain",
            "aspect_ratio": "16:9",
            "steps": "20",
            "cfg": "3.5",
            "seed": "999",
        }
        res = self.client.post("/api/image-jobs", data=data, headers={"X-CSRF-Token": self.token})
        self.assertEqual(res.status_code, 200, res.text)
        created = res.json()
        self.assertEqual(created["prompt"], "A cybernetic futuristic sports car in rain")
        self.assertEqual(created["aspect_ratio"], "16:9")
        self.assertEqual(created["width"], 1344)
        self.assertEqual(created["height"], 768)
        self.assertEqual(created["steps"], 20)
        self.assertEqual(created["cfg"], 3.5)
        self.assertEqual(created["status"], "queued")

        # List image jobs
        list_res = self.client.get("/api/image-jobs")
        self.assertEqual(list_res.status_code, 200)
        jobs = list_res.json()["image_jobs"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["id"], created["id"])

        # Also appears in /api/jobs
        all_jobs_res = self.client.get("/api/jobs")
        self.assertIn("image_jobs", all_jobs_res.json())
        self.assertEqual(len(all_jobs_res.json()["image_jobs"]), 1)

        # Cancel image job
        cancel_res = self.client.post(f"/api/image-jobs/{created['id']}/cancel", headers={"X-CSRF-Token": self.token})
        self.assertEqual(cancel_res.status_code, 200)

        # Check canceled status
        list_res = self.client.get("/api/image-jobs")
        self.assertEqual(list_res.json()["image_jobs"][0]["status"], "canceled")

        # Delete image job
        del_res = self.client.delete(f"/api/image-jobs/{created['id']}", headers={"X-CSRF-Token": self.token})
        self.assertEqual(del_res.status_code, 200)
        list_res = self.client.get("/api/image-jobs")
        self.assertEqual(len(list_res.json()["image_jobs"]), 0)

    def test_create_image_job_with_reference_image(self):
        # Create a small dummy PNG in memory
        img_buffer = io.BytesIO()
        img = Image.new("RGB", (64, 64), color="blue")
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        files = [
            ("reference_images", ("test_ref.png", img_buffer, "image/png"))
        ]
        data = {
            "prompt": "Style transfer test with reference image",
            "aspect_ratio": "1:1",
            "steps": "15",
            "cfg": "4.0",
        }
        res = self.client.post(
            "/api/image-jobs",
            data=data,
            files=files,
            headers={"X-CSRF-Token": self.token},
        )
        self.assertEqual(res.status_code, 200, res.text)
        job = res.json()
        self.assertEqual(len(job["reference_images"]), 1)
        self.assertTrue(job["reference_images"][0].startswith("upload_"))

    def test_image_job_timing_and_metrics(self):
        job = db_module.create_image_job(
            prompt="Test timer and ETA",
            aspect_ratio="1:1",
            steps=20,
        )
        job_id = job["id"]
        # Update with started_at and initial eta_seconds
        db_module.update_image_job(
            job_id,
            status="starting",
            started_at="2026-09-22T00:00:00+00:00",
            eta_seconds=110.5,
        )
        fetched = db_module.get_image_job(job_id)
        self.assertEqual(fetched["status"], "starting")
        self.assertEqual(fetched["eta_seconds"], 110.5)

        # Update with progress and dynamic eta
        db_module.update_image_job(
            job_id,
            status="running",
            progress=0.5,
            step=10,
            total_steps=20,
            eta_seconds=55.2,
        )
        fetched = db_module.get_image_job(job_id)
        self.assertEqual(fetched["progress"], 0.5)
        self.assertEqual(fetched["step"], 10)
        self.assertEqual(fetched["eta_seconds"], 55.2)

        # Complete with metrics
        db_module.update_image_job(
            job_id,
            status="completed",
            progress=1.0,
            eta_seconds=0,
            finished_at="2026-09-22T00:01:45+00:00",
            metrics={"generation_seconds": 105.0},
        )
        fetched = db_module.get_image_job(job_id)
        self.assertEqual(fetched["status"], "completed")
        self.assertEqual(fetched["eta_seconds"], 0)
        self.assertEqual(fetched["metrics"]["generation_seconds"], 105.0)
        self.assertEqual(fetched["generation_seconds"], 105.0)


if __name__ == "__main__":
    unittest.main()
