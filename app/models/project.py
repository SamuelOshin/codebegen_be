# Project model
"""
SQLAlchemy model for storing user projects and metadata.
Tracks project details, generation history, and settings.
"""

from typing import Optional, List
from sqlalchemy import String, Text, JSON, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import BaseModel

if TYPE_CHECKING:
    from .generation import Generation
    from .user import User
    from .organization import Organization


class Project(BaseModel):
    """Project model for user projects"""
    
    __tablename__ = "projects"
    
    # References
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Project configuration
    domain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ecommerce, social_media, etc.
    tech_stack: Mapped[str] = mapped_column(String(50), nullable=False)  # fastapi_postgres, etc.
    constraints: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)  # ["dockerized", "tested"]
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)  # draft, active, archived
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Auto-creation tracking
    auto_created: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creation_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # homepage_generation, api_call, etc.
    original_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Store original prompt for auto-created projects
    
    # GitHub integration
    github_repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_repo_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Settings
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Version tracking (new architecture)
    active_generation_id: Mapped[Optional[str]] = mapped_column(
        String(36), 
        ForeignKey("generations.id"), 
        nullable=True
    )
    latest_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="projects")
    generations: Mapped[List["Generation"]] = relationship(
        "Generation", 
        back_populates="project", 
        cascade="all, delete-orphan",
        foreign_keys="Generation.project_id"
    )
    active_generation: Mapped[Optional["Generation"]] = relationship(
        "Generation",
        foreign_keys=[active_generation_id],
        post_update=True
    )
    
    def __repr__(self) -> str:
        return f"<Project(name={self.name}, user={self.user_id}, status={self.status})>"
    
    def get_latest_generation(self) -> Optional["Generation"]:
        """Get the most recent generation for this project"""
        if self.generations:
            return max(self.generations, key=lambda g: g.created_at)
        return None
    
    def get_generation_by_version(self, version: int) -> Optional["Generation"]:
        """Get specific version of generation"""
        return next(
            (g for g in self.generations if g.version == version),
            None
        )
    
    def set_active_generation(self, generation_id: str):
        """Mark a generation as active, unmark others"""
        for gen in self.generations:
            gen.is_active = (gen.id == generation_id)
        self.active_generation_id = generation_id
    
    def is_active(self) -> bool:
        """Check if project is active"""
        return self.status == "active"