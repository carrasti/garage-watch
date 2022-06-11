import asyncio
import aiofile
import aiohttp
from datetime import datetime
import logging

from config import settings

_logger = logging.getLogger("garagewatch.snapshot")


async def save_snapshot_to_disk(data, filename):
    async with aiofile.async_open(filename, "wb") as f:
        await f.write(data)
        _logger.info("Saved snapshot %s", filename)


async def upload_snapshot(data):
    _logger.info("Upload scheduled")


async def get_snapshot(base_url):
    async with aiohttp.ClientSession() as session:
        timestamp_filename = datetime.now().strftime("%Y%m%d%H%M%S")
        _logger.info("Taking snapshot %s", timestamp_filename)
        url = f"{base_url}snapshot"
        _logger.info(url)
        async with session.get(url) as resp:
            if resp.status == 200:
                filename = (
                    f"{settings.SNAPSHOT_DIRECTORY}/snapshot_{timestamp_filename}.jpg"
                )
                data = await resp.read()
                asyncio.ensure_future(save_snapshot_to_disk(data, filename))
                asyncio.ensure_future(upload_snapshot(data))
