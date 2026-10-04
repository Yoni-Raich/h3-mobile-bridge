import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import backend.db as db_module
from backend.db import connect, now_iso
from backend.worker import QueueWorker, describe_exception, prompt_is_active


class WorkerSequenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="h3-worker-test-")
        self.path = Path(self.temp.name) / "jobs.sqlite3"
        self.original_path = db_module.DB_PATH
        db_module.DB_PATH = self.path
        db_module.init_db()

    async def asyncTearDown(self):
        db_module.DB_PATH = self.original_path
        self.temp.cleanup()

    async def test_final_mp4_assembly_cannot_be_canceled_mid_write(self):
        sequence_id = "assembling-sequence"
        now = now_iso()
        with connect() as db:
            db.execute(
                """INSERT INTO sequences
                   (id,kind,title,status,position,progress,phase,current_item,
                    total_items,created_at,updated_at,started_at)
                   VALUES(?,'connected','test','verifying',1,0.99,'assembling',2,2,?,?,?)""",
                (sequence_id, now, now, now),
            )

        worker = QueueWorker()
        worker.current_sequence = sequence_id
        self.assertFalse(await worker.cancel_sequence(sequence_id))

        with connect() as db:
            row = db.execute(
                "SELECT status,phase FROM sequences WHERE id=?", (sequence_id,)
            ).fetchone()
        self.assertEqual(tuple(row), ("verifying", "assembling"))

    async def test_transient_history_failure_keeps_active_prompt_alive(self):
        worker = QueueWorker()
        worker.comfy.history = AsyncMock(side_effect=TimeoutError())
        worker.comfy.queue = AsyncMock(return_value={
            "queue_running": [[1, "active-prompt", {}, {}, []]],
            "queue_pending": [],
        })

        history, error, active = await worker._poll_history("active-prompt")

        self.assertIsNone(history)
        self.assertEqual(error, "TimeoutError")
        self.assertTrue(active)

    async def test_history_and_queue_failures_keep_descriptive_error(self):
        worker = QueueWorker()
        worker.comfy.history = AsyncMock(side_effect=TimeoutError())
        worker.comfy.queue = AsyncMock(side_effect=ConnectionError("offline"))

        history, error, active = await worker._poll_history("missing-prompt")

        self.assertIsNone(history)
        self.assertEqual(error, "TimeoutError; queue check failed: ConnectionError: offline")
        self.assertFalse(active)

    async def test_late_comfy_event_cannot_reopen_completed_job(self):
        worker = QueueWorker()
        completion_seen = asyncio.Event()
        states = []
        prompt_id = "completed-prompt"
        job = {
            "id": "late-event-job", "prompt": "test prompt", "mode": "text", "duration": 0.5,
            "engine": "turbo", "turbo_profile": "v1", "encoder": "native",
            "steps": 4, "width": 512, "height": 288, "megapixels": 0.15,
            "aspect_ratio": "16:9", "seed": 7, "no_audio": False,
        }

        async def monitor(_client_id, on_message, ready, stop):
            ready.set()
            await completion_seen.wait()
            await on_message({
                "type": "executing",
                "data": {"prompt_id": prompt_id, "node": "92"},
            })
            await stop.wait()

        def record_state(_job_id, **values):
            states.append(values)
            if values.get("status") == "completed":
                completion_seen.set()

        worker.comfy.ensure_started = AsyncMock()
        worker.comfy.object_info = AsyncMock(return_value={
            "UNETLoader": {}, "VAELoader": {}, "MiniMaxH3ImageToVideo": {},
            "CreateVideo": {}, "SaveVideo": {}, "ResolutionSelector": {},
            "ComfyMathExpression": {}, "CLIPLoader": {},
            "MiniMaxH3TurboLoRA": {}, "MiniMaxH3TurboSampler": {},
            "MiniMaxH3SigmaShift": {},
        })
        worker.comfy.submit = AsyncMock(return_value=prompt_id)
        worker.comfy.history = AsyncMock(return_value={
            "status": {"status_str": "success", "completed": True, "messages": []},
        })
        worker.comfy.monitor_progress = monitor
        worker._wait_for_stable_video = AsyncMock(return_value=Path("result.mp4"))

        with patch("backend.worker.historical_generation_seconds", return_value=None), \
             patch("backend.worker.turbo_workflow", return_value={}), \
             patch("backend.worker.media_probe", return_value={"streams": []}), \
             patch("backend.worker.finalize_completed_asset", return_value=None), \
             patch("backend.worker.update_job", side_effect=record_state):
            await worker.run_job(job)

        completion_index = next(
            index for index, state in enumerate(states)
            if state.get("status") == "completed"
        )
        self.assertEqual(states[-1]["status"], "completed")
        self.assertNotIn(
            "running",
            [state.get("status") for state in states[completion_index + 1:]],
        )

    def test_queue_parser_checks_running_and_pending_prompts(self):
        queue = {
            "queue_running": [[1, "running-prompt"]],
            "queue_pending": [[2, "pending-prompt"]],
        }
        self.assertTrue(prompt_is_active(queue, "running-prompt"))
        self.assertTrue(prompt_is_active(queue, "pending-prompt"))
        self.assertFalse(prompt_is_active(queue, "other-prompt"))

    def test_empty_exception_message_keeps_exception_type(self):
        self.assertEqual(describe_exception(TimeoutError()), "TimeoutError")


if __name__ == "__main__":
    unittest.main()
