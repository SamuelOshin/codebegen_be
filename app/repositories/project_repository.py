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
    
    async def get_user_project_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user project statistics for dashboard"""
        # Get basic project counts
        total_projects_stmt = select(func.count(Project.id)).where(Project.user_id == user_id)
        active_projects_stmt = select(func.count(Project.id)).where(
            and_(Project.user_id == user_id, Project.status == "active")
        )
        completed_projects_stmt = select(func.count(Project.id)).where(
            and_(Project.user_id == user_id, Project.status == "completed")
        )
        draft_projects_stmt = select(func.count(Project.id)).where(
            and_(Project.user_id == user_id, Project.status == "draft")
        )
        public_projects_stmt = select(func.count(Project.id)).where(
            and_(Project.user_id == user_id, Project.is_public == True)
        )
        private_projects_stmt = select(func.count(Project.id)).where(
            and_(Project.user_id == user_id, Project.is_public == False)
        )
        
        # Execute count queries
        total_projects = (await self.db.execute(total_projects_stmt)).scalar() or 0
        active_projects = (await self.db.execute(active_projects_stmt)).scalar() or 0
        completed_projects = (await self.db.execute(completed_projects_stmt)).scalar() or 0
        draft_projects = (await self.db.execute(draft_projects_stmt)).scalar() or 0
        public_projects = (await self.db.execute(public_projects_stmt)).scalar() or 0
        private_projects = (await self.db.execute(private_projects_stmt)).scalar() or 0
        
        # Get projects by domain
        domain_stats_stmt = (
            select(Project.domain, func.count(Project.id))
            .where(and_(Project.user_id == user_id, Project.domain.isnot(None)))
            .group_by(Project.domain)
        )
        domain_result = await self.db.execute(domain_stats_stmt)
        projects_by_domain = {domain: count for domain, count in domain_result.fetchall()}
        
        # Get projects by tech stack (simplified - count occurrences of each tech)
        projects_stmt = select(Project.tech_stack).where(
            and_(Project.user_id == user_id, Project.tech_stack.isnot(None))
        )
        projects_result = await self.db.execute(projects_stmt)
        
        tech_stack_count = {}
        for (tech_stack,) in projects_result.fetchall():
            if tech_stack:
                for tech in tech_stack:
                    tech_stack_count[tech] = tech_stack_count.get(tech, 0) + 1
        
        return {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "draft_projects": draft_projects,
            "public_projects": public_projects,
            "private_projects": private_projects,
            "projects_by_domain": projects_by_domain,
            "projects_by_tech_stack": tech_stack_count
        }
