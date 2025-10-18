"""
Generation Service Layer

Business logic for managing AI code generations with version tracking.
Coordinates between database (Generation/Project models) and file system (FileManager).

Design Principles:
- Single Responsibility: Only handles generation management logic
- Dependency Injection: Database session and FileManager injected
- DRY: Reuses model methods and FileManager capabilities
- Transaction Safety: Proper commit/rollback handling
"""

from loguru import logger
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.generation import Generation
from app.models.project import Project
from app.services.file_manager import FileManager

logger = logger


class GenerationServiceError(Exception):
    """Base exception for GenerationService errors."""
    pass


class GenerationNotFoundError(GenerationServiceError):
    """Raised when a generation is not found."""
    pass


class ProjectNotFoundError(GenerationServiceError):
    """Raised when a project is not found."""
    pass


class GenerationService:
    """
    Service layer for generation management.
    
    Encapsulates all business logic for creating, storing, and managing
    AI code generations with version tracking and hierarchical storage.
    """
    
    def __init__(self, db: AsyncSession, file_manager: Optional[FileManager] = None):
        """
        Initialize GenerationService.
        
        Args:
            db: Database session
            file_manager: FileManager instance (injected for testability)
        """
        self.db = db
        self.file_manager = file_manager or FileManager()
    
    async def create_generation(
        self,
        project_id: str,
        user_id: str,
        prompt: str,
        context: Optional[Dict] = None,
        version_name: Optional[str] = None,
        is_iteration: bool = False,
        parent_generation_id: Optional[str] = None
    ) -> Generation:
        """
        Create a new generation with automatic version numbering.
        
        This method:
        1. Validates project exists
        2. Determines next version number
        3. Creates Generation record with status="processing"
        4. Updates project's latest_version
        
        Args:
            project_id: Project UUID
            user_id: User UUID
            prompt: User's generation prompt
            context: Optional context data
            version_name: Optional custom version name (e.g., "v1.0", "hotfix")
            is_iteration: Whether this is iterating on a previous generation
            parent_generation_id: If iteration, the parent generation ID
            
        Returns:
            Created Generation instance
            
        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        try:
            # Get project and validate it exists
            project = await self.db.get(Project, project_id)
            if not project:
                raise ProjectNotFoundError(f"Project {project_id} not found")
            
            # Determine next version number
            # Version tracking logic: Each project maintains its own version sequence
            # starting from 1. Versions are assigned sequentially based on creation order,
            # not completion order. This ensures predictable, gap-free version numbers
            # that users can reference consistently.
            next_version = project.latest_version + 1
            
            # Create generation record
            generation = Generation(
                id=str(uuid4()),
                project_id=project_id,
                user_id=user_id,
                version=next_version,
                version_name=version_name,
                prompt=prompt,
                context=context,
                status="processing",
                is_iteration=is_iteration,
                parent_generation_id=parent_generation_id,
                is_active=False  # Will be set active after successful completion
            )
            
            self.db.add(generation)
            
            # Update project's latest version
            project.latest_version = next_version
            
            await self.db.commit()
            await self.db.refresh(generation)
            
            logger.info(f"✅ Created generation v{next_version} for project {project_id}")
            return generation
            
        except ProjectNotFoundError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error creating generation: {e}")
            raise GenerationServiceError(f"Failed to create generation: {e}")
    
    async def save_generation_output(
        self,
        generation_id: str,
        files: Dict[str, str],
        extracted_schema: Optional[Dict] = None,
        documentation: Optional[Dict] = None,
        auto_activate: bool = True
    ) -> Generation:
        """
        Save generation output to file system and update database.
        
        This method:
        1. Saves files using hierarchical storage structure
        2. Updates Generation record with storage path, file count, size
        3. Creates diff from previous version (if exists)
        4. Updates status to "completed"
        5. Optionally sets as active generation
        
        Args:
            generation_id: Generation UUID
            files: Dictionary of file_path -> content
            extracted_schema: Optional schema extraction results
            documentation: Optional generated documentation
            auto_activate: Whether to automatically set as active generation
            
        Returns:
            Updated Generation instance
            
        Raises:
            GenerationNotFoundError: If generation doesn't exist
        """
        try:
            # Get generation and validate
            generation = await self.db.get(Generation, generation_id)
            if not generation:
                raise GenerationNotFoundError(f"Generation {generation_id} not found")
            
            # Save files to hierarchical storage
            storage_path, file_count, total_size_bytes = await self.file_manager.save_generation_files_hierarchical(
                project_id=generation.project_id,
                generation_id=generation_id,
                version=generation.version,
                files=files,
                metadata={
                    "prompt": generation.prompt,
                    "created_at": generation.created_at.isoformat() if generation.created_at else None
                }
            )
            
            # Update generation record
            generation.storage_path = storage_path
            generation.file_count = file_count
            generation.total_size_bytes = total_size_bytes
            generation.output_files = files  # Keep for backward compatibility (will be removed later)
            generation.status = "completed"
            
            # Save optional metadata
            if extracted_schema:
                generation.extracted_schema = extracted_schema
            if documentation:
                generation.documentation = documentation
            
            # Create diff from previous version if exists
            if generation.version > 1:
                diff_path = await self.file_manager.create_generation_diff(
                    project_id=generation.project_id,
                    from_version=generation.version - 1,
                    to_version=generation.version
                )
                if diff_path:
                    generation.diff_from_previous = diff_path
                    
                    # Calculate changes summary (simple count for now)
                    generation.changes_summary = {
                        "diff_created_at": datetime.utcnow().isoformat(),
                        "from_version": generation.version - 1,
                        "to_version": generation.version
                    }
            
            await self.db.commit()
            await self.db.refresh(generation)
            
            # Auto-activate if requested
            if auto_activate:
                await self.set_active_generation(generation.project_id, generation_id)
            
            logger.info(
                f"✅ Saved generation v{generation.version} output "
                f"({file_count} files, {total_size_bytes:,} bytes)"
            )
            return generation
            
        except GenerationNotFoundError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error saving generation output: {e}")
            raise GenerationServiceError(f"Failed to save generation output: {e}")
    
    async def set_active_generation(
        self,
        project_id: str,
        generation_id: str
    ) -> Generation:
        """
        Mark a generation as the active one for its project.
        
        This method:
        1. Validates generation belongs to project
        2. Uses Project.set_active_generation() to update DB (DRY principle)
        3. Creates/updates file system symlink to active generation
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID to set as active
            
        Returns:
            The activated Generation instance
            
        Raises:
            ProjectNotFoundError: If project doesn't exist
            GenerationNotFoundError: If generation doesn't exist
        """
        try:
            # Get project with generations eagerly loaded
            result = await self.db.execute(
                select(Project)
                .options(selectinload(Project.generations))
                .where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                raise ProjectNotFoundError(f"Project {project_id} not found")
            
            # Get generation and validate it belongs to this project
            generation = await self.db.get(Generation, generation_id)
            if not generation:
                raise GenerationNotFoundError(f"Generation {generation_id} not found")
            
            if generation.project_id != project_id:
                raise GenerationServiceError(
                    f"Generation {generation_id} does not belong to project {project_id}"
                )
            
            # Use Project's set_active_generation method (DRY principle)
            project.set_active_generation(generation_id)
            
            # Update file system symlink
            # Active generation management: Creates/updates symlink at
            # ./storage/projects/{project_id}/generations/active -> v{version}__{generation_id}/
            # This allows applications to always access the "current" version via a stable path,
            # while maintaining full version history in separate directories.
            await self.file_manager.set_active_generation_symlink(
                project_id=project_id,
                generation_version=generation.version
            )
            
            await self.db.commit()
            await self.db.refresh(generation)
            
            logger.info(f"✅ Set generation v{generation.version} as active for project {project_id}")
            return generation
            
        except (ProjectNotFoundError, GenerationNotFoundError, GenerationServiceError):
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error setting active generation: {e}")
            raise GenerationServiceError(f"Failed to set active generation: {e}")
    
    async def get_generation_by_version(
        self,
        project_id: str,
        version: int
    ) -> Optional[Generation]:
        """
        Get a specific generation version for a project.
        
        Uses Project.get_generation_by_version() method (DRY principle).
        
        Args:
            project_id: Project UUID
            version: Version number to retrieve
            
        Returns:
            Generation instance or None if not found
        """
        try:
            # Get project with generations
            result = await self.db.execute(
                select(Project)
                .options(selectinload(Project.generations))
                .where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                return None
            
            # Use Project's get_generation_by_version method (DRY principle)
            return project.get_generation_by_version(version)
            
        except Exception as e:
            logger.error(f"❌ Error getting generation by version: {e}")
            return None
    
    async def get_active_generation(
        self,
        project_id: str
    ) -> Optional[Generation]:
        """
        Get the currently active generation for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Active Generation instance or None
        """
        try:
            # Get project with active generation eagerly loaded
            result = await self.db.execute(
                select(Project)
                .options(selectinload(Project.active_generation))
                .where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                return None
            
            return project.active_generation
            
        except Exception as e:
            logger.error(f"❌ Error getting active generation: {e}")
            return None
    
    async def list_project_generations(
        self,
        project_id: str,
        include_failed: bool = False,
        limit: Optional[int] = None
    ) -> List[Generation]:
        """
        List all generations for a project.
        
        Args:
            project_id: Project UUID
            include_failed: Whether to include failed generations
            limit: Optional limit on number of results
            
        Returns:
            List of Generation instances, ordered by version (newest first)
        """
        try:
            query = select(Generation).where(Generation.project_id == project_id)
            
            # Filter out failed if requested
            if not include_failed:
                query = query.where(Generation.status != "failed")
            
            # Order by version descending (newest first)
            query = query.order_by(desc(Generation.version))
            
            # Apply limit if specified
            if limit:
                query = query.limit(limit)
            
            result = await self.db.execute(query)
            generations = result.scalars().all()
            
            return list(generations)
            
        except Exception as e:
            logger.error(f"❌ Error listing project generations: {e}")
            return []
    
    async def compare_generations(
        self,
        project_id: str,
        from_version: int,
        to_version: int
    ) -> Optional[Dict]:
        """
        Compare two generation versions and return diff information.
        
        Args:
            project_id: Project UUID
            from_version: Source version number
            to_version: Target version number
            
        Returns:
            Dictionary with comparison results or None if error
        """
        try:
            # Get both generations
            from_gen = await self.get_generation_by_version(project_id, from_version)
            to_gen = await self.get_generation_by_version(project_id, to_version)
            
            if not from_gen or not to_gen:
                logger.warning(f"Cannot compare: version {from_version} or {to_version} not found")
                return None
            
            # Check if diff already exists
            diff_path = to_gen.diff_from_previous if to_version == from_version + 1 else None
            
            # If not, create it
            if not diff_path:
                diff_path = await self.file_manager.create_generation_diff(
                    project_id=project_id,
                    from_version=from_version,
                    to_version=to_version
                )
            
            # Read diff content if exists
            diff_content = None
            if diff_path:
                try:
                    from pathlib import Path
                    diff_content = Path(diff_path).read_text(encoding='utf-8')
                except Exception as e:
                    logger.warning(f"Could not read diff file: {e}")
            
            return {
                "from_version": from_version,
                "to_version": to_version,
                "from_generation_id": from_gen.id,
                "to_generation_id": to_gen.id,
                "from_file_count": from_gen.file_count,
                "to_file_count": to_gen.file_count,
                "from_size_bytes": from_gen.total_size_bytes,
                "to_size_bytes": to_gen.total_size_bytes,
                "diff_path": diff_path,
                "diff_content": diff_content,
                "changes_summary": to_gen.changes_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Error comparing generations: {e}")
            return None
    
    async def delete_generation(
        self,
        generation_id: str,
        delete_files: bool = True
    ) -> bool:
        """
        Delete a generation from database and optionally from file system.
        
        Note: Cannot delete if it's the active generation or the only generation.
        
        Args:
            generation_id: Generation UUID
            delete_files: Whether to delete files from storage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            generation = await self.db.get(Generation, generation_id)
            if not generation:
                raise GenerationNotFoundError(f"Generation {generation_id} not found")
            
            # Check if it's the active generation
            if generation.is_active:
                raise GenerationServiceError("Cannot delete active generation")
            
            # Delete files if requested
            if delete_files and generation.storage_path:
                from pathlib import Path
                storage_path = Path(generation.storage_path)
                if storage_path.exists():
                    import shutil
                    shutil.rmtree(storage_path)
                    logger.info(f"🗑️  Deleted files for generation {generation_id}")
            
            # Delete from database
            await self.db.delete(generation)
            await self.db.commit()
            
            logger.info(f"✅ Deleted generation {generation_id}")
            return True
            
        except (GenerationNotFoundError, GenerationServiceError):
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error deleting generation: {e}")
            raise GenerationServiceError(f"Failed to delete generation: {e}")
    
    async def update_generation_status(
        self,
        generation_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Generation:
        """
        Update generation status (e.g., from "processing" to "completed" or "failed").
        
        Args:
            generation_id: Generation UUID
            status: New status value
            error_message: Optional error message if status is "failed"
            
        Returns:
            Updated Generation instance
        """
        try:
            generation = await self.db.get(Generation, generation_id)
            if not generation:
                raise GenerationNotFoundError(f"Generation {generation_id} not found")
            
            generation.status = status
            if error_message:
                generation.error_message = error_message
            
            await self.db.commit()
            await self.db.refresh(generation)
            
            logger.info(f"✅ Updated generation {generation_id} status to {status}")
            return generation
            
        except GenerationNotFoundError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error updating generation status: {e}")
            raise GenerationServiceError(f"Failed to update generation status: {e}")
