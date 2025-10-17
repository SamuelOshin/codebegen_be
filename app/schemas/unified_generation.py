"""
Unified generation schemas that consolidate both simple and enhanced generation flows.
Backward compatible with existing clients while enabling feature flag-based processing.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator

from app.schemas.generation import GenerationStatus, ArtifactType


class DomainType(str, Enum):
    """Domain type enumeration"""
    ECOMMERCE = "ecommerce"
    SOCIAL_MEDIA = "social_media"
    CONTENT_MANAGEMENT = "content_management"
    TASK_MANAGEMENT = "task_management"
    FINTECH = "fintech"
    HEALTHCARE = "healthcare"
    GENERAL = "general"


class TechStack(str, Enum):
    """Technology stack enumeration"""
    FASTAPI_SQLITE = "fastapi_sqlite"
    FASTAPI_POSTGRES = "fastapi_postgres"
    FASTAPI_MONGO = "fastapi_mongo"


class GenerationMode(str, Enum):
    """Generation mode enumeration"""
    ENHANCED = "enhanced"
    CLASSIC = "classic"
    AUTO = "auto"  # Auto-detect based on feature flags


class UnifiedGenerationRequest(BaseModel):
    """
    Unified schema for generation requests that supports both classic and enhanced modes.
    Backward compatible with both GenerationCreate and GenerationRequest schemas.
    """
    # Core fields (required for both modes)
    prompt: str = Field(..., min_length=10, max_length=5000, description="Detailed description of what to generate")
    
    # Optional fields for both modes
    project_id: Optional[str] = Field(None, description="Optional project to associate with")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for generation")
    
    # Enhanced mode fields (optional, ignored in classic mode)
    tech_stack: Optional[TechStack] = Field(TechStack.FASTAPI_POSTGRES, description="Technology stack preference")
    domain: Optional[DomainType] = Field(None, description="Domain type for enhanced generation")
    constraints: List[str] = Field(default_factory=list, description="Requirements like 'dockerized', 'tested', 'authenticated'")
    
    # Classic mode fields (optional, ignored in enhanced mode)
    is_iteration: bool = Field(default=False, description="Whether this is an iteration of existing code")
    parent_generation_id: Optional[str] = Field(None, description="Parent generation if this is an iteration")
    
    # Mode control
    generation_mode: GenerationMode = Field(GenerationMode.AUTO, description="Force specific generation mode")
    
    @validator('parent_generation_id')
    def validate_iteration(cls, v, values):
        """Ensure parent_generation_id is provided when is_iteration is True"""
        if values.get('is_iteration', False) and not v:
            raise ValueError('parent_generation_id is required when is_iteration is True')
        return v


class UnifiedGenerationResponse(BaseModel):
    """
    Unified response schema that provides comprehensive information for both modes.
    Contains all fields from both GenerationResponse schemas.
    """
    # Core identification
    generation_id: str
    status: GenerationStatus
    message: str
    
    # Generation metadata
    user_id: str
    project_id: Optional[str] = None
    prompt: str
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Auto-created project metadata (new)
    auto_created_project: Optional[bool] = Field(None, description="Whether project was auto-created")
    project_name: Optional[str] = Field(None, description="Name of auto-created or existing project")
    project_domain: Optional[str] = Field(None, description="Domain of the project")
    
    # Generation results
    files: Optional[Dict[str, str]] = None
    output_files: Optional[Dict[str, Any]] = None
    extracted_schema: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    
    # Enhanced mode metadata
    review_feedback: Optional[Dict[str, Any]] = None
    documentation: Optional[Dict[str, Any]] = None
    
    # Processing metadata
    generation_mode: GenerationMode
    ab_group: Optional[str] = None
    enhanced_features: Optional[Dict[str, bool]] = None
    
    # Performance metrics
    schema_extraction_time: Optional[float] = None
    code_generation_time: Optional[float] = None
    review_time: Optional[float] = None
    docs_generation_time: Optional[float] = None
    total_time: Optional[float] = None
    
    # Error handling
    error_message: Optional[str] = None
    
    # Iteration support
    is_iteration: bool = False
    parent_generation_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Enhanced metadata (optional)
    generation_method: Optional[str] = None
    strategy_used: Optional[Dict[str, Any]] = None
    improvement_suggestions: Optional[List[str]] = None
    
    class Config:
        from_attributes = True


class StreamingProgressEvent(BaseModel):
    """Unified streaming progress event"""
    generation_id: str
    status: str
    stage: str
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage (0.0 to 1.0)")
    message: str
    
    # Enhanced mode fields
    ab_group: Optional[str] = None
    enhanced_features: Optional[Dict[str, bool]] = None
    generation_mode: Optional[GenerationMode] = None
    
    # Optional metadata
    estimated_time_remaining: Optional[float] = None
    current_file: Optional[str] = None
    partial_output: Optional[Dict[str, Any]] = None
    
    # Timestamps
    timestamp: float


class IterationRequest(BaseModel):
    """Schema for creating an iteration (enhanced version)"""
    parent_generation_id: str = Field(..., description="ID of the generation to iterate on")
    modification_prompt: str = Field(..., min_length=10, max_length=2000, 
                                   description="Description of modifications to make")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for iteration")
    generation_mode: GenerationMode = Field(GenerationMode.AUTO, description="Force specific generation mode")


class UnifiedGenerationUpdate(BaseModel):
    """Update schema matching unified generation system"""
    name: Optional[str] = Field(None, max_length=255, description="Display name for the generation")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the generation")
    tags: Optional[List[str]] = Field(None, description="Tags for organization and search")
    
    # Preserve unified generation context
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context metadata")
    
    # Metadata updates
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('context')
    def validate_context_preservation(cls, v):
        """Ensure context updates don't break generation integrity"""
        if v and 'generation_mode' in v:
            raise ValueError("Cannot modify generation_mode after creation")
        return v


class GenerationDeletionRequest(BaseModel):
    """Request schema for generation deletion with cascade options"""
    cascade_files: bool = Field(True, description="Delete associated files and artifacts")
    cascade_metrics: bool = Field(True, description="Delete AB testing metrics and analytics")
    cascade_iterations: bool = Field(False, description="Delete all child iterations")
    force_delete: bool = Field(False, description="Force delete even if generation is processing")
    deletion_reason: Optional[str] = Field(None, description="Reason for deletion (for audit)")
    
    @validator('deletion_reason')
    def validate_reason_for_force_delete(cls, v, values):
        """Require reason when force deleting"""
        if values.get('force_delete') and not v:
            raise ValueError("deletion_reason is required when force_delete=True")
        return v
