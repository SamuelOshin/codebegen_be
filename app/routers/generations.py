"""
Generations router for AI-powered code generation endpoints.
"""

import asyncio
import json
from loguru import logger
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime

from app.core.database import get_async_db
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.repositories.generation_repository import GenerationRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.generation import (
    GenerationCreate, GenerationUpdate, GenerationResponse, 
    GenerationStatsResponse, GenerationFilters, StreamingProgress,
    GenerationFileResponse, GenerationSearchRequest, GenerationSearchResponse,
    GitHubDeploymentRequest, GitHubDeploymentResponse,
    GenerationComparisonRequest, GenerationComparisonResponse,
    GenerationSummary, VersionListResponse, ActivateGenerationRequest,
    ActivateGenerationResponse, VersionComparisonResponse
)
from app.schemas.user import UserResponse
from app.services.ai_orchestrator import ai_orchestrator
from app.services.file_manager import file_manager
from app.services.generation_service import GenerationService
from app.services.storage_manager import HybridStorageManager
from app.services.github_service import github_service
from app.services.quality_assessor import quality_assessor
from app.services.generation_file_service import (
    generation_file_service, generation_search_service
)

from app.services.github_deployment_service import (
    github_deployment_service, generation_comparison_service
)
from app.services.storage_integration_helper import storage_helper
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
    IterationRequest,
    UnifiedGenerationUpdate,
    GenerationDeletionRequest
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


logger = logger
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
        # Get project info for response
        project_repo = ProjectRepository(db)
        project = await project_repo.get_by_id(generation_record.project_id) if generation_record.project_id else None
        
        return UnifiedGenerationResponse(
            generation_id=generation_id,
            status=GenerationStatus.PENDING,
            message=f"Generation started in {generation_config.mode} mode",
            user_id=current_user.id,
            project_id=generation_record.project_id,
            prompt=request.prompt,
            context=request.context,
            generation_mode=generation_config.mode,
            ab_group=generation_config.ab_group,
            enhanced_features=generation_config.features_enabled,
            is_iteration=request.is_iteration,
            parent_generation_id=request.parent_generation_id,
            created_at=generation_record.created_at,
            updated_at=generation_record.updated_at,
            # Include auto-created project information
            auto_created_project=project.auto_created if project else None,
            project_name=project.name if project else None,
            project_domain=project.domain if project else None
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


# Rate limiting storage for SSE token generation
from collections import defaultdict
from datetime import datetime, timedelta

_token_generation_attempts = defaultdict(list)
_MAX_TOKEN_REQUESTS_PER_MINUTE = 10  # Max 10 token requests per minute per generation


@router.post(
    "/generate/{generation_id}/stream-token",
    summary="Generate SSE token",
    description="Generate a short-lived token for SSE streaming (60 seconds, single-use)"
)
async def create_sse_token(
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Generate a short-lived SSE token for secure streaming.
    
    Security:
    - Requires valid Bearer token authentication
    - Generates single-use, 60-second token
    - Verifies user has access to generation
    - No JWT exposure in URLs
    - Rate limited to prevent abuse
    
    Returns:
        SSE token, expiration time, and stream URL
    """
    from app.services.sse_token_service import sse_token_service
    
    try:
        # Rate limiting check
        rate_limit_key = f"{current_user.id}:{generation_id}"
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Clean old attempts
        _token_generation_attempts[rate_limit_key] = [
            timestamp for timestamp in _token_generation_attempts[rate_limit_key]
            if timestamp > one_minute_ago
        ]
        
        # Check rate limit
        if len(_token_generation_attempts[rate_limit_key]) >= _MAX_TOKEN_REQUESTS_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for user {current_user.id}, generation {generation_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many token requests. Maximum {_MAX_TOKEN_REQUESTS_PER_MINUTE} requests per minute. Please wait before retrying."
            )
        
        # Record this attempt
        _token_generation_attempts[rate_limit_key].append(now)
        
        # Verify generation exists
        generation_repo = GenerationRepository(db)
        generation = await generation_repo.get_by_id(generation_id)
        
        if not generation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation not found"
            )
        
        # Verify user has access
        if generation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this generation"
            )
        
        # Check if generation is in a terminal state
        if generation.status in ["failed", "cancelled"]:
            logger.warning(f"Attempted to stream {generation.status} generation {generation_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Generation has {generation.status}. Error: {generation.error_message or 'Unknown error'}. Cannot stream."
            )
        
        # Check if generation is already completed
        if generation.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Generation already completed. Streaming not available for completed generations."
            )
        
        # Generate short-lived SSE token
        sse_token = sse_token_service.generate_sse_token(
            user_id=current_user.id,
            generation_id=generation_id,
            ttl_seconds=60  # 1 minute validity
        )
        
        logger.info(f"Generated SSE token for user {current_user.id}, generation {generation_id}")
        
        return {
            "sse_token": sse_token,
            "expires_in": 60,
            "stream_url": f"/generations/generate/{generation_id}/stream",
            "generation_id": generation_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating SSE token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate SSE token"
        )


@router.get(
    "/generate/{generation_id}/stream",
    summary="Stream generation progress",
    description="Get real-time streaming updates of generation progress using SSE token"
)
async def stream_generation_progress(
    generation_id: str,
    token: str = Query(..., description="Short-lived SSE token from /stream-token endpoint"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Stream real-time generation progress with unified event format.
    
    Security:
    - Uses short-lived (60s), single-use tokens
    - Tokens generated via authenticated /stream-token endpoint
    - No JWT exposure in URLs
    - Token automatically invalidated after connection closes
    
    Note: Token must be obtained from POST /generate/{generation_id}/stream-token
    """
    from app.services.sse_token_service import sse_token_service
    
    # Validate SSE token
    user_id = sse_token_service.validate_sse_token(token, generation_id)
    
    if not user_id:
        logger.warning(f"Invalid SSE token attempt for generation {generation_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SSE token. Please request a new token from /stream-token endpoint."
        )
    
    # Verify generation exists and belongs to user
    generation_repo = GenerationRepository(db)
    generation = await generation_repo.get_by_id(generation_id)
    
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )
    
    if generation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    logger.info(f"SSE stream started for user {user_id}, generation {generation_id}")
    
    """Stream real-time generation progress with unified event format"""
    
    async def event_stream():
        last_event_index = 0
        max_empty_polls = 120  # Max 60 seconds of polling (120 * 0.5s)
        empty_poll_count = 0
        
        logger.info(f"📡 [SSE] Stream started for generation {generation_id[:8]}...")
        
        try:
            # Send initial connection event
            initial_event = StreamingProgressEvent(
                generation_id=generation_id,
                status=generation.status,
                stage="connected",
                progress=0.0,
                message="Stream connected",
                timestamp=time.time()
            )
            yield f"data: {initial_event.json()}\n\n"
            logger.info(f"📤 [SSE] Sent initial connection event")
            
            # Check if generation is already in terminal state
            if generation.status in ["failed", "cancelled"]:
                # Refresh generation to get latest status
                await db.refresh(generation)
                
                terminal_event = StreamingProgressEvent(
                    generation_id=generation_id,
                    status=generation.status,
                    stage="terminal",
                    progress=0.0 if generation.status == "failed" else 1.0,
                    message=generation.error_message or f"Generation {generation.status}",
                    timestamp=time.time()
                )
                yield f"data: {terminal_event.json()}\n\n"
                logger.warning(f"Generation {generation_id} is in terminal state: {generation.status}")
                return  # Stop streaming - frontend should not retry
            
            # Check if generation completed successfully
            if generation.status == "completed":
                complete_event = StreamingProgressEvent(
                    generation_id=generation_id,
                    status="completed",
                    stage="complete",
                    progress=1.0,
                    message="Generation completed successfully",
                    timestamp=time.time()
                )
                yield f"data: {complete_event.json()}\n\n"
                logger.info(f"Generation {generation_id} already completed")
                return  # Stop streaming
            
            while True:
                try:
                    # Check if there are new events
                    if generation_id in generation_events:
                        events = generation_events[generation_id]
                        
                        if len(events) > last_event_index:
                            logger.info(f"📊 [SSE] Found {len(events)} total events, sending from index {last_event_index}")
                        
                        # Reset empty poll counter when events exist
                        empty_poll_count = 0
                        
                        # Send new events
                        for event in events[last_event_index:]:
                            logger.info(f"📤 [SSE] Sending event: stage={event.get('stage')}, progress={event.get('progress')}")
                            
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
                            
                            yield f"data: {unified_event.json()}\n\n"
                            last_event_index += 1
                        
                        # Check if generation is complete
                        if events and events[-1].get("status") in ["completed", "failed", "cancelled"]:
                            logger.info(f"Generation {generation_id} reached terminal status: {events[-1].get('status')}")
                            break
                    else:
                        # No events yet - check if generation has started
                        empty_poll_count += 1
                        
                        if empty_poll_count % 10 == 0:  # Log every 5 seconds
                            logger.info(f"⏳ [SSE] Still waiting for events... (poll #{empty_poll_count}/{max_empty_polls})")
                        
                        # Refresh generation status from database
                        await db.refresh(generation)
                        
                        # Check if generation entered error state
                        if generation.status in ["failed", "cancelled"]:
                            error_event = StreamingProgressEvent(
                                generation_id=generation_id,
                                status=generation.status,
                                stage="error",
                                progress=0.0,
                                message=generation.error_message or f"Generation {generation.status}",
                                timestamp=time.time()
                            )
                            yield f"data: {error_event.json()}\n\n"
                            logger.error(f"Generation {generation_id} failed during streaming: {generation.error_message}")
                            break
                        
                        # Timeout if no events for too long
                        if empty_poll_count >= max_empty_polls:
                            timeout_event = StreamingProgressEvent(
                                generation_id=generation_id,
                                status="failed",
                                stage="timeout",
                                progress=0.0,
                                message="Generation timed out - no events received",
                                timestamp=time.time()
                            )
                            yield f"data: {timeout_event.json()}\n\n"
                            logger.error(f"Generation {generation_id} stream timeout after {max_empty_polls * 0.5}s")
                            break
                    
                    await asyncio.sleep(0.5)
                
                except Exception as e:
                    logger.error(f"Error in event stream: {e}")
                    error_event = StreamingProgressEvent(
                        generation_id=generation_id,
                        status="failed",
                        stage="error",
                        progress=0.0,
                        message=f"Stream error: {str(e)}",
                        timestamp=time.time()
                    )
                    yield f"data: {error_event.json()}\n\n"
                    break
        finally:
            # Cleanup: Invalidate token after stream closes
            logger.info(f"SSE stream closed for generation {generation_id}, invalidating token")
            sse_token_service.invalidate_token(token)
    
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
    """
    Create generation record in database with intelligent auto-project creation.
    
    When project_id is None:
    1. Analyzes the user's prompt using NLP
    2. Extracts key entities, technologies, and domain
    3. Generates a meaningful project name
    4. Sets appropriate domain and tech_stack
    5. Marks project as auto_created=True
    6. Creates generation linked to this project
    7. Returns generation record with project_id set
    """
    from app.services.auto_project_service import create_auto_project_service
    
    generation_repo = GenerationRepository(db)
    
    # Handle project_id - use intelligent auto-creation if not provided
    project_id = request.project_id
    auto_created_project = None
    
    if not project_id:
        logger.info(f"No project_id provided. Starting intelligent auto-project creation for user {user_id}")
        
        # Create auto-project service
        auto_project_service = create_auto_project_service(db)
        
        # Prepare context from request
        context = {
            "domain": request.domain,
            "tech_stack": request.tech_stack,
            **request.context
        }
        
        # Determine creation source
        creation_source = "homepage_generation" if not request.project_id else "api_call"
        
        # Create or find appropriate project using AI-powered analysis
        auto_created_project, analysis_result = await auto_project_service.create_or_find_project(
            user_id=user_id,
            prompt=request.prompt,
            context=context,
            creation_source=creation_source
        )
        
        project_id = auto_created_project.id
        
        logger.info(
            f"Auto-created project '{auto_created_project.name}' (ID: {project_id}) "
            f"with domain '{analysis_result.domain}' and confidence {analysis_result.confidence:.2f}"
        )
        
        # Emit event for frontend notification
        await _emit_event(generation_id, {
            "type": "project_auto_created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "project_id": project_id,
                "project_name": auto_created_project.name,
                "domain": analysis_result.domain,
                "entities": analysis_result.entities,
                "features": analysis_result.features,
                "confidence": analysis_result.confidence
            }
        })
    
    # Create generation record
    generation_data = {
        "id": generation_id,
        "user_id": user_id,
        "project_id": project_id,  # Now guaranteed to be not None
        "prompt": request.prompt,
        "context": {
            **request.context,
            "generation_mode": generation_config.mode,
            "ab_group": generation_config.ab_group,
            "enhanced_features": generation_config.features_enabled,
            "auto_created_project": auto_created_project is not None
        },
        "is_iteration": request.is_iteration,
        "parent_generation_id": request.parent_generation_id,
        "status": "pending"
    }
    
    generation_record = await generation_repo.create(generation_data)
    
    # Store project_id in generation record's context for frontend access
    if auto_created_project:
        generation_record.context["auto_created_project_id"] = project_id
    
    return generation_record


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
            # Use AI orchestrator directly with file_manager for incremental saving
            generation_result = await ai_orchestrator.process_generation(
                generation_id,
                {
                    "prompt": enhanced_prompt,
                    "context": {
                        **request.context,
                        "tech_stack": request.tech_stack or "fastapi_postgres",
                        "domain": request.domain,
                        "constraints": request.constraints
                    },
                    "user_id": user_id,
                    "use_enhanced_prompts": False
                },
                file_manager=file_manager  # Pass file_manager for incremental saving
            )
        
        # Defensive check: Ensure generation_result is not None
        if generation_result is None:
            raise ValueError("AI Orchestrator returned None - generation may have succeeded but response was not properly formatted")
        
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
        
        # Step 5: File Management and Storage (with cloud support)
        # Get generation record to access project_id and version
        generation_repo = GenerationRepository(db)
        generation_record = await generation_repo.get_by_id(generation_id)
        
        # Save to local + cloud storage (if enabled)
        storage_path, file_count, total_size = await storage_helper.save_generation_with_cloud(
            project_id=generation_record.project_id,
            generation_id=generation_id,
            version=generation_record.version,
            files=generation_result.get("files", {}),
            metadata={
                "mode": generation_config.mode,
                "quality_score": quality_metrics.overall_score if 'quality_metrics' in locals() else None,
                "file_count": len(generation_result.get("files", {}))
            }
        )
        
        file_metadata = {
            "storage_path": str(storage_path),
            "file_count": file_count,
            "total_size": total_size
        }
        
        # Create downloadable ZIP
        zip_path = await file_manager.create_zip_archive(generation_id)
        
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
        
        # Get cloud download URL if available
        cloud_download_url = await storage_helper.get_download_url_for_generation(
            project_id=generation_record.project_id,
            generation_id=generation_id,
            version=generation_record.version
        )
        
        result_data = {
            **generation_result,
            "quality_metrics": quality_metrics.__dict__,
            "file_metadata": file_metadata,
            "download_url": cloud_download_url or f"/api/generations/{generation_id}/download",
            "cloud_storage_enabled": storage_helper.cloud_enabled
        }
        
        await generation_repo.update(
            generation_id,
            status="completed",
            result=result_data,
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
    start_time = time.time()  # Track generation time
    
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
            # ✅ FIX 4: Fetch parent files for iteration
            generation_repo = GenerationRepository(db)
            parent_files = None
            if request.is_iteration and request.parent_generation_id:
                try:
                    parent_gen = await generation_repo.get_by_id(request.parent_generation_id)
                    if parent_gen:
                        parent_files = parent_gen.output_files or {}
                        logger.info(f"[Classic] Fetched {len(parent_files)} parent files for iteration")
                except Exception as fetch_err:
                    logger.warning(f"[Classic] Could not fetch parent files: {fetch_err}")
            
            # ✅ CRITICAL FIX: Route iterations to iterate_project() for context-aware editing
            if request.is_iteration and parent_files:
                logger.info(f"[Iteration] Routing to iterate_project() with {len(parent_files)} parent files")
                
                # Use iterate_project for context-aware iteration
                result_files = await ai_orchestrator.iterate_project(
                    existing_files=parent_files,
                    modification_prompt=request.prompt,
                    context={
                        "tech_stack": request.tech_stack or "fastapi_postgres",
                        "domain": request.domain,
                        "constraints": request.constraints,
                        "generation_mode": "classic",
                        "generation_id": generation_id  # ✅ Pass generation_id for event emission
                    },
                    event_callback=_emit_event  # ✅ Pass event callback for SSE updates
                )
                
                # Build result dict for saving
                result_dict = {
                    "files": result_files,
                    "schema": {},
                    "review_feedback": [],
                    "documentation": {},
                    "quality_score": 0.8
                }
                
                logger.info(f"[Iteration] Generated {len(result_files)} files (parent: {len(parent_files)}, new/modified: {len(result_files) - len(parent_files)})")
                
                # Continue to quality assessment and saving...
            else:
                # Normal generation (non-iteration) uses process_generation
                await ai_orchestrator.process_generation(
                    generation_id=generation_id,
                    generation_data={
                        "prompt": request.prompt,
                        "context": {
                            **request.context,
                            "tech_stack": request.tech_stack or "fastapi_postgres",
                            "domain": request.domain,
                            "constraints": request.constraints,
                            "generation_mode": "classic",
                            "is_iteration": request.is_iteration,  # ✅ FIX 2: Propagate iteration flag
                            "parent_generation_id": request.parent_generation_id,  # ✅ FIX 2: Propagate parent ID
                            "parent_files": parent_files,  # ✅ FIX 4: Include parent files in context
                        },
                        "user_id": user_id,
                        "use_enhanced_prompts": False
                    },
                    file_manager=file_manager,  # ✅ Enable incremental file saving
                    event_callback=_emit_event  # ✅ Enable live progress updates
                )
                # process_generation handles everything internally, so return early
                return
            
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
                },
                file_manager=file_manager,  # Enable incremental file saving
                event_callback=_emit_event  # Enable live progress updates
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
        
        # ✅ FIX 7: Validate iteration results to detect data loss
        files_to_save = result_dict.get("files", {})
        if request.is_iteration and request.parent_generation_id:
            try:
                parent_gen = await generation_repo.get_by_id(request.parent_generation_id)
                if parent_gen:
                    parent_file_count = len(parent_gen.output_files or {})
                    new_file_count = len(files_to_save)
                    
                    # Warn if we lost significant number of files (80% threshold)
                    if new_file_count < parent_file_count * 0.8:
                        logger.warning(
                            f"[Validation] Iteration result has {new_file_count} files but parent had {parent_file_count}. "
                            f"Possible data loss detected! Expected at least {int(parent_file_count * 0.8)} files."
                        )
                        await _emit_event(generation_id, {
                            "status": "warning",
                            "stage": "validation",
                            "message": f"⚠️ Warning: Expected ~{parent_file_count} files, got {new_file_count}. "
                                       f"Some parent files may be missing.",
                            "progress": 80,
                            "warning_type": "data_loss_detection",
                            "parent_file_count": parent_file_count,
                            "new_file_count": new_file_count
                        })
                    else:
                        logger.info(f"[Validation] Iteration validation passed: {new_file_count} files (parent had {parent_file_count})")
            except Exception as validation_err:
                logger.warning(f"[Validation] Could not validate iteration results: {validation_err}")
        
        # Step 3: File Management and Storage (with cloud support)
        # Get generation record to access project_id and version
        generation_repo = GenerationRepository(db)
        generation_record = await generation_repo.get_by_id(generation_id)
        
        # Save to local + cloud storage (if enabled)
        storage_path, file_count, total_size = await storage_helper.save_generation_with_cloud(
            project_id=generation_record.project_id,
            generation_id=generation_id,
            version=generation_record.version,
            files=files_to_save,
            metadata={
                "mode": generation_config.mode,
                "quality_score": quality_metrics.overall_score if 'quality_metrics' in locals() else None,
                "file_count": len(files_to_save),
                "is_iteration": True
            }
        )
        
        file_metadata = {
            "storage_path": str(storage_path),
            "file_count": file_count,
            "total_size": total_size
        }
        
        # Create downloadable ZIP
        zip_path = await file_manager.create_zip_archive(generation_id)
        
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
        
        # Get cloud download URL if available
        generation_record = await generation_repo.get_by_id(generation_id)
        cloud_download_url = await storage_helper.get_download_url_for_generation(
            project_id=generation_record.project_id,
            generation_id=generation_id,
            version=generation_record.version
        )
        
        # Update progress with output files and metadata
        await generation_repo.update_progress(
            generation_id=generation_id,
            stage_times={
                "total": time.time() - start_time if 'start_time' in locals() else 0
            },
            output_files=result_dict.get("files", {}),
            extracted_schema=result_dict.get("schema", {}),
            review_feedback=result_dict.get("review_feedback", []),
            documentation=result_dict.get("documentation", {}),
            cloud_download_url=cloud_download_url
        )
        
        # Update status to completed with quality score
        await generation_repo.update_status(
            generation_id=generation_id,
            status="completed",
            quality_score=quality_metrics.overall_score
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
    logger.info(f"🔔 [_emit_event] gen={generation_id[:8]}..., stage={event_data.get('stage')}, progress={event_data.get('progress')}")
    
    if generation_id not in generation_events:
        generation_events[generation_id] = []
        logger.info(f"📝 [_emit_event] Created new event list for {generation_id[:8]}...")
    
    event_data["timestamp"] = time.time()
    generation_events[generation_id].append(event_data)
    
    logger.info(f"📊 [_emit_event] Total events stored: {len(generation_events[generation_id])}")
    
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
    
    # Enrich responses with cloud storage info
    enriched_responses = []
    for gen in generations:
        response_dict = GenerationResponse.from_orm(gen).dict()
        enriched = await storage_helper.enrich_generation_response(
            response_dict,
            include_download_url=True
        )
        enriched_responses.append(GenerationResponse(**enriched))
    
    return enriched_responses


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
    
    # Convert to response and enrich with cloud storage info
    response = GenerationResponse.from_orm(generation)
    response_dict = response.dict()
    
    # Enrich response with download URL and cloud storage info
    enriched_response = await storage_helper.enrich_generation_response(
        response_dict,
        include_download_url=True
    )
    
    return GenerationResponse(**enriched_response)


@router.patch(
    "/{generation_id}",
    response_model=UnifiedGenerationResponse,
    summary="Update generation metadata",
    description="Update generation metadata while preserving unified generation context"
)
async def update_generation(
    generation_id: str,
    generation_update: UnifiedGenerationUpdate,
    current_user: UserResponse = Depends(get_current_user),
    enhanced_service=Depends(get_enhanced_generation_service),
    db: AsyncSession = Depends(get_async_db)
):
    """Update generation with unified generation service integration"""
    generation_repo = GenerationRepository(db)
    
    # Verify generation exists and access
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
    
    # Prevent updates to processing generations
    if generation.status in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update generation while it's being processed"
        )
    
    try:
        # Get generation config to maintain context
        generation_config = generation_feature_flag.get_generation_config(
            user_id=current_user.id,
            requested_mode=GenerationMode.AUTO,
            is_iteration=generation.is_iteration or False,
            project_id=generation.project_id
        )
        
        # Prepare update data
        update_data = generation_update.dict(exclude_unset=True)
        
        # Preserve critical unified context
        if generation.context and 'generation_mode' in generation.context:
            if 'context' not in update_data:
                update_data['context'] = {}
            update_data['context']['generation_mode'] = generation.context['generation_mode']
            update_data['context']['ab_group'] = generation.context.get('ab_group')
            update_data['context']['enhanced_features'] = generation.context.get('enhanced_features')
        
        # Update generation with validation
        updated_generation = await generation_repo.update(generation_id, update_data)
        
        # Record update metrics if enabled
        if generation_config.use_metrics_tracking:
            validation_metrics.track_generation_update(
                generation_id=generation_id,
                user_id=current_user.id,
                update_fields=list(update_data.keys()),
                success=True
            )
        
        # Log successful update
        logger.info(f"Generation {generation_id} updated by user {current_user.id}")
        
        # Convert to unified response format
        return UnifiedGenerationResponse(
            generation_id=updated_generation.id,
            status=updated_generation.status,
            message="Generation updated successfully",
            user_id=updated_generation.user_id,
            project_id=updated_generation.project_id,
            prompt=updated_generation.prompt,
            context=updated_generation.context or {},
            files=updated_generation.output_files,
            quality_score=updated_generation.quality_score,
            generation_mode=GenerationMode(updated_generation.context.get('generation_mode', 'auto')),
            ab_group=updated_generation.context.get('ab_group'),
            enhanced_features=updated_generation.context.get('enhanced_features'),
            created_at=updated_generation.created_at,
            updated_at=updated_generation.updated_at,
            is_iteration=updated_generation.is_iteration or False,
            parent_generation_id=updated_generation.parent_generation_id
        )
        
    except ValueError as e:
        logger.warning(f"Generation update validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Generation update failed for {generation_id}: {e}")
        
        # Record failure metrics
        generation_config = generation_feature_flag.get_generation_config(
            user_id=current_user.id,
            requested_mode=GenerationMode.AUTO
        )
        if generation_config.use_metrics_tracking:
            validation_metrics.track_generation_update(
                generation_id=generation_id,
                user_id=current_user.id,
                update_fields=list(generation_update.dict(exclude_unset=True).keys()),
                success=False,
                errors=[str(e)]
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Update failed"
        )


@router.delete(
    "/{generation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete generation with cascade cleanup",
    description="Delete generation and associated artifacts with proper cleanup"
)
async def delete_generation(
    generation_id: str,
    cascade_files: bool = Query(True, description="Delete associated files and artifacts"),
    cascade_metrics: bool = Query(True, description="Delete AB testing metrics"),
    cascade_iterations: bool = Query(False, description="Delete all child iterations"),
    force_delete: bool = Query(False, description="Force delete even if processing"),
    deletion_reason: Optional[str] = Query(None, description="Reason for deletion"),
    current_user: UserResponse = Depends(get_current_user),
    enhanced_service=Depends(get_enhanced_generation_service),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete generation with comprehensive cleanup"""
    generation_repo = GenerationRepository(db)
    
    # Verify generation exists and access
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
    
    # Validate force delete reason
    if force_delete and not deletion_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="deletion_reason is required when force_delete=true"
        )
    
    # Prevent deletion of processing generations unless forced
    if generation.status in ["pending", "processing"] and not force_delete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete generation while it's being processed. Use force_delete=true to override."
        )
    
    # Check for dependent iterations
    iterations = await generation_repo.get_iterations(generation_id)
    if iterations and not cascade_iterations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Generation has {len(iterations)} iterations. Use cascade_iterations=true to delete all."
        )
    
    try:
        # Get generation config for metrics
        generation_config = generation_feature_flag.get_generation_config(
            user_id=current_user.id,
            requested_mode=GenerationMode.AUTO
        )
        
        # Track cascade operations
        cascade_operations = []
        
        # Delete iterations if requested
        if cascade_iterations and iterations:
            for iteration in iterations:
                await generation_repo.delete(iteration.id)
                cascade_operations.append(f"deleted_iteration_{iteration.id}")
        
        # Delete associated files if requested
        if cascade_files:
            try:
                await file_manager.delete_generation_files(generation_id)
                cascade_operations.append("deleted_files")
            except Exception as e:
                logger.warning(f"Failed to delete files for generation {generation_id}: {e}")
                if not force_delete:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to delete associated files. Use force_delete=true to ignore."
                    )
                cascade_operations.append("failed_file_deletion")
        
        # Delete metrics if requested
        if cascade_metrics and generation_config.use_metrics_tracking:
            try:
                # Clean up metrics from AB testing system
                validation_metrics.delete_generation_metrics(generation_id)
                cascade_operations.append("deleted_metrics")
            except Exception as e:
                logger.warning(f"Failed to delete metrics for generation {generation_id}: {e}")
                # Don't fail the deletion for metrics cleanup failure
                cascade_operations.append("failed_metrics_deletion")
        
        # Delete generation record
        await generation_repo.delete(generation_id)
        cascade_operations.append("deleted_generation")
        
        # Clean up streaming events
        if generation_id in generation_events:
            del generation_events[generation_id]
            cascade_operations.append("cleaned_streaming_events")
        
        # Record deletion metrics before final cleanup
        if generation_config.use_metrics_tracking:
            try:
                validation_metrics.track_generation_deletion(
                    generation_id=generation_id,
                    user_id=current_user.id,
                    deletion_reason=deletion_reason,
                    cascade_operations=cascade_operations,
                    success=True
                )
            except Exception as e:
                logger.warning(f"Failed to record deletion metrics: {e}")
        
        logger.info(f"Generation {generation_id} deleted successfully by user {current_user.id}. "
                   f"Operations: {', '.join(cascade_operations)}")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.warning(f"Generation deletion validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Generation deletion failed for {generation_id}: {e}")
        
        # Record failure metrics
        generation_config = generation_feature_flag.get_generation_config(
            user_id=current_user.id,
            requested_mode=GenerationMode.AUTO
        )
        if generation_config.use_metrics_tracking:
            try:
                validation_metrics.track_generation_deletion(
                    generation_id=generation_id,
                    user_id=current_user.id,
                    deletion_reason=deletion_reason,
                    cascade_operations=[],
                    success=False,
                    errors=[str(e)]
                )
            except Exception as metrics_error:
                logger.warning(f"Failed to record deletion failure metrics: {metrics_error}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deletion failed"
        )


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
    
    # Enrich responses with cloud storage info
    enriched_responses = []
    for iteration in iterations:
        response_dict = GenerationResponse.from_orm(iteration).dict()
        enriched = await storage_helper.enrich_generation_response(
            response_dict,
            include_download_url=True
        )
        enriched_responses.append(GenerationResponse(**enriched))
    
    return enriched_responses



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
    
    # Enrich responses with cloud storage info
    enriched_responses = []
    for gen in generations:
        response_dict = GenerationResponse.from_orm(gen).dict()
        enriched = await storage_helper.enrich_generation_response(
            response_dict,
            include_download_url=True
        )
        enriched_responses.append(GenerationResponse(**enriched))
    
    return enriched_responses


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
    
    # Enrich responses with cloud storage info
    enriched_responses = []
    for gen in active_generations:
        response_dict = GenerationResponse.from_orm(gen).dict()
        enriched = await storage_helper.enrich_generation_response(
            response_dict,
            include_download_url=True
        )
        enriched_responses.append(GenerationResponse(**enriched))
    
    return enriched_responses


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


# ============================================================================
# VERSION MANAGEMENT ENDPOINTS (NEW)
# ============================================================================

@router.get(
    "/projects/{project_id}/versions",
    response_model=VersionListResponse,
    summary="List all generation versions for a project",
    description="Get all versions of generations for a specific project with lightweight metadata"
)
async def list_project_versions(
    project_id: str,
    include_failed: bool = Query(False, description="Include failed generations"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List all generation versions for a project"""
    try:
        # Verify project exists and user has access
        project_repo = ProjectRepository(db)
        project = await project_repo.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Use GenerationService to list versions
        storage_manager = HybridStorageManager()
        generation_service = GenerationService(db, storage_manager)
        generations = await generation_service.list_project_generations(
            project_id,
            include_failed=include_failed
        )
        
        # Convert to summary format
        version_summaries = [
            GenerationSummary(
                id=str(gen.id),
                version=gen.version,
                version_name=gen.version_name,
                status=gen.status,
                is_active=gen.is_active or False,
                file_count=gen.file_count,
                total_size_bytes=gen.total_size_bytes,
                quality_score=gen.quality_score,
                created_at=gen.created_at,
                prompt_preview=gen.prompt[:100] if gen.prompt else ""
            )
            for gen in generations
        ]
        
        return VersionListResponse(
            project_id=project_id,
            total_versions=len(version_summaries),
            active_version=project.active_generation.version if project.active_generation else None,
            versions=version_summaries,
            latest_version=project.latest_version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list project versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list versions: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/versions/{version}",
    response_model=GenerationResponse,
    summary="Get a specific version of a generation",
    description="Retrieve a generation by its version number within a project"
)
async def get_generation_by_version(
    project_id: str,
    version: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific version of a generation"""
    try:
        # Verify project exists and user has access
        project_repo = ProjectRepository(db)
        project = await project_repo.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Use GenerationService to get version
        storage_manager = HybridStorageManager()
        generation_service = GenerationService(db, storage_manager)
        generation = await generation_service.get_generation_by_version(
            project_id,
            version
        )
        
        if not generation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found for project {project_id}"
            )
        
        return GenerationResponse.model_validate(generation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get generation by version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get version: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/versions/active",
    response_model=GenerationResponse,
    summary="Get the active generation for a project",
    description="Retrieve the currently active generation for a project"
)
async def get_active_generation(
    project_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get the active generation for a project"""
    try:
        # Verify project exists and user has access
        project_repo = ProjectRepository(db)
        project = await project_repo.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Use GenerationService to get active generation
        storage_manager = HybridStorageManager()
        generation_service = GenerationService(db, storage_manager)
        generation = await generation_service.get_active_generation(project_id)
        
        if not generation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active generation found for project {project_id}"
            )
        
        return GenerationResponse.model_validate(generation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active generation: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/versions/{generation_id}/activate",
    response_model=ActivateGenerationResponse,
    summary="Activate a specific generation",
    description="Set a generation as the active version for the project"
)
async def activate_generation(
    project_id: str,
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Activate a specific generation as the active version"""
    try:
        # Verify project exists and user has access
        project_repo = ProjectRepository(db)
        project = await project_repo.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Verify generation exists and belongs to project
        generation_repo = GenerationRepository(db)
        generation = await generation_repo.get_by_id(generation_id)
        
        if not generation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generation {generation_id} not found"
            )
        
        if generation.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Generation {generation_id} does not belong to project {project_id}"
            )
        
        if generation.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only activate completed generations"
            )
        
        # Store previous active generation ID
        previous_active_id = str(project.active_generation_id) if project.active_generation_id else None
        
        # Use GenerationService to set active generation
        storage_manager = HybridStorageManager()
        generation_service = GenerationService(db, storage_manager)
        await generation_service.set_active_generation(project_id, generation_id)
        
        # Refresh to get updated data
        await db.refresh(generation)
        await db.refresh(project)
        
        return ActivateGenerationResponse(
            success=True,
            generation_id=generation_id,
            version=generation.version or 0,
            message=f"Generation v{generation.version} activated successfully",
            previous_active_id=previous_active_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate generation: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/versions/compare/{from_version}/{to_version}",
    response_model=VersionComparisonResponse,
    summary="Compare two versions",
    description="Compare two generation versions and get detailed diff"
)
async def compare_versions(
    project_id: str,
    from_version: int,
    to_version: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Compare two versions of generations within a project"""
    try:
        # Verify project exists and user has access
        project_repo = ProjectRepository(db)
        project = await project_repo.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Use GenerationService to compare versions
        storage_manager = HybridStorageManager()
        generation_service = GenerationService(db, storage_manager)
        comparison = await generation_service.compare_generations(
            project_id,
            from_version,
            to_version
        )
        
        if not comparison:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not compare versions {from_version} and {to_version}"
            )
        
        # Parse the comparison data
        from_gen = comparison["from_generation"]
        to_gen = comparison["to_generation"]
        
        # Calculate time difference
        time_diff = (to_gen.created_at - from_gen.created_at).total_seconds()
        
        # Calculate metric changes
        size_change = (to_gen.total_size_bytes or 0) - (from_gen.total_size_bytes or 0)
        file_count_change = (to_gen.file_count or 0) - (from_gen.file_count or 0)
        quality_change = None
        if from_gen.quality_score and to_gen.quality_score:
            quality_change = to_gen.quality_score - from_gen.quality_score
        
        return VersionComparisonResponse(
            project_id=project_id,
            from_version=from_version,
            to_version=to_version,
            from_generation_id=str(from_gen.id),
            to_generation_id=str(to_gen.id),
            files_added=comparison.get("files_added", []),
            files_removed=comparison.get("files_removed", []),
            files_modified=comparison.get("files_modified", []),
            files_unchanged=comparison.get("files_unchanged", []),
            size_change_bytes=size_change,
            file_count_change=file_count_change,
            quality_score_change=quality_change,
            unified_diff=comparison.get("diff", ""),
            diff_summary=comparison.get("summary", "No changes"),
            time_between_versions=time_diff,
            created_at_from=from_gen.created_at,
            created_at_to=to_gen.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare versions: {str(e)}"
        )
