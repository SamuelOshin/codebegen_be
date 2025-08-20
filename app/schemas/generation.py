"""
Generation Pydantic schemas for AI code generation requests and responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator

from app.schemas.base import PaginationMeta


class GenerationStatus(str, Enum):
    """Generation status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactType(str, Enum):
    """Artifact type enumeration"""
    ZIP = "zip"
    GITHUB_PR = "github_pr"
    OPENAPI = "openapi"
    DIFF = "diff"
    DOCUMENTATION = "documentation"


class GenerationCreate(BaseModel):
    """Schema for creating a new generation request"""
    prompt: str = Field(..., min_length=10, max_length=5000, description="Detailed description of what to generate")
    project_id: Optional[str] = Field(None, description="Optional project to associate with")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for generation")
    is_iteration: bool = Field(default=False, description="Whether this is an iteration of existing code")
    parent_generation_id: Optional[str] = Field(None, description="Parent generation if this is an iteration")
    
    @validator('parent_generation_id')
    def validate_iteration(cls, v, values):
        """Ensure parent_generation_id is provided when is_iteration is True"""
        if values.get('is_iteration', False) and not v:
            raise ValueError('parent_generation_id is required when is_iteration is True')
        return v


class GenerationUpdate(BaseModel):
    """Schema for updating generation metadata"""
    status: Optional[GenerationStatus] = None
    error_message: Optional[str] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    output_files: Optional[Dict[str, Any]] = None
    extracted_schema: Optional[Dict[str, Any]] = None
    review_feedback: Optional[Dict[str, Any]] = None
    documentation: Optional[Dict[str, Any]] = None


class ArtifactResponse(BaseModel):
    """Schema for artifact information"""
    id: str
    type: ArtifactType
    storage_url: str
    file_size: Optional[int] = None
    file_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class GenerationResponse(BaseModel):
    """Schema for generation response"""
    id: str
    user_id: str
    project_id: Optional[str] = None
    prompt: str
    status: GenerationStatus
    context: Dict[str, Any]
    output_files: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    extracted_schema: Optional[Dict[str, Any]] = None
    review_feedback: Optional[Dict[str, Any]] = None
    documentation: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # Performance metrics
    schema_extraction_time: Optional[float] = None
    code_generation_time: Optional[float] = None
    review_time: Optional[float] = None
    docs_generation_time: Optional[float] = None
    total_time: Optional[float] = None
    
    # Iteration fields
    is_iteration: bool = False
    parent_generation_id: Optional[str] = None
    
    # Relationships
    artifacts: List[ArtifactResponse] = []
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GenerationFilters(BaseModel):
    """Schema for filtering generations"""
    status: Optional[GenerationStatus] = None
    project_id: Optional[str] = None
    is_iteration: Optional[bool] = None
    min_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class PaginatedGenerationResponse(BaseModel):
    """Paginated generation response"""
    data: List[GenerationResponse]
    meta: PaginationMeta


class GenerationStatsResponse(BaseModel):
    """Generation statistics response"""
    total_generations: int
    completed_generations: int
    failed_generations: int
    pending_generations: int
    average_quality_score: Optional[float] = None
    average_generation_time: Optional[float] = None
    total_files_generated: int
    popular_project_types: List[Dict[str, Any]] = []


class StreamingProgress(BaseModel):
    """Schema for streaming generation progress"""
    generation_id: str
    status: GenerationStatus
    stage: str = Field(..., description="Current stage of generation")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage (0.0 to 1.0)")
    message: str = Field(..., description="Human-readable progress message")
    estimated_time_remaining: Optional[float] = Field(None, description="Estimated seconds remaining")
    current_file: Optional[str] = Field(None, description="Currently processing file")


class GenerationCancelRequest(BaseModel):
    """Schema for cancelling a generation"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for cancellation")


class IterationRequest(BaseModel):
    """Schema for creating an iteration of existing generation"""
    parent_generation_id: str = Field(..., description="ID of the generation to iterate on")
    modification_prompt: str = Field(..., min_length=10, max_length=2000, 
                                   description="Description of modifications to make")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for iteration")


class TemplateSearchRequest(BaseModel):
    """Template search request schema"""
    query: Optional[str] = Field(None, min_length=2, max_length=100, description="Search query")
    domain: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    complexity: Optional[str] = Field(None, description="low, medium, high")
    features: Optional[List[str]] = None


class TemplateInfo(BaseModel):
    """Template information"""
    name: str
    display_name: str
    description: str
    tech_stack: List[str]
    domain: Optional[str] = None
    complexity: str = "medium"
    features: List[str] = []
    estimated_files: int = 0
    estimated_setup_time: Optional[str] = None


class TemplateSearchResponse(BaseModel):
    """Template search response"""
    templates: List[TemplateInfo]
    total: int
    query: Optional[str] = None
    filters_applied: Dict[str, Any] = {}


class GenerationFileResponse(BaseModel):
    """Individual file content response"""
    path: str
    content: str
    file_type: str
    size: int
    encoding: str = "utf-8"
    language: Optional[str] = None
    last_modified: Optional[datetime] = None


class GenerationSearchRequest(BaseModel):
    """Search within generation files request"""
    query: str = Field(..., min_length=1, max_length=200)
    file_types: Optional[List[str]] = None
    case_sensitive: bool = False
    regex: bool = False
    include_content: bool = True


class SearchMatch(BaseModel):
    """Individual search match"""
    file_path: str
    line_number: int
    line_content: str
    match_start: int
    match_end: int
    context_before: List[str] = []
    context_after: List[str] = []


class GenerationSearchResponse(BaseModel):
    """Search within generation response"""
    matches: List[SearchMatch]
    total_matches: int
    files_searched: int
    query: str
    execution_time: float
