"""
Chunked upload endpoints.

Chunk data is received as raw bytes (Content-Type: application/octet-stream)
rather than multipart/form-data to avoid the overhead of multipart parsing for
potentially large binary payloads.
"""
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_uploader
from app.models.upload_session import ChunkStatus, UploadChunk, UploadSession, UploadSessionStatus
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.schemas.upload import (
    ChunkUploadResponse,
    CompleteUploadResponse,
    InitUploadRequest,
    InitUploadResponse,
)
from app.services import oss_service

router = APIRouter(prefix="/videos/upload", tags=["upload"])
settings = get_settings()


def _compute_chunk_size(file_size: int, requested: int | None) -> int:
    """Pick a chunk size that keeps total parts ≤ MAX_PARTS."""
    min_size = math.ceil(file_size / settings.MAX_PARTS)
    default = max(settings.DEFAULT_CHUNK_SIZE_BYTES, min_size)
    if requested is None:
        return default
    # Clamp to [min_size, MAX_CHUNK_SIZE_BYTES]
    return max(min_size, min(requested, settings.MAX_CHUNK_SIZE_BYTES))


@router.post("/init", response_model=InitUploadResponse, status_code=status.HTTP_201_CREATED)
async def init_upload(
    payload: InitUploadRequest,
    current_user: Annotated[User, Depends(require_uploader)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    chunk_size = _compute_chunk_size(payload.file_size, payload.chunk_size)
    total_chunks = math.ceil(payload.file_size / chunk_size)

    ext = os.path.splitext(payload.filename)[1].lower()
    oss_key = f"videos/{current_user.id}/{os.urandom(8).hex()}{ext}"

    # Initiate OSS multipart upload
    oss_upload_id = await oss_service.init_multipart_upload(oss_key)

    video = Video(
        title=payload.title,
        description=payload.description,
        uploader_id=current_user.id,
        file_size=payload.file_size,
        oss_key=oss_key,
        content_type=payload.content_type,
        status=VideoStatus.uploading,
    )
    db.add(video)
    await db.flush()

    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.UPLOAD_SESSION_TTL_HOURS)
    session = UploadSession(
        video_id=video.id,
        uploader_id=current_user.id,
        oss_upload_id=oss_upload_id,
        oss_key=oss_key,
        total_size=payload.file_size,
        chunk_size=chunk_size,
        total_chunks=total_chunks,
        status=UploadSessionStatus.initiated,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()

    chunks = [
        UploadChunk(
            session_id=session.id,
            chunk_number=i + 1,
            size=min(chunk_size, payload.file_size - i * chunk_size),
            status=ChunkStatus.pending,
        )
        for i in range(total_chunks)
    ]
    db.add_all(chunks)
    await db.commit()

    return InitUploadResponse(
        session_id=session.id,
        video_id=video.id,
        oss_key=oss_key,
        chunk_size=chunk_size,
        total_chunks=total_chunks,
        uploaded_chunks=[],
    )


@router.put("/{session_id}/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    session_id: UUID,
    request: Request,
    chunk_number: Annotated[int, Query(ge=1)],
    current_user: Annotated[User, Depends(require_uploader)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = await db.get(UploadSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if str(session.uploader_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your upload session")
    if session.status not in (UploadSessionStatus.initiated, UploadSessionStatus.uploading):
        raise HTTPException(status_code=409, detail=f"Session is {session.status.value}")
    if chunk_number > session.total_chunks:
        raise HTTPException(status_code=400, detail="chunk_number exceeds total_chunks")

    # Fetch the chunk record
    result = await db.execute(
        select(UploadChunk).where(
            UploadChunk.session_id == session_id,
            UploadChunk.chunk_number == chunk_number,
        )
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk record not found")

    # If already uploaded, skip re-upload (idempotent)
    if chunk.status == ChunkStatus.uploaded:
        pass
    else:
        data = await request.body()
        if not data:
            raise HTTPException(status_code=400, detail="Empty chunk body")

        etag = await oss_service.upload_part(
            session.oss_key, session.oss_upload_id, chunk_number, data
        )
        chunk.etag = etag
        chunk.status = ChunkStatus.uploaded
        chunk.uploaded_at = datetime.now(timezone.utc)

        if session.status == UploadSessionStatus.initiated:
            session.status = UploadSessionStatus.uploading

        await db.commit()

    # Count uploaded chunks for progress
    count_result = await db.execute(
        select(func.count()).where(
            UploadChunk.session_id == session_id,
            UploadChunk.status == ChunkStatus.uploaded,
        )
    )
    uploaded_count = count_result.scalar()
    progress = round(uploaded_count / session.total_chunks * 100, 2)

    return ChunkUploadResponse(
        chunk_number=chunk_number,
        uploaded_chunks=uploaded_count,
        total_chunks=session.total_chunks,
        progress=progress,
    )


@router.post("/{session_id}/complete", response_model=CompleteUploadResponse)
async def complete_upload(
    session_id: UUID,
    current_user: Annotated[User, Depends(require_uploader)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = await db.get(UploadSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if str(session.uploader_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your upload session")
    if session.status == UploadSessionStatus.completed:
        return CompleteUploadResponse(
            video_id=session.video_id, status="completed", message="Already completed"
        )
    if session.status not in (UploadSessionStatus.initiated, UploadSessionStatus.uploading):
        raise HTTPException(status_code=409, detail=f"Session is {session.status.value}")

    # Verify all chunks are uploaded
    chunks_result = await db.execute(
        select(UploadChunk)
        .where(UploadChunk.session_id == session_id)
        .order_by(UploadChunk.chunk_number)
    )
    chunks = chunks_result.scalars().all()

    missing = [c.chunk_number for c in chunks if c.status != ChunkStatus.uploaded]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Chunks not yet uploaded: {missing[:10]}{'...' if len(missing) > 10 else ''}",
        )

    parts = [{"part_number": c.chunk_number, "etag": c.etag} for c in chunks]

    session.status = UploadSessionStatus.completing
    await db.commit()

    try:
        await oss_service.complete_multipart_upload(session.oss_key, session.oss_upload_id, parts)
    except Exception as exc:
        session.status = UploadSessionStatus.failed
        await db.commit()
        raise HTTPException(status_code=502, detail=f"OSS complete failed: {exc}") from exc

    # Update session and video status
    session.status = UploadSessionStatus.completed
    video = await db.get(Video, session.video_id)
    video.status = VideoStatus.processing  # would trigger background transcoding/thumbnail

    # Increment user storage counter
    user = await db.get(User, current_user.id)
    user.storage_used += video.file_size

    await db.commit()

    return CompleteUploadResponse(
        video_id=video.id,
        status="processing",
        message="Upload complete. Video is being processed.",
    )


@router.delete("/{session_id}/abort", status_code=status.HTTP_204_NO_CONTENT)
async def abort_upload(
    session_id: UUID,
    current_user: Annotated[User, Depends(require_uploader)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = await db.get(UploadSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if str(session.uploader_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your upload session")
    if session.status in (UploadSessionStatus.completed, UploadSessionStatus.aborted):
        return None

    await oss_service.abort_multipart_upload(session.oss_key, session.oss_upload_id)

    session.status = UploadSessionStatus.aborted
    video = await db.get(Video, session.video_id)
    video.status = VideoStatus.failed
    await db.commit()

    return None
