import asyncio
import aiofile
import aiohttp
from datetime import datetime, timedelta
import logging
import jwt
from jwt.api_jwk import PyJWK
from aiopath import AsyncPath
from config import settings

_logger = logging.getLogger("garagewatch.snapshot")


jwk = None
if settings.SNAPSHOT_UPLOAD_JWK:
    jwk = PyJWK.from_json(settings.SNAPSHOT_UPLOAD_JWK)


async def save_snapshot_to_disk(data, filename):
    async with aiofile.async_open(filename, "wb") as f:
        await f.write(data)
        _logger.info("Saved snapshot %s", filename)


async def upload_snapshot(data):
    """
    Upload the file on the given path to the server
    via HTTP post

    Uses class configuration to determine the url and key to sign
    Authorization Bearer token with JWT
    """
    _logger.info("Uploading to server")
    if not settings.SNAPSHOT_UPLOAD_URL or not jwk:
        return

    encoded_jwt = jwt.encode(
        {
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=300),
        },
        key=jwk.key,
        algorithm="EdDSA",
        headers={
            "kid": jwk.key_id,
        },
    )

    auth_header = f"Bearer {encoded_jwt}"
    async with aiohttp.ClientSession() as session:
        formdata = aiohttp.FormData()
        formdata.add_field(
            "file",
            data,
            content_type="image/jpeg",
        )

        async with session.post(
            settings.SNAPSHOT_UPLOAD_URL,
            data=formdata,
            headers={
                "Authorization": auth_header,
            },
        ) as response:
            if not response.status != 200:
                _logger.error(
                    "Error uploading snapshot. Status code %s", response.status
                )
            else:
                _logger.info("Upload done!")


async def get_snapshot(base_url):
    async with aiohttp.ClientSession() as session:
        now = datetime.now()
        snapshot_directory = now.strftime("%Y/%m/%d/")
        full_snapshot_directory = f"{settings.SNAPSHOT_DIRECTORY}/{snapshot_directory}"
        path = AsyncPath(full_snapshot_directory)
        await path.mkdir(parents=True, exist_ok=True)
        filename = full_snapshot_directory + now.strftime("%H%M%S.jpg")
        _logger.info("Taking snapshot %s", filename)
        url = f"{base_url}snapshot"
        _logger.info(url)
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                asyncio.ensure_future(save_snapshot_to_disk(data, filename))
                asyncio.ensure_future(upload_snapshot(data))
