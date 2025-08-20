"""
Generations router for AI-powered code generation endpoints.
"""

import asyncio
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from app.core.database import get_async_db
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.repositories.generation_repository import GenerationRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.generation import (
    GenerationCreate, GenerationUpdate, GenerationResponse, 
    GenerationStatsResponse, GenerationFilters, StreamingProgress,
    TemplateSearchRequest, TemplateSearchResponse, 
    GenerationFileResponse, GenerationSearchRequest, GenerationSearchResponse,
    GitHubDeploymentRequest, GitHubDeploymentResponse,
    GenerationComparisonRequest, GenerationComparisonResponse
)
from app.schemas.user import UserResponse
from app.services.ai_orchestrator import ai_orchestrator
from app.services.file_manager import file_manager
from app.services.github_service import github_service
from app.services.quality_assessor import quality_assessor
from app.services.generation_file_service import (
    generation_file_service, generation_search_service, template_search_service
)
from app.services.github_deployment_service import (
    github_deployment_service, generation_comparison_service
)
from app.models.generation import Generation

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new code generation",
    description="Start a new AI-powered code generation process"
)
async def create_generation(
    generation_data: GenerationCreate,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new generation request"""
    generation_repo = GenerationRepository(db)
    project_repo = ProjectRepository(db)
    
    # Verify project exists and user has access
    project = await project_repo.get_by_id(generation_data.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to generate code for this project"
        )
    
    # Create generation record
    generation = Generation(
        user_id=current_user.id,
        project_id=generation_data.project_id,
        type=generation_data.type,
        template=generation_data.template,
        description=generation_data.description,
        requirements=generation_data.requirements,
        template_variables=generation_data.template_variables,
        parent_generation_id=generation_data.parent_generation_id,
        is_iteration=generation_data.parent_generation_id is not None,
        status="pending"
    )
    
    saved_generation = await generation_repo.create(generation)
    
    # Start generation process in background
    background_tasks.add_task(
        start_generation_process,
        saved_generation.id,
        generation_data.dict()
    )
    
    return GenerationResponse.from_orm(saved_generation)


@router.get(
    "/",
    response_model=List[GenerationResponse],
    summary="List user generations",
    description="Get paginated list of user's generations with filtering"
)
async def list_generations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    status: Optional[str] = Query(None, description="Filter by generation status"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    is_iteration: Optional[bool] = Query(None, description="Filter iterations"),
    min_quality_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum quality score"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List user's generations with filtering and pagination"""
    generation_repo = GenerationRepository(db)
    
    filters = GenerationFilters(
        status=status,
        project_id=project_id,
        is_iteration=is_iteration,
        min_quality_score=min_quality_score
    )
    
    generations = await generation_repo.get_by_user_id(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        filters=filters
    )
    
    return [GenerationResponse.from_orm(gen) for gen in generations]


@router.get(
    "/{generation_id}",
    response_model=GenerationResponse,
    summary="Get generation details",
    description="Get detailed information about a specific generation"
)
async def get_generation(
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get generation by ID"""
    generation_repo = GenerationRepository(db)
    
    generation = await generation_repo.get_by_id(generation_id)
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this generation"
        )
    
    return GenerationResponse.from_orm(generation)


@router.patch(
    "/{generation_id}",
    response_model=GenerationResponse,
    summary="Update generation",
    description="Update generation details (limited fields)"
)
async def update_generation(
    generation_id: str,
    generation_update: GenerationUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update a generation"""
    generation_repo = GenerationRepository(db)
    
    generation = await generation_repo.get_by_id(generation_id)
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this generation"
        )
    
    # Update only allowed fields
    update_data = generation_update.dict(exclude_unset=True)
    updated_generation = await generation_repo.update(generation_id, update_data)
    
    return GenerationResponse.from_orm(updated_generation)


@router.delete(
    "/{generation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete generation",
    description="Delete a generation and its artifacts"
)
async def delete_generation(
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a generation"""
    generation_repo = GenerationRepository(db)
    
    generation = await generation_repo.get_by_id(generation_id)
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this generation"
        )
    
    await generation_repo.delete(generation_id)


@router.post(
    "/{generation_id}/cancel",
    response_model=GenerationResponse,
    summary="Cancel generation",
    description="Cancel a pending or processing generation"
)
async def cancel_generation(
    generation_id: str,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Cancel a generation request"""
    generation_repo = GenerationRepository(db)
    
    generation = await generation_repo.get_by_id(generation_id)
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to cancel this generation"
        )
    
    if generation.status not in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel generation with status: {generation.status}"
        )
    
    cancelled_generation = await generation_repo.cancel_generation(generation_id, reason)
    return GenerationResponse.from_orm(cancelled_generation)


@router.get(
    "/{generation_id}/stream",
    summary="Stream generation progress",
    description="Get real-time streaming updates of generation progress"
)
async def stream_generation_progress(
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Stream generation progress in real-time"""
    generation_repo = GenerationRepository(db)
    
    generation = await generation_repo.get_by_id(generation_id)
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this generation"
        )
    
    async def generate_progress_stream():
        """Generate Server-Sent Events for progress updates"""
        while True:
            # Get latest generation state
            current_generation = await generation_repo.get_by_id(generation_id)
            if not current_generation:
                break
                
            progress = StreamingProgress(
                status=current_generation.status,
                stage="unknown",  # This would be set by the AI orchestrator
                progress_percent=0.0,  # This would be calculated based on stage
                message=f"Generation is {current_generation.status}",
                estimated_time_remaining=None
            )
            
            # Send progress update
            yield f"data: {progress.json()}\n\n"
            
            # Break if generation is complete
            if current_generation.status in ["completed", "failed", "cancelled"]:
                break
                
            # Wait before next update
            await asyncio.sleep(2)
    
    return StreamingResponse(
        generate_progress_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@router.get(
    "/{generation_id}/iterations",
    response_model=List[GenerationResponse],
    summary="Get generation iterations",
    description="Get all iterations of a parent generation"
)
async def get_generation_iterations(
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get all iterations of a generation"""
    generation_repo = GenerationRepository(db)
    
    # Verify parent generation exists and user has access
    parent_generation = await generation_repo.get_by_id(generation_id)
    if not parent_generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if parent_generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this generation"
        )
    
    iterations = await generation_repo.get_iterations(generation_id)
    return [GenerationResponse.from_orm(iteration) for iteration in iterations]


@router.post(
    "/{generation_id}/iterate",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create generation iteration",
    description="Create a new iteration based on existing generation"
)
async def create_iteration(
    generation_id: str,
    iteration_data: GenerationCreate,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create an iteration of an existing generation"""
    generation_repo = GenerationRepository(db)
    
    # Verify parent generation exists and user has access
    parent_generation = await generation_repo.get_by_id(generation_id)
    if not parent_generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent generation not found"
        )
    
    if parent_generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to iterate on this generation"
        )
    
    # Force iteration settings
    iteration_data.parent_generation_id = generation_id
    iteration_data.project_id = parent_generation.project_id
    
    # Create iteration
    iteration = Generation(
        user_id=current_user.id,
        project_id=parent_generation.project_id,
        type=iteration_data.type,
        template=iteration_data.template,
        description=iteration_data.description,
        requirements=iteration_data.requirements,
        template_variables=iteration_data.template_variables,
        parent_generation_id=generation_id,
        is_iteration=True,
        status="pending"
    )
    
    saved_iteration = await generation_repo.create(iteration)
    
    # Start iteration process in background
    background_tasks.add_task(
        start_generation_process,
        saved_iteration.id,
        iteration_data.dict()
    )
    
    return GenerationResponse.from_orm(saved_iteration)


@router.get(
    "/statistics",
    response_model=GenerationStatsResponse,
    summary="Get generation statistics",
    description="Get comprehensive statistics for user's generations"
)
async def get_generation_statistics(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user's generation statistics"""
    generation_repo = GenerationRepository(db)
    
    stats = await generation_repo.get_user_statistics(current_user.id)
    return stats


@router.get(
    "/project/{project_id}",
    response_model=List[GenerationResponse],
    summary="Get project generations",
    description="Get all generations for a specific project"
)
async def get_project_generations(
    project_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get all generations for a project"""
    generation_repo = GenerationRepository(db)
    project_repo = ProjectRepository(db)
    
    # Verify project exists and user has access
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this project's generations"
        )
    
    generations = await generation_repo.get_by_project_id(project_id)
    return [GenerationResponse.from_orm(gen) for gen in generations]


@router.get(
    "/active",
    response_model=List[GenerationResponse],
    summary="Get active generations",
    description="Get all pending or processing generations for current user"
)
async def get_active_generations(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user's active generations"""
    generation_repo = GenerationRepository(db)
    
    active_generations = await generation_repo.get_active_generations(current_user.id)
    return [GenerationResponse.from_orm(gen) for gen in active_generations]


# Background task for generation processing
async def start_generation_process(generation_id: str, generation_data: dict):
    """Background task to handle generation process"""
    try:
        # This would integrate with the AI orchestrator
        await ai_orchestrator.process_generation(generation_id, generation_data)
    except Exception as e:
        # Update generation status to failed
        # In a real implementation, we'd need to get a new DB session here
        logger.error(f"Generation {generation_id} failed: {e}")
        # TODO: Update generation status to failed with error message


@router.get(
    "/{generation_id}/files",
    response_model=dict,
    summary="Get generation files",
    description="Get all files from a completed generation"
)
async def get_generation_files(
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get all files from a generation"""
    generation_repo = GenerationRepository(db)
    generation = await generation_repo.get_by_id(generation_id)
    
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get files from file manager
    files = await file_manager.get_project_files(generation_id)
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation files not found"
        )
    
    return {"files": files}


@router.get(
    "/{generation_id}/download",
    response_class=FileResponse,
    summary="Download generation",
    description="Download the generated project as a ZIP file"
)
async def download_generation(
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Download generation as ZIP file"""
    generation_repo = GenerationRepository(db)
    generation = await generation_repo.get_by_id(generation_id)
    
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Create ZIP archive if it doesn't exist
    zip_path = await file_manager.create_zip_archive(generation_id)
    
    if not zip_path or not zip_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated files not found"
        )
    
    return FileResponse(
        path=zip_path,
        filename=f"codebegen_project_{generation_id}.zip",
        media_type="application/zip"
    )


@router.get(
    "/{generation_id}/review",
    summary="Get code review",
    description="Get AI-generated code review for the project"
)
async def get_code_review(
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get code review for generation"""
    generation_repo = GenerationRepository(db)
    generation = await generation_repo.get_by_id(generation_id)
    
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get files and perform quality assessment
    files = await file_manager.get_project_files(generation_id)
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation files not found"
        )
    
    # Perform quality assessment
    quality_report = await quality_assessor.assess_project(generation_id, files)
    
    return {
        "generation_id": generation_id,
        "quality_report": {
            "overall_score": quality_report.overall_score,
            "overall_level": quality_report.overall_level,
            "total_files": quality_report.total_files,
            "total_lines": quality_report.total_lines,
            "issues": [
                {
                    "file": issue.file,
                    "line": issue.line,
                    "severity": issue.severity,
                    "category": issue.category,
                    "message": issue.message,
                    "suggestion": issue.suggestion
                } for issue in quality_report.issues
            ],
            "metrics": quality_report.metrics,
            "recommendations": quality_report.recommendations
        }
    }


@router.post(
    "/{generation_id}/export",
    summary="Export to GitHub",
    description="Export the generated project to a GitHub repository"
)
async def export_to_github(
    generation_id: str,
    export_data: dict,  # Should include repo_name, description, private, etc.
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Export generation to GitHub"""
    generation_repo = GenerationRepository(db)
    generation = await generation_repo.get_by_id(generation_id)
    
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get user's GitHub access token (this would come from OAuth)
    github_token = export_data.get("github_token")
    if not github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub access token required"
        )
    
    repo_name = export_data.get("repo_name", f"codebegen_project_{generation_id}")
    description = export_data.get("description", "Generated by CodebeGen")
    private = export_data.get("private", False)
    
    try:
        # Create GitHub repository
        repo_info = await github_service.create_repository(
            access_token=github_token,
            repo_name=repo_name,
            description=description,
            private=private
        )
        
        # Upload files to repository
        success = await github_service.upload_files_to_repo(
            access_token=github_token,
            owner=repo_info["owner"]["login"],
            repo_name=repo_name,
            generation_id=generation_id,
            commit_message="Initial commit from CodebeGen"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload files to GitHub"
            )
        
        return {
            "success": True,
            "repository_url": repo_info["html_url"],
            "clone_url": repo_info["clone_url"],
            "message": "Project successfully exported to GitHub"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub export failed: {str(e)}"
        )


@router.get(
    "/templates",
    summary="Get available templates",
    description="Get list of available project templates"
)
async def get_available_templates():
    """Get available project templates"""
    # This would come from the template service
    return {
        "templates": [
            {
                "name": "fastapi_basic",
                "display_name": "FastAPI Basic",
                "description": "Basic FastAPI project with authentication",
                "tech_stack": ["fastapi", "pydantic", "uvicorn"]
            },
            {
                "name": "fastapi_sqlalchemy",
                "display_name": "FastAPI + SQLAlchemy",
                "description": "FastAPI with SQLAlchemy ORM and PostgreSQL",
                "tech_stack": ["fastapi", "sqlalchemy", "postgresql", "alembic"]
            },
            {
                "name": "fastapi_mongo",
                "display_name": "FastAPI + MongoDB",
                "description": "FastAPI with MongoDB database",
                "tech_stack": ["fastapi", "motor", "mongodb", "beanie"]
            }
        ]
    }


@router.get(
    "/recent",
    response_model=List[GenerationResponse],
    summary="Get recent generations",
    description="Get user's most recent generations"
)
async def get_recent_generations(
    limit: int = Query(10, ge=1, le=50),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user's recent generations"""
    generation_repo = GenerationRepository(db)
    
    recent_generations = await generation_repo.get_recent_generations(
        user_id=current_user.id, 
        limit=limit
    )
    
    return [GenerationResponse.from_orm(gen) for gen in recent_generations]


@router.get(
    "/{generation_id}/files/{file_path:path}",
    response_model=GenerationFileResponse,
    summary="Get individual file content",
    description="Get content of a specific file from generation for code viewer"
)
async def get_generation_file(
    generation_id: str,
    file_path: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get content of a specific file from generation"""
    generation_repo = GenerationRepository(db)
    generation = await generation_repo.get_by_id(generation_id)
    
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        file_response = await generation_file_service.get_file_content(generation_id, file_path)
        return file_response
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{generation_id}/search",
    response_model=GenerationSearchResponse,
    summary="Search within generated files",
    description="Search for text within all files of a generation"
)
async def search_generation_files(
    generation_id: str,
    search_request: GenerationSearchRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Search within all files of a generation"""
    generation_repo = GenerationRepository(db)
    generation = await generation_repo.get_by_id(generation_id)
    
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        search_results = await generation_search_service.search_generation(generation_id, search_request)
        return search_results
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation files not found"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/templates/search",
    response_model=TemplateSearchResponse,
    summary="Search and filter templates",
    description="Search for templates based on criteria like domain, tech stack, etc."
)
async def search_templates(
    query: Optional[str] = Query(None, min_length=2, max_length=100, description="Search query"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    tech_stack: Optional[List[str]] = Query(None, description="Filter by tech stack"),
    complexity: Optional[str] = Query(None, description="Filter by complexity (low, medium, high)"),
    features: Optional[List[str]] = Query(None, description="Filter by features"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """Search and filter available templates"""
    search_request = TemplateSearchRequest(
        query=query,
        domain=domain,
        tech_stack=tech_stack,
        complexity=complexity,
        features=features
    )
    
    template_results = await template_search_service.search_templates(search_request)
    return template_results


@router.post(
    "/{generation_id}/deploy/github",
    response_model=GitHubDeploymentResponse,
    summary="Deploy to GitHub with advanced options",
    description="Deploy generation to GitHub with CI/CD, Pages, or Vercel configuration"
)
async def deploy_to_github_advanced(
    generation_id: str,
    deployment_request: GitHubDeploymentRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Deploy generation to GitHub with advanced deployment options"""
    generation_repo = GenerationRepository(db)
    generation = await generation_repo.get_by_id(generation_id)
    
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        deployment_result = await github_deployment_service.deploy_to_github(
            generation_id, deployment_request
        )
        
        if not deployment_result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=deployment_result.message
            )
        
        return deployment_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"GitHub deployment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}"
        )


@router.get(
    "/compare/{generation_id_1}/{generation_id_2}",
    response_model=GenerationComparisonResponse,
    summary="Compare two generations",
    description="Compare two generations and analyze differences in files, structure, and metrics"
)
async def compare_generations(
    generation_id_1: str,
    generation_id_2: str,
    include_content: bool = Query(True, description="Include file content differences"),
    comparison_type: str = Query("diff", description="Type of comparison: diff, structure, metrics"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Compare two generations and return detailed analysis"""
    generation_repo = GenerationRepository(db)
    
    # Verify both generations exist and user has access
    generation_1 = await generation_repo.get_by_id(generation_id_1)
    generation_2 = await generation_repo.get_by_id(generation_id_2)
    
    if not generation_1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation {generation_id_1} not found"
        )
    
    if not generation_2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation {generation_id_2} not found"
        )
    
    if generation_1.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to generation {generation_id_1}"
        )
    
    if generation_2.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to generation {generation_id_2}"
        )
    
    try:
        comparison_request = GenerationComparisonRequest(
            include_content=include_content,
            comparison_type=comparison_type
        )
        
        comparison_result = await generation_comparison_service.compare_generations(
            generation_id_1, generation_id_2, comparison_request
        )
        
        return comparison_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Generation comparison failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison failed: {str(e)}"
        )
