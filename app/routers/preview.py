# Preview API endpoints
"""
FastAPI router for preview instance management.
Provides endpoints for launching, monitoring, and controlling preview instances.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.auth.dependencies import get_current_user
from app.core.database import get_async_db
from app.models.user import User
from app.services.preview_service import PreviewService
from app.services.preview_proxy_service import PreviewProxyService
from app.services.endpoint_extractor import EndpointExtractor
from app.services.preview_log_streamer import get_streamer
from app.schemas.preview import (
    PreviewLaunchRequest,
    PreviewLaunchResponse,
    PreviewStatusResponse,
    PreviewStopResponse,
    PreviewEndpointsResponse,
    PreviewConfigResponse,
    ProxyRequest,
    ProxyResponse
)

router = APIRouter(
    prefix="/generations/{generation_id}/preview",
    tags=["Preview"]
)


# Dependency to get preview service
async def get_preview_service() -> PreviewService:
    """Get preview service instance."""
    return PreviewService()


# Dependency to get proxy service
async def get_proxy_service() -> PreviewProxyService:
    """Get proxy service instance."""
    return PreviewProxyService()


# Dependency to get endpoint extractor
async def get_endpoint_extractor() -> EndpointExtractor:
    """Get endpoint extractor instance."""
    return EndpointExtractor()


@router.post("/launch", response_model=PreviewLaunchResponse)
async def launch_preview(
    generation_id: str,
    request: PreviewLaunchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    preview_service: PreviewService = Depends(get_preview_service)
):
    """
    Launch a preview instance for a generation.

    Starts a FastAPI server with the generated code and returns connection details.
    """
    try:
        preview = await preview_service.launch_preview(
            generation_id=generation_id,
            project_id=request.project_id,
            user_id=current_user.id,
            db=db
        )

        return PreviewLaunchResponse(
            status="launched",
            preview_instance_id=preview.id,
            generation_id=generation_id,
            base_url=preview.base_url,
            preview_token=preview.preview_token,
            expires_at=preview.expires_at
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/status", response_model=PreviewStatusResponse)
async def get_preview_status(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    preview_service: PreviewService = Depends(get_preview_service)
):
    """
    Get status of active preview instance for a generation.
    """
    try:
        preview = await preview_service.get_preview_status(generation_id, db)

        if not preview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active preview for this generation"
            )

        # Check if user owns this preview
        if preview.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized access to preview"
            )

        # Check if expired
        if preview.is_expired():
            await preview_service.stop_preview(preview, db)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Preview expired"
            )

        return PreviewStatusResponse(
            preview_instance_id=preview.id,
            status=preview.status,
            base_url=preview.base_url,
            uptime=preview.get_uptime_seconds(),
            last_health_check=preview.last_health_check,
            health_status=preview.health_status,
            created_at=preview.created_at,
            expires_at=preview.expires_at,
            generated_endpoints=[]  # TODO: Implement endpoint extraction
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preview status for {generation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching preview status: {str(e)}"
        )


@router.delete("", response_model=PreviewStopResponse)
async def stop_preview(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    preview_service: PreviewService = Depends(get_preview_service)
):
    """
    Stop the active preview instance for a generation.
    """
    preview = await preview_service.get_preview_status(generation_id, db)

    if not preview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active preview for this generation"
        )

    # Check if user owns this preview
    if preview.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access to preview"
        )

    await preview_service.stop_preview(preview, db)

    return PreviewStopResponse(
        status="stopped",
        message="Preview instance stopped successfully",
        stopped_at=preview.stopped_at
    )


@router.get("/endpoints", response_model=PreviewEndpointsResponse)
async def get_generated_endpoints(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    endpoint_extractor: EndpointExtractor = Depends(get_endpoint_extractor)
):
    """
    Get list of endpoints available in the generated API.
    """
    # Get generation
    from app.repositories.generation_repository import GenerationRepository
    generation_repo = GenerationRepository(db)
    generation = await generation_repo.get_by_id(generation_id)

    if not generation or generation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found"
        )

    # Extract endpoints
    endpoints = await endpoint_extractor.extract_endpoints_from_generation(generation)

    return PreviewEndpointsResponse(endpoints=endpoints)


@router.post("/request", response_model=ProxyResponse)
async def proxy_api_request(
    generation_id: str,
    request: ProxyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    preview_service: PreviewService = Depends(get_preview_service),
    proxy_service: PreviewProxyService = Depends(get_proxy_service)
):
    """
    Proxy an API request to the running preview instance.
    """
    preview = await preview_service.get_preview_status(generation_id, db)

    if not preview or preview.status != "running":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Preview not available"
        )

    # Check if user owns this preview
    if preview.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access to preview"
        )

    # Validate preview token
    if request.headers.get("X-Preview-Token") != preview.preview_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid preview token"
        )

    # Forward request to preview instance
    try:
        response = await proxy_service.proxy_request(
            base_url=preview.base_url,
            method=request.method,
            path=request.path,
            query=request.query,
            body=request.body,
            headers=request.headers
        )

        return ProxyResponse(**response)

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Preview request timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Preview error: {str(e)}"
        )


@router.get("/config", response_model=PreviewConfigResponse)
async def get_preview_config(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get preview configuration for the current user.
    """
    # TODO: Implement user tier checking
    # For MVP, return basic config
    return PreviewConfigResponse(
        preview_timeout=3600,
        max_instances=1,
        session_expiry=3600,
        auto_stop_inactive_after=1800,
        environment={
            "NODE_ENV": "development",
            "LOG_LEVEL": "ERROR"
        },
        limitations={
            "tier": "free",
            "max_concurrent_previews": 1,
            "max_session_duration": 3600,
            "features": {
                "websocket_logs": False,
                "advanced_metrics": False
            }
        }
    )


@router.get("/logs/stream")
async def stream_preview_logs(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    preview_service: PreviewService = Depends(get_preview_service)
):
    """
    Stream preview logs in real-time via Server-Sent Events.

    Frontend connects via EventSource API for terminal-style log display.
    """
    preview = await preview_service.get_preview_status(generation_id, db)

    if not preview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active preview for this generation"
        )

    # Check if user owns this preview
    if preview.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access to preview"
        )

    # Get streamer
    streamer = get_streamer(preview.id)
    if not streamer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Preview logs not available"
        )

    # Return SSE stream
    return StreamingResponse(
        streamer.stream_logs(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )