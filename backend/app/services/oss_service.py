"""
All Alibaba Cloud OSS operations.

oss2 is a synchronous library; every call is offloaded to a thread pool
so it doesn't block the FastAPI event loop.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import oss2

from app.config import get_settings

settings = get_settings()

# Dedicated thread pool for OSS I/O — keeps the default event-loop executor free
_oss_executor = ThreadPoolExecutor(max_workers=32, thread_name_prefix="oss")


def _make_bucket() -> oss2.Bucket:
    endpoint = settings.OSS_INTERNAL_ENDPOINT or settings.OSS_ENDPOINT
    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, endpoint, settings.OSS_BUCKET_NAME)


# Singleton bucket instance — oss2.Bucket is thread-safe for concurrent calls
_bucket: oss2.Bucket | None = None


def get_bucket() -> oss2.Bucket:
    global _bucket
    if _bucket is None:
        _bucket = _make_bucket()
    return _bucket


async def _run(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_oss_executor, partial(func, *args, **kwargs))


async def init_multipart_upload(key: str) -> str:
    """Initiate a multipart upload and return the OSS upload_id."""
    result = await _run(get_bucket().init_multipart_upload, key)
    return result.upload_id


async def upload_part(key: str, upload_id: str, part_number: int, data: bytes) -> str:
    """Upload one part; returns the ETag (with surrounding quotes)."""
    result = await _run(get_bucket().upload_part, key, upload_id, part_number, data)
    return result.etag


async def complete_multipart_upload(key: str, upload_id: str, parts: list[dict]) -> None:
    """
    Complete the multipart upload.
    `parts` must be sorted by part_number ascending.
    Each dict: {"part_number": int, "etag": str}
    """
    part_infos = [oss2.models.PartInfo(p["part_number"], p["etag"]) for p in parts]
    await _run(get_bucket().complete_multipart_upload, key, upload_id, part_infos)


async def abort_multipart_upload(key: str, upload_id: str) -> None:
    try:
        await _run(get_bucket().abort_multipart_upload, key, upload_id)
    except oss2.exceptions.NoSuchUpload:
        pass  # already aborted or never existed; ignore


async def delete_object(key: str) -> None:
    try:
        await _run(get_bucket().delete_object, key)
    except oss2.exceptions.NoSuchKey:
        pass


async def generate_presigned_url(key: str, expires: int = 3600) -> str:
    """Return a presigned GET URL valid for `expires` seconds."""
    url = await _run(get_bucket().sign_url, "GET", key, expires)
    return url
