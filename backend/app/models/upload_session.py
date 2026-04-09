import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class UploadSessionStatus(str, enum.Enum):
    initiated = "initiated"
    uploading = "uploading"
    completing = "completing"
    completed = "completed"
    aborted = "aborted"
    failed = "failed"


class ChunkStatus(str, enum.Enum):
    pending = "pending"
    uploaded = "uploaded"
    failed = "failed"


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
    uploader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    oss_upload_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    oss_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    total_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chunk_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[UploadSessionStatus] = mapped_column(
        Enum(UploadSessionStatus), nullable=False, default=UploadSessionStatus.initiated
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    video = relationship("Video", back_populates="upload_sessions", lazy="noload")
    chunks = relationship(
        "UploadChunk", back_populates="session", cascade="all, delete-orphan", lazy="noload"
    )


class UploadChunk(Base):
    __tablename__ = "upload_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("upload_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-indexed (OSS requirement)
    etag: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[ChunkStatus] = mapped_column(Enum(ChunkStatus), nullable=False, default=ChunkStatus.pending)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session = relationship("UploadSession", back_populates="chunks", lazy="noload")

    __table_args__ = (UniqueConstraint("session_id", "chunk_number", name="uq_session_chunk"),)
