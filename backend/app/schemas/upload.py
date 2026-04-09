from uuid import UUID

from pydantic import BaseModel, field_validator

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
ALLOWED_CONTENT_TYPES = {
    "video/mp4", "video/quicktime", "video/x-msvideo",
    "video/x-matroska", "video/webm",
}


class InitUploadRequest(BaseModel):
    title: str
    description: str | None = None
    filename: str
    file_size: int
    content_type: str
    chunk_size: int | None = None  # client can override; server enforces limits

    @field_validator("filename")
    @classmethod
    def filename_ext(cls, v: str) -> str:
        import os
        ext = os.path.splitext(v)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension '{ext}'. Allowed: {ALLOWED_EXTENSIONS}")
        return v

    @field_validator("content_type")
    @classmethod
    def content_type_valid(cls, v: str) -> str:
        if v not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"Unsupported content type '{v}'")
        return v

    @field_validator("file_size")
    @classmethod
    def size_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("file_size must be positive")
        return v


class InitUploadResponse(BaseModel):
    session_id: UUID
    video_id: UUID
    oss_key: str
    chunk_size: int
    total_chunks: int
    uploaded_chunks: list[int]  # already-uploaded chunk numbers (for resume)


class ChunkUploadResponse(BaseModel):
    chunk_number: int
    uploaded_chunks: int
    total_chunks: int
    progress: float  # 0.0 – 100.0


class CompleteUploadResponse(BaseModel):
    video_id: UUID
    status: str
    message: str
