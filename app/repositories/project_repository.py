"""
Project repository for managing project entities.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository
from app.models.project import Project
from app.models.generation import Generation
from app.schemas.project import ProjectFilters


class ProjectRepository(BaseRepository[Project]):
    """Repository for managing project entities"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Project)
    
    async def get_by_user_id(
        self, 
        user_id: str, 
        filters: Optional[ProjectFilters] = None,
        skip: int = 0, 
        limit: int = 50
    ) -> List[Project]:
        """Get projects by user ID with optional filtering"""
        stmt = select(Project).where(Project.user_id == user_id)
        
        # Apply filters
        if filters:
            if filters.domain:
                stmt = stmt.where(Project.domain == filters.domain)
            if filters.tech_stack:
                # Check if any of the tech stack items match
                for tech in filters.tech_stack:
                    stmt = stmt.where(Project.tech_stack.contains([tech]))
            if filters.status:
                stmt = stmt.where(Project.status == filters.status)
            if filters.is_public is not None:
                stmt = stmt.where(Project.is_public == filters.is_public)
            if filters.has_github is not None:
                if filters.has_github:
                    stmt = stmt.where(Project.github_repo_url.isnot(None))
                else:
                    stmt = stmt.where(Project.github_repo_url.is_(None))
        
        stmt = (
            stmt.order_by(desc(Project.updated_at))
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_organization_id(
        self, 
        organization_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Project]:
        """Get projects by organization ID"""
        stmt = (
            select(Project)
            .where(Project.organization_id == organization_id)
            .order_by(desc(Project.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_public_projects(
        self, 
        filters: Optional[ProjectFilters] = None,
        skip: int = 0, 
        limit: int = 50
    ) -> List[Project]:
        """Get public projects with optional filtering"""
        stmt = select(Project).where(Project.is_public == True)
        
        # Apply filters
        if filters:
            if filters.domain:
                stmt = stmt.where(Project.domain == filters.domain)
            if filters.tech_stack:
                for tech in filters.tech_stack:
                    stmt = stmt.where(Project.tech_stack.contains([tech]))
        
        stmt = (
            stmt.order_by(desc(Project.updated_at))
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def search_projects(
        self, 
        query: str,
        user_id: Optional[str] = None,
        include_public: bool = True,
        skip: int = 0,
        limit: int = 50
    ) -> List[Project]:
        """Search projects by name or description"""
        search_filter = or_(
            Project.name.ilike(f"%{query}%"),
            Project.description.ilike(f"%{query}%")
        )
        
        access_filter = []
        if user_id:
            access_filter.append(Project.user_id == user_id)
        if include_public:
            access_filter.append(Project.is_public == True)
        
        if access_filter:
            stmt = select(Project).where(
                and_(search_filter, or_(*access_filter))
            )
        else:
            stmt = select(Project).where(search_filter)
        
        stmt = (
            stmt.order_by(desc(Project.updated_at))
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        """Get project statistics"""
        # Count generations by status
        stmt = (
            select(
                func.count(Generation.id).label('total_generations'),
                func.sum(func.case((Generation.status == 'completed', 1), else_=0)).label('successful_generations'),
                func.sum(func.case((Generation.status == 'failed', 1), else_=0)).label('failed_generations'),
                func.avg(Generation.quality_score).label('average_quality_score'),
                func.max(Generation.created_at).label('last_activity')
            )
            .where(Generation.project_id == project_id)
        )
        
        result = await self.db.execute(stmt)
        stats = result.first()
        
        # Count total files generated (simplified - would need to count from artifacts)
        total_files_stmt = (
            select(func.count(Generation.id))
            .where(
                and_(
                    Generation.project_id == project_id,
                    Generation.output_files.isnot(None)
                )
            )
        )
        files_result = await self.db.execute(total_files_stmt)
        total_files = files_result.scalar() or 0
        
        return {
            "total_generations": stats.total_generations or 0,
            "successful_generations": stats.successful_generations or 0,
            "failed_generations": stats.failed_generations or 0,
            "total_files_generated": total_files,
            "average_quality_score": float(stats.average_quality_score) if stats.average_quality_score else None,
            "last_activity": stats.last_activity
        }
    
    async def count_user_projects(
        self, 
        user_id: str,
        filters: Optional[ProjectFilters] = None
    ) -> int:
        """Count total projects for a user with optional filters"""
        stmt = select(func.count(Project.id)).where(Project.user_id == user_id)
        
        if filters:
            if filters.domain:
                stmt = stmt.where(Project.domain == filters.domain)
            if filters.status:
                stmt = stmt.where(Project.status == filters.status)
            if filters.is_public is not None:
                stmt = stmt.where(Project.is_public == filters.is_public)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def get_user_project_domains(self, user_id: str) -> List[str]:
        """Get unique domains used by user's projects"""
        stmt = (
            select(Project.domain)
            .where(
                and_(
                    Project.user_id == user_id,
                    Project.domain.isnot(None)
                )
            )
            .distinct()
        )
        
        result = await self.db.execute(stmt)
        return [domain for domain in result.scalars().all() if domain]
    
    async def update_project_activity(self, project_id: str) -> None:
        """Update project's last activity timestamp"""
        from datetime import datetime
        await self.update(project_id, updated_at=datetime.utcnow())
