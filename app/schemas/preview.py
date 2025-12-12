# Preview API schemas
"""
Pydantic schemas for preview API endpoints.
Defines request/response models for preview instance management.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class PreviewLaunchRequest(BaseModel):
    """Request model for launching a preview."""
    project_id: str = Field(..., description="Project ID containing the generation")


class PreviewLaunchResponse(BaseModel):
    """Response model for preview launch."""
    status: str = Field(..., description="Launch status")
    preview_instance_id: str = Field(..., description="Unique preview instance ID")
    generation_id: str = Field(..., description="Generation being previewed")
    base_url: str = Field(..., description="Base URL for the preview instance")
    preview_token: str = Field(..., description="Token for accessing preview endpoints")
    expires_at: datetime = Field(..., description="When the preview expires")


class PreviewStatusResponse(BaseModel):
    """Response model for preview status."""
    preview_instance_id: str
    status: str
    base_url: str
    uptime: Optional[float] = None
    last_health_check: Optional[datetime] = None
    health_status: str
    created_at: datetime
    expires_at: datetime
    generated_endpoints: List[Dict[str, Any]] = Field(default_factory=list)


class PreviewStopResponse(BaseModel):
    """Response model for preview stop."""
    status: str
    message: str
    stopped_at: Optional[datetime] = None


class EndpointInfo(BaseModel):
    """Information about a generated API endpoint."""
    method: str
    path: str
    description: Optional[str] = None
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None


class PreviewEndpointsResponse(BaseModel):
    """Response model for generated endpoints."""
    endpoints: List[EndpointInfo] = Field(default_factory=list)


class ProxyRequest(BaseModel):
    """Request model for proxying API calls."""
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="API endpoint path")
    query: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Query parameters")
    body: Optional[Any] = Field(None, description="Request body")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")


class ProxyResponse(BaseModel):
    """Response model for proxied API calls."""
    status_code: int
    data: Any
    headers: Dict[str, str]


class PreviewConfigResponse(BaseModel):
    """Response model for preview configuration."""
    preview_timeout: int
    max_instances: int
    session_expiry: int
    auto_stop_inactive_after: int
    environment: Dict[str, str]
    limitations: Dict[str, Any]