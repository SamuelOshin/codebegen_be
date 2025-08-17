# Organization model
"""
SQLAlchemy model for organizations and team management.
Handles team collaboration, billing, and shared resources.
"""

from typing import Optional, List
from sqlalchemy import String, Boolean, Text, JSON, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Organization(BaseModel):
    """Organization model for team collaboration"""
    
    __tablename__ = "organizations"
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Owner
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_projects: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # Billing
    subscription_plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Preferences
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="organization", cascade="all, delete-orphan"
    )
    memberships: Mapped[List["OrganizationMember"]] = relationship(
        "OrganizationMember", back_populates="organization", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Organization(name={self.name}, slug={self.slug})>"


class OrganizationMember(BaseModel):
    """Organization membership model"""
    
    __tablename__ = "organization_members"
    
    # References
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Role and permissions
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)  # owner, admin, member
    permissions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    invited_by_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    invited_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[invited_by_id])
    
    def __repr__(self) -> str:
        return f"<OrganizationMember(org={self.organization_id}, user={self.user_id}, role={self.role})>"
