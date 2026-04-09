from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.video import Video, VideoStatus
from app.schemas.video import VideoListResponse, VideoResponse, UploaderInfo
from app.services import oss_service

router = APIRouter(prefix="/videos", tags=["videos"])


def _video_to_schema(v: Video, presigned_url: str | None = None) -> VideoResponse:
    return VideoResponse(
        id=v.id,
        title=v.title,
        description=v.description,
        uploader=UploaderInfo(id=v.uploader.id, email=v.uploader.email),
        file_size=v.file_size,
        content_type=v.content_type,
        status=v.status.value,
        view_count=v.view_count,
        created_at=v.created_at,
        presigned_url=presigned_url,
    )


@router.get("", response_model=VideoListResponse)
async def list_videos(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    base_query = select(Video).where(Video.is_deleted.is_(False))

    # Uploaders only see their own videos; viewers and admins see all ready videos
    if current_user.role == UserRole.uploader:
        base_query = base_query.where(Video.uploader_id == current_user.id)
    elif current_user.role == UserRole.viewer:
        base_query = base_query.where(Video.status == VideoStatus.ready)

    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = total_result.scalar()

    result = await db.execute(
        base_query.order_by(Video.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    videos = result.scalars().all()

    return VideoListResponse(
        items=[_video_to_schema(v) for v in videos],
        total=total,
        page=page,
        size=size,
        pages=max(1, -(-total // size)),  # ceiling division
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.get(Video, video_id)
    if not video or video.is_deleted:
        raise HTTPException(status_code=404, detail="Video not found")

    # Viewers can only access ready videos
    if current_user.role == UserRole.viewer and video.status != VideoStatus.ready:
        raise HTTPException(status_code=404, detail="Video not found")

    # Uploaders can only access their own videos
    if current_user.role == UserRole.uploader and str(video.uploader_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your video")

    # Increment view count for viewers
    if current_user.role == UserRole.viewer:
        video.view_count += 1
        await db.commit()

    presigned_url = None
    if video.status == VideoStatus.ready:
        presigned_url = await oss_service.generate_presigned_url(video.oss_key, expires=3600)

    return _video_to_schema(video, presigned_url)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.get(Video, video_id)
    if not video or video.is_deleted:
        raise HTTPException(status_code=404, detail="Video not found")

    # Uploaders can only delete their own videos
    if current_user.role == UserRole.uploader and str(video.uploader_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your video")

    # Viewers cannot delete
    if current_user.role == UserRole.viewer:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Soft delete
    video.is_deleted = True
    video.deleted_at = datetime.now(timezone.utc)
    video.status = VideoStatus.deleted

    # Decrement storage counter
    uploader = await db.get(User, video.uploader_id)
    if uploader:
        uploader.storage_used = max(0, uploader.storage_used - video.file_size)

    await db.commit()
    return None
