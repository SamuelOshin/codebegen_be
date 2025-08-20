# 🎯 Implementation Plan for Missing Frontend API Endpoints

## 📋 Overview

This document provides a detailed implementation plan for the **8 missing endpoints** identified in the frontend API integration design. The plan follows existing codebase patterns and ensures no breaking changes to current functionality.

---

## 🔍 **Missing Endpoints Analysis**

### **Critical for Frontend Flow (High Priority)**
1. `POST /projects/validate` - Real-time configuration validation
2. `POST /projects/preview` - Configuration preview with file structure
3. `GET /generations/{generation_id}/files/{file_path}` - Individual file content
4. `GET /generations/templates/search` - Template search/filtering

### **Important for User Experience (Medium Priority)**
5. `GET /generations/{generation_id}/search` - Search within generated files
6. `GET /projects/stats` - Global user stats (dashboard)

### **Advanced Features (Low Priority)**
7. `POST /generations/{generation_id}/deploy/github` - GitHub deployment
8. `GET /generations/compare/{generation_id_1}/{generation_id_2}` - Generation comparison

---

## 🏗️ **Implementation Strategy**

### **Phase 1: Core Validation & Preview (Week 1)**
Focus on endpoints needed for the Configuration page (Step 2/3)

### **Phase 2: File Management Enhancement (Week 2)** 
Enhance file viewing and search capabilities

### **Phase 3: Advanced Features (Week 3)**
Add GitHub deployment and comparison features

---

## 📁 **Phase 1: Core Validation & Preview**

### **1. POST /projects/validate**

#### **Purpose**
Validate project configuration in real-time without saving to database.

#### **Implementation Location**
- **Router**: `app/routers/projects.py`
- **Schema**: `app/schemas/project.py` (add `ProjectValidationResponse`)
- **Service**: `app/services/project_validation_service.py` (new)

#### **Code Implementation**

**Schema Addition** (`app/schemas/project.py`):
```python
class ValidationError(BaseModel):
    field: str
    message: str
    code: str

class ValidationWarning(BaseModel):
    field: str
    message: str
    suggestion: str

class ProjectValidationResponse(BaseModel):
    valid: bool
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []
    estimated_files: int
    estimated_endpoints: int
    estimated_generation_time: int
```

**Service** (`app/services/project_validation_service.py`):
```python
"""
Project validation service for real-time configuration validation.
"""

import logging
from typing import Dict, List, Any, Tuple
from app.schemas.project import ProjectCreate, ProjectValidationResponse, ValidationError, ValidationWarning
from app.services.template_selector import TemplateSelector
from app.services.advanced_template_system import AdvancedTemplateSystem

logger = logging.getLogger(__name__)

class ProjectValidationService:
    """Validates project configurations without database operations."""
    
    def __init__(self):
        self.template_selector = TemplateSelector()
        self.template_system = AdvancedTemplateSystem()
        
    async def validate_project_config(self, config: ProjectCreate) -> ProjectValidationResponse:
        """Validate project configuration and return detailed feedback."""
        errors = []
        warnings = []
        
        # 1. Basic field validation
        field_errors = self._validate_required_fields(config)
        errors.extend(field_errors)
        
        # 2. Tech stack validation
        tech_stack_errors, tech_stack_warnings = self._validate_tech_stack(config.tech_stack)
        errors.extend(tech_stack_errors)
        warnings.extend(tech_stack_warnings)
        
        # 3. Domain compatibility validation
        domain_warnings = self._validate_domain_compatibility(config.domain, config.tech_stack)
        warnings.extend(domain_warnings)
        
        # 4. Constraints validation
        constraint_errors = self._validate_constraints(config.constraints)
        errors.extend(constraint_errors)
        
        # 5. Settings validation (data models, features)
        settings_errors, settings_warnings = self._validate_settings(config.settings)
        errors.extend(settings_errors)
        warnings.extend(settings_warnings)
        
        # 6. Estimate project complexity
        estimates = self._estimate_project_complexity(config)
        
        return ProjectValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            estimated_files=estimates["files"],
            estimated_endpoints=estimates["endpoints"],
            estimated_generation_time=estimates["time_seconds"]
        )
    
    def _validate_required_fields(self, config: ProjectCreate) -> List[ValidationError]:
        """Validate required fields."""
        errors = []
        
        if not config.name or len(config.name.strip()) < 3:
            errors.append(ValidationError(
                field="name",
                message="Project name must be at least 3 characters long",
                code="NAME_TOO_SHORT"
            ))
        
        if not config.description or len(config.description.strip()) < 10:
            errors.append(ValidationError(
                field="description", 
                message="Description must be at least 10 characters long",
                code="DESCRIPTION_TOO_SHORT"
            ))
        
        return errors
    
    def _validate_tech_stack(self, tech_stack: List[str]) -> Tuple[List[ValidationError], List[ValidationWarning]]:
        """Validate tech stack compatibility."""
        errors = []
        warnings = []
        
        if not tech_stack:
            errors.append(ValidationError(
                field="tech_stack",
                message="At least one technology must be selected",
                code="TECH_STACK_EMPTY"
            ))
            return errors, warnings
        
        # Check for conflicting databases
        databases = [t for t in tech_stack if t.lower() in ["postgresql", "mongodb", "sqlite", "mysql"]]
        if len(databases) > 1:
            warnings.append(ValidationWarning(
                field="tech_stack",
                message=f"Multiple databases selected: {', '.join(databases)}",
                suggestion="Consider using only one primary database"
            ))
        
        # Check for FastAPI requirement
        if not any("fastapi" in t.lower() for t in tech_stack):
            warnings.append(ValidationWarning(
                field="tech_stack",
                message="FastAPI not explicitly selected",
                suggestion="FastAPI will be included by default"
            ))
        
        return errors, warnings
    
    def _validate_domain_compatibility(self, domain: str, tech_stack: List[str]) -> List[ValidationWarning]:
        """Check domain and tech stack compatibility."""
        warnings = []
        
        if not domain:
            return warnings
        
        # Domain-specific recommendations
        if domain == "fintech":
            if not any("postgresql" in t.lower() for t in tech_stack):
                warnings.append(ValidationWarning(
                    field="domain",
                    message="FinTech applications typically require ACID compliance",
                    suggestion="Consider PostgreSQL for financial data integrity"
                ))
        
        elif domain == "ecommerce":
            if not any(auth in " ".join(tech_stack).lower() for auth in ["jwt", "oauth", "auth"]):
                warnings.append(ValidationWarning(
                    field="domain",
                    message="E-commerce applications require robust authentication",
                    suggestion="Consider adding JWT or OAuth authentication"
                ))
        
        return warnings
    
    def _validate_constraints(self, constraints: Dict[str, Any]) -> List[ValidationError]:
        """Validate project constraints."""
        errors = []
        
        if not constraints:
            return errors
        
        # Validate constraint format
        for key, value in constraints.items():
            if not isinstance(key, str) or not key.strip():
                errors.append(ValidationError(
                    field="constraints",
                    message=f"Invalid constraint key: {key}",
                    code="INVALID_CONSTRAINT_KEY"
                ))
        
        return errors
    
    def _validate_settings(self, settings: Dict[str, Any]) -> Tuple[List[ValidationError], List[ValidationWarning]]:
        """Validate project settings including data models."""
        errors = []
        warnings = []
        
        if not settings:
            return errors, warnings
        
        # Validate data models
        data_models = settings.get("data_models", [])
        if data_models:
            for i, model in enumerate(data_models):
                if not isinstance(model, dict):
                    errors.append(ValidationError(
                        field=f"settings.data_models[{i}]",
                        message="Data model must be an object",
                        code="INVALID_MODEL_FORMAT"
                    ))
                    continue
                
                if not model.get("name"):
                    errors.append(ValidationError(
                        field=f"settings.data_models[{i}].name",
                        message="Model name is required",
                        code="MISSING_MODEL_NAME"
                    ))
                
                fields = model.get("fields", [])
                if not fields:
                    warnings.append(ValidationWarning(
                        field=f"settings.data_models[{i}].fields",
                        message=f"Model '{model.get('name', 'unnamed')}' has no fields",
                        suggestion="Add at least one field to make the model useful"
                    ))
        
        # Validate features
        features = settings.get("features", [])
        if not features:
            warnings.append(ValidationWarning(
                field="settings.features",
                message="No features selected",
                suggestion="Consider adding authentication, CRUD operations, or file upload"
            ))
        
        return errors, warnings
    
    def _estimate_project_complexity(self, config: ProjectCreate) -> Dict[str, int]:
        """Estimate project complexity metrics."""
        base_files = 8  # Basic FastAPI structure
        base_endpoints = 4  # Health, docs, basic CRUD
        base_time = 30  # Base generation time in seconds
        
        # Add complexity based on tech stack
        tech_multiplier = 1.0
        if config.tech_stack:
            if any("postgresql" in t.lower() for t in config.tech_stack):
                tech_multiplier += 0.3
            if any("mongo" in t.lower() for t in config.tech_stack):
                tech_multiplier += 0.2
            if any("auth" in t.lower() for t in config.tech_stack):
                tech_multiplier += 0.4
        
        # Add complexity based on settings
        settings_multiplier = 1.0
        if config.settings:
            data_models = config.settings.get("data_models", [])
            settings_multiplier += len(data_models) * 0.2
            
            features = config.settings.get("features", [])
            settings_multiplier += len(features) * 0.1
        
        total_multiplier = tech_multiplier * settings_multiplier
        
        return {
            "files": int(base_files * total_multiplier),
            "endpoints": int(base_endpoints * total_multiplier),
            "time_seconds": int(base_time * total_multiplier)
        }

# Service instance
project_validation_service = ProjectValidationService()
```

**Router Addition** (`app/routers/projects.py`):
```python
# Add this endpoint to the existing projects router

@router.post("/validate", response_model=ProjectValidationResponse)
async def validate_project_configuration(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user)
):
    """Validate project configuration without saving to database"""
    from app.services.project_validation_service import project_validation_service
    
    try:
        validation_result = await project_validation_service.validate_project_config(project_data)
        return validation_result
        
    except Exception as e:
        logger.error(f"Project validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation service error"
        )
```

---

### **2. POST /projects/preview**

#### **Purpose**
Generate preview of project structure and configuration without creating the project.

#### **Schema Addition** (`app/schemas/project.py`):
```python
class FileStructureNode(BaseModel):
    path: str
    type: Literal["file", "folder"]
    description: str
    estimated_lines: Optional[int] = None

class ProjectEndpoint(BaseModel):
    method: str
    path: str
    description: str
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None

class ProjectDependency(BaseModel):
    package: str
    version: str
    purpose: str

class ProjectConfigurationPreview(BaseModel):
    file_structure: List[FileStructureNode]
    endpoints: List[ProjectEndpoint]
    dependencies: List[ProjectDependency]
```

**Service Enhancement** (`app/services/project_validation_service.py`):
```python
# Add this method to ProjectValidationService

async def generate_project_preview(self, config: ProjectCreate) -> ProjectConfigurationPreview:
    """Generate preview of project structure and configuration."""
    
    # 1. Determine template
    template_decision = self.template_selector.decide(
        config.description, 
        config.tech_stack
    )
    
    # 2. Generate file structure
    file_structure = self._generate_file_structure_preview(template_decision, config)
    
    # 3. Generate endpoints preview
    endpoints = self._generate_endpoints_preview(config)
    
    # 4. Generate dependencies
    dependencies = self._generate_dependencies_preview(template_decision, config)
    
    return ProjectConfigurationPreview(
        file_structure=file_structure,
        endpoints=endpoints,
        dependencies=dependencies
    )

def _generate_file_structure_preview(self, template_decision, config: ProjectCreate) -> List[FileStructureNode]:
    """Generate preview of file structure."""
    
    # Base structure from template
    base_structure = [
        FileStructureNode(path="app/", type="folder", description="Main application package"),
        FileStructureNode(path="app/main.py", type="file", description="FastAPI application entry point", estimated_lines=25),
        FileStructureNode(path="app/core/", type="folder", description="Core configuration and utilities"),
        FileStructureNode(path="app/core/config.py", type="file", description="Application configuration", estimated_lines=40),
        FileStructureNode(path="app/models/", type="folder", description="Database models"),
        FileStructureNode(path="app/schemas/", type="folder", description="Pydantic schemas"),
        FileStructureNode(path="app/routers/", type="folder", description="API route handlers"),
        FileStructureNode(path="requirements.txt", type="file", description="Python dependencies", estimated_lines=15),
        FileStructureNode(path="README.md", type="file", description="Project documentation", estimated_lines=50),
    ]
    
    # Add database-specific files
    if template_decision.base_template == "fastapi_sqlalchemy":
        base_structure.extend([
            FileStructureNode(path="app/core/database.py", type="file", description="Database connection setup", estimated_lines=30),
            FileStructureNode(path="alembic/", type="folder", description="Database migrations"),
            FileStructureNode(path="alembic.ini", type="file", description="Alembic configuration", estimated_lines=80),
        ])
    
    # Add auth-specific files if needed
    settings = config.settings or {}
    features = settings.get("features", [])
    if "authentication" in features:
        base_structure.extend([
            FileStructureNode(path="app/auth/", type="folder", description="Authentication module"),
            FileStructureNode(path="app/auth/dependencies.py", type="file", description="Auth dependencies", estimated_lines=25),
            FileStructureNode(path="app/core/security.py", type="file", description="Security utilities", estimated_lines=35),
        ])
    
    # Add model-specific files
    data_models = settings.get("data_models", [])
    for model in data_models:
        model_name = model.get("name", "").lower()
        if model_name:
            base_structure.extend([
                FileStructureNode(
                    path=f"app/models/{model_name}.py", 
                    type="file", 
                    description=f"{model['name']} database model",
                    estimated_lines=20 + len(model.get("fields", []) * 3)
                ),
                FileStructureNode(
                    path=f"app/schemas/{model_name}.py", 
                    type="file", 
                    description=f"{model['name']} Pydantic schemas",
                    estimated_lines=15 + len(model.get("fields", []) * 2)
                ),
                FileStructureNode(
                    path=f"app/routers/{model_name}.py", 
                    type="file", 
                    description=f"{model['name']} API endpoints",
                    estimated_lines=100
                ),
            ])
    
    return sorted(base_structure, key=lambda x: x.path)

def _generate_endpoints_preview(self, config: ProjectCreate) -> List[ProjectEndpoint]:
    """Generate preview of API endpoints."""
    endpoints = [
        ProjectEndpoint(
            method="GET",
            path="/",
            description="Root endpoint with API information"
        ),
        ProjectEndpoint(
            method="GET", 
            path="/health",
            description="Health check endpoint"
        ),
    ]
    
    # Add auth endpoints if authentication is enabled
    settings = config.settings or {}
    features = settings.get("features", [])
    if "authentication" in features:
        endpoints.extend([
            ProjectEndpoint(
                method="POST",
                path="/auth/login",
                description="User authentication",
                request_schema={"username": "string", "password": "string"},
                response_schema={"access_token": "string", "token_type": "string"}
            ),
            ProjectEndpoint(
                method="POST",
                path="/auth/register",
                description="User registration",
                request_schema={"username": "string", "email": "string", "password": "string"},
                response_schema={"id": "string", "username": "string", "email": "string"}
            ),
        ])
    
    # Add CRUD endpoints for each data model
    data_models = settings.get("data_models", [])
    for model in data_models:
        model_name = model.get("name", "").lower()
        if model_name:
            model_plural = f"{model_name}s"  # Simple pluralization
            endpoints.extend([
                ProjectEndpoint(
                    method="GET",
                    path=f"/{model_plural}",
                    description=f"List all {model_plural}"
                ),
                ProjectEndpoint(
                    method="POST", 
                    path=f"/{model_plural}",
                    description=f"Create new {model_name}"
                ),
                ProjectEndpoint(
                    method="GET",
                    path=f"/{model_plural}/{{id}}",
                    description=f"Get {model_name} by ID"
                ),
                ProjectEndpoint(
                    method="PUT",
                    path=f"/{model_plural}/{{id}}",
                    description=f"Update {model_name} by ID"
                ),
                ProjectEndpoint(
                    method="DELETE",
                    path=f"/{model_plural}/{{id}}",
                    description=f"Delete {model_name} by ID"
                ),
            ])
    
    return endpoints

def _generate_dependencies_preview(self, template_decision, config: ProjectCreate) -> List[ProjectDependency]:
    """Generate preview of project dependencies."""
    
    # Base FastAPI dependencies
    dependencies = [
        ProjectDependency(package="fastapi", version=">=0.104.0", purpose="Web framework"),
        ProjectDependency(package="uvicorn", version=">=0.24.0", purpose="ASGI server"),
        ProjectDependency(package="pydantic", version=">=2.5.0", purpose="Data validation"),
    ]
    
    # Database dependencies
    if template_decision.base_template == "fastapi_sqlalchemy":
        dependencies.extend([
            ProjectDependency(package="sqlalchemy", version=">=2.0.0", purpose="ORM"),
            ProjectDependency(package="alembic", version=">=1.12.0", purpose="Database migrations"),
            ProjectDependency(package="psycopg2-binary", version=">=2.9.0", purpose="PostgreSQL driver"),
        ])
    elif template_decision.base_template == "fastapi_mongo":
        dependencies.extend([
            ProjectDependency(package="motor", version=">=3.3.0", purpose="Async MongoDB driver"),
            ProjectDependency(package="pymongo", version=">=4.6.0", purpose="MongoDB client"),
        ])
    
    # Feature-specific dependencies
    settings = config.settings or {}
    features = settings.get("features", [])
    
    if "authentication" in features:
        dependencies.extend([
            ProjectDependency(package="python-jose", version=">=3.3.0", purpose="JWT handling"),
            ProjectDependency(package="passlib", version=">=1.7.0", purpose="Password hashing"),
            ProjectDependency(package="python-multipart", version=">=0.0.6", purpose="Form handling"),
        ])
    
    if "file_upload" in features:
        dependencies.append(
            ProjectDependency(package="python-multipart", version=">=0.0.6", purpose="File upload handling")
        )
    
    if "caching" in features:
        dependencies.append(
            ProjectDependency(package="redis", version=">=5.0.0", purpose="Caching and sessions")
        )
    
    return dependencies
```

**Router Addition** (`app/routers/projects.py`):
```python
@router.post("/preview", response_model=ProjectConfigurationPreview)
async def preview_project_configuration(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user)
):
    """Generate preview of project structure and configuration"""
    from app.services.project_validation_service import project_validation_service
    
    try:
        preview = await project_validation_service.generate_project_preview(project_data)
        return preview
        
    except Exception as e:
        logger.error(f"Project preview failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Preview generation error"
        )
```

---

## 📁 **Phase 2: File Management Enhancement**

### **3. GET /generations/{generation_id}/files/{file_path}**

#### **Purpose**
Get content of individual files from a generation for the code viewer.

#### **Implementation Location**
- **Router**: `app/routers/generations.py`
- **Schema**: `app/schemas/generation.py` (add `FileContentResponse`)
- **Service**: Use existing `file_manager` service

#### **Code Implementation**

**Schema Addition** (`app/schemas/generation.py`):
```python
class FileContentResponse(BaseModel):
    content: str
    language: str
    size: int
    last_modified: datetime
    path: str
```

**Router Addition** (`app/routers/generations.py`):
```python
@router.get(
    "/{generation_id}/files/{file_path:path}",
    response_model=FileContentResponse,
    summary="Get file content",
    description="Get content of a specific file from generation"
)
async def get_file_content(
    generation_id: str,
    file_path: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get content of a specific file from generation"""
    from app.services.file_manager import file_manager
    
    # Verify generation exists and user has access
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
        # Get file content from file manager
        file_content = await file_manager.get_file_content(generation_id, file_path)
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}"
            )
        
        # Determine language from file extension
        language = _detect_language_from_path(file_path)
        
        return FileContentResponse(
            content=file_content["content"],
            language=language,
            size=len(file_content["content"]),
            last_modified=file_content.get("last_modified", generation.created_at),
            path=file_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file content for {generation_id}/{file_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving file content"
        )


def _detect_language_from_path(file_path: str) -> str:
    """Detect programming language from file extension."""
    extension_map = {
        ".py": "python",
        ".js": "javascript", 
        ".ts": "typescript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".txt": "text",
        ".sql": "sql",
        ".html": "html",
        ".css": "css",
        ".sh": "bash",
        ".dockerfile": "dockerfile",
        ".toml": "toml",
        ".ini": "ini",
        ".env": "properties"
    }
    
    for ext, lang in extension_map.items():
        if file_path.lower().endswith(ext):
            return lang
    
    return "text"
```

**File Manager Enhancement** (`app/services/file_manager.py`):
```python
# Add this method to the FileManager class

async def get_file_content(self, generation_id: str, file_path: str) -> Optional[Dict[str, Any]]:
    """Get content of a specific file from generation."""
    try:
        # Get generation directory
        generation_path = self.storage_path / generation_id
        
        if not generation_path.exists():
            logger.warning(f"Generation directory not found: {generation_id}")
            return None
        
        # Construct full file path and validate it's within generation directory
        full_path = generation_path / file_path
        
        # Security check: ensure path is within generation directory
        try:
            full_path.resolve().relative_to(generation_path.resolve())
        except ValueError:
            logger.warning(f"Invalid file path (outside generation directory): {file_path}")
            return None
        
        if not full_path.exists() or not full_path.is_file():
            logger.warning(f"File not found: {full_path}")
            return None
        
        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Handle binary files
            with open(full_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='replace')
        
        # Get file stats
        stat = full_path.stat()
        
        return {
            "content": content,
            "size": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime),
            "path": file_path
        }
        
    except Exception as e:
        logger.error(f"Error reading file {generation_id}/{file_path}: {e}")
        return None
```

---

### **4. GET /generations/templates/search**

#### **Purpose**
Search and filter templates for the Template Selection page.

#### **Router Addition** (`app/routers/generations.py`):
```python
@router.get(
    "/templates/search",
    summary="Search templates",
    description="Search and filter available templates"
)
async def search_templates(
    q: Optional[str] = Query(None, description="Search query"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    tech_stack: Optional[List[str]] = Query(None, description="Filter by tech stack"),
    complexity: Optional[str] = Query(None, description="Filter by complexity"),
    features: Optional[List[str]] = Query(None, description="Filter by features"),
    current_user: UserResponse = Depends(get_current_user)
):
    """Search and filter available templates"""
    
    # Get all templates (reuse existing endpoint logic)
    all_templates = [
        {
            "name": "fastapi_basic",
            "display_name": "FastAPI Basic",
            "description": "Basic FastAPI project with minimal dependencies",
            "tech_stack": ["fastapi", "pydantic", "uvicorn"],
            "domain_compatibility": ["general", "content_management", "task_management"],
            "features": ["REST API endpoints", "Basic project structure", "Docker support"],
            "complexity_level": "basic",
            "rating": 4.5,
            "estimated_generation_time": 30
        },
        {
            "name": "fastapi_sqlalchemy",
            "display_name": "FastAPI + SQLAlchemy",
            "description": "Production-ready FastAPI template with PostgreSQL and authentication",
            "tech_stack": ["fastapi", "sqlalchemy", "postgresql", "alembic"],
            "domain_compatibility": ["ecommerce", "social_media", "fintech", "general"],
            "features": ["REST API endpoints", "PostgreSQL database", "JWT authentication", "User management", "Repository pattern", "Alembic migrations", "Docker support", "Production ready"],
            "complexity_level": "intermediate",
            "rating": 4.8,
            "estimated_generation_time": 60
        },
        {
            "name": "fastapi_mongo",
            "display_name": "FastAPI + MongoDB",
            "description": "FastAPI template with MongoDB and modern async patterns",
            "tech_stack": ["fastapi", "motor", "mongodb", "beanie"],
            "domain_compatibility": ["content_management", "social_media", "general"],
            "features": ["REST API endpoints", "MongoDB database", "JWT authentication", "Document-based models", "Async MongoDB operations", "Pydantic ODM", "Docker support"],
            "complexity_level": "intermediate",
            "rating": 4.6,
            "estimated_generation_time": 50
        }
    ]
    
    # Apply filters
    filtered_templates = all_templates.copy()
    
    # Text search
    if q:
        query_lower = q.lower()
        filtered_templates = [
            t for t in filtered_templates
            if (query_lower in t["display_name"].lower() or 
                query_lower in t["description"].lower() or
                any(query_lower in feature.lower() for feature in t["features"]))
        ]
    
    # Domain filter
    if domain:
        filtered_templates = [
            t for t in filtered_templates
            if domain in t["domain_compatibility"]
        ]
    
    # Tech stack filter
    if tech_stack:
        filtered_templates = [
            t for t in filtered_templates
            if any(tech in t["tech_stack"] for tech in tech_stack)
        ]
    
    # Complexity filter
    if complexity:
        filtered_templates = [
            t for t in filtered_templates
            if t["complexity_level"] == complexity
        ]
    
    # Features filter
    if features:
        filtered_templates = [
            t for t in filtered_templates
            if any(feature in " ".join(t["features"]).lower() for feature in [f.lower() for f in features])
        ]
    
    return {
        "templates": filtered_templates,
        "total": len(filtered_templates),
        "query": q,
        "filters": {
            "domain": domain,
            "tech_stack": tech_stack,
            "complexity": complexity,
            "features": features
        }
    }
```

---

### **5. GET /generations/{generation_id}/search**

#### **Purpose**
Search within generated files for code exploration.

#### **Schema Addition** (`app/schemas/generation.py`):
```python
class FileSearchResult(BaseModel):
    file_path: str
    line_number: int
    line_content: str
    context_before: List[str] = []
    context_after: List[str] = []

class GenerationSearchResponse(BaseModel):
    results: List[FileSearchResult]
    total_matches: int
    search_query: str
    files_searched: int
```

#### **Router Addition** (`app/routers/generations.py`):
```python
@router.get(
    "/{generation_id}/search",
    response_model=GenerationSearchResponse,
    summary="Search within generation files",
    description="Search for text within all files of a generation"
)
async def search_generation_files(
    generation_id: str,
    q: str = Query(..., description="Search query"),
    file_types: Optional[List[str]] = Query(None, description="Filter by file extensions"),
    case_sensitive: bool = Query(False, description="Case sensitive search"),
    context_lines: int = Query(3, ge=0, le=10, description="Number of context lines"),
    max_results: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Search for text within all files of a generation"""
    from app.services.file_manager import file_manager
    
    # Verify generation exists and user has access
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
        # Get search results from file manager
        search_results = await file_manager.search_files(
            generation_id=generation_id,
            query=q,
            file_types=file_types,
            case_sensitive=case_sensitive,
            context_lines=context_lines,
            max_results=max_results
        )
        
        return GenerationSearchResponse(
            results=search_results["results"],
            total_matches=search_results["total_matches"],
            search_query=q,
            files_searched=search_results["files_searched"]
        )
        
    except Exception as e:
        logger.error(f"Error searching files for {generation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching files"
        )
```

**File Manager Enhancement** (`app/services/file_manager.py`):
```python
# Add this method to the FileManager class

async def search_files(
    self, 
    generation_id: str, 
    query: str,
    file_types: Optional[List[str]] = None,
    case_sensitive: bool = False,
    context_lines: int = 3,
    max_results: int = 100
) -> Dict[str, Any]:
    """Search for text within all files of a generation."""
    
    generation_path = self.storage_path / generation_id
    
    if not generation_path.exists():
        return {
            "results": [],
            "total_matches": 0,
            "files_searched": 0
        }
    
    results = []
    files_searched = 0
    total_matches = 0
    
    # Prepare search query
    search_query = query if case_sensitive else query.lower()
    
    try:
        # Walk through all files in generation directory
        for file_path in generation_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            # Filter by file types if specified
            if file_types:
                file_ext = file_path.suffix.lower()
                if not any(file_ext.endswith(ext.lower()) for ext in file_types):
                    continue
            
            # Skip binary files and large files
            if file_path.stat().st_size > 10 * 1024 * 1024:  # Skip files > 10MB
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    files_searched += 1
                    
                    # Search within file
                    for line_num, line in enumerate(lines, 1):
                        search_line = line if case_sensitive else line.lower()
                        
                        if search_query in search_line:
                            total_matches += 1
                            
                            # Get context lines
                            context_before = []
                            context_after = []
                            
                            if context_lines > 0:
                                start_idx = max(0, line_num - context_lines - 1)
                                end_idx = min(len(lines), line_num + context_lines)
                                
                                context_before = [
                                    lines[i].rstrip() 
                                    for i in range(start_idx, line_num - 1)
                                ]
                                context_after = [
                                    lines[i].rstrip() 
                                    for i in range(line_num, end_idx)
                                ]
                            
                            # Get relative path
                            relative_path = file_path.relative_to(generation_path)
                            
                            results.append(FileSearchResult(
                                file_path=str(relative_path),
                                line_number=line_num,
                                line_content=line.rstrip(),
                                context_before=context_before,
                                context_after=context_after
                            ))
                            
                            # Stop if we've reached max results
                            if len(results) >= max_results:
                                break
                    
                    # Stop searching files if we've reached max results
                    if len(results) >= max_results:
                        break
                        
            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read as text
                continue
                
    except Exception as e:
        logger.error(f"Error during file search: {e}")
        raise
    
    return {
        "results": results,
        "total_matches": total_matches,
        "files_searched": files_searched
    }
```

---

## 📁 **Phase 3: Advanced Features**

### **6. GET /projects/stats**

#### **Purpose**
Get global user statistics for dashboard.

#### **Schema Addition** (`app/schemas/project.py`):
```python
class GlobalUserStats(BaseModel):
    total_projects: int
    active_projects: int
    total_generations: int
    successful_generations: int
    average_quality_score: float
    most_used_templates: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
```

#### **Router Addition** (`app/routers/projects.py`):
```python
@router.get("/stats", response_model=GlobalUserStats)
async def get_user_global_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get global statistics for current user"""
    repo = ProjectRepository(db)
    generation_repo = GenerationRepository(db)
    
    try:
        # Get project stats
        total_projects = await repo.count_user_projects(current_user.id)
        active_projects = await repo.count_user_projects(current_user.id, {"status": "active"})
        
        # Get generation stats
        total_generations = await generation_repo.count_user_generations(current_user.id)
        successful_generations = await generation_repo.count_successful_generations(current_user.id)
        
        # Calculate average quality score
        avg_quality = await generation_repo.get_average_quality_score(current_user.id)
        
        # Get most used templates
        template_usage = await generation_repo.get_template_usage_stats(current_user.id)
        
        # Get recent activity
        recent_activity = await repo.get_recent_activity(current_user.id, limit=10)
        
        return GlobalUserStats(
            total_projects=total_projects,
            active_projects=active_projects,
            total_generations=total_generations,
            successful_generations=successful_generations,
            average_quality_score=avg_quality or 0.0,
            most_used_templates=template_usage,
            recent_activity=recent_activity
        )
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving statistics"
        )
```

---

### **7. POST /generations/{generation_id}/deploy/github**

#### **Purpose**
Deploy generated project to GitHub repository.

#### **Schema Addition** (`app/schemas/generation.py`):
```python
class GitHubDeployRequest(BaseModel):
    repository_name: str
    description: str
    private: bool = False
    initialize_readme: bool = True

class GitHubDeployResponse(BaseModel):
    success: bool
    repository_url: Optional[str] = None
    clone_url: Optional[str] = None
    message: str
    error: Optional[str] = None
```

#### **Router Addition** (`app/routers/generations.py`):
```python
@router.post(
    "/{generation_id}/deploy/github",
    response_model=GitHubDeployResponse,
    summary="Deploy to GitHub",
    description="Deploy generated project to a GitHub repository"
)
async def deploy_to_github(
    generation_id: str,
    deploy_request: GitHubDeployRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Deploy generation to GitHub repository"""
    from app.services.github_service import github_service
    
    # Verify generation exists and user has access
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
    
    if generation.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only deploy completed generations"
        )
    
    try:
        # TODO: Get user's GitHub token from OAuth integration
        # For now, return error requesting user to connect GitHub
        
        # GitHub integration would require:
        # 1. OAuth flow to get user's GitHub access token
        # 2. Store token securely in user profile
        # 3. Use github_service to create repo and upload files
        
        return GitHubDeployResponse(
            success=False,
            message="GitHub integration not yet implemented",
            error="Please connect your GitHub account first"
        )
        
    except Exception as e:
        logger.error(f"GitHub deployment failed for {generation_id}: {e}")
        return GitHubDeployResponse(
            success=False,
            message="Deployment failed",
            error=str(e)
        )
```

---

### **8. GET /generations/compare/{generation_id_1}/{generation_id_2}**

#### **Purpose**
Compare two generations to show differences.

#### **Schema Addition** (`app/schemas/generation.py`):
```python
class FileComparison(BaseModel):
    path: str
    changes: Dict[str, Any]  # additions, deletions, diff

class GenerationComparison(BaseModel):
    added_files: List[str]
    modified_files: List[FileComparison] 
    deleted_files: List[str]
    summary: str
```

#### **Router Addition** (`app/routers/generations.py`):
```python
@router.get(
    "/compare/{generation_id_1}/{generation_id_2}",
    response_model=GenerationComparison,
    summary="Compare generations",
    description="Compare two generations to show differences"
)
async def compare_generations(
    generation_id_1: str,
    generation_id_2: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Compare two generations to show differences"""
    from app.services.file_manager import file_manager
    
    generation_repo = GenerationRepository(db)
    
    # Verify both generations exist and user has access
    gen1 = await generation_repo.get_by_id(generation_id_1)
    gen2 = await generation_repo.get_by_id(generation_id_2)
    
    if not gen1 or not gen2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both generations not found"
        )
    
    if gen1.user_id != current_user.id or gen2.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Get file listings for both generations
        files1 = await file_manager.get_project_files(generation_id_1)
        files2 = await file_manager.get_project_files(generation_id_2)
        
        if not files1 or not files2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation files not found"
            )
        
        # Compare files
        comparison = await file_manager.compare_generations(files1, files2)
        
        return GenerationComparison(
            added_files=comparison["added_files"],
            modified_files=comparison["modified_files"], 
            deleted_files=comparison["deleted_files"],
            summary=comparison["summary"]
        )
        
    except Exception as e:
        logger.error(f"Error comparing generations {generation_id_1} and {generation_id_2}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error comparing generations"
        )
```

---

## 🎯 **Implementation Timeline**

### **Week 1: Core Validation & Preview**
- **Day 1-2**: Implement `POST /projects/validate`
- **Day 3-4**: Implement `POST /projects/preview`  
- **Day 5**: Testing and refinement

### **Week 2: File Management Enhancement**
- **Day 1-2**: Implement `GET /generations/{id}/files/{path}`
- **Day 3**: Implement `GET /generations/templates/search`
- **Day 4**: Implement `GET /generations/{id}/search`
- **Day 5**: Testing and integration

### **Week 3: Advanced Features**
- **Day 1**: Implement `GET /projects/stats`
- **Day 2-3**: Implement GitHub deployment (basic structure)
- **Day 4**: Implement generation comparison
- **Day 5**: Final testing and documentation

---

## ✅ **Testing Strategy**

### **Unit Tests**
- Test each service method independently
- Mock database and file system operations
- Validate input/output schemas

### **Integration Tests**
- Test full API endpoint flows
- Test with real database and file system
- Validate error handling

### **Performance Tests**
- Test file operations with large generations
- Test search functionality with many files
- Validate memory usage for file content loading

---

## 🔒 **Security Considerations**

### **File Access Security**
- Validate file paths to prevent directory traversal
- Check user permissions for all file operations
- Limit file sizes for content operations

### **Input Validation** 
- Sanitize all search queries
- Validate file type restrictions
- Implement rate limiting for expensive operations

### **Authorization**
- Verify user ownership for all operations
- Implement proper access controls
- Log security-related events

---

## 📈 **Monitoring & Metrics**

### **Performance Metrics**
- Track endpoint response times
- Monitor file operation performance
- Track memory usage for large operations

### **Usage Metrics**
- Track validation and preview usage
- Monitor search query patterns
- Track template selection patterns

### **Error Metrics**
- Track validation failures
- Monitor file access errors
- Track deployment failures

---

## 🔄 **Backward Compatibility**

All new endpoints are additive and don't modify existing functionality. The implementation:

1. **Adds new endpoints** without changing existing ones
2. **Uses existing services** and patterns where possible
3. **Follows established** authentication and authorization patterns
4. **Maintains existing** database schema and repository patterns

---

## 🎉 **Summary**

This implementation plan provides:

1. **8 new endpoints** to support the complete frontend flow
2. **Progressive implementation** across 3 weeks
3. **Existing code patterns** and architecture respect
4. **Comprehensive testing** and security considerations
5. **Performance optimization** and monitoring

The plan ensures the frontend will have all necessary APIs for a smooth user experience while maintaining system reliability and security.
