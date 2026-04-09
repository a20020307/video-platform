from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UploaderInfo(BaseModel):
    id: UUID
    email: str

    model_config = {"from_attributes": True}


class VideoResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    uploader: UploaderInfo
    file_size: int
    content_type: str
    status: str
    view_count: int
    created_at: datetime
    presigned_url: str | None = None  # populated when fetching single video

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    size: int
    pages: int
