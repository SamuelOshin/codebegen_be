"""
Projects router for project management endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_user_optional
from app.core.database import get_async_db
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.services.project_validation_service import project_validation_service, project_preview_service
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectFilters,
    PaginatedProjectResponse,
    ProjectStatsResponse,
    ProjectValidationRequest,
    ProjectValidationResponse,
    ProjectPreviewRequest,
    ProjectPreviewResponse
)

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new project"""
    repo = ProjectRepository(db)
    
    # Create project data with user ID
    project_dict = project_data.model_dump()
    project_dict["user_id"] = current_user.id
    
    project = await repo.create(project_dict)
    return ProjectResponse.model_validate(project)


@router.get("/", response_model=PaginatedProjectResponse)
async def list_user_projects(
    skip: int = Query(0, ge=0, description="Number of projects to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of projects to return"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    status: Optional[str] = Query(None, description="Filter by status"),
    tech_stack: Optional[List[str]] = Query(None, description="Filter by tech stack"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    has_github: Optional[bool] = Query(None, description="Filter by GitHub repository"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List current user's projects with filtering and pagination"""
    repo = ProjectRepository(db)
    
    # Build filters
    filters = ProjectFilters(
        domain=domain,
        status=status,
        tech_stack=tech_stack,
        is_public=is_public,
        has_github=has_github
    )
    
    # Get projects and count
    projects = await repo.get_by_user_id(current_user.id, filters, skip, limit)
    total = await repo.count_user_projects(current_user.id, filters)
    
    # Convert to response models
    project_responses = [ProjectResponse.model_validate(p) for p in projects]
    
    return PaginatedProjectResponse(
        projects=project_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/public", response_model=PaginatedProjectResponse)
async def list_public_projects(
    skip: int = Query(0, ge=0, description="Number of projects to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of projects to return"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    tech_stack: Optional[List[str]] = Query(None, description="Filter by tech stack"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_async_db)
):
    """List public projects with filtering and pagination"""
    repo = ProjectRepository(db)
    
    # Build filters
    filters = ProjectFilters(
        domain=domain,
        tech_stack=tech_stack
    )
    
    projects = await repo.get_public_projects(filters, skip, limit)
    
    # For simplicity, we'll count all public projects (could optimize)
    total_stmt_filters = ProjectFilters(domain=domain, tech_stack=tech_stack, is_public=True)
    total = await repo.count_user_projects("", total_stmt_filters) if not current_user else len(projects)
    
    # Convert to response models
    project_responses = [ProjectResponse.model_validate(p) for p in projects]
    
    return PaginatedProjectResponse(
        projects=project_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/search", response_model=PaginatedProjectResponse)
async def search_projects(
    q: str = Query(..., min_length=2, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of projects to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of projects to return"),
    include_public: bool = Query(True, description="Include public projects in search"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_async_db)
):
    """Search projects by name or description"""
    repo = ProjectRepository(db)
    
    user_id = current_user.id if current_user else None
    projects = await repo.search_projects(q, user_id, include_public, skip, limit)
    
    # Convert to response models
    project_responses = [ProjectResponse.model_validate(p) for p in projects]
    
    return PaginatedProjectResponse(
        projects=project_responses,
        total=len(project_responses),  # Simplified count
        skip=skip,
        limit=limit
    )


@router.get("/domains")
async def get_user_domains(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get unique domains used by user's projects"""
    repo = ProjectRepository(db)
    domains = await repo.get_user_project_domains(current_user.id)
    return {"domains": domains}


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific project by ID"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check access permissions
    if not project.is_public:
        if not current_user or project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to private project"
            )
    
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update a project"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own projects"
        )
    
    # Update project
    update_data = project_data.model_dump(exclude_unset=True)
    updated_project = await repo.update(project_id, **update_data)
    
    return ProjectResponse.model_validate(updated_project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a project"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete your own projects"
        )
    
    await repo.delete(project_id)


@router.get("/{project_id}/stats", response_model=ProjectStatsResponse)
async def get_project_stats(
    project_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_async_db)
):
    """Get project statistics"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check access permissions
    if not project.is_public:
        if not current_user or project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to private project"
            )
    
    stats = await repo.get_project_stats(project_id)
    return ProjectStatsResponse(**stats)


@router.post("/validate", response_model=ProjectValidationResponse)
async def validate_project_config(
    validation_request: ProjectValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """Validate project configuration without saving to database"""
    return await project_validation_service.validate_project(validation_request)


@router.post("/preview", response_model=ProjectPreviewResponse)
async def preview_project_structure(
    preview_request: ProjectPreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate preview of project structure before generation"""
    return await project_preview_service.generate_preview(preview_request)


@router.get("/stats", response_model=ProjectStatsResponse)
async def get_global_project_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get global user statistics for dashboard"""
    repo = ProjectRepository(db)
    stats = await repo.get_user_project_stats(current_user.id)
    return ProjectStatsResponse(**stats)
