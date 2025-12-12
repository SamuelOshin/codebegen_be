# Preview models for MVP implementation
"""
SQLAlchemy models for preview instances and their logs.
Handles database persistence for running preview sessions.
"""

from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, JSON, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timedelta, timezone

from app.models.base import BaseModel


class PreviewInstance(BaseModel):
    """Represents a running preview instance of generated code."""

    __tablename__ = "preview_instances"

    # Identifiers
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("generations.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    # Runtime Information
    status: Mapped[str] = mapped_column(String(20), default="launching", nullable=False)  # launching, running, failed, stopped
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 3001-3100
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # http://localhost:3001
    process_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # OS process ID

    # Lifecycle
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow() + timedelta(hours=1),
        nullable=False
    )

    # Authentication
    preview_token: Mapped[str] = mapped_column(String(100), nullable=False)  # One-time token for this session
    token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow() + timedelta(hours=1),
        nullable=False
    )

    # Health & Diagnostics
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)  # unknown, healthy, unhealthy
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Configuration (MVP = simple)
    temp_directory: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Path to temp project files
    log_level: Mapped[str] = mapped_column(String(10), default="ERROR", nullable=False)  # ERROR, WARN, INFO

    # Relationships
    generation = relationship("Generation", back_populates="preview_instances")
    user = relationship("User")
    project = relationship("Project")
    logs = relationship("PreviewLog", back_populates="preview", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PreviewInstance(id={self.id}, status={self.status}, port={self.port})>"

    def is_running(self) -> bool:
        """Check if preview instance is currently running."""
        return self.status == "running"

    def is_expired(self) -> bool:
        """Check if preview instance has expired."""
        # Use timezone-aware datetime for comparison with timezone-aware expires_at
        return datetime.now(timezone.utc) > self.expires_at

    def get_uptime_seconds(self) -> Optional[float]:
        """Get uptime in seconds if instance is running."""
        if self.started_at and self.is_running():
            return (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return None


class PreviewLog(BaseModel):
    """Lightweight log entries from preview instances."""

    __tablename__ = "preview_logs"

    preview_instance_id: Mapped[str] = mapped_column(String(36), ForeignKey("preview_instances.id"), nullable=False)

    # Log Entry
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False)  # ERROR, WARN, INFO, DEBUG
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    preview = relationship("PreviewInstance", back_populates="logs")

    def __repr__(self) -> str:
        return f"<PreviewLog(preview_id={self.preview_instance_id}, level={self.level}, message={self.message[:50]}...)>"

    @classmethod
    def create_error_log(cls, preview_instance_id: str, message: str) -> "PreviewLog":
        """Create an error log entry."""
        return cls(
            preview_instance_id=preview_instance_id,
            level="ERROR",
            message=message
        )

    @classmethod
    def create_info_log(cls, preview_instance_id: str, message: str) -> "PreviewLog":
        """Create an info log entry."""
        return cls(
            preview_instance_id=preview_instance_id,
            level="INFO",
            message=message
        )