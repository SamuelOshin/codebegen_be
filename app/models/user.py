# User model
"""
SQLAlchemy model for user accounts and profiles.
Handles authentication, preferences, and user data.
"""

from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


if TYPE_CHECKING:
    from .project import Project
    from .generation import Generation


class User(BaseModel):
    """User account model"""
    
    __tablename__ = "users"
    
    # Basic info
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Authentication
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Profile
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # GitHub integration
    github_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True)
    github_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    github_access_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Preferences
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Usage tracking
    total_generations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships (forward references to avoid circular imports)
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="user", cascade="all, delete-orphan"
    )
    generations: Mapped[List["Generation"]] = relationship(
        "Generation", back_populates="user", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(email={self.email}, username={self.username})>"
    
    def increment_generations(self) -> None:
        """Increment the total generations counter"""
        self.total_generations += 1
