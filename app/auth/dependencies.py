"""
Authentication dependencies for FastAPI endpoints.
Provides JWT token validation and user extraction.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import get_async_db
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.schemas.user import TokenData

# OAuth2 Password Bearer scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# HTTP Bearer token scheme (for direct API access)
security = HTTPBearer()

# Optional OAuth2 scheme that doesn't raise errors
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Extract and validate the current user from JWT token.
    
    Args:
        token: JWT token from OAuth2 scheme
        db: Database session
        
    Returns:
        User: The authenticated user
        
    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: Optional[str] = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Token missing user ID")
            
        token_data = TokenData(user_id=user_id)
        
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")
    
    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(token_data.user_id)
    
    if user is None:
        raise AuthenticationError("User not found")
        
    if not user.is_active:
        raise AuthenticationError("Inactive user")
        
    return user


async def get_current_user_bearer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Extract and validate the current user from Bearer token (direct API access).
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        User: The authenticated user
        
    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: Optional[str] = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Token missing user ID")
            
        token_data = TokenData(user_id=user_id)
        
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")
    
    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(token_data.user_id)
    
    if user is None:
        raise AuthenticationError("User not found")
        
    if not user.is_active:
        raise AuthenticationError("Inactive user")
        
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and ensure they are active.
    This is an alias for get_current_user but can be extended.
    """
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and ensure they are a superuser.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        User: The authenticated superuser
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


class RoleChecker:
    """
    Role-based access control checker.
    Can be used as a dependency to check user roles.
    """
    
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """
        Check if user has one of the allowed roles.
        
        Note: This is a placeholder - roles are not yet implemented in the User model.
        For now, we'll use is_superuser as admin role.
        """
        # TODO: Implement proper role system
        if "admin" in self.allowed_roles and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user


# Common role checkers
require_admin = RoleChecker(["admin"])


# Optional authentication dependency
async def get_current_user_optional(
    db: AsyncSession = Depends(get_async_db),
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[User]:
    """
    Get current user if token is provided, otherwise return None.
    Useful for endpoints that work both with and without authentication.
    """
    if not token:
        return None
        
    try:
        # Use the same logic as get_current_user
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: Optional[str] = payload.get("sub")
        
        if user_id is None:
            return None
            
        token_data = TokenData(user_id=user_id)
        
        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(token_data.user_id)
        
        if user is None or not user.is_active:
            return None
            
        return user
    except JWTError:
        return None

