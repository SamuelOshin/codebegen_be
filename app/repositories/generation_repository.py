"""
Generation repository for managing generation requests and artifacts.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository
from app.models.generation import Generation, Artifact
from app.schemas.generation import GenerationFilters, GenerationStatsResponse


class GenerationRepository(BaseRepository[Generation]):
    """Repository for managing generation entities"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Generation)
    
    async def get_by_id(self, generation_id: str) -> Optional[Generation]:
        """Get generation by ID with eagerly loaded artifacts"""
        stmt = (
            select(Generation)
            .where(Generation.id == generation_id)
            .options(selectinload(Generation.artifacts))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(self, obj_data: Dict[str, Any]) -> Generation:
        """Create new generation with eagerly loaded artifacts"""
        # Create the generation
        db_obj = Generation(**obj_data)
        self.db.add(db_obj)
        try:
            await self.db.commit()
            await self.db.refresh(db_obj)
            
            # Re-fetch with loaded artifacts
            return await self.get_by_id(db_obj.id)
        except Exception as e:
            await self.db.rollback()
            raise ValueError(f"Failed to create Generation: {str(e)}")
    
    async def get_by_user_id(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 50,
        filters: Optional[GenerationFilters] = None
    ) -> List[Generation]:
        """Get generations by user ID with filtering and pagination"""
        stmt = (
            select(Generation)
            .where(Generation.user_id == user_id)
            .options(selectinload(Generation.artifacts))
        )
        
        # Apply filters
        if filters:
            if filters.status:
                stmt = stmt.where(Generation.status == filters.status)
            if filters.project_id:
                stmt = stmt.where(Generation.project_id == filters.project_id)
            if filters.is_iteration is not None:
                stmt = stmt.where(Generation.is_iteration == filters.is_iteration)
            if filters.min_quality_score is not None:
                stmt = stmt.where(Generation.quality_score >= filters.min_quality_score)
            if filters.start_date:
                stmt = stmt.where(Generation.created_at >= filters.start_date)
            if filters.end_date:
                stmt = stmt.where(Generation.created_at <= filters.end_date)
        
        stmt = stmt.order_by(Generation.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_project_id(self, project_id: str) -> List[Generation]:
        """Get all generations for a project"""
        stmt = (
            select(Generation)
            .where(Generation.project_id == project_id)
            .options(selectinload(Generation.artifacts))
            .order_by(Generation.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_status(self, status: str, limit: int = 100) -> List[Generation]:
        """Get generations by status"""
        stmt = (
            select(Generation)
            .where(Generation.status == status)
            .order_by(Generation.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_active_generations(self, user_id: str) -> List[Generation]:
        """Get all active (pending/processing) generations for a user"""
        stmt = (
            select(Generation)
            .where(
                and_(
                    Generation.user_id == user_id,
                    or_(
                        Generation.status == "pending",
                        Generation.status == "processing"
                    )
                )
            )
            .options(selectinload(Generation.artifacts))
            .order_by(Generation.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_iterations(self, parent_generation_id: str) -> List[Generation]:
        """Get all iterations of a parent generation"""
        stmt = (
            select(Generation)
            .where(Generation.parent_generation_id == parent_generation_id)
            .options(selectinload(Generation.artifacts))
            .order_by(Generation.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def update_status(
        self, 
        generation_id: str, 
        status: str, 
        error_message: Optional[str] = None,
        quality_score: Optional[float] = None
    ) -> Optional[Generation]:
        """Update generation status and related fields"""
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        
        if error_message:
            update_data["error_message"] = error_message
        if quality_score is not None:
            update_data["quality_score"] = quality_score
            
        stmt = (
            update(Generation)
            .where(Generation.id == generation_id)
            .values(**update_data)
            .returning(Generation)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar()
    
    async def update_progress(
        self, 
        generation_id: str, 
        stage_times: Dict[str, float],
        output_files: Optional[Dict[str, Any]] = None,
        extracted_schema: Optional[Dict[str, Any]] = None,
        review_feedback: Optional[Dict[str, Any]] = None,
        documentation: Optional[Dict[str, Any]] = None
    ) -> Optional[Generation]:
        """Update generation progress and timing information"""
        update_data = {"updated_at": datetime.utcnow()}
        
        # Update timing information
        if "schema_extraction" in stage_times:
            update_data["schema_extraction_time"] = stage_times["schema_extraction"]
        if "code_generation" in stage_times:
            update_data["code_generation_time"] = stage_times["code_generation"]
        if "review" in stage_times:
            update_data["review_time"] = stage_times["review"]
        if "docs_generation" in stage_times:
            update_data["docs_generation_time"] = stage_times["docs_generation"]
        if "total" in stage_times:
            update_data["total_time"] = stage_times["total"]
            
        # Update generated content
        if output_files:
            update_data["output_files"] = output_files
        if extracted_schema:
            update_data["extracted_schema"] = extracted_schema
        if review_feedback:
            update_data["review_feedback"] = review_feedback
        if documentation:
            update_data["documentation"] = documentation
            
        stmt = (
            update(Generation)
            .where(Generation.id == generation_id)
            .values(**update_data)
            .returning(Generation)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar()
    
    async def add_artifact(
        self, 
        generation_id: str, 
        artifact_type: str, 
        storage_url: str, 
        file_size: Optional[int] = None, 
        file_metadata: Optional[dict] = None
    ) -> Artifact:
        """Add an artifact to a generation"""
        artifact = Artifact(
            generation_id=generation_id,
            type=artifact_type,
            storage_url=storage_url,
            file_size=file_size,
            file_metadata=file_metadata
        )
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact
    
    async def get_user_statistics(self, user_id: str) -> GenerationStatsResponse:
        """Get comprehensive statistics for a user's generations"""
        
        # Basic counts
        total_stmt = select(func.count(Generation.id)).where(Generation.user_id == user_id)
        completed_stmt = select(func.count(Generation.id)).where(
            and_(Generation.user_id == user_id, Generation.status == "completed")
        )
        failed_stmt = select(func.count(Generation.id)).where(
            and_(Generation.user_id == user_id, Generation.status == "failed")
        )
        pending_stmt = select(func.count(Generation.id)).where(
            and_(Generation.user_id == user_id, or_(
                Generation.status == "pending", 
                Generation.status == "processing"
            ))
        )
        
        # Average quality score
        avg_quality_stmt = select(func.avg(Generation.quality_score)).where(
            and_(Generation.user_id == user_id, Generation.quality_score.is_not(None))
        )
        
        # Average generation time
        avg_time_stmt = select(func.avg(Generation.total_time)).where(
            and_(Generation.user_id == user_id, Generation.total_time.is_not(None))
        )
        
        # Execute all queries
        total_result = await self.db.execute(total_stmt)
        completed_result = await self.db.execute(completed_stmt)
        failed_result = await self.db.execute(failed_stmt)
        pending_result = await self.db.execute(pending_stmt)
        avg_quality_result = await self.db.execute(avg_quality_stmt)
        avg_time_result = await self.db.execute(avg_time_stmt)
        
        # Count total files generated (sum of artifacts)
        files_stmt = select(func.count(Artifact.id)).join(Generation).where(Generation.user_id == user_id)
        files_result = await self.db.execute(files_stmt)
        
        return GenerationStatsResponse(
            total_generations=total_result.scalar() or 0,
            completed_generations=completed_result.scalar() or 0,
            failed_generations=failed_result.scalar() or 0,
            pending_generations=pending_result.scalar() or 0,
            average_quality_score=avg_quality_result.scalar(),
            average_generation_time=avg_time_result.scalar(),
            total_files_generated=files_result.scalar() or 0,
            popular_project_types=[]  # TODO: Implement based on project metadata
        )
    
    async def cancel_generation(self, generation_id: str, reason: Optional[str] = None) -> Optional[Generation]:
        """Cancel a generation request"""
        update_data = {
            "status": "cancelled",
            "updated_at": datetime.utcnow()
        }
        
        if reason:
            update_data["error_message"] = f"Cancelled: {reason}"
            
        stmt = (
            update(Generation)
            .where(
                and_(
                    Generation.id == generation_id,
                    or_(
                        Generation.status == "pending",
                        Generation.status == "processing"
                    )
                )
            )
            .values(**update_data)
            .returning(Generation)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar()
    
    async def get_recent_generations(self, user_id: str, limit: int = 10) -> List[Generation]:
        """Get user's most recent generations"""
        stmt = (
            select(Generation)
            .where(Generation.user_id == user_id)
            .options(selectinload(Generation.artifacts))
            .order_by(Generation.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
