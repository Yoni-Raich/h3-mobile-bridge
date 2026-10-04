import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import system_status as status


class HardwareStatusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        status._sample = {}
        status._sampled_at = 0
        status._lock = asyncio.Lock()

    async def test_concurrent_requests_share_one_hardware_sample(self):
        with patch.object(status, 'gpu_sample', return_value={'vram_total_mib': 8188}) as gpu:
            results = await asyncio.gather(*(status.system_status() for _ in range(5)))
        self.assertEqual(gpu.call_count, 1)
        self.assertTrue(all(result['available'] for result in results))
        self.assertTrue(all(result['disk_free_gib'] > 0 for result in results))

    async def test_unavailable_gpu_is_not_reported_as_zero_usage(self):
        with patch.object(status, 'gpu_sample', return_value={}):
            sample = await status.system_status()
        self.assertFalse(sample['available'])
        self.assertNotIn('vram_used_mib', sample)

    async def test_disk_is_reported_before_models_folder_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'not-installed' / 'models'
            with patch.object(status, 'MODELS', missing), patch.object(status, 'gpu_sample', return_value={}):
                sample = await status.system_status()
        self.assertGreater(sample['disk_free_gib'], 0)
        self.assertFalse(sample['available'])
