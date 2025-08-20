"""
Project validation service for real-time configuration validation.
"""

import re
from typing import List, Dict, Any, Optional
from app.schemas.project import (
    ProjectValidationRequest, ProjectValidationResponse, 
    ValidationIssue, ProjectPreviewRequest, ProjectPreviewResponse, FilePreview
)
from app.services.template_selector import TemplateSelector
from app.services.advanced_template_system import advanced_template_system


class ProjectValidationService:
    """Service for validating project configurations."""
    
    def __init__(self):
        self.reserved_names = {"test", "admin", "api", "www", "mail", "ftp"}
        self.tech_stack_compatibility = {
            "fastapi": ["pydantic", "uvicorn", "sqlalchemy", "alembic"],
            "django": ["djangorestframework", "celery", "postgresql"],
            "flask": ["flask-sqlalchemy", "flask-migrate", "gunicorn"],
            "react": ["typescript", "tailwindcss", "nextjs"],
            "vue": ["typescript", "nuxt", "pinia"],
            "angular": ["typescript", "rxjs", "angular-material"]
        }
    
    async def validate_project(self, request: ProjectValidationRequest) -> ProjectValidationResponse:
        """Validate project configuration and return issues/suggestions."""
        issues = []
        suggestions = []
        
        # Validate name
        name_issues = self._validate_name(request.name)
        issues.extend(name_issues)
        
        # Validate tech stack compatibility
        if request.tech_stack:
            tech_issues, tech_suggestions = self._validate_tech_stack(request.tech_stack)
            issues.extend(tech_issues)
            suggestions.extend(tech_suggestions)
        
        # Validate domain constraints
        if request.domain and request.constraints:
            domain_issues = self._validate_domain_constraints(request.domain, request.constraints)
            issues.extend(domain_issues)
        
        # Estimate complexity
        complexity = self._estimate_complexity(request)
        
        # Estimate duration
        duration = self._estimate_duration(complexity, request.tech_stack or [])
        
        # Check if configuration is valid (no errors)
        is_valid = not any(issue.severity == "error" for issue in issues)
        
        return ProjectValidationResponse(
            is_valid=is_valid,
            issues=issues,
            suggestions=suggestions,
            estimated_complexity=complexity,
            estimated_duration=duration
        )
    
    def _validate_name(self, name: str) -> List[ValidationIssue]:
        """Validate project name."""
        issues = []
        
        # Check reserved names
        if name.lower() in self.reserved_names:
            issues.append(ValidationIssue(
                field="name",
                message=f"'{name}' is a reserved name and should not be used",
                severity="warning",
                suggestion="Consider adding a prefix or suffix to make it unique"
            ))
        
        # Check special characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            issues.append(ValidationIssue(
                field="name",
                message="Project name should only contain letters, numbers, underscores, and hyphens",
                severity="error",
                suggestion="Remove special characters and spaces"
            ))
        
        # Check length
        if len(name) < 3:
            issues.append(ValidationIssue(
                field="name",
                message="Project name should be at least 3 characters long",
                severity="error"
            ))
        
        return issues
    
    def _validate_tech_stack(self, tech_stack: List[str]) -> tuple[List[ValidationIssue], List[str]]:
        """Validate tech stack compatibility."""
        issues = []
        suggestions = []
        
        # Check for conflicting frameworks
        frameworks = {"fastapi", "django", "flask", "express", "spring"}
        framework_count = sum(1 for tech in tech_stack if tech.lower() in frameworks)
        
        if framework_count > 1:
            issues.append(ValidationIssue(
                field="tech_stack",
                message="Multiple frameworks detected. This may cause conflicts.",
                severity="warning",
                suggestion="Consider using one primary framework"
            ))
        
        # Suggest compatible technologies
        for tech in tech_stack:
            if tech.lower() in self.tech_stack_compatibility:
                compatible = self.tech_stack_compatibility[tech.lower()]
                missing_compatible = [c for c in compatible if c not in [t.lower() for t in tech_stack]]
                if missing_compatible:
                    suggestions.append(f"For {tech}, consider adding: {', '.join(missing_compatible)}")
        
        return issues, suggestions
    
    def _validate_domain_constraints(self, domain: str, constraints: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate domain-specific constraints."""
        issues = []
        
        # Example validations for different domains
        if domain == "ecommerce":
            required_features = ["authentication", "payment", "inventory"]
            missing_features = [f for f in required_features 
                              if f not in constraints.get("features", [])]
            if missing_features:
                issues.append(ValidationIssue(
                    field="constraints",
                    message=f"E-commerce projects typically need: {', '.join(missing_features)}",
                    severity="info",
                    suggestion="Consider adding these features to your project"
                ))
        
        return issues
    
    def _estimate_complexity(self, request: ProjectValidationRequest) -> str:
        """Estimate project complexity based on configuration."""
        complexity_score = 0
        
        # Base score from tech stack size
        if request.tech_stack:
            complexity_score += len(request.tech_stack)
        
        # Domain complexity
        domain_complexity = {
            "ecommerce": 3,
            "social": 3,
            "enterprise": 4,
            "analytics": 3,
            "simple": 1,
            "blog": 1
        }
        complexity_score += domain_complexity.get(request.domain or "simple", 2)
        
        # Constraints complexity
        if request.constraints:
            complexity_score += len(request.constraints.get("features", []))
            if request.constraints.get("scalability") == "high":
                complexity_score += 2
        
        if complexity_score <= 3:
            return "low"
        elif complexity_score <= 7:
            return "medium"
        else:
            return "high"
    
    def _estimate_duration(self, complexity: str, tech_stack: List[str]) -> str:
        """Estimate project duration."""
        base_duration = {
            "low": "2-4 hours",
            "medium": "1-2 days", 
            "high": "3-5 days"
        }
        
        # Adjust for tech stack complexity
        if len(tech_stack) > 5:
            duration_map = {
                "low": "4-6 hours",
                "medium": "2-3 days",
                "high": "5-7 days"
            }
            return duration_map.get(complexity, base_duration[complexity])
        
        return base_duration.get(complexity, "2-4 hours")


class ProjectPreviewService:
    """Service for generating project structure previews."""
    
    def __init__(self):
        self.template_service = advanced_template_system
    
    async def generate_preview(self, request: ProjectPreviewRequest) -> ProjectPreviewResponse:
        """Generate project structure preview."""
        
        # Determine template
        template_name = request.template_name or self._determine_template(request)
        
        # Generate file structure
        file_structure = self._generate_file_structure(template_name, request)
        
        # Calculate estimates
        estimated_files = len(file_structure)
        estimated_lines = self._estimate_lines(file_structure, template_name)
        
        # Get technologies and features
        technologies = self._get_technologies(template_name, request.tech_stack or [])
        features = self._get_features(template_name, request.constraints or {})
        
        # Generate setup instructions
        setup_instructions = self._generate_setup_instructions(template_name, technologies)
        
        return ProjectPreviewResponse(
            project_structure=file_structure,
            estimated_files=estimated_files,
            estimated_lines=estimated_lines,
            technologies_used=technologies,
            features_included=features,
            setup_instructions=setup_instructions
        )
    
    def _determine_template(self, request: ProjectPreviewRequest) -> str:
        """Determine the best template based on request."""
        # Simple logic to determine template
        tech_stack = request.tech_stack or []
        
        if "fastapi" in [t.lower() for t in tech_stack]:
            return "fastapi_basic"
        elif "django" in [t.lower() for t in tech_stack]:
            return "django_basic"
        elif "react" in [t.lower() for t in tech_stack]:
            return "react_app"
        else:
            return "fastapi_basic"  # Default
    
    def _generate_file_structure(self, template_name: str, request: ProjectPreviewRequest) -> List[FilePreview]:
        """Generate file structure based on template."""
        
        base_structures = {
            "fastapi_basic": [
                FilePreview(path="app/", type="directory", description="Main application directory"),
                FilePreview(path="app/main.py", type="file", size_estimate=2000, description="FastAPI application entry point"),
                FilePreview(path="app/routers/", type="directory", description="API route handlers"),
                FilePreview(path="app/models/", type="directory", description="Database models"),
                FilePreview(path="app/schemas/", type="directory", description="Pydantic schemas"),
                FilePreview(path="app/services/", type="directory", description="Business logic services"),
                FilePreview(path="requirements.txt", type="file", size_estimate=500, description="Python dependencies"),
                FilePreview(path="README.md", type="file", size_estimate=1000, description="Project documentation"),
                FilePreview(path="Dockerfile", type="file", size_estimate=800, description="Docker configuration"),
                FilePreview(path=".env.example", type="file", size_estimate=300, description="Environment variables template"),
            ],
            "django_basic": [
                FilePreview(path="manage.py", type="file", size_estimate=500, description="Django management script"),
                FilePreview(path="project/", type="directory", description="Django project directory"),
                FilePreview(path="project/settings.py", type="file", size_estimate=3000, description="Django settings"),
                FilePreview(path="project/urls.py", type="file", size_estimate=800, description="URL configuration"),
                FilePreview(path="apps/", type="directory", description="Django applications"),
                FilePreview(path="requirements.txt", type="file", size_estimate=600, description="Python dependencies"),
                FilePreview(path="README.md", type="file", size_estimate=1200, description="Project documentation"),
            ],
            "react_app": [
                FilePreview(path="src/", type="directory", description="Source code directory"),
                FilePreview(path="src/App.jsx", type="file", size_estimate=1500, description="Main React component"),
                FilePreview(path="src/components/", type="directory", description="React components"),
                FilePreview(path="src/pages/", type="directory", description="Page components"),
                FilePreview(path="public/", type="directory", description="Static assets"),
                FilePreview(path="package.json", type="file", size_estimate=1000, description="Node.js dependencies"),
                FilePreview(path="README.md", type="file", size_estimate=800, description="Project documentation"),
            ]
        }
        
        structure = base_structures.get(template_name, base_structures["fastapi_basic"])
        
        # Add domain-specific files
        if request.domain == "ecommerce":
            structure.extend([
                FilePreview(path="app/models/product.py", type="file", size_estimate=1500, description="Product model"),
                FilePreview(path="app/models/order.py", type="file", size_estimate=2000, description="Order model"),
                FilePreview(path="app/routers/payment.py", type="file", size_estimate=2500, description="Payment endpoints"),
            ])
        
        return structure
    
    def _estimate_lines(self, file_structure: List[FilePreview], template_name: str) -> int:
        """Estimate total lines of code."""
        total_lines = 0
        
        for file_preview in file_structure:
            if file_preview.type == "file":
                # Rough estimate based on file size
                estimated_bytes = file_preview.size_estimate or 1000
                # Assume ~30 characters per line on average
                total_lines += estimated_bytes // 30
        
        # Add bonus for template complexity
        template_multipliers = {
            "fastapi_basic": 1.0,
            "django_basic": 1.3,
            "react_app": 1.2
        }
        
        multiplier = template_multipliers.get(template_name, 1.0)
        return int(total_lines * multiplier)
    
    def _get_technologies(self, template_name: str, tech_stack: List[str]) -> List[str]:
        """Get technologies used in the project."""
        base_technologies = {
            "fastapi_basic": ["Python", "FastAPI", "Pydantic", "Uvicorn"],
            "django_basic": ["Python", "Django", "PostgreSQL", "Gunicorn"],
            "react_app": ["JavaScript", "React", "HTML", "CSS"]
        }
        
        technologies = base_technologies.get(template_name, ["Python", "FastAPI"])
        
        # Add from tech stack
        technologies.extend(tech_stack)
        
        return list(set(technologies))  # Remove duplicates
    
    def _get_features(self, template_name: str, constraints: Dict[str, Any]) -> List[str]:
        """Get features included in the project."""
        base_features = {
            "fastapi_basic": ["REST API", "Automatic Documentation", "Data Validation"],
            "django_basic": ["Admin Interface", "ORM", "Authentication", "Templates"],
            "react_app": ["Component-based UI", "State Management", "Routing"]
        }
        
        features = base_features.get(template_name, ["REST API"])
        
        # Add from constraints
        constraint_features = constraints.get("features", [])
        features.extend(constraint_features)
        
        return list(set(features))  # Remove duplicates
    
    def _generate_setup_instructions(self, template_name: str, technologies: List[str]) -> List[str]:
        """Generate setup instructions."""
        
        base_instructions = {
            "fastapi_basic": [
                "Install Python 3.8+",
                "Create virtual environment: python -m venv venv",
                "Activate virtual environment: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)",
                "Install dependencies: pip install -r requirements.txt",
                "Set up environment variables: cp .env.example .env",
                "Run application: uvicorn app.main:app --reload"
            ],
            "django_basic": [
                "Install Python 3.8+",
                "Create virtual environment: python -m venv venv",
                "Activate virtual environment: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)",
                "Install dependencies: pip install -r requirements.txt",
                "Run migrations: python manage.py migrate",
                "Create superuser: python manage.py createsuperuser",
                "Run development server: python manage.py runserver"
            ],
            "react_app": [
                "Install Node.js 16+",
                "Install dependencies: npm install",
                "Start development server: npm start",
                "Build for production: npm run build"
            ]
        }
        
        instructions = base_instructions.get(template_name, base_instructions["fastapi_basic"])
        
        # Add technology-specific instructions
        if "docker" in [t.lower() for t in technologies]:
            instructions.extend([
                "Build Docker image: docker build -t project-name .",
                "Run with Docker: docker run -p 8000:8000 project-name"
            ])
        
        return instructions


# Create singleton instances
project_validation_service = ProjectValidationService()
project_preview_service = ProjectPreviewService()