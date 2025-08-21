"""
Projects router for project management endpoints.
"""

from typing import List, Optional
import json
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


def convert_project_to_response(project) -> dict:
    """Convert a project model to response data, handling string-to-dict conversions"""
    # Handle constraints: parse JSON string to dict
    constraints = project.constraints or {}
    if isinstance(constraints, str):
        try:
            constraints = json.loads(constraints) if constraints.strip() else {}
        except (json.JSONDecodeError, AttributeError):
            constraints = {}
    
    # Handle settings: parse JSON string to dict  
    settings = project.settings or {}
    if isinstance(settings, str):
        try:
            settings = json.loads(settings) if settings.strip() else {}
        except (json.JSONDecodeError, AttributeError):
            settings = {}
    
    return {
        "id": project.id,
        "user_id": project.user_id,
        "organization_id": project.organization_id,
        "name": project.name,
        "description": project.description,
        "domain": project.domain,
        "tech_stack": project.tech_stack.split(",") if project.tech_stack else [],
        "constraints": constraints,
        "status": project.status,
        "is_public": project.is_public,
        "github_repo_url": project.github_repo_url,
        "github_repo_name": project.github_repo_name,
        "settings": settings,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "generation_count": getattr(project, 'generation_count', 0),
        "last_generation_at": getattr(project, 'last_generation_at', None)
    }


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
    
    # Handle tech_stack: convert list to single string (join with commas) 
    # since the model expects a single string, not a list
    if "tech_stack" in project_dict and project_dict["tech_stack"]:
        if isinstance(project_dict["tech_stack"], list):
            project_dict["tech_stack"] = ",".join(project_dict["tech_stack"])
    else:
        project_dict["tech_stack"] = ""  # Set default empty string
    
    try:
        project = await repo.create(project_dict)
        
        # Convert string fields back to expected types for response
        project_data = {
            "id": project.id,
            "user_id": project.user_id,
            "organization_id": project.organization_id,
            "name": project.name,
            "description": project.description,
            "domain": project.domain,
            "tech_stack": project.tech_stack.split(",") if project.tech_stack else [],
            "constraints": project.constraints or {},
            "status": project.status,
            "is_public": project.is_public,
            "github_repo_url": project.github_repo_url,
            "github_repo_name": project.github_repo_name,
            "settings": project.settings or {},
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "generation_count": 0,  # Default for new project
            "last_generation_at": None
        }
        
        return ProjectResponse(**project_data)
        
    except Exception as e:
        # Surface error details for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project creation failed: {str(e)}"
        )


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
    
    # Convert to response models, handling tech_stack and constraints conversion
    project_responses = []
    for p in projects:
        # Handle constraints: parse JSON string to dict
        constraints = p.constraints or {}
        if isinstance(constraints, str):
            try:
                import json
                constraints = json.loads(constraints) if constraints.strip() else {}
            except (json.JSONDecodeError, AttributeError):
                constraints = {}
        
        # Handle settings: parse JSON string to dict  
        settings = p.settings or {}
        if isinstance(settings, str):
            try:
                import json
                settings = json.loads(settings) if settings.strip() else {}
            except (json.JSONDecodeError, AttributeError):
                settings = {}
        
        project_data = {
            "id": p.id,
            "user_id": p.user_id,
            "organization_id": p.organization_id,
            "name": p.name,
            "description": p.description,
            "domain": p.domain,
            "tech_stack": p.tech_stack.split(",") if p.tech_stack else [],
            "constraints": constraints,
            "status": p.status,
            "is_public": p.is_public,
            "github_repo_url": p.github_repo_url,
            "github_repo_name": p.github_repo_name,
            "settings": settings,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "generation_count": getattr(p, 'generation_count', 0),
            "last_generation_at": getattr(p, 'last_generation_at', None)
        }
        project_responses.append(ProjectResponse(**project_data))
    
    # Calculate pagination values
    page = (skip // limit) + 1
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    return PaginatedProjectResponse(
        projects=project_responses,
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages
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
    
    # Convert to response models, handling tech_stack and constraints conversion
    project_responses = []
    for p in projects:
        # Handle constraints: parse JSON string to dict
        constraints = p.constraints or {}
        if isinstance(constraints, str):
            try:
                import json
                constraints = json.loads(constraints) if constraints.strip() else {}
            except (json.JSONDecodeError, AttributeError):
                constraints = {}
        
        # Handle settings: parse JSON string to dict  
        settings = p.settings or {}
        if isinstance(settings, str):
            try:
                import json
                settings = json.loads(settings) if settings.strip() else {}
            except (json.JSONDecodeError, AttributeError):
                settings = {}
        
        project_data = {
            "id": p.id,
            "user_id": p.user_id,
            "organization_id": p.organization_id,
            "name": p.name,
            "description": p.description,
            "domain": p.domain,
            "tech_stack": p.tech_stack.split(",") if p.tech_stack else [],
            "constraints": constraints,
            "status": p.status,
            "is_public": p.is_public,
            "github_repo_url": p.github_repo_url,
            "github_repo_name": p.github_repo_name,
            "settings": settings,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "generation_count": getattr(p, 'generation_count', 0),
            "last_generation_at": getattr(p, 'last_generation_at', None)
        }
        project_responses.append(ProjectResponse(**project_data))
    
    # Calculate pagination values
    page = (skip // limit) + 1
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    return PaginatedProjectResponse(
        projects=project_responses,
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages
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
    
    # Convert to response models, handling tech_stack and constraints conversion
    project_responses = []
    for p in projects:
        # Handle constraints: parse JSON string to dict
        constraints = p.constraints or {}
        if isinstance(constraints, str):
            try:
                import json
                constraints = json.loads(constraints) if constraints.strip() else {}
            except (json.JSONDecodeError, AttributeError):
                constraints = {}
        
        # Handle settings: parse JSON string to dict  
        settings = p.settings or {}
        if isinstance(settings, str):
            try:
                import json
                settings = json.loads(settings) if settings.strip() else {}
            except (json.JSONDecodeError, AttributeError):
                settings = {}
        
        project_data = {
            "id": p.id,
            "user_id": p.user_id,
            "organization_id": p.organization_id,
            "name": p.name,
            "description": p.description,
            "domain": p.domain,
            "tech_stack": p.tech_stack.split(",") if p.tech_stack else [],
            "constraints": constraints,
            "status": p.status,
            "is_public": p.is_public,
            "github_repo_url": p.github_repo_url,
            "github_repo_name": p.github_repo_name,
            "settings": settings,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "generation_count": getattr(p, 'generation_count', 0),
            "last_generation_at": getattr(p, 'last_generation_at', None)
        }
        project_responses.append(ProjectResponse(**project_data))
    
    # Calculate pagination values
    total = len(project_responses)  # Simplified count
    page = (skip // limit) + 1
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    return PaginatedProjectResponse(
        projects=project_responses,
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages
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
    
    # Convert to response model, handling tech_stack conversion
    project_data = {
        "id": project.id,
        "user_id": project.user_id,
        "organization_id": project.organization_id,
        "name": project.name,
        "description": project.description,
        "domain": project.domain,
        "tech_stack": project.tech_stack.split(",") if project.tech_stack else [],
        "constraints": project.constraints or {},
        "status": project.status,
        "is_public": project.is_public,
        "github_repo_url": project.github_repo_url,
        "github_repo_name": project.github_repo_name,
        "settings": project.settings or {},
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "generation_count": getattr(project, 'generation_count', 0),
        "last_generation_at": getattr(project, 'last_generation_at', None)
    }
    
    return ProjectResponse(**project_data)


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
    
    # Convert to response model, handling tech_stack conversion
    project_data = {
        "id": updated_project.id,
        "user_id": updated_project.user_id,
        "organization_id": updated_project.organization_id,
        "name": updated_project.name,
        "description": updated_project.description,
        "domain": updated_project.domain,
        "tech_stack": updated_project.tech_stack.split(",") if updated_project.tech_stack else [],
        "constraints": updated_project.constraints or {},
        "status": updated_project.status,
        "is_public": updated_project.is_public,
        "github_repo_url": updated_project.github_repo_url,
        "github_repo_name": updated_project.github_repo_name,
        "settings": updated_project.settings or {},
        "created_at": updated_project.created_at,
        "updated_at": updated_project.updated_at,
        "generation_count": getattr(updated_project, 'generation_count', 0),
        "last_generation_at": getattr(updated_project, 'last_generation_at', None)
    }
    
    return ProjectResponse(**project_data)


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
