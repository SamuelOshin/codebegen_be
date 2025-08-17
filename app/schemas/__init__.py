"""
Schema exports for the application.
"""

from app.schemas.user import UserCreate, UserResponse, UserUpdate, Token, TokenData
from app.schemas.base import BaseResponse, ErrorResponse

# For backward compatibility
User = UserResponse

__all__ = [
    "UserCreate",
    "UserResponse", 
    "UserUpdate",
    "Token",
    "TokenData",
    "User",  # Alias for UserResponse
    "BaseResponse",
    "ErrorResponse"
]