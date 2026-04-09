import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class VideoStatus(str, enum.Enum):
    uploading = "uploading"   # chunks still being received
    processing = "processing" # upload complete, post-processing (thumbnail etc)
    ready = "ready"           # available to viewers
    failed = "failed"         # upload or processing failed
    deleted = "deleted"       # soft-deleted


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    oss_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[VideoStatus] = mapped_column(Enum(VideoStatus), nullable=False, default=VideoStatus.uploading)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    uploader = relationship("User", back_populates="videos", lazy="selectin")
    upload_sessions = relationship("UploadSession", back_populates="video", lazy="noload")
