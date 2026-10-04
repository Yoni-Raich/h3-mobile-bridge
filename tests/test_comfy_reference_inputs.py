import copy
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.comfy_inputs import prepare_comfy_inputs
from backend.comfy import ComfyClient


class ComfyReferenceInputsTests(unittest.TestCase):
    def test_all_reference_groups_are_sent_as_dynamic_sockets(self):
        graph = {"136": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {
            "prompt": "Keep <Picture 1> and <Audio 1> exactly.",
            "ref_images": {"ref_image_0": ["130", 0], "ref_image_2": ["131", 0]},
            "ref_videos": {"ref_video_0": ["132", 0]},
            "ref_video_audios": {"ref_video_audio_0": ["133", 0]},
            "ref_audios": {"ref_audio_0": ["134", 0]},
        }}}
        original = copy.deepcopy(graph)
        inputs = prepare_comfy_inputs(graph)["136"]["inputs"]
        self.assertEqual(inputs, {
            "prompt": original["136"]["inputs"]["prompt"],
            "ref_images.ref_image_0": ["130", 0],
            "ref_images.ref_image_2": ["131", 0],
            "ref_videos.ref_video_0": ["132", 0],
            "ref_video_audios.ref_video_audio_0": ["133", 0],
            "ref_audios.ref_audio_0": ["134", 0],
        })
        self.assertEqual(graph, original)
        self.assertEqual(prepare_comfy_inputs(prepare_comfy_inputs(graph)), prepare_comfy_inputs(graph))

    def test_conflicting_links_fail_before_a_reference_is_lost(self):
        graph = {"136": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {
            "ref_images": {"ref_image_0": ["130", 0]},
            "ref_images.ref_image_0": ["131", 0],
        }}}
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            prepare_comfy_inputs(graph)

    def test_other_node_inputs_are_preserved(self):
        graph = {"1": {"class_type": "OtherNode", "inputs": {"ref_images": {"x": ["2", 0]}}}}
        self.assertEqual(prepare_comfy_inputs(graph), graph)


class ComfyReferenceSubmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_submit_posts_reference_links_in_the_resolved_wire_format(self):
        graph = {"136": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {
            "ref_images": {"ref_image_0": ["130", 0]},
            "ref_audios": {"ref_audio_0": ["180", 0]},
        }}}
        original = copy.deepcopy(graph)
        response = MagicMock(status_code=200)
        response.json.return_value = {"prompt_id": "accepted-reference", "node_errors": {}}
        client = AsyncMock()
        client.post.return_value = response
        with patch("backend.comfy.httpx.AsyncClient") as factory:
            factory.return_value.__aenter__.return_value = client
            prompt_id = await ComfyClient().submit(graph, "test-client")
        sent = client.post.call_args.kwargs["json"]
        self.assertEqual(prompt_id, "accepted-reference")
        self.assertEqual(sent["client_id"], "test-client")
        self.assertEqual(sent["prompt"]["136"]["inputs"], {
            "ref_images.ref_image_0": ["130", 0],
            "ref_audios.ref_audio_0": ["180", 0],
        })
        self.assertEqual(graph, original)


if __name__ == "__main__":
    unittest.main()
