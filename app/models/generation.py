# Generation model
"""
SQLAlchemy model for AI generation results and processing history.
Tracks generation requests, outputs, and quality metrics.
"""

from typing import Optional, List
from enum import Enum
from sqlalchemy import String, Text, JSON, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import BaseModel


if TYPE_CHECKING:
    from .project import Project
    from .user import User


class Generation(BaseModel):
    """AI generation model"""
    
    __tablename__ = "generations"
    
    # References
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Generation details
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # AI pipeline results
    extracted_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_files: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # file_path -> content
    review_feedback: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    documentation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Quality metrics
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default="processing", nullable=False)  # processing, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Processing times (in seconds)
    schema_extraction_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    code_generation_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    docs_generation_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Iteration tracking
    is_iteration: Mapped[bool] = mapped_column(default=False, nullable=False)
    parent_generation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("generations.id"), nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="generations")
    user: Mapped["User"] = relationship("User", back_populates="generations")
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact", back_populates="generation", cascade="all, delete-orphan"
    )
    parent_generation: Mapped[Optional["Generation"]] = relationship(
        "Generation", foreign_keys=[parent_generation_id], remote_side="Generation.id"
    )
    
    def __repr__(self) -> str:
        return f"<Generation(id={self.id}, status={self.status}, project={self.project_id})>"
    
    def is_completed(self) -> bool:
        """Check if generation is completed"""
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        """Check if generation failed"""
        return self.status == "failed"


class GenerationStatus(str, Enum):
    """Enum for generation status values used across API and models."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Artifact(BaseModel):
    """Artifact model for storing generation outputs"""
    
    __tablename__ = "artifacts"
    
    # References
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("generations.id"), nullable=False)
    
    # Artifact details
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # zip, openapi, diff, github_pr
    storage_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # PR URL, download count, etc.
    
    # Relationships
    generation: Mapped["Generation"] = relationship("Generation", back_populates="artifacts")
    
    def __repr__(self) -> str:
        return f"<Artifact(id={self.id}, type={self.type}, generation={self.generation_id})>"
