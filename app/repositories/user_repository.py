# User repository
"""
User data access operations.
Handles user queries, authentication lookups, and profile management.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """User repository with authentication-specific methods"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_github_id(self, github_id: int) -> Optional[User]:
        """Get user by GitHub ID"""
        stmt = select(User).where(User.github_id == github_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_user(
        self,
        email: str,
        password: str,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        is_superuser: bool = False,
        **kwargs
    ) -> User:
        """Create new user with password hashing"""
        from app.core.security import get_password_hash
        
        hashed_password = get_password_hash(password)
        
        # Create user data dictionary for base repository
        user_data = {
            "email": email,
            "username": username,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "is_superuser": is_superuser,
            **kwargs
        }
        
        return await self.create(user_data)
    
    async def update_last_login(self, user_id: str) -> Optional[User]:
        """Update user's last login timestamp"""
        from datetime import datetime
        return await self.update(user_id, last_login=datetime.utcnow())
    
    async def deactivate_user(self, user_id: str) -> Optional[User]:
        """Deactivate user account"""
        return await self.update(user_id, is_active=False)
    
    async def activate_user(self, user_id: str) -> Optional[User]:
        """Activate user account"""
        return await self.update(user_id, is_active=True)
    
    async def verify_user(self, user_id: str) -> Optional[User]:
        """Mark user as verified"""
        return await self.update(user_id, is_verified=True)
    
    async def update_github_info(
        self, 
        user_id: str, 
        github_id: int, 
        github_username: str, 
        github_access_token: str
    ) -> Optional[User]:
        """Update user's GitHub integration info"""
        return await self.update(
            user_id,
            github_id=github_id,
            github_username=github_username,
            github_access_token=github_access_token
        )
    
    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all active users"""
        return await self.get_multi(skip=skip, limit=limit, filters={"is_active": True})
    
    async def search_users(self, query: str, skip: int = 0, limit: int = 100) -> list[User]:
        """Search users by email, username, or full name"""
        stmt = (
            select(User)
            .where(
                User.email.ilike(f"%{query}%")
                | User.username.ilike(f"%{query}%") 
                | User.full_name.ilike(f"%{query}%")
            )
            .offset(skip)
            .limit(limit)
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())
