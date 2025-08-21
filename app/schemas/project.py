"""
Project Pydantic schemas for request/response models.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class ProjectBase(BaseModel):
    """Shared project properties"""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    domain: Optional[str] = Field(None, description="Project domain (e.g., 'web', 'api', 'mobile')")
    tech_stack: Optional[List[str]] = Field(default_factory=list, description="Technology stack")
    constraints: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Project constraints")
    is_public: bool = Field(default=False, description="Whether project is publicly visible")


class ProjectCreate(ProjectBase):
    """Project creation schema"""
    organization_id: Optional[str] = Field(None, description="Organization ID if creating for an org")
    github_repo_url: Optional[HttpUrl] = Field(None, description="Existing GitHub repository URL")


class ProjectUpdate(BaseModel):
    """Project update schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    domain: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    status: Optional[str] = Field(None, description="Project status")
    github_repo_url: Optional[HttpUrl] = None
    github_repo_name: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectResponse(ProjectBase):
    """Project response schema"""
    id: str
    user_id: str
    organization_id: Optional[str] = None
    status: str = "active"
    github_repo_url: Optional[str] = None
    github_repo_name: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    generation_count: int = Field(default=0, description="Number of generations for this project")
    last_generation_at: Optional[datetime] = Field(None, description="Last generation timestamp")
    
    class Config:
        from_attributes = True


class ProjectStats(BaseModel):
    """Project statistics"""
    total_generations: int
    successful_generations: int
    failed_generations: int
    total_files_generated: int
    average_quality_score: Optional[float] = None
    last_activity: Optional[datetime] = None


class ProjectWithStats(ProjectResponse):
    """Project with statistics"""
    stats: ProjectStats


class ProjectListResponse(BaseModel):
    """Paginated project list response"""
    projects: List[ProjectResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ProjectFilters(BaseModel):
    """Project filtering options"""
    domain: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    status: Optional[str] = None
    organization_id: Optional[str] = None
    is_public: Optional[bool] = None
    has_github: Optional[bool] = None


class PaginatedProjectResponse(BaseModel):
    """Paginated project response"""
    projects: List[ProjectResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ProjectStatsResponse(BaseModel):
    """Project statistics response"""
    total_projects: int
    active_projects: int
    completed_projects: int
    draft_projects: int
    public_projects: int
    private_projects: int
    projects_by_domain: Dict[str, int]
    projects_by_tech_stack: Dict[str, int]


class ProjectValidationRequest(BaseModel):
    """Project validation request schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    domain: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None


class ValidationIssue(BaseModel):
    """Individual validation issue"""
    field: str
    message: str
    severity: str = Field(..., description="error, warning, info")
    suggestion: Optional[str] = None


class ProjectValidationResponse(BaseModel):
    """Project validation response schema"""
    is_valid: bool
    issues: List[ValidationIssue] = []
    suggestions: List[str] = []
    estimated_complexity: str = Field(..., description="low, medium, high")
    estimated_duration: Optional[str] = None


class FilePreview(BaseModel):
    """File preview in project structure"""
    path: str
    type: str = Field(..., description="file, directory")
    size_estimate: Optional[int] = None
    description: Optional[str] = None


class ProjectPreviewRequest(BaseModel):
    """Project preview request schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    domain: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    template_name: Optional[str] = None


class ProjectPreviewResponse(BaseModel):
    """Project preview response schema"""
    project_structure: List[FilePreview]
    estimated_files: int
    estimated_lines: int
    technologies_used: List[str]
    features_included: List[str]
    setup_instructions: List[str]
