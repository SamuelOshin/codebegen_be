"""
Auto Project Creation Service

Handles automatic project creation when project_id is not provided
during generation. Uses prompt analysis to create meaningful project
metadata and configuration.

Features:
- Intelligent project naming from prompts
- Domain and tech stack detection
- Project deduplication and reuse
- Metadata tracking for auto-created projects
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project
from app.services.prompt_analysis_service import prompt_analysis_service, PromptAnalysisResult

logger = logging.getLogger(__name__)


class AutoProjectService:
    """
    Service for automatic project creation from generation prompts.
    
    Intelligently creates projects with meaningful metadata when users
    start generating without explicitly creating a project first.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_or_find_project(
        self,
        user_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        creation_source: str = "generation_endpoint"
    ) -> tuple[Project, PromptAnalysisResult]:
        """
        Create a new auto-generated project or find existing similar project.
        
        Strategy:
        1. Analyze prompt to extract metadata
        2. Check if recent similar auto-created project exists
        3. Either reuse existing or create new project
        4. Return project with analysis results
        
        Args:
            user_id: User ID creating the project
            prompt: User's generation prompt
            context: Optional context with preferences
            creation_source: Source identifier (e.g., "homepage_generation")
            
        Returns:
            Tuple of (Project, PromptAnalysisResult)
        """
        logger.info(f"Auto-creating project for user {user_id}")
        
        # Step 1: Analyze prompt
        analysis = await prompt_analysis_service.analyze_prompt(prompt, context)
        
        logger.info(
            f"Prompt analysis complete: name='{analysis.suggested_name}', "
            f"domain='{analysis.domain}', confidence={analysis.confidence:.2f}"
        )
        
        # Step 2: Check for existing similar project (optional optimization)
        existing_project = await self._find_similar_project(
            user_id, analysis, creation_source
        )
        
        if existing_project:
            logger.info(f"Reusing existing project: {existing_project.id}")
            return existing_project, analysis
        
        # Step 3: Create new project
        new_project = await self._create_project_from_analysis(
            user_id, prompt, analysis, creation_source
        )
        
        logger.info(f"Created new auto project: {new_project.id} - '{new_project.name}'")
        
        return new_project, analysis
    
    async def _find_similar_project(
        self,
        user_id: str,
        analysis: PromptAnalysisResult,
        creation_source: str
    ) -> Optional[Project]:
        """
        Find existing auto-created project that matches criteria.
        
        Matching criteria:
        - Same user
        - Auto-created
        - Same domain
        - Same creation source
        - Created recently (within last hour)
        - Has same suggested name
        
        This prevents creating duplicate projects when user makes
        multiple generations in quick succession.
        """
        try:
            # Query for recent auto-created projects
            query = select(Project).where(
                Project.user_id == user_id,
                Project.auto_created == True,
                Project.domain == analysis.domain,
                Project.creation_source == creation_source
            ).order_by(Project.created_at.desc()).limit(5)
            
            result = await self.db.execute(query)
            recent_projects = result.scalars().all()
            
            # Check if any have the same suggested name
            for project in recent_projects:
                # Allow reuse if created within last hour and same name
                time_diff = datetime.now(timezone.utc) - project.created_at
                if (time_diff.total_seconds() < 3600 and 
                    project.name.lower() == analysis.suggested_name.lower()):
                    return project
            
            return None
            
        except Exception as e:
            logger.warning(f"Error finding similar project: {e}")
            return None
    
    async def _create_project_from_analysis(
        self,
        user_id: str,
        prompt: str,
        analysis: PromptAnalysisResult,
        creation_source: str
    ) -> Project:
        """
        Create new project from prompt analysis results.
        
        Maps analysis results to project model fields and persists to database.
        """
        
        # Determine tech_stack string format
        # Convert list to underscore-separated string (e.g., ["fastapi", "postgres"] -> "fastapi_postgres")
        tech_stack_str = self._format_tech_stack(analysis.tech_stack)
        
        # Build constraints from detected features
        constraints = {
            "features": analysis.features,
            "complexity": analysis.complexity,
            "auto_detected": True
        }
        
        # Create project instance
        project = Project(
            id=str(uuid4()),
            user_id=user_id,
            name=analysis.suggested_name,
            description=analysis.description,
            domain=analysis.domain,
            tech_stack=tech_stack_str,
            constraints=constraints,
            status="active",  # Auto-created projects start as active
            is_public=False,
            auto_created=True,
            creation_source=creation_source,
            original_prompt=prompt[:1000],  # Store first 1000 chars
            settings={
                "auto_created_metadata": {
                    "entities": analysis.entities,
                    "confidence": analysis.confidence,
                    "detected_features": analysis.features,
                    "complexity": analysis.complexity
                }
            },
            latest_version=0
        )
        
        # Persist to database
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        
        logger.info(
            f"Created project '{project.name}' (ID: {project.id}) "
            f"with domain '{project.domain}' and tech stack '{project.tech_stack}'"
        )
        
        return project
    
    def _format_tech_stack(self, tech_list: list[str]) -> str:
        """
        Format tech stack list into database string format.
        
        Strategy:
        1. Identify primary framework (fastapi, django, flask)
        2. Identify primary database (postgresql, mongodb, sqlite)
        3. Combine as framework_database
        4. Fall back to joining with underscores
        """
        
        frameworks = {"fastapi", "django", "flask", "express", "spring"}
        databases = {"postgresql", "postgres", "mongodb", "mongo", "sqlite", "mysql"}
        
        framework = None
        database = None
        
        for tech in tech_list:
            tech_lower = tech.lower()
            if tech_lower in frameworks and not framework:
                framework = tech_lower
            if tech_lower in databases and not database:
                # Normalize database names
                if tech_lower in ["postgres", "postgresql"]:
                    database = "postgres"
                elif tech_lower in ["mongo", "mongodb"]:
                    database = "mongo"
                else:
                    database = tech_lower
        
        # Build tech stack string
        if framework and database:
            return f"{framework}_{database}"
        elif framework:
            return f"{framework}_postgres"  # Default to postgres
        elif database:
            return f"fastapi_{database}"  # Default to fastapi
        else:
            # Join all techs with underscores
            return "_".join(tech_list[:3]) if tech_list else "fastapi_postgres"
    
    async def update_project_on_success(
        self,
        project_id: str,
        generation_id: str
    ) -> None:
        """
        Update auto-created project after successful generation.
        
        - Marks project as having successful generation
        - Can be used to promote from draft to active
        """
        try:
            query = select(Project).where(Project.id == project_id)
            result = await self.db.execute(query)
            project = result.scalar_one_or_none()
            
            if not project:
                logger.warning(f"Project {project_id} not found for update")
                return
            
            # Update status if it's still draft
            if project.status == "draft":
                project.status = "active"
            
            # Update latest_version
            project.latest_version = max(project.latest_version, 1)
            
            await self.db.commit()
            
            logger.info(f"Updated auto-created project {project_id} after generation")
            
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {e}")
            await self.db.rollback()
    
    async def get_auto_created_projects(
        self,
        user_id: str,
        limit: int = 10
    ) -> list[Project]:
        """
        Get user's auto-created projects for UI display.
        
        Can be used to show "Quick Generations" or "Experiments" section.
        """
        query = select(Project).where(
            Project.user_id == user_id,
            Project.auto_created == True
        ).order_by(Project.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def convert_to_explicit_project(
        self,
        project_id: str,
        new_name: Optional[str] = None,
        new_description: Optional[str] = None
    ) -> Project:
        """
        Convert auto-created project to explicit user-created project.
        
        Allows users to "promote" an experiment to a real project.
        """
        query = select(Project).where(Project.id == project_id)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Update fields
        project.auto_created = False
        project.creation_source = "user_promoted"
        
        if new_name:
            project.name = new_name
        
        if new_description:
            project.description = new_description
        
        await self.db.commit()
        await self.db.refresh(project)
        
        logger.info(f"Converted project {project_id} to explicit project")
        
        return project


def create_auto_project_service(db: AsyncSession) -> AutoProjectService:
    """Factory function for creating AutoProjectService instance"""
    return AutoProjectService(db)
