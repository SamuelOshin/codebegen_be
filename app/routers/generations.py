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
    generation_file_service, generation_search_service
)

from app.services.github_deployment_service import (
    github_deployment_service, generation_comparison_service
)
from app.models.generation import Generation
import time
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.auth.dependencies import get_current_user
from app.schemas.unified_generation import (
    UnifiedGenerationRequest, 
    UnifiedGenerationResponse, 
    GenerationMode,
    StreamingProgressEvent,
    IterationRequest
)
from app.schemas.user import UserResponse
from app.services.generation_feature_flag import generation_feature_flag
from app.services.enhanced_generation_service import create_enhanced_generation_service
from app.services.ai_orchestrator import ai_orchestrator
from app.services.enhanced_ab_testing import enhanced_ab_test_manager, GenerationMetrics, GenerationMethod
from app.services.validation_metrics import validation_metrics
from app.services.file_manager import file_manager
from app.services.quality_assessor import quality_assessor
from app.repositories.generation_repository import GenerationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.generation import GenerationStatus


logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory event store for streaming (in production, use Redis)
generation_events = {}

# Enhanced service cache
enhanced_service_cache = {}



async def get_enhanced_generation_service(db: AsyncSession = Depends(get_async_db)):
    """Get or create Enhanced Generation Service instance"""
    if "enhanced_service" not in enhanced_service_cache:
        project_repo = ProjectRepository(db)
        user_repo = UserRepository(db)
        generation_repo = GenerationRepository(db)
        
        service = create_enhanced_generation_service(
            project_repository=project_repo,
            user_repository=user_repo,
            generation_repository=generation_repo
        )
        
        await service.initialize()
        enhanced_service_cache["enhanced_service"] = service
    
    return enhanced_service_cache["enhanced_service"]


@router.post(
    "/generate",
    response_model=UnifiedGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI-powered code",
    description="Unified endpoint for both classic and enhanced code generation"
)
async def generate_project(
    request: UnifiedGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    enhanced_service=Depends(get_enhanced_generation_service),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Unified generation endpoint that supports both classic and enhanced modes.
    Mode is determined automatically based on feature flags and A/B testing,
    or can be explicitly specified in the request.
    """
    try:
        # Get generation configuration based on feature flags
        generation_config = generation_feature_flag.get_generation_config(
            user_id=current_user.id,
            requested_mode=request.generation_mode,
            is_iteration=request.is_iteration,
            project_id=request.project_id
        )
        
        logger.info(f"Generation mode selected: {generation_config.mode} for user {current_user.id}")
        
        # Validate project access if project_id is provided
        if request.project_id:
            await _validate_project_access(request.project_id, current_user.id, db)
        
        # Generate unique ID for this generation
        generation_id = str(uuid4())
        
        # Initialize event stream
        generation_events[generation_id] = []
        
        # Create generation record in database
        generation_record = await _create_generation_record(
            generation_id, request, current_user.id, generation_config, db
        )
        
        # Start appropriate background processing
        if generation_config.mode == GenerationMode.ENHANCED:
            background_tasks.add_task(
                _process_enhanced_generation,
                generation_id,
                request,
                current_user.id,
                enhanced_service,
                generation_config,
                db
            )
        else:
            background_tasks.add_task(
                _process_classic_generation,
                generation_id,
                request,
                current_user.id,
                generation_config,
                db
            )
        
        # Return unified response
        return UnifiedGenerationResponse(
            generation_id=generation_id,
            status=GenerationStatus.PENDING,
            message=f"Generation started in {generation_config.mode} mode",
            user_id=current_user.id,
            project_id=request.project_id,
            prompt=request.prompt,
            context=request.context,
            generation_mode=generation_config.mode,
            ab_group=generation_config.ab_group,
            enhanced_features=generation_config.features_enabled,
            is_iteration=request.is_iteration,
            parent_generation_id=request.parent_generation_id,
            created_at=generation_record.created_at,
            updated_at=generation_record.updated_at
        )
        
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Unexpected error in unified generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during generation"
        )


@router.get(
    "/generate/{generation_id}/stream",
    summary="Stream generation progress",
    description="Get real-time streaming updates of generation progress"
)
async def stream_generation_progress(
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Stream real-time generation progress with unified event format"""
    
    async def event_stream():
        last_event_index = 0
        
        while True:
            try:
                # Check if there are new events
                if generation_id in generation_events:
                    events = generation_events[generation_id]
                    
                    # Send new events
                    for event in events[last_event_index:]:
                        # Convert to unified format
                        unified_event = StreamingProgressEvent(
                            generation_id=generation_id,
                            status=event.get("status", "processing"),
                            stage=event.get("stage", "unknown"),
                            progress=event.get("progress", 0) / 100.0,  # Convert to 0-1 range
                            message=event.get("message", "Processing..."),
                            ab_group=event.get("ab_group"),
                            enhanced_features=event.get("enhanced_features"),
                            generation_mode=event.get("generation_mode"),
                            timestamp=event.get("timestamp", time.time())
                        )
                        
                        yield f"data: {unified_event.json()}\\n\\n"
                        last_event_index += 1
                    
                    # Check if generation is complete
                    if events and events[-1].get("status") in ["completed", "failed"]:
                        break
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in event stream: {e}")
                yield f"data: {{'error': '{str(e)}'}}\\n\\n"
                break
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.post(
    "/iterate",
    response_model=UnifiedGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create generation iteration",
    description="Create a new iteration based on existing generation"
)
async def create_iteration(
    request: IterationRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    enhanced_service=Depends(get_enhanced_generation_service),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new iteration based on existing generation"""
    
    try:
        # Validate parent generation exists and user has access
        generation_repo = GenerationRepository(db)
        parent_generation = await generation_repo.get_by_id(request.parent_generation_id)
        
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
        
        # Create unified request for iteration
        unified_request = UnifiedGenerationRequest(
            prompt=request.modification_prompt,
            project_id=parent_generation.project_id,
            context=request.context,
            is_iteration=True,
            parent_generation_id=request.parent_generation_id,
            generation_mode=request.generation_mode
        )
        
        # Process as regular generation
        return await generate_project(
            unified_request,
            background_tasks,
            current_user,
            enhanced_service,
            db
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating iteration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create iteration"
        )


# Helper functions

async def _validate_project_access(project_id: str, user_id: str, db: AsyncSession):
    """Validate that user has access to the project"""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this project"
        )


async def _create_generation_record(
    generation_id: str,
    request: UnifiedGenerationRequest,
    user_id: str,
    generation_config,
    db: AsyncSession
):
    """Create generation record in database"""
    generation_repo = GenerationRepository(db)
    project_repo = ProjectRepository(db)
    
    # Handle project_id requirement - create default project if none provided
    project_id = request.project_id
    if not project_id:
        # Create or get default project for standalone generations
        default_project_name = f"Standalone Generations - {datetime.utcnow().strftime('%Y-%m')}"
        
        # Try to find existing default project for this user
        user_projects = await project_repo.get_by_user_id(user_id)
        default_project = None
        
        for project in user_projects:
            if project.name.startswith("Standalone Generations"):
                default_project = project
                break
        
        # Create default project if it doesn't exist
        if not default_project:
            default_project_data = {
                "name": default_project_name,
                "description": "Auto-created project for standalone AI generations",
                "user_id": user_id,
                "tech_stack": request.tech_stack or "fastapi_postgres",
                "domain": request.domain or "general",
                "settings": {
                    "auto_created": True,
                    "type": "standalone_generations",
                    "created_for": "unified_generation_router"
                }
            }
            default_project = await project_repo.create(default_project_data)
        
        project_id = default_project.id
    
    generation_data = {
        "id": generation_id,
        "user_id": user_id,
        "project_id": project_id,  # Now guaranteed to be not None
        "prompt": request.prompt,
        "context": {
            **request.context,
            "generation_mode": generation_config.mode,
            "ab_group": generation_config.ab_group,
            "enhanced_features": generation_config.features_enabled
        },
        "is_iteration": request.is_iteration,
        "parent_generation_id": request.parent_generation_id,
        "status": "pending"
    }
    
    return await generation_repo.create(generation_data)


async def _process_enhanced_generation(
    generation_id: str,
    request: UnifiedGenerationRequest,
    user_id: str,
    enhanced_service,
    generation_config,
    db: AsyncSession
):
    """Process generation using enhanced mode with full consolidated logic"""
    try:
        # Start AB testing assignment and metrics tracking
        ab_assignment = enhanced_ab_test_manager.assign_user(user_id)
        
        logger.info(f"Enhanced generation {generation_id} assigned to group: {ab_assignment.group}")
        
        # Emit initial progress
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "context_analysis",
            "message": "Analyzing context and requirements...",
            "progress": 10,
            "generation_mode": generation_config.mode,
            "ab_group": ab_assignment.group
        })
        
        # Step 1: Context Analysis (if enabled)
        context_analysis = None
        if generation_config.use_context_analysis:
            context_analysis = await enhanced_service.analyze_context(
                prompt=request.prompt,
                project_context=request.context,
                tech_stack=request.tech_stack or "fastapi_postgres"
            )
            
            await _emit_event(generation_id, {
                "status": "processing",
                "stage": "prompt_enhancement",
                "message": "Enhancing prompts based on context...",
                "progress": 25,
                "generation_mode": generation_config.mode
            })
        
        # Step 2: Enhanced Prompt Generation (if enabled)
        enhanced_prompt = request.prompt
        if generation_config.use_enhanced_prompts:
            enhanced_prompt = await enhanced_service.enhance_prompt(
                original_prompt=request.prompt,
                context_analysis=context_analysis,
                user_patterns=await enhanced_service.get_user_patterns(user_id) if generation_config.use_user_patterns else None
            )
        
        await _emit_event(generation_id, {
            "status": "processing", 
            "stage": "code_generation",
            "message": "Generating code using AI models...",
            "progress": 40,
            "generation_mode": generation_config.mode
        })
        
        # Step 3: AI Code Generation
        if generation_config.use_hybrid_generation:
            # Use hybrid approach (templates + AI)
            generation_result = await enhanced_service.hybrid_generate(
                prompt=enhanced_prompt,
                context=request.context,
                tech_stack=request.tech_stack or "fastapi_postgres",
                domain=request.domain,
                constraints=request.constraints
            )
        else:
            # Use AI orchestrator directly
            generation_result = await ai_orchestrator.process_generation(
                prompt=enhanced_prompt,
                context={
                    **request.context,
                    "tech_stack": request.tech_stack or "fastapi_postgres",
                    "domain": request.domain,
                    "constraints": request.constraints
                },
                user_id=user_id,
                generation_id=generation_id
            )
        
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "quality_assessment", 
            "message": "Assessing code quality...",
            "progress": 70,
            "generation_mode": generation_config.mode
        })
        
        # Step 4: Quality Assessment
        quality_metrics = await quality_assessor.assess_project(
            generation_id=generation_id,
            files=generation_result.get("files", {})
        )
        
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "file_management",
            "message": "Organizing and saving files...",
            "progress": 85,
            "generation_mode": generation_config.mode
        })
        
        # Step 5: File Management and Storage
        file_metadata = await file_manager.save_generation_files(
            generation_id=generation_id,
            files=generation_result.get("files", {})
        )
        
        # Create downloadable ZIP
        zip_path = await file_manager.create_generation_zip(generation_id, user_id)
        
        # Step 6: Record Metrics and Validation
        if generation_config.use_metrics_tracking:
            generation_metrics = GenerationMetrics(
                generation_id=generation_id,
                user_id=user_id,
                group=ab_assignment.group,
                method=GenerationMethod.ENHANCED_PROMPTS,
                quality_score=quality_metrics.overall_score,
                complexity_score=getattr(quality_metrics, 'complexity_score', 0.5),
                file_count=len(generation_result.get("files", {})),
                total_lines=sum(len(content.split('\n')) for content in generation_result.get("files", {}).values()),
                test_coverage=getattr(quality_metrics, 'test_coverage', 0.0),
                generation_time_ms=int((time.time() - time.time()) * 1000),  # Will be calculated properly
                prompt_tokens=len(request.prompt.split()),
                response_tokens=sum(len(content.split()) for content in generation_result.get("files", {}).values()),
                user_modifications=0,  # Not yet available
                user_satisfaction=None,  # Not yet available
                abandoned=False,
                abandonment_stage=None,
                similar_projects_found=0,  # Will be tracked by enhanced service
                user_patterns_applied=0,  # Will be tracked by enhanced service
                template_confidence=getattr(quality_metrics, 'template_confidence', 0.5),
                deployment_success=False,  # Not yet available
                time_to_deployment=None,  # Not yet available
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
            enhanced_ab_test_manager.track_generation_metrics(generation_metrics)
            validation_metrics.track_generation_success(
                generation_id=generation_id,
                user_id=user_id,
                success=True,
                duration_ms=int(time.time() * 1000)
            )
        
        # Step 7: Update database with final result
        generation_repo = GenerationRepository(db)
        await generation_repo.update(
            generation_id,
            status="completed",
            result={
                **generation_result,
                "quality_metrics": quality_metrics.__dict__,
                "file_metadata": file_metadata,
                "download_url": f"/api/generations/{generation_id}/download"
            },
            completed_at=datetime.utcnow()
        )
        
        # Final success event
        await _emit_event(generation_id, {
            "status": "completed",
            "stage": "complete",
            "message": "Generation completed successfully",
            "progress": 100,
            "generation_mode": generation_config.mode,
            "ab_group": ab_assignment.group,
            "quality_score": quality_metrics.overall_score,
            "files_count": len(generation_result.get("files", {}))
        })
        
        logger.info(f"Enhanced generation {generation_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Enhanced generation failed for {generation_id}: {e}")
        
        # Record failure metrics
        if generation_config.use_metrics_tracking:
            failure_metrics = GenerationMetrics(
                generation_id=generation_id,
                user_id=user_id,
                group=getattr(ab_assignment, 'group', 'unknown'),
                method=GenerationMethod.ENHANCED_PROMPTS,
                quality_score=0.0,
                complexity_score=0.0,
                file_count=0,
                total_lines=0,
                test_coverage=0.0,
                generation_time_ms=0,
                prompt_tokens=len(request.prompt.split()),
                response_tokens=0,
                user_modifications=0,
                user_satisfaction=None,
                abandoned=True,
                abandonment_stage="generation_error",
                similar_projects_found=0,
                user_patterns_applied=0,
                template_confidence=0.0,
                deployment_success=False,
                time_to_deployment=None,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            enhanced_ab_test_manager.track_generation_metrics(failure_metrics)
            validation_metrics.track_generation_success(
                generation_id=generation_id,
                user_id=user_id,
                success=False,
                errors=[str(e)]
            )
        
        # Update database with failure
        generation_repo = GenerationRepository(db)
        await generation_repo.update(generation_id, 
            status="failed",
            error=str(e),
            failed_at=datetime.utcnow()
        )
        
        await _emit_event(generation_id, {
            "status": "failed",
            "stage": "error",
            "message": f"Enhanced generation failed: {str(e)}",
            "progress": 0,
            "generation_mode": generation_config.mode,
            "error": str(e)
        })


async def _process_classic_generation(
    generation_id: str,
    request: UnifiedGenerationRequest,
    user_id: str,
    generation_config,
    db: AsyncSession
):
    """Process generation using classic mode with full consolidated logic"""
    try:
        # Emit initial event
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "initializing",
            "message": "Starting classic generation...",
            "progress": 10,
            "generation_mode": generation_config.mode
        })
        
        # Step 1: Use AI orchestrator directly for classic generation
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "code_generation", 
            "message": "Generating code using classic AI pipeline...",
            "progress": 30,
            "generation_mode": generation_config.mode
        })
        
        # Classic generation uses AI orchestrator's process_generation method
        # This method processes the generation and updates the database, but doesn't return files
        # We need to use a different approach for classic generation
        
        # For now, let's use a simpler approach that generates the result directly
        try:
            # Create a GenerationRequest object for the orchestrator
            from app.services.ai_orchestrator import GenerationRequest
            orchestrator_request = GenerationRequest(
                prompt=request.prompt,
                context={
                    **request.context,
                    "tech_stack": request.tech_stack or "fastapi_postgres",
                    "domain": request.domain,
                    "constraints": request.constraints,
                    "generation_mode": "classic"
                },
                user_id=user_id,
                use_enhanced_prompts=False
            )
            
            # Use the generate_project method instead of process_generation
            generation_result = await ai_orchestrator.generate_project(orchestrator_request)
            
            # Convert GenerationResult to dict format
            result_dict = {
                "files": generation_result.files,
                "schema": generation_result.schema,
                "review_feedback": generation_result.review_feedback,
                "documentation": generation_result.documentation,
                "quality_score": generation_result.quality_score
            }
            
        except Exception as inner_e:
            logger.warning(f"Direct generation failed, falling back to process_generation: {inner_e}")
            # Fallback to process_generation (which handles the DB updates internally)
            await ai_orchestrator.process_generation(
                generation_id=generation_id,
                generation_data={
                    "prompt": request.prompt,
                    "context": {
                        **request.context,
                        "tech_stack": request.tech_stack or "fastapi_postgres",
                        "domain": request.domain,
                        "constraints": request.constraints,
                        "generation_mode": "classic"
                    },
                    "user_id": user_id,
                    "use_enhanced_prompts": False
                }
            )
            # In this case, the orchestrator handles everything, so we'll return early
            return
        
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "quality_assessment",
            "message": "Performing basic quality checks...",
            "progress": 60,
            "generation_mode": generation_config.mode
        })
        
        # Step 2: Basic Quality Assessment (simplified for classic mode)
        quality_metrics = await quality_assessor.assess_generation(
            generation_result=result_dict,
            original_prompt=request.prompt,
            enhanced_prompt=None,  # No enhanced prompt in classic mode
            context_analysis=None   # No context analysis in classic mode
        )
        
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "file_management",
            "message": "Organizing and saving files...",
            "progress": 80,
            "generation_mode": generation_config.mode
        })
        
        # Step 3: File Management and Storage
        file_metadata = await file_manager.save_generation_files(
            generation_id=generation_id,
            files=result_dict.get("files", {})
        )
        
        # Create downloadable ZIP
        zip_path = await file_manager.create_generation_zip(generation_id, user_id)
        
        # Step 4: Record basic metrics (if enabled)
        if generation_config.use_metrics_tracking:
            generation_metrics = GenerationMetrics(
                generation_id=generation_id,
                user_id=user_id,
                group=generation_config.ab_group or "classic",
                method=GenerationMethod.STANDARD,
                quality_score=quality_metrics.overall_score,
                complexity_score=getattr(quality_metrics, 'complexity_score', 0.5),
                file_count=len(result_dict.get("files", {})),
                total_lines=sum(len(content.split('\n')) for content in result_dict.get("files", {}).values()),
                test_coverage=getattr(quality_metrics, 'test_coverage', 0.0),
                generation_time_ms=int(time.time() * 1000),  # Simplified
                prompt_tokens=len(request.prompt.split()),
                response_tokens=sum(len(content.split()) for content in result_dict.get("files", {}).values()),
                user_modifications=0,
                user_satisfaction=None,
                abandoned=False,
                abandonment_stage=None,
                similar_projects_found=0,
                user_patterns_applied=0,
                template_confidence=getattr(quality_metrics, 'template_confidence', 0.0),
                deployment_success=False,
                time_to_deployment=None,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
            validation_metrics.track_generation_success(
                generation_id=generation_id,
                user_id=user_id,
                success=True,
                duration_ms=int(time.time() * 1000)
            )
        
        # Step 5: Update database with final result
        generation_repo = GenerationRepository(db)
        await generation_repo.update(
            generation_id,
            status="completed",
            result={
                **result_dict,
                "quality_metrics": quality_metrics.__dict__,
                "file_metadata": file_metadata,
                "download_url": f"/api/generations/{generation_id}/download"
            },
            completed_at=datetime.utcnow()
        )
        
        # Final success event
        await _emit_event(generation_id, {
            "status": "completed",
            "stage": "complete",
            "message": "Classic generation completed successfully",
            "progress": 100,
            "generation_mode": generation_config.mode,
            "quality_score": quality_metrics.overall_score,
            "files_count": len(result_dict.get("files", {}))
        })
        
        logger.info(f"Classic generation {generation_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Classic generation failed for {generation_id}: {e}")
        
        # Record failure metrics
        if generation_config.use_metrics_tracking:
            failure_metrics = GenerationMetrics(
                generation_id=generation_id,
                user_id=user_id,
                group=generation_config.ab_group or "classic",
                method=GenerationMethod.STANDARD,
                quality_score=0.0,
                complexity_score=0.0,
                file_count=0,
                total_lines=0,
                test_coverage=0.0,
                generation_time_ms=0,
                prompt_tokens=len(request.prompt.split()),
                response_tokens=0,
                user_modifications=0,
                user_satisfaction=None,
                abandoned=True,
                abandonment_stage="generation_error",
                similar_projects_found=0,
                user_patterns_applied=0,
                template_confidence=0.0,
                deployment_success=False,
                time_to_deployment=None,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
            validation_metrics.track_generation_success(
                generation_id=generation_id,
                user_id=user_id,
                success=False,
                errors=[str(e)]
            )
        
        # Update database with failure
        generation_repo = GenerationRepository(db)
        await generation_repo.update(generation_id, 
            status="failed",
            error=str(e),
            failed_at=datetime.utcnow()
        )
        
        await _emit_event(generation_id, {
            "status": "failed",
            "stage": "error",
            "message": f"Classic generation failed: {str(e)}",
            "progress": 0,
            "generation_mode": generation_config.mode,
            "error": str(e)
        })


async def _emit_event(generation_id: str, event_data: Dict[str, Any]):
    """Emit an event for streaming"""
    if generation_id not in generation_events:
        generation_events[generation_id] = []
    
    event_data["timestamp"] = time.time()
    generation_events[generation_id].append(event_data)
    
    # Keep only last 50 events to prevent memory bloat
    if len(generation_events[generation_id]) > 50:
        generation_events[generation_id] = generation_events[generation_id][-50:]


# Backward compatibility endpoints

@router.post(
    "/legacy/classic",
    response_model=UnifiedGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Legacy classic generation endpoint",
    description="Backward compatibility endpoint for classic generation",
    deprecated=False
)
async def legacy_classic_generation(
    request: UnifiedGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    enhanced_service=Depends(get_enhanced_generation_service),
    db: AsyncSession = Depends(get_async_db)
):
    """Legacy endpoint that forces classic mode for backward compatibility"""
    # Force classic mode
    request.generation_mode = GenerationMode.CLASSIC
    return await generate_project(request, background_tasks, current_user, enhanced_service, db)


@router.post(
    "/legacy/enhanced", 
    response_model=UnifiedGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Legacy enhanced generation endpoint",
    description="Backward compatibility endpoint for enhanced generation",
    deprecated=False
)
async def legacy_enhanced_generation(
    request: UnifiedGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    enhanced_service=Depends(get_enhanced_generation_service),
    db: AsyncSession = Depends(get_async_db)
):
    """Legacy endpoint that forces enhanced mode for backward compatibility"""
    # Force enhanced mode
    request.generation_mode = GenerationMode.ENHANCED
    return await generate_project(request, background_tasks, current_user, enhanced_service, db)


# Utility endpoints for debugging and monitoring

@router.get(
    "/config/{user_id}",
    summary="Get generation configuration for user",
    description="Debug endpoint to see what configuration a user would receive"
)
async def get_user_generation_config(
    user_id: str,
    generation_mode: GenerationMode = Query(GenerationMode.AUTO),
    is_iteration: bool = Query(False),
    project_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get generation configuration for a user (admin/debug endpoint)"""
    
    # Only allow users to check their own config unless admin
    if user_id != current_user.id and not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only check your own configuration"
        )
    
    config = generation_feature_flag.get_generation_config(
        user_id=user_id,
        requested_mode=generation_mode,
        is_iteration=is_iteration,
        project_id=project_id
    )
    
    return {
        "user_id": user_id,
        "generation_mode": config.mode,
        "ab_group": config.ab_group,
        "features_enabled": config.features_enabled,
        "expected_improvement": config.expected_improvement,
        "use_enhanced_prompts": config.use_enhanced_prompts,
        "use_context_analysis": config.use_context_analysis,
        "use_user_patterns": config.use_user_patterns,
        "use_hybrid_generation": config.use_hybrid_generation,
        "use_ab_testing": config.use_ab_testing,
        "use_metrics_tracking": config.use_metrics_tracking
    }


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
