# Project model
"""
SQLAlchemy model for storing user projects and metadata.
Tracks project details, generation history, and settings.
"""

from typing import Optional, List
from sqlalchemy import String, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


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
    
    # GitHub integration
    github_repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_repo_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Settings
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="projects")
    generations: Mapped[List["Generation"]] = relationship(
        "Generation", back_populates="project", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Project(name={self.name}, user={self.user_id}, status={self.status})>"
    
    def get_latest_generation(self) -> Optional["Generation"]:
        """Get the most recent generation for this project"""
        if self.generations:
            return max(self.generations, key=lambda g: g.created_at)
        return None
    
    def is_active(self) -> bool:
        """Check if project is active"""
        return self.status == "active"