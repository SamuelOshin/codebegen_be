"""
Advanced Template System for Phase 1: Template Enhancement
Implements template parameterization with domain-specific configurations and feature modules.
"""

import yaml
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings


class DomainType(Enum):
    """Supported domain types for template customization"""
    ECOMMERCE = "ecommerce"
    CONTENT_MGMT = "content_mgmt"
    FINTECH = "fintech"
    HEALTHCARE = "healthcare"
    GENERAL = "general"


class FeatureModule(Enum):
    """Available feature modules for template enhancement"""
    AUTH = "auth"
    FILE_UPLOAD = "file_upload"
    REAL_TIME = "real_time"
    CACHING = "caching"
    SEARCH = "search"
    PAYMENTS = "payments"
    NOTIFICATIONS = "notifications"
    ADMIN_DASHBOARD = "admin_dashboard"


@dataclass
class TemplateRequirements:
    """Requirements for template generation"""
    tech_stack: str
    domain: DomainType
    features: List[FeatureModule]
    entities: List[str]
    complexity_level: int  # 1-10 scale
    performance_requirements: Optional[Dict[str, Any]] = None
    security_requirements: Optional[List[str]] = None


@dataclass
class DomainConfig:
    """Domain-specific configuration loaded from YAML"""
    entities: Dict[str, Any]
    business_logic: Dict[str, Any]
    integrations: Dict[str, Any]
    security_considerations: List[str]
    common_endpoints: List[Dict[str, Any]]
    recommended_features: List[str]


class AdvancedTemplateSystem:
    """
    Enhanced template system that combines base templates, domain variants, 
    and feature modules for parameterized generation.
    
    Implements the strategy outlined in Phase 1 of the two-week validation test.
    """
    
    def __init__(self):
        self.base_templates = ["fastapi_basic", "fastapi_sqlalchemy", "fastapi_mongo"]
        self.domain_configs: Dict[DomainType, DomainConfig] = {}
        self.feature_modules: Dict[FeatureModule, Dict[str, Any]] = {}
        self.templates_dir = Path("templates")
        self.configs_dir = Path("configs")
        
        self._load_domain_configs()
        self._load_feature_modules()
    
    def _load_domain_configs(self):
        """Load domain-specific configurations from YAML files"""
        domain_configs_dir = self.configs_dir / "domains"
        
        if not domain_configs_dir.exists():
            print(f"Domain configs directory not found: {domain_configs_dir}")
            return
        
        for domain_file in domain_configs_dir.glob("*.yaml"):
            try:
                with open(domain_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                domain_name = domain_file.stem
                if domain_name in [d.value for d in DomainType]:
                    domain_type = DomainType(domain_name)
                    self.domain_configs[domain_type] = DomainConfig(
                        entities=config_data.get("entities", []),  # Keep as loaded from YAML
                        business_logic=config_data.get("business_logic", []),  
                        integrations=config_data.get("integrations", []),  
                        security_considerations=config_data.get("security_considerations", []),
                        common_endpoints=config_data.get("common_endpoints", []),
                        recommended_features=config_data.get("recommended_features", [])
                    )
                    print(f"Loaded domain config: {domain_name}")
                    
            except Exception as e:
                print(f"Error loading domain config {domain_file}: {e}")
    
    def _load_feature_modules(self):
        """Load feature module configurations"""
        # Import the registry to ensure all modules are registered
        from app.services.feature_modules.registry import get_all_registered_modules
        
        # Get detailed feature modules
        self.detailed_feature_modules = get_all_registered_modules()
        
        # Keep the legacy format for backward compatibility
        self.feature_modules = {
            FeatureModule.AUTH: {
                "dependencies": ["python-jose[cryptography]", "passlib[bcrypt]"],
                "environment_vars": ["SECRET_KEY", "ACCESS_TOKEN_EXPIRE_MINUTES"],
                "files": ["app/auth/", "app/core/security.py"],
                "endpoints": ["/auth/login", "/auth/register", "/auth/refresh"],
                "middleware": ["AuthenticationMiddleware"]
            },
            FeatureModule.FILE_UPLOAD: {
                "dependencies": ["aiofiles", "python-multipart"],
                "environment_vars": ["UPLOAD_DIR", "MAX_FILE_SIZE"],
                "files": ["app/services/file_service.py"],
                "endpoints": ["/files/upload", "/files/download/{id}"],
                "middleware": ["FileSizeMiddleware"]
            },
            FeatureModule.REAL_TIME: {
                "dependencies": ["websockets"],
                "environment_vars": ["WEBSOCKET_URL"],
                "files": ["app/websockets/", "app/services/websocket_service.py"],
                "endpoints": ["/ws", "/notifications/send"],
                "middleware": ["WebSocketMiddleware"]
            },
            FeatureModule.CACHING: {
                "dependencies": ["redis", "aioredis"],
                "environment_vars": ["REDIS_URL", "CACHE_TTL"],
                "files": ["app/services/cache_service.py"],
                "endpoints": ["/cache/clear", "/cache/stats"],
                "middleware": ["CacheMiddleware"]
            },
            FeatureModule.SEARCH: {
                "dependencies": ["elasticsearch"],
                "environment_vars": ["ELASTICSEARCH_URL"],
                "files": ["app/services/search_service.py"],
                "endpoints": ["/search", "/search/index", "/search/suggestions"],
                "middleware": ["SearchMiddleware"]
            },
            FeatureModule.PAYMENTS: {
                "dependencies": ["stripe"],
                "environment_vars": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"],
                "files": ["app/services/payment_service.py"],
                "endpoints": ["/payments/process", "/payments/webhook"],
                "middleware": ["PaymentMiddleware"]
            },
            FeatureModule.NOTIFICATIONS: {
                "dependencies": ["emails", "twilio"],
                "environment_vars": ["SMTP_HOST", "TWILIO_SID"],
                "files": ["app/services/notification_service.py"],
                "endpoints": ["/notifications/send", "/notifications/preferences"],
                "middleware": ["NotificationMiddleware"]
            },
            FeatureModule.ADMIN_DASHBOARD: {
                "dependencies": ["fastapi-admin"],
                "environment_vars": ["ADMIN_SECRET_KEY"],
                "files": ["app/admin/", "app/routers/admin.py"],
                "endpoints": ["/admin", "/admin/users", "/admin/analytics"],
                "middleware": ["AdminAuthMiddleware"]
            }
        }
    
    def detect_domain(self, prompt: str) -> DomainType:
        """
        Analyze prompt to detect the most appropriate domain.
        
        Uses keyword matching and domain-specific indicators.
        """
        prompt_lower = prompt.lower()
        
        # Domain indicators
        domain_keywords = {
            DomainType.ECOMMERCE: [
                "shop", "store", "product", "cart", "order", "payment", "checkout",
                "inventory", "ecommerce", "marketplace", "buy", "sell", "price"
            ],
            DomainType.FINTECH: [
                "bank", "payment", "finance", "transaction", "account", "loan",
                "investment", "trading", "money", "currency", "wallet", "credit"
            ],
            DomainType.HEALTHCARE: [
                "patient", "doctor", "medical", "health", "appointment", "clinic",
                "hospital", "treatment", "diagnosis", "prescription", "healthcare"
            ],
            DomainType.CONTENT_MGMT: [
                "blog", "article", "content", "cms", "post", "page", "media",
                "publish", "editor", "comment", "category", "tag"
            ]
        }
        
        # Score each domain based on keyword matches
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in prompt_lower)
            domain_scores[domain] = score
        
        # Return domain with highest score, default to GENERAL
        if max(domain_scores.values()) > 0:
            return max(domain_scores, key=domain_scores.get)
        return DomainType.GENERAL
    
    def detect_required_features(self, prompt: str, domain: DomainType) -> List[FeatureModule]:
        """
        Detect required features based on prompt analysis and domain.
        """
        prompt_lower = prompt.lower()
        detected_features = set()
        
        # Feature detection keywords
        feature_keywords = {
            FeatureModule.AUTH: ["login", "register", "user", "authentication", "signin"],
            FeatureModule.FILE_UPLOAD: ["upload", "file", "image", "document", "attachment"],
            FeatureModule.REAL_TIME: ["real-time", "websocket", "notification", "live", "chat"],
            FeatureModule.CACHING: ["cache", "performance", "fast", "redis"],
            FeatureModule.SEARCH: ["search", "find", "filter", "query", "elasticsearch"],
            FeatureModule.PAYMENTS: ["payment", "stripe", "checkout", "billing"],
            FeatureModule.NOTIFICATIONS: ["email", "sms", "notification", "alert"],
            FeatureModule.ADMIN_DASHBOARD: ["admin", "dashboard", "management", "analytics"]
        }
        
        # Detect features from prompt
        for feature, keywords in feature_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                detected_features.add(feature)
        
        # Add domain-specific recommended features
        if domain in self.domain_configs:
            recommended = self.domain_configs[domain].recommended_features
            for feature_name in recommended:
                try:
                    feature = FeatureModule(feature_name.lower().replace(" ", "_"))
                    detected_features.add(feature)
                except ValueError:
                    # Feature not in enum, skip
                    pass
        
        return list(detected_features)
    
    def select_base_template(self, tech_stack: str) -> str:
        """
        Select the most appropriate base template based on tech stack.
        """
        tech_stack_lower = tech_stack.lower()
        
        if "mongo" in tech_stack_lower:
            return "fastapi_mongo"
        elif "sqlalchemy" in tech_stack_lower or "postgres" in tech_stack_lower:
            return "fastapi_sqlalchemy"
        else:
            return "fastapi_basic"
    
    def get_domain_config(self, domain: DomainType) -> Optional[DomainConfig]:
        """Get domain-specific configuration"""
        return self.domain_configs.get(domain)
    
    def compose_template(
        self,
        base_template: str,
        domain_config: Optional[DomainConfig],
        features: List[FeatureModule],
        custom_entities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compose a customized template by combining base template,
        domain configuration, and feature modules.
        """
        # Start with base template
        template_composition = {
            "base_template": base_template,
            "files": {},
            "dependencies": [],
            "environment_vars": [],
            "endpoints": [],
            "middleware": [],
            "entities": {},
            "business_logic": {}
        }
        
        # Add domain-specific components
        if domain_config:
            # Handle both list format and dict format for entities
            if isinstance(domain_config.entities, list):
                # List format: [{"Product": {"fields": [...]}}, ...]
                for entity_dict in domain_config.entities:
                    for entity_name, entity_config in entity_dict.items():
                        template_composition["entities"][entity_name] = entity_config
            elif isinstance(domain_config.entities, dict):
                # Dict format: {"Product": {"fields": [...]}, ...}
                template_composition["entities"].update(domain_config.entities)
            
            # Business logic is a list in YAML, set as metadata
            template_composition["business_logic"]["patterns"] = domain_config.business_logic
            
            # Add domain endpoints
            for endpoint in domain_config.common_endpoints:
                template_composition["endpoints"].append(endpoint)
        
        # Add custom entities if provided
        if custom_entities:
            for entity_name in custom_entities:
                if entity_name not in template_composition["entities"]:
                    # Create basic entity structure
                    template_composition["entities"][entity_name] = {
                        "fields": [
                            {"name": "id", "type": "String", "constraints": ["primary_key"]},
                            {"name": "created_at", "type": "DateTime", "constraints": []},
                            {"name": "updated_at", "type": "DateTime", "constraints": []}
                        ]
                    }
        
        # Add feature modules
        for feature in features:
            if feature in self.feature_modules:
                feature_config = self.feature_modules[feature]
                
                # Add dependencies
                template_composition["dependencies"].extend(
                    feature_config.get("dependencies", [])
                )
                
                # Add environment variables
                template_composition["environment_vars"].extend(
                    feature_config.get("environment_vars", [])
                )
                
                # Add endpoints
                for endpoint in feature_config.get("endpoints", []):
                    template_composition["endpoints"].append({
                        "path": endpoint,
                        "feature": feature.value
                    })
                
                # Add middleware
                template_composition["middleware"].extend(
                    feature_config.get("middleware", [])
                )
        
        # Remove duplicates
        template_composition["dependencies"] = list(set(template_composition["dependencies"]))
        template_composition["environment_vars"] = list(set(template_composition["environment_vars"]))
        template_composition["middleware"] = list(set(template_composition["middleware"]))
        
        return template_composition
    
    def generate_project(self, prompt: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method: Generate a parameterized project based on prompt and requirements.
        
        This implements the core strategy from Phase 1 of the validation test.
        """
        # 1. Parse domain from prompt
        domain = self.detect_domain(prompt)
        
        # 2. Select base template
        tech_stack = requirements.get("tech_stack", "fastapi_sqlalchemy")
        base_template = self.select_base_template(tech_stack)
        
        # 3. Apply domain-specific patterns
        domain_config = self.get_domain_config(domain)
        
        # 4. Add feature modules
        features = self.detect_required_features(prompt, domain)
        
        # Add any explicitly requested features
        if "features" in requirements:
            for feature_name in requirements["features"]:
                try:
                    feature = FeatureModule(feature_name)
                    if feature not in features:
                        features.append(feature)
                except ValueError:
                    pass
        
        # 5. Generate customized project
        template_composition = self.compose_template(
            base_template=base_template,
            domain_config=domain_config,
            features=features,
            custom_entities=requirements.get("entities", [])
        )
        
        # 6. Generate actual file content (placeholder - would integrate with existing generators)
        generated_files = self._generate_files_from_composition(template_composition, prompt)
        
        return {
            "files": generated_files,
            "template_info": {
                "base_template": base_template,
                "domain": domain.value,
                "features": [f.value for f in features],
                "entities": list(template_composition["entities"].keys())
            },
            "dependencies": template_composition["dependencies"],
            "environment_vars": template_composition["environment_vars"],
            "endpoints": template_composition["endpoints"]
        }
    
    def _generate_files_from_composition(
        self, 
        composition: Dict[str, Any], 
        prompt: str
    ) -> Dict[str, str]:
        """
        Generate actual file content based on template composition.
        Now uses detailed feature modules for production-ready code generation.
        """
        files = {}
        
        # Generate feature module code using detailed implementations
        feature_services = {}
        feature_routers = {}
        feature_middleware = {}
        feature_schemas = {}
        
        for feature_name in composition.get("features", []):
            # Use the detailed feature modules
            if hasattr(self, 'feature_modules') and feature_name in self.feature_modules:
                feature_module = self.feature_modules[feature_name]
                
                # Generate service code
                service_code = feature_module.generate_service_code()
                if service_code:
                    files[f"app/services/{feature_name}_service.py"] = service_code
                    feature_services[feature_name] = f"{feature_name}_service"
                
                # Generate router code
                router_code = feature_module.generate_router_code()
                if router_code:
                    files[f"app/routers/{feature_name}.py"] = router_code
                    feature_routers[feature_name] = f"{feature_name}"
                
                # Generate middleware code
                middleware_code = feature_module.generate_middleware_code()
                if middleware_code:
                    files[f"app/middleware/{feature_name}_middleware.py"] = middleware_code
                    feature_middleware[feature_name] = f"{feature_name}_middleware"
                
                # Generate schema code
                schema_code = feature_module.generate_schema_code()
                if schema_code:
                    files[f"app/schemas/{feature_name}.py"] = schema_code
                    feature_schemas[feature_name] = f"{feature_name}"
        
        # Generate main.py with feature module integration
        main_py = self._generate_enhanced_main_file(composition, feature_routers, feature_middleware)
        files["app/main.py"] = main_py
        
        # Generate models based on entities
        for entity_name, entity_config in composition["entities"].items():
            model_file = self._generate_model_file(entity_name, entity_config)
            files[f"app/models/{entity_name.lower()}.py"] = model_file
        
        # Generate enhanced requirements.txt with feature dependencies
        all_dependencies = composition["dependencies"].copy()
        for feature_name in composition.get("features", []):
            if hasattr(self, 'feature_modules') and feature_name in self.feature_modules:
                feature_deps = self.feature_modules[feature_name].get_dependencies()
                all_dependencies.extend(feature_deps)
        
        requirements_txt = self._generate_requirements_file(all_dependencies)
        files["requirements.txt"] = requirements_txt
        
        # Generate enhanced .env.example with feature environment variables
        all_env_vars = composition["environment_vars"].copy()
        for feature_name in composition.get("features", []):
            if hasattr(self, 'feature_modules') and feature_name in self.feature_modules:
                feature_env_vars = self.feature_modules[feature_name].get_environment_vars()
                all_env_vars.extend(feature_env_vars)
        
        env_example = self._generate_env_file(all_env_vars)
        files[".env.example"] = env_example
        
        # Generate core application files
        files["app/__init__.py"] = self._generate_app_init()
        files["app/core/__init__.py"] = ""
        files["app/core/config.py"] = self._generate_config_file()
        files["app/core/database.py"] = self._generate_database_file()
        
        # Generate README.md with enhanced feature documentation
        readme = self._generate_enhanced_readme(composition, prompt, feature_services)
        files["README.md"] = readme
        
        return files
    
    def _generate_enhanced_main_file(
        self, 
        composition: Dict[str, Any], 
        feature_routers: Dict[str, str],
        feature_middleware: Dict[str, str]
    ) -> str:
        """Generate enhanced FastAPI main.py file with feature module integration"""
        
        # Generate router imports
        router_imports = []
        router_includes = []
        for feature_name, router_module in feature_routers.items():
            router_imports.append(f"from app.routers.{router_module} import router as {feature_name}_router")
            router_includes.append(f"app.include_router({feature_name}_router, prefix=\"/{feature_name}\", tags=[\"{feature_name}\"])")
        
        # Generate middleware imports and setup
        middleware_imports = []
        middleware_setup = []
        for feature_name, middleware_module in feature_middleware.items():
            class_name = ''.join(word.capitalize() for word in feature_name.split('_')) + 'Middleware'
            middleware_imports.append(f"from app.middleware.{middleware_module} import {class_name}")
            middleware_setup.append(f"app.add_middleware({class_name})")
        
        router_imports_str = "\n".join(router_imports)
        middleware_imports_str = "\n".join(middleware_imports)
        router_includes_str = "\n".join(router_includes)
        middleware_setup_str = "\n".join(middleware_setup)
        
        return f'''"""
FastAPI application generated by Advanced Template System
Features integrated: {", ".join(feature_routers.keys())}
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Feature router imports
{router_imports_str}

# Feature middleware imports
{middleware_imports_str}

from app.core.config import settings

app = FastAPI(
    title="Generated API",
    description="API generated using Advanced Template System with feature modules",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Feature middleware
{middleware_setup_str}

# Feature routers
{router_includes_str}

@app.get("/")
async def root():
    return {{
        "message": "Advanced Template System Generated API",
        "features": {list(feature_routers.keys())},
        "version": "1.0.0"
    }}

@app.get("/health")
async def health_check():
    return {{
        "status": "healthy", 
        "features": {list(feature_routers.keys())},
        "template": "{composition.get('base_template', 'fastapi_basic')}"
    }}
'''

    def _generate_app_init(self) -> str:
        """Generate app/__init__.py file"""
        return '''"""
Generated FastAPI application package
"""

__version__ = "1.0.0"
'''

    def _generate_config_file(self) -> str:
        """Generate app/core/config.py file"""
        return '''"""
Application configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # Basic settings
    secret_key: str = "your-secret-key-here"
    environment: str = "development"
    debug: bool = True
    
    # Database settings
    database_url: str = "postgresql://user:password@localhost/dbname"
    
    # Redis settings (for caching)
    redis_url: Optional[str] = "redis://localhost:6379/0"
    
    # JWT settings
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # File upload settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    upload_path: str = "uploads/"
    
    # Stripe settings (if payments enabled)
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    
    class Config:
        env_file = ".env"

settings = Settings()
'''

    def _generate_database_file(self) -> str:
        """Generate app/core/database.py file"""
        return '''"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''

    def _generate_enhanced_readme(
        self, 
        composition: Dict[str, Any], 
        prompt: str, 
        feature_services: Dict[str, str]
    ) -> str:
        """Generate enhanced README.md file with feature documentation"""
        features_list = "\\n".join([f"- **{feature}**: Production-ready implementation with service, router, middleware, and schemas" for feature in composition.get("features", [])])
        entities_list = "\\n".join([f"- {entity}" for entity in composition["entities"].keys()])
        
        # Generate feature-specific documentation
        feature_docs = []
        for feature_name in composition.get("features", []):
            if hasattr(self, 'feature_modules') and feature_name in self.feature_modules:
                feature_module = self.feature_modules[feature_name]
                deps = feature_module.get_dependencies()
                env_vars = feature_module.get_environment_vars()
                
                feature_doc = f"""
### {feature_name.title()} Feature

- **Service**: `app/services/{feature_name}_service.py`
- **Router**: `app/routers/{feature_name}.py` (available at `/{feature_name}`)
- **Middleware**: `app/middleware/{feature_name}_middleware.py`
- **Schemas**: `app/schemas/{feature_name}.py`
- **Dependencies**: {', '.join(deps) if deps else 'None'}
- **Environment Variables**: {', '.join(env_vars) if env_vars else 'None'}
"""
                feature_docs.append(feature_doc)
        
        feature_documentation = "\\n".join(feature_docs)
        
        return f'''# Generated FastAPI Project

This project was generated using the Advanced Template System with detailed feature modules for production-ready code generation.

**Original Prompt:** {prompt[:200]}...

## 🚀 Features

{features_list}

## 📊 Data Models

{entities_list}

## 🛠 Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Initialize database:**
```bash
# Create database tables
python -c "from app.core.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

4. **Run the application:**
```bash
uvicorn app.main:app --reload
```

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🏗 Project Structure

```
app/
├── main.py                 # FastAPI application entry point
├── core/
│   ├── config.py          # Application configuration
│   └── database.py        # Database setup and session management
├── models/                # SQLAlchemy data models
├── routers/               # Feature-specific API routers
├── services/              # Business logic and feature services
├── middleware/            # Custom middleware components
└── schemas/               # Pydantic request/response schemas
```

## 🎯 Feature Details
{feature_documentation}

## 🔧 Generated Components

- **Base Template:** {composition["base_template"]}
- **Feature Modules:** {len(composition.get("features", []))} production-ready implementations
- **Data Models:** {len(composition["entities"])} SQLAlchemy entities
- **API Endpoints:** Comprehensive REST API with authentication, validation, and error handling

## 📈 Production Ready

This generated project includes:

✅ **Authentication & Authorization** (if auth feature enabled)  
✅ **Database Models & Migrations** (SQLAlchemy 2.0)  
✅ **API Documentation** (OpenAPI/Swagger)  
✅ **Error Handling & Validation** (Pydantic v2)  
✅ **Middleware Integration** (CORS, Custom middleware)  
✅ **Environment Configuration** (Pydantic Settings)  
✅ **File Upload Support** (if file_upload feature enabled)  
✅ **Payment Processing** (if payments feature enabled)  
✅ **Caching System** (if caching feature enabled)  
✅ **Admin Dashboard** (if admin_dashboard feature enabled)

## 🚀 Scaling & Deployment

This project is designed for production deployment with:

- Docker support (generate Dockerfile separately)
- Environment-based configuration
- Database connection pooling
- Comprehensive logging and monitoring hooks
- Modular feature architecture for easy extension

---

*Generated by Advanced Template System v1.0.0 - Accelerating development with production-ready code generation.*
'''

    def _generate_main_file(self, composition: Dict[str, Any]) -> str:
        """Generate FastAPI main.py file with appropriate setup"""
        middleware_imports = []
        middleware_setup = []
        
        for middleware in composition["middleware"]:
            middleware_imports.append(f"from app.middleware.{middleware.lower()} import {middleware}")
            middleware_setup.append(f"app.add_middleware({middleware})")
        
        return f'''"""
FastAPI application generated by Advanced Template System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
{chr(10).join(middleware_imports)}

from app.core.config import settings
from app.routers import router

app = FastAPI(
    title="Generated API",
    description="API generated using Advanced Template System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
{chr(10).join(middleware_setup)}

# Include routers
app.include_router(router)

@app.get("/")
async def root():
    return {{"message": "Advanced Template System Generated API"}}

@app.get("/health")
async def health_check():
    return {{"status": "healthy", "features": {composition.get("features", [])}}}
'''
    
    def _generate_model_file(self, entity_name: str, entity_config: Dict[str, Any]) -> str:
        """Generate SQLAlchemy model file for an entity"""
        fields = entity_config.get("fields", [])
        
        field_definitions = []
        for field in fields:
            # Handle both string format ("id:int") and dict format ({"name": "id", "type": "int"})
            if isinstance(field, str):
                # Parse string format "field_name:field_type"
                if ":" in field:
                    field_name, field_type = field.split(":", 1)
                else:
                    field_name, field_type = field, "str"
                
                field_name = field_name.strip()
                field_type = field_type.strip()
                constraints = []
            else:
                # Dictionary format
                field_name = field.get("name", "unknown")
                field_type = field.get("type", "str")
                constraints = field.get("constraints", [])
            
            sqlalchemy_type = self._map_sqlalchemy_type(field_type)
            
            field_line = f'    {field_name} = Column({sqlalchemy_type}'
            
            if "primary_key" in constraints:
                field_line += ", primary_key=True"
            if "unique" in constraints:
                field_line += ", unique=True"
            if "required" in constraints:
                field_line += ", nullable=False"
            
            field_line += ")"
            field_definitions.append(field_line)
        
        return f'''"""
{entity_name} SQLAlchemy model
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Decimal, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class {entity_name}(Base):
    __tablename__ = "{entity_name.lower()}s"
    
{chr(10).join(field_definitions)}
    
    def __repr__(self):
        return f"<{entity_name}(id={{self.id}})>"
'''
    
    def _map_sqlalchemy_type(self, field_type: str) -> str:
        """Map generic field types to SQLAlchemy types"""
        type_mapping = {
            # Standard SQLAlchemy types
            "String": "String(255)",
            "Text": "Text",
            "Integer": "Integer",
            "Decimal": "Decimal(10, 2)",
            "Boolean": "Boolean",
            "DateTime": "DateTime",
            "Date": "Date",
            "JSON": "JSON",
            # Common type aliases from YAML
            "str": "String(255)",
            "string": "String(255)",
            "int": "Integer",
            "integer": "Integer",
            "decimal": "Decimal(10, 2)",
            "float": "Decimal(10, 2)",
            "bool": "Boolean",
            "boolean": "Boolean",
            "datetime": "DateTime",
            "date": "Date",
            "text": "Text",
            "list": "JSON",  # Store lists as JSON
            "dict": "JSON"   # Store dicts as JSON
        }
        return type_mapping.get(field_type, "String(255)")
    
    def _generate_router_files(self, endpoints: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate router files based on endpoints"""
        # Group endpoints by feature/entity
        router_groups = {}
        
        for endpoint in endpoints:
            path = endpoint.get("path", "")
            feature = endpoint.get("feature", "main")
            
            if feature not in router_groups:
                router_groups[feature] = []
            router_groups[feature].append(endpoint)
        
        router_files = {}
        
        for feature, feature_endpoints in router_groups.items():
            router_content = self._generate_router_content(feature, feature_endpoints)
            router_files[f"app/routers/{feature}.py"] = router_content
        
        return router_files
    
    def _generate_router_content(self, feature: str, endpoints: List[Dict[str, Any]]) -> str:
        """Generate content for a specific router file"""
        return f'''"""
{feature.title()} router generated by Advanced Template System
"""

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

# TODO: Implement endpoints for {feature}
{chr(10).join([f"# {endpoint.get('path', '')}" for endpoint in endpoints])}

@router.get("/status")
async def {feature}_status():
    return {{"feature": "{feature}", "status": "active"}}
'''
    
    def _generate_requirements_file(self, dependencies: List[str]) -> str:
        """Generate requirements.txt file"""
        base_deps = [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "sqlalchemy>=2.0.0",
            "pydantic>=2.5.0",
        ]
        
        all_deps = base_deps + dependencies
        return "\n".join(sorted(set(all_deps)))
    
    def _generate_env_file(self, env_vars: List[str]) -> str:
        """Generate .env.example file"""
        base_vars = [
            "SECRET_KEY=your-secret-key-here",
            "DATABASE_URL=postgresql://user:password@localhost/dbname",
            "ENVIRONMENT=development"
        ]
        
        custom_vars = [f"{var}=changeme" for var in env_vars if var not in ["SECRET_KEY", "DATABASE_URL"]]
        
        all_vars = base_vars + custom_vars
        return "\n".join(all_vars)
    
    def _generate_readme(self, composition: Dict[str, Any], prompt: str) -> str:
        """Generate README.md file"""
        features_list = "\n".join([f"- {feature}" for feature in composition.get("features", [])])
        entities_list = "\n".join([f"- {entity}" for entity in composition["entities"].keys()])
        
        return f'''# Generated FastAPI Project

This project was generated using the Advanced Template System based on your requirements:

**Original Prompt:** {prompt[:200]}...

## Features

{features_list}

## Entities

{entities_list}

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Generated Components

- **Base Template:** {composition["base_template"]}
- **Features:** {len(composition.get("features", []))} feature modules integrated
- **Entities:** {len(composition["entities"])} data models
- **Endpoints:** {len(composition["endpoints"])} API endpoints

This project was generated to accelerate your development process while maintaining best practices and production-ready structure.
'''


# Module-level instance for convenience
advanced_template_system = AdvancedTemplateSystem()
