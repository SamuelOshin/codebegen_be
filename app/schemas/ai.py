# AI schema
"""
Pydantic schemas for AI generation requests and responses.
Defines the data structures for the AI pipeline.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum

class DomainType(str, Enum):
    ECOMMERCE = "ecommerce"
    SOCIAL_MEDIA = "social_media"
    CONTENT_MANAGEMENT = "content_management"
    TASK_MANAGEMENT = "task_management"
    FINTECH = "fintech"
    HEALTHCARE = "healthcare"
    GENERAL = "general"

class TechStack(str, Enum):
    FASTAPI_SQLITE = "fastapi_sqlite"
    FASTAPI_POSTGRES = "fastapi_postgres"
    FASTAPI_MONGO = "fastapi_mongo"

class GenerationRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of the API")
    project_id: Optional[str] = Field(None, description="Optional project ID to associate with generation")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context like domain, tech preferences"
    )
    tech_stack: TechStack = TechStack.FASTAPI_POSTGRES
    domain: Optional[DomainType] = None
    constraints: List[str] = Field(
        default_factory=list,
        description="Requirements like 'dockerized', 'tested', 'authenticated'"
    )

class GenerationResponse(BaseModel):
    generation_id: str
    status: str  # processing, completed, failed
    message: str
    files: Optional[Dict[str, str]] = None
    # `schema` would shadow BaseModel.schema(); use alias to keep JSON key but avoid attribute name collision
    extracted_schema: Optional[Dict[str, Any]] = Field(None, alias="schema")
    quality_score: Optional[float] = None

    class Config:
        allow_population_by_field_name = True

class IterationRequest(BaseModel):
    original_generation_id: str
    modification_prompt: str = Field(
        ..., 
        description="What to add/change in the existing project"
    )

class StreamingGenerationEvent(BaseModel):
    generation_id: str
    status: str
    stage: str  # schema_extraction, code_generation, review, documentation
    progress: int  # 0-100
    message: str
    partial_output: Optional[Dict[str, Any]] = None

class SchemaExtractionResult(BaseModel):
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    endpoints: List[Dict[str, Any]]
    constraints: List[str]

class CodeReviewResult(BaseModel):
    issues: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    security_score: float
    maintainability_score: float
    performance_score: float