"""
API endpoints for AI-powered code generation.
Handles project generation, iteration, and status tracking.

Enhanced for Phase 2: Prompt Engineering Enhancement
- Integrates Enhanced Generation Service
- Supports context-aware generation
- Provides hybrid template + AI approach
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import json
import asyncio
from loguru import logger
import time
from datetime import datetime
from uuid import uuid4

from app.core.database import get_async_db
from app.auth.dependencies import get_current_user
from app.schemas.ai import (
    GenerationRequest,
    GenerationResponse,
    IterationRequest,
    StreamingGenerationEvent
)
from app.schemas.user import UserResponse as User
from app.services.ai_orchestrator import ai_orchestrator
from app.services.enhanced_generation_service import create_enhanced_generation_service
from app.services.ab_test import ab_test_manager
from app.services.enhanced_ab_testing import enhanced_ab_test_manager, GenerationMetrics, GenerationMethod
from app.services.validation_metrics import validation_metrics
from app.services.file_manager import file_manager
from app.services.quality_assessor import quality_assessor
from app.repositories.generation_repository import GenerationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.models.generation import GenerationStatus

logger = logger
router = APIRouter()

# In-memory event store for streaming (in production, use Redis)
generation_events = {}

# Enhanced Generation Service (initialized per request)
enhanced_service_cache = {}

async def get_enhanced_generation_service(db: AsyncSession = Depends(get_async_db)):
    """Get or create Enhanced Generation Service instance"""
    
    # Use a simple cache to avoid recreating the service for each request
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

@router.post("/generate", response_model=GenerationResponse)
async def generate_project(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    enhanced_service = Depends(get_enhanced_generation_service),
    db: AsyncSession = Depends(get_async_db)
):
    """Generate a new FastAPI project from natural language prompt"""
    
    try:
        # Create generation record
        gen_repo = GenerationRepository(db)
        context = request.context or {}
        context["tech_stack"] = request.tech_stack or ["fastapi", "sqlalchemy"]
        
        # Extract project_id from request or context
        project_id = request.project_id or context.get("created_project_id") or context.get("project_id")
        
        generation_data = {
            "user_id": current_user.id,
            "project_id": project_id,
            "prompt": request.prompt,
            "context": context,
            "status": GenerationStatus.PROCESSING,
            "output_files": {}
        }
        
        generation = await gen_repo.create(generation_data)
        
        # Initialize event stream
        generation_events[str(generation.id)] = []

        # Enhanced A/B assignment for Phase 2 testing
        enhanced_assignment = enhanced_ab_test_manager.assign_user(current_user.id)
        
        # Determine generation features based on assignment
        features = enhanced_assignment.features_enabled
        use_enhanced_prompts = features.get("enhanced_prompts", False)
        use_context_analysis = features.get("context_analysis", False)
        use_user_patterns = features.get("user_patterns", False)
        use_hybrid_generation = features.get("hybrid_generation", False)
        
        # Legacy A/B assignment for backward compatibility
        legacy_assignment = ab_test_manager.assign(current_user.id)
        
        # Track enhanced A/B assignment
        validation_metrics.track_metric(
            generation_id=str(generation.id),
            user_id=current_user.id,
            name="enhanced_ab_group",
            value=enhanced_assignment.group,
        )
        
        validation_metrics.track_metric(
            generation_id=str(generation.id),
            user_id=current_user.id,
            name="enhanced_features",
            value=json.dumps(features),
        )
        
        validation_metrics.track_metric(
            generation_id=str(generation.id),
            user_id=current_user.id,
            name="expected_improvement",
            value=enhanced_assignment.expected_improvement,
        )
        
        # Legacy metrics for backward compatibility
        validation_metrics.track_metric(
            generation_id=str(generation.id),
            user_id=current_user.id,
            name="ab_group",
            value=legacy_assignment.group,
        )
        
        validation_metrics.track_metric(
            generation_id=str(generation.id),
            user_id=current_user.id,
            name="enhanced_prompts_enabled",
            value=str(use_enhanced_prompts),
        )
        
        # Start enhanced generation in background
        background_tasks.add_task(
            _process_enhanced_generation,
            str(generation.id),
            request,
            current_user.id,
            enhanced_service,
            enhanced_assignment
        )
        
        return GenerationResponse(
            generation_id=str(generation.id),
            status=GenerationStatus.PROCESSING,
            message=f"Enhanced project generation started (Enhanced Prompts: {use_enhanced_prompts})"
        )
        
    except HTTPException as he:
        # Re-raise HTTP exceptions (like service unavailable)
        logger.error(f"HTTP error starting enhanced generation: {he.detail}")
        raise he
    except ValueError as ve:
        # Handle validation/data errors
        logger.error(f"Validation error starting enhanced generation: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request data: {str(ve)}"
        )
    except Exception as e:
        # Handle all other errors with detailed information
        import traceback
        error_detail = f"Error starting generation: {str(e)}"
        logger.error(f"Unexpected error starting enhanced generation: {error_detail}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )

@router.get("/generate/{generation_id}/stream")
async def stream_generation_progress(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stream real-time generation progress"""
    
    async def event_stream():
        try:
            last_event_index = 0
            
            while True:
                # Check for new events
                events = generation_events.get(generation_id, [])
                
                if len(events) > last_event_index:
                    # Send new events
                    for event in events[last_event_index:]:
                        yield f"data: {json.dumps(event)}\n\n"
                        
                        # Check if generation is complete
                        if event.get("status") in ["completed", "failed"]:
                            return
                    
                    last_event_index = len(events)
                
                await asyncio.sleep(0.5)  # Poll every 500ms
                
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for generation {generation_id}")
            return
        except Exception as e:
            logger.error(f"Error in event stream: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

@router.post("/iterate", response_model=GenerationResponse)
async def iterate_project(
    request: IterationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Modify an existing generated project"""
    
    try:
        # Get original generation
        gen_repo = GenerationRepository(db)
        original = await gen_repo.get_by_id(request.original_generation_id)
        
        if not original or original.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Generation not found")
        
        # Create new generation record for iteration
        iteration_context = {"iteration_of": request.original_generation_id}
        original_tech_stack = original.context.get("tech_stack") if original.context else []
        iteration_context["tech_stack"] = original_tech_stack
        new_generation = await gen_repo.create({
            "user_id": current_user.id,
            "prompt": request.modification_prompt,
            "context": iteration_context,
            "status": GenerationStatus.PROCESSING,
            "output_files": {}
        })
        
        # Initialize event stream
        generation_events[str(new_generation.id)] = []
        
        # Start iteration in background
        background_tasks.add_task(
            _process_iteration,
            str(new_generation.id),
            request,
            original.output_files,
            current_user.id
        )
        
        return GenerationResponse(
            generation_id=str(new_generation.id),
            status=GenerationStatus.PROCESSING,
            message="Project iteration started"
        )
        
    except Exception as e:
        logger.error(f"Error starting iteration: {e}")
        raise HTTPException(status_code=500, detail="Failed to start iteration")

async def _process_generation(
    generation_id: str,
    request: GenerationRequest,
    user_id: str
):
    """Background task to process AI generation"""
    try:
        # Emit initial event
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "initializing",
            "message": "Starting project generation...",
            "progress": 0
        })
        
        # Schema extraction stage
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "schema_extraction",
            "message": "Extracting project schema...",
            "progress": 20
        })
        
        # Generate project using AI orchestrator
        if not ai_orchestrator:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI generation service is not available"
            )
        
        result = await ai_orchestrator.generate_project(request)
        
        if not result or not result.get("files"):
            raise Exception("AI generation failed - no files generated")
        
        # Code review stage
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "code_review",
            "message": "Reviewing generated code...",
            "progress": 60
        })
        
        # Quality assessment
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "quality_assessment",
            "message": "Assessing code quality...",
            "progress": 80
        })
        
        quality_report = await quality_assessor.assess_project(
            generation_id, result["files"]
        )
        
        # Save files to storage
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "file_storage",
            "message": "Saving generated files...",
            "progress": 90
        })
        
        project_dir = await file_manager.create_project_structure(
            generation_id, result["files"], result.get("template", "fastapi_basic")
        )
        
        # Create ZIP archive
        zip_path = await file_manager.create_zip_archive(generation_id)
        
        # Save completed generation
        await _save_generation_result(generation_id, {
            "files": result["files"],
            "template": result.get("template", "fastapi_basic"),
            "quality_report": quality_report.__dict__,
            "download_url": file_manager.get_download_url(generation_id)
        })
        
        # Final success event
        await _emit_event(generation_id, {
            "status": "completed",
            "stage": "completed",
            "message": "Project generation completed successfully!",
            "progress": 100,
            "download_url": file_manager.get_download_url(generation_id),
            "quality_score": quality_report.overall_score
        })

        # Baseline success metric
        validation_metrics.track_generation_success(
            generation_id=generation_id,
            user_id=user_id,
            success=True,
            duration_ms=None,
        )
        
    except Exception as e:
        logger.error(f"Generation failed for {generation_id}: {e}")
        await _emit_event(generation_id, {
            "status": "failed",
            "stage": "error",
            "message": f"Generation failed: {str(e)}",
            "progress": 0,
            "error": str(e)
        })
        
        # Update database status
        await _update_generation_status(generation_id, GenerationStatus.FAILED, str(e))

        # Baseline failure metric
        try:
            validation_metrics.track_generation_success(
                generation_id=generation_id,
                user_id=user_id,
                success=False,
                duration_ms=None,
                errors=[str(e)],
            )
        except Exception:
            # Metrics must never break the primary flow
            pass

async def _process_iteration(
    generation_id: str,
    request: IterationRequest,
    existing_files: Dict[str, str],
    user_id: str
):
    """Background task to process project iteration"""
    try:
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "iteration",
            "message": "Applying modifications...",
            "progress": 20
        })
        
        # Apply modifications using AI orchestrator
        if not ai_orchestrator:
            raise Exception("AI generation service is not available")
        
        modified_files = await ai_orchestrator.iterate_project(
            existing_files=existing_files,
            modification_prompt=request.modification_prompt
        )
        
        if not modified_files:
            raise Exception("Iteration failed - no files modified")
        
        # Quality assessment
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "quality_assessment",
            "message": "Assessing modified code...",
            "progress": 60
        })
        
        quality_report = await quality_assessor.assess_project(
            generation_id, modified_files
        )
        
        # Save files
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "file_storage",
            "message": "Saving modified files...",
            "progress": 80
        })
        
        await file_manager.create_project_structure(
            generation_id, modified_files
        )
        
        zip_path = await file_manager.create_zip_archive(generation_id)
        
        # Save result
        await _save_generation_result(generation_id, {
            "files": modified_files,
            "quality_report": quality_report.__dict__,
            "download_url": file_manager.get_download_url(generation_id)
        })
        
        await _emit_event(generation_id, {
            "status": "completed",
            "stage": "completed",
            "message": "Project iteration completed!",
            "progress": 100,
            "download_url": file_manager.get_download_url(generation_id),
            "quality_score": quality_report.overall_score
        })
        
    except Exception as e:
        logger.error(f"Iteration failed for {generation_id}: {e}")
        await _emit_event(generation_id, {
            "status": "failed",
            "stage": "error",
            "message": f"Iteration failed: {str(e)}",
            "progress": 0,
            "error": str(e)
        })
        
        await _update_generation_status(generation_id, GenerationStatus.FAILED, str(e))

async def _emit_event(generation_id: str, event_data: Dict[str, Any]):
    """Emit an event for streaming"""
    if generation_id not in generation_events:
        generation_events[generation_id] = []
    
    event_data["timestamp"] = asyncio.get_event_loop().time()
    generation_events[generation_id].append(event_data)
    
    # Keep only last 50 events to prevent memory bloat
    if len(generation_events[generation_id]) > 50:
        generation_events[generation_id] = generation_events[generation_id][-50:]

async def _update_generation_status(
    generation_id: str, 
    status: GenerationStatus, 
    error: str = None
):
    """Update generation status in database"""
    try:
        # This would update the database record
        # Implementation depends on your database setup
        logger.info(f"Updated generation {generation_id} status to {status}")
    except Exception as e:
        logger.error(f"Failed to update generation status: {e}")

async def _save_generation_result(generation_id: str, result: Dict[str, Any]):
    """Save final generation result to database"""
    try:
        # This would save the result to the database
        # Implementation depends on your database setup
        logger.info(f"Saved generation result for {generation_id}")
    except Exception as e:
        logger.error(f"Failed to save generation result: {e}")


async def _process_enhanced_generation(
    generation_id: str,
    request: GenerationRequest,
    user_id: str,
    enhanced_service,
    enhanced_assignment
):
    """
    Enhanced background task to process AI generation with comprehensive A/B testing
    Integrates Enhanced Generation Service for Phase 2 improvements
    """
    start_time = time.time()
    
    try:
        # Extract features from assignment
        features = enhanced_assignment.features_enabled
        use_enhanced_prompts = features.get("enhanced_prompts", False)
        use_context_analysis = features.get("context_analysis", False)
        use_user_patterns = features.get("user_patterns", False)
        use_hybrid_generation = features.get("hybrid_generation", False)
        
        # Emit initial event
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "initializing",
            "message": f"Starting enhanced generation (Group: {enhanced_assignment.group})",
            "progress": 0,
            "ab_group": enhanced_assignment.group,
            "enhanced_features": features,
            "expected_improvement": enhanced_assignment.expected_improvement
        })
        
        # Strategy analysis stage
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "strategy_analysis",
            "message": "Analyzing generation strategy...",
            "progress": 10,
            "enhanced_prompts": use_enhanced_prompts
        })
        
        # Extract domain and tech stack from request
        domain = None
        tech_stack = None
        
        if hasattr(request, 'context') and request.context:
            domain = request.context.get('domain')
            tech_stack = request.context.get('tech_stack')
        
        if hasattr(request, 'tech_stack') and request.tech_stack:
            tech_stack = ','.join(request.tech_stack) if isinstance(request.tech_stack, list) else request.tech_stack
        
        # Enhanced prompt generation stage
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "enhanced_prompts",
            "message": "Generating context-aware prompts..." if use_enhanced_prompts else "Using standard prompts...",
            "progress": 25,
            "enhanced_prompts": use_enhanced_prompts
        })
        
        # Template analysis stage
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "template_analysis",
            "message": "Analyzing template suitability...",
            "progress": 40,
            "enhanced_prompts": use_enhanced_prompts
        })
        
        # Project generation using Enhanced Generation Service
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "project_generation",
            "message": "Generating project with optimal strategy...",
            "progress": 60,
            "enhanced_prompts": use_enhanced_prompts
        })
        
        # Use Enhanced Generation Service
        result = await enhanced_service.generate_project(
            prompt=request.prompt,
            user_id=user_id,
            domain=domain,
            tech_stack=tech_stack,
            use_enhanced_prompts=use_enhanced_prompts,
            use_templates=True
        )
        
        # Calculate generation time
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        # Validation and quality assessment
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "quality_assessment",
            "message": "Assessing generation quality...",
            "progress": 80,
            "ab_group": enhanced_assignment.group
        })
        
        # Track comprehensive A/B testing metrics
        quality_metrics = result.get("quality_metrics", {})
        strategy_used = result.get("strategy_used", {})
        context_analysis = result.get("context_analysis", {})
        
        # Determine generation method
        generation_method = GenerationMethod.STANDARD
        if result.get("generation_method") == "hybrid_enhanced":
            generation_method = GenerationMethod.HYBRID
        elif result.get("generation_method") == "ai_only":
            generation_method = GenerationMethod.AI_ONLY
        elif result.get("generation_method") == "template_only":
            generation_method = GenerationMethod.TEMPLATE_ONLY
        elif use_enhanced_prompts:
            generation_method = GenerationMethod.ENHANCED_PROMPTS
        
        # Create comprehensive metrics for A/B testing
        comprehensive_metrics = GenerationMetrics(
            generation_id=generation_id,
            user_id=user_id,
            group=enhanced_assignment.group,
            method=generation_method,
            
            # Quality metrics
            quality_score=quality_metrics.get("final_quality_score", 0.8),
            complexity_score=strategy_used.get("complexity_analysis", {}).get("complexity_score", 0.5),
            file_count=quality_metrics.get("file_count", 0),
            total_lines=quality_metrics.get("total_lines", 0),
            test_coverage=0.0,  # TODO: Calculate from generated test files
            
            # Performance metrics
            generation_time_ms=generation_time_ms,
            prompt_tokens=0,  # TODO: Track actual token usage
            response_tokens=0,  # TODO: Track actual token usage
            
            # User interaction metrics (will be updated later)
            user_modifications=0,
            user_satisfaction=None,
            abandoned=False,
            abandonment_stage=None,
            
            # Context metrics
            similar_projects_found=len(context_analysis.get("similar_projects", [])),
            user_patterns_applied=len(context_analysis.get("user_context", {}).get("common_modifications", [])),
            template_confidence=strategy_used.get("template_analysis", {}).get("confidence", 0.0),
            
            # Business metrics (will be updated later)
            deployment_success=False,  # TODO: Track deployment
            time_to_deployment=None,
            
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        # Track metrics in enhanced A/B testing system
        enhanced_ab_test_manager.track_generation_metrics(comprehensive_metrics)
        
        # Legacy metrics for backward compatibility
        validation_metrics.track_metric(
            generation_id=generation_id,
            user_id=user_id,
            name="generation_quality_score",
            value=quality_metrics.get("final_quality_score", 0.8)
        )
        
        validation_metrics.track_metric(
            generation_id=generation_id,
            user_id=user_id,
            name="file_count",
            value=quality_metrics.get("file_count", 0)
        )
        
        validation_metrics.track_metric(
            generation_id=generation_id,
            user_id=user_id,
            name="total_lines",
            value=quality_metrics.get("total_lines", 0)
        )
        
        validation_metrics.track_metric(
            generation_id=generation_id,
            user_id=user_id,
            name="generation_method",
            value=result.get("generation_method", "unknown")
        )
        
        validation_metrics.track_metric(
            generation_id=generation_id,
            user_id=user_id,
            name="generation_time_ms",
            value=generation_time_ms
        )
        
        # File packaging stage
        await _emit_event(generation_id, {
            "status": "processing",
            "stage": "file_packaging",
            "message": "Packaging generated files...",
            "progress": 90,
            "ab_group": enhanced_assignment.group
        })
        
        # Save files using file manager
        if result.get("files"):
            await file_manager.save_generation_files(generation_id, result["files"])
        
        # Save final result
        await _save_generation_result(generation_id, result)
        await _update_generation_status(generation_id, GenerationStatus.COMPLETED)
        
        # Final success event
        await _emit_event(generation_id, {
            "status": "completed",
            "stage": "completed",
            "message": "Enhanced project generation completed successfully!",
            "progress": 100,
            "ab_group": enhanced_assignment.group,
            "enhanced_features": features,
            "download_url": file_manager.get_download_url(generation_id),
            "quality_score": quality_metrics.get("final_quality_score", 0.8),
            "generation_method": result.get("generation_method", "unknown"),
            "file_count": quality_metrics.get("file_count", 0),
            "generation_time_ms": generation_time_ms,
            "expected_improvement": enhanced_assignment.expected_improvement,
            "actual_improvement": max(0, quality_metrics.get("final_quality_score", 0.8) - 0.8),
            "strategy_used": result.get("strategy_used", {}),
            "improvement_suggestions": result.get("improvement_suggestions", [])
        })
        
        # Log success for monitoring
        logger.info(f"Enhanced generation completed for {generation_id}: "
                   f"group={enhanced_assignment.group}, "
                   f"method={result.get('generation_method')}, "
                   f"quality={quality_metrics.get('final_quality_score', 0.8):.3f}, "
                   f"files={quality_metrics.get('file_count', 0)}, "
                   f"time={generation_time_ms}ms")
        
    except Exception as e:
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        # Track failed generation metrics
        failed_metrics = GenerationMetrics(
            generation_id=generation_id,
            user_id=user_id,
            group=enhanced_assignment.group,
            method=GenerationMethod.STANDARD,
            
            # Set default values for failed generation
            quality_score=0.0,
            complexity_score=0.5,
            file_count=0,
            total_lines=0,
            test_coverage=0.0,
            generation_time_ms=generation_time_ms,
            prompt_tokens=0,
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
        
        enhanced_ab_test_manager.track_generation_metrics(failed_metrics)
        
        logger.error(f"Enhanced generation failed for {generation_id}: {e}")
        await _emit_event(generation_id, {
            "status": "failed",
            "stage": "error",
            "message": f"Enhanced generation failed: {str(e)}",
            "progress": 0,
            "ab_group": enhanced_assignment.group,
            "enhanced_features": features,
            "error": str(e),
            "generation_time_ms": generation_time_ms
        })
        
        await _update_generation_status(generation_id, GenerationStatus.FAILED, str(e))