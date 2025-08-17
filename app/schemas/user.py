"""
User Pydantic schemas for request/response models.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Shared user properties"""
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserUpdate(BaseModel):
    """User update schema"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    """User response schema"""
    id: str
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    total_generations: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class User(BaseModel):
    """Minimal user schema used in tests and lightweight contexts.

    Includes the fields referenced by tests while keeping additional fields optional
    to avoid requiring database-backed timestamps during construction.
    """
    id: str
    email: EmailStr
    username: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    total_generations: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserGitHubAuth(BaseModel):
    """GitHub authentication data"""
    github_id: int
    github_username: str
    github_access_token: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """JWT token payload data"""
    user_id: Optional[str] = None

