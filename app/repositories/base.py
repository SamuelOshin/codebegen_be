"""
Base repository class with common CRUD operations.
Provides consistent data access patterns across all repositories.
"""

from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError

from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model
    
    async def get(self, id: str) -> Optional[ModelType]:
        """Get model by ID"""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, id: str) -> Optional[ModelType]:
        """Alias for get method"""
        return await self.get(id)
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get multiple models with pagination and filters"""
        stmt = select(self.model)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)
        
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(self, obj_data: Dict[str, Any]) -> ModelType:
        """Create new model instance"""
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        try:
            await self.db.commit()
            await self.db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            await self.db.rollback()
            raise ValueError(f"Failed to create {self.model.__name__}: {str(e)}")
    
    async def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """Update model by ID"""
        # First get the existing object
        existing = await self.get(id)
        if not existing:
            return None
        
        # Update the attributes
        for key, value in kwargs.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        
        try:
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        except IntegrityError as e:
            await self.db.rollback()
            raise ValueError(f"Failed to update {self.model.__name__}: {str(e)}")
    
    async def delete(self, id: str) -> bool:
        """Delete model by ID"""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count models with optional filters"""
        stmt = select(func.count(self.model.id))
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    stmt = stmt.where(getattr(self.model, key) == value)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def exists(self, id: str) -> bool:
        """Check if model exists by ID"""
        stmt = select(self.model.id).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
