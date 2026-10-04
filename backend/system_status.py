"""Small cached local hardware samples for the studio."""
import asyncio
import shutil
import time

from .comfy import gpu_sample
from .config import MODELS

_sample: dict = {}
_sampled_at = 0.0
_lock = asyncio.Lock()


async def system_status() -> dict:
    global _sample, _sampled_at
    async with _lock:
        if time.monotonic() - _sampled_at >= 5:
            sample = await asyncio.to_thread(gpu_sample)
            # Hardware status must also work before models are installed.
            disk_path = next(path for path in (MODELS, *MODELS.parents) if path.exists())
            disk = await asyncio.to_thread(shutil.disk_usage, disk_path)
            _sample = {
                **sample,
                "available": bool(sample),
                "disk_free_gib": round(disk.free / 1024 ** 3, 1),
            }
            _sampled_at = time.monotonic()
        return {**_sample, "sample_age_seconds": round(time.monotonic() - _sampled_at, 1)}
