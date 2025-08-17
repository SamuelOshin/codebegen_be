# codebegen File Structure Documentation
**For Senior/Junior Engineers and AI Agents**

*Current Date: 2025-08-14 19:34:35 UTC*  
*Documented by: SamuelOshin*

---

## 📋 Project Overview

**codebegen** is an AI-powered FastAPI backend generator that transforms natural language prompts into production-ready FastAPI projects. This document explains the purpose and responsibility of each file in the project structure.

---

## 📁 **Root Directory Structure**

### **`pyproject.toml`**
**Purpose**: Modern Python project configuration file using PEP 518 standards.
**Contains**: Build system requirements, project metadata, tool configurations (Black, isort, pytest), dependency specifications, and development scripts.
**Used by**: pip, build tools, linters, formatters, and IDEs for project setup and tooling configuration.

### **`.gitignore`**
**Purpose**: Specifies files and directories that Git should ignore.
**Contains**: Python cache files, virtual environments, IDE files, model weights, generated projects, environment files, and temporary data.
**Used by**: Git version control to prevent committing sensitive or unnecessary files.

---

## 📁 **app/ Directory - Main Application Code**

### **`app/__init__.py`**
**Purpose**: Makes the app directory a Python package and initializes application-level imports.
**Contains**: Package initialization, version information, and common imports that other modules might need.
**Used by**: Python import system to recognize app as a package.

### **`app/main.py`**
**Purpose**: FastAPI application entry point and configuration hub.
**Contains**: FastAPI app instance, middleware setup, router registration, startup/shutdown events, CORS configuration, rate limiting, and AI model initialization.
**Used by**: ASGI servers (uvicorn) to serve the application and by deployment systems as the main entry point.

---

## 📁 **app/core/ - Application Core Components**

### **`app/core/__init__.py`**
**Purpose**: Core package initialization.
**Contains**: Core component exports and initialization logic.

### **`app/core/config.py`**
**Purpose**: Centralized configuration management using Pydantic settings.
**Contains**: Environment variable definitions, database URLs, AI model paths, external service credentials, feature flags, and validation logic.
**Used by**: All application components that need configuration values, environment-specific settings, and deployment configurations.

### **`app/core/security.py`**
**Purpose**: Security utilities and authentication helpers.
**Contains**: JWT token creation/validation, password hashing, OAuth helpers, API key validation, and security middleware functions.
**Used by**: Authentication routes, protected endpoints, and middleware for securing API access.

### **`app/core/database.py`**
**Purpose**: Database connection and session management.
**Contains**: SQLAlchemy engine setup, session factory, connection pooling configuration, and dependency injection for database sessions.
**Used by**: Repository classes, API routes, and migration scripts for database operations.

### **`app/core/exceptions.py`**
**Purpose**: Custom exception classes and global exception handlers.
**Contains**: Business logic exceptions, HTTP exception mappers, error response formatters, and FastAPI exception handlers.
**Used by**: Services, routes, and middleware for consistent error handling and user-friendly error responses.

---

## 📁 **app/auth/ - Authentication System**

### **`app/auth/__init__.py`**
**Purpose**: Authentication package initialization.
**Contains**: Auth module exports and common authentication imports.

### **`app/auth/dependencies.py`**
**Purpose**: FastAPI dependency functions for authentication and authorization.
**Contains**: Current user dependency, permission checkers, token validation, and role-based access control functions.
**Used by**: API routes that require authentication, protected endpoints, and middleware for access control.

### **`app/auth/handlers.py`**
**Purpose**: Authentication business logic and OAuth integrations.
**Contains**: Login/logout logic, GitHub OAuth flow, token refresh, user registration, and password reset functionality.
**Used by**: Authentication routes and external service integrations for user management.

### **`app/auth/models.py`**
**Purpose**: Authentication-related database models.
**Contains**: User sessions, OAuth tokens, API keys, and authentication audit logs.
**Used by**: Authentication services and routes for storing and retrieving auth-related data.

---

## 📁 **app/models/ - Database Models (SQLAlchemy ORM)**

### **`app/models/__init__.py`**
**Purpose**: Models package initialization and exports.
**Contains**: All model imports for easy access and Alembic auto-discovery.

### **`app/models/base.py`**
**Purpose**: Base model class with common fields and utilities.
**Contains**: Common fields (id, created_at, updated_at), base class methods, and database table configuration.
**Used by**: All other models as a parent class for consistent structure and behavior.

### **`app/models/user.py`**
**Purpose**: User account and profile data model.
**Contains**: User information (email, username, profile), account status, preferences, and relationship definitions.
**Used by**: Authentication system, user management, and billing for storing user data.

### **`app/models/project.py`**
**Purpose**: User projects and their metadata.
**Contains**: Project details (name, description, domain), technical specifications, settings, and relationships to generations.
**Used by**: Project management features, AI generation tracking, and user workspace organization.

### **`app/models/generation.py`**
**Purpose**: AI generation results and processing history.
**Contains**: Generation requests, AI pipeline outputs, processing status, quality metrics, and file storage references.
**Used by**: AI services, generation tracking, and result delivery for storing and retrieving generated code.

### **`app/models/organization.py`**
**Purpose**: Team/organization management for collaborative features.
**Contains**: Organization details, member roles, billing information, and shared resources.
**Used by**: Team features, billing system, and access control for multi-user collaboration.

---

## 📁 **app/schemas/ - Pydantic Data Models**

### **`app/schemas/__init__.py`**
**Purpose**: Schemas package initialization and exports.
**Contains**: Common schema imports and validation utilities.

### **`app/schemas/base.py`**
**Purpose**: Base schema classes with common fields and validation.
**Contains**: Common response formats, pagination schemas, and base validation logic.
**Used by**: All other schemas as parent classes for consistent API data structures.

### **`app/schemas/user.py`**
**Purpose**: User-related request/response data structures.
**Contains**: User registration, profile updates, authentication responses, and user listing formats.
**Used by**: User management routes for request validation and response formatting.

### **`app/schemas/project.py`**
**Purpose**: Project-related API data structures.
**Contains**: Project creation requests, update schemas, listing responses, and project configuration formats.
**Used by**: Project management routes for handling project CRUD operations.

### **`app/schemas/generation.py`**
**Purpose**: AI generation request/response schemas.
**Contains**: Generation request validation, progress tracking, result formatting, and error response structures.
**Used by**: AI generation routes for request validation and response formatting.

### **`app/schemas/ai.py`**
**Purpose**: AI service-specific data structures.
**Contains**: Model configuration, prompt formatting, pipeline stage definitions, and AI model response formats.
**Used by**: AI services and routes for handling AI-specific data and responses.

---

## 📁 **app/routers/ - API Endpoints**

### **`app/routers/__init__.py`**
**Purpose**: Routers package initialization.
**Contains**: Router exports and common route utilities.

### **`app/routers/auth.py`**
**Purpose**: Authentication and authorization API endpoints.
**Contains**: Login, logout, registration, password reset, OAuth callbacks, and token refresh endpoints.
**Used by**: Frontend applications and clients for user authentication flows.

### **`app/routers/projects.py`**
**Purpose**: Project management API endpoints.
**Contains**: Project CRUD operations, sharing, templates, and project-specific settings management.
**Used by**: Frontend project management interfaces and project organization features.

### **`app/routers/generations.py`**
**Purpose**: AI generation management endpoints.
**Contains**: Generation history, status tracking, result retrieval, and generation analytics.
**Used by**: Frontend generation monitoring and result management interfaces.

### **`app/routers/ai.py`**
**Purpose**: AI service endpoints for code generation.
**Contains**: Project generation, iteration requests, streaming progress, and AI model interaction endpoints.
**Used by**: Frontend generation interface and AI service interactions.

### **`app/routers/webhooks.py`**
**Purpose**: External service webhook handlers.
**Contains**: GitHub webhooks, Stripe billing webhooks, and other third-party service notifications.
**Used by**: External services to notify the application of events and status changes.

---

## 📁 **app/services/ - Business Logic Layer**

### **`app/services/__init__.py`**
**Purpose**: Services package initialization.
**Contains**: Service exports and common business logic utilities.

### **`app/services/ai_orchestrator.py`**
**Purpose**: Main AI pipeline coordinator and multi-model management.
**Contains**: Pipeline orchestration, model loading, generation workflow, quality scoring, and model resource management.
**Used by**: AI routes and background tasks for coordinating the complete AI generation process.

### **`app/services/schema_parser.py`**
**Purpose**: Natural language to database schema extraction service.
**Contains**: Entity extraction, relationship inference, field type detection, and schema validation logic.
**Used by**: AI orchestrator for converting user prompts into structured database schemas.

### **`app/services/code_generator.py`**
**Purpose**: FastAPI project code generation service.
**Contains**: Template selection, code generation, file structure creation, and code formatting logic.
**Used by**: AI orchestrator for generating complete FastAPI project files from schemas and prompts.

### **`app/services/code_reviewer.py`**
**Purpose**: AI-powered code quality and security review service.
**Contains**: Code analysis, security scanning, best practice validation, and improvement suggestions.
**Used by**: AI orchestrator for ensuring generated code quality and security standards.

### **`app/services/docs_generator.py`**
**Purpose**: Documentation and README generation service.
**Contains**: README creation, API documentation, deployment guides, and usage instructions generation.
**Used by**: AI orchestrator for creating comprehensive documentation for generated projects.

### **`app/services/github_service.py`**
**Purpose**: GitHub integration and repository management service.
**Contains**: Repository creation, PR generation, branch management, and GitHub API interactions.
**Used by**: Generation delivery system for pushing generated code to GitHub repositories.

### **`app/services/billing_service.py`**
**Purpose**: Subscription and payment management service.
**Contains**: Stripe integration, usage tracking, billing calculations, and subscription management.
**Used by**: Billing routes and usage enforcement for handling payments and subscriptions.

---

## 📁 **app/repositories/ - Data Access Layer**

### **`app/repositories/__init__.py`**
**Purpose**: Repositories package initialization.
**Contains**: Repository exports and common data access utilities.

### **`app/repositories/base.py`**
**Purpose**: Base repository class with common CRUD operations.
**Contains**: Generic CRUD methods, query utilities, pagination helpers, and transaction management.
**Used by**: All other repositories as a parent class for consistent data access patterns.

### **`app/repositories/user_repository.py`**
**Purpose**: User data access operations.
**Contains**: User queries, authentication lookups, profile management, and user-specific data operations.
**Used by**: User services and authentication systems for database operations involving users.

### **`app/repositories/project_repository.py`**
**Purpose**: Project data access operations.
**Contains**: Project CRUD, search, filtering, and project-specific queries.
**Used by**: Project services for managing project data and relationships.

### **`app/repositories/generation_repository.py`**
**Purpose**: Generation data access operations.
**Contains**: Generation history, status updates, result storage, and generation-specific queries.
**Used by**: AI services and generation tracking for managing generation data.

---

## 📁 **app/utils/ - Utility Functions**

### **`app/utils/__init__.py`**
**Purpose**: Utils package initialization.
**Contains**: Utility function exports and common helpers.

### **`app/utils/file_utils.py`**
**Purpose**: File and storage management utilities.
**Contains**: File upload/download, ZIP creation, file validation, and storage abstraction.
**Used by**: Generation services and file management features for handling generated project files.

### **`app/utils/validators.py`**
**Purpose**: Custom validation functions for data integrity.
**Contains**: Input validation, business rule validation, and data consistency checks.
**Used by**: Services and routes for ensuring data quality and business rule compliance.

### **`app/utils/formatters.py`**
**Purpose**: Data formatting and transformation utilities.
**Contains**: Code formatting, response formatting, data serialization, and presentation utilities.
**Used by**: Services and routes for consistent data presentation and formatting.

---

## 📁 **ai_models/ - AI Model Management**

### **`ai_models/__init__.py`**
**Purpose**: AI models package initialization.
**Contains**: Model imports and AI system initialization.

### **`ai_models/model_loader.py`**
**Purpose**: Common model loading and management utilities.
**Contains**: Model download, caching, memory management, and loading abstractions.
**Used by**: All AI model services for consistent model loading and resource management.

### **`ai_models/qwen_generator.py`**
**Purpose**: Qwen2.5-Coder-32B model wrapper for code generation.
**Contains**: Model initialization, LoRA loading, prompt formatting, and code generation logic.
**Used by**: AI orchestrator for the primary code generation functionality.

### **`ai_models/llama_parser.py`**
**Purpose**: Llama-3.1-8B model wrapper for schema extraction.
**Contains**: Natural language processing, entity extraction, and schema inference logic.
**Used by**: AI orchestrator for converting prompts into structured schemas.

### **`ai_models/starcoder_reviewer.py`**
**Purpose**: Starcoder2-15B model wrapper for code review.
**Contains**: Code analysis, security scanning, and quality assessment logic.
**Used by**: AI orchestrator for automated code review and quality assurance.

### **`ai_models/mistral_docs.py`**
**Purpose**: Mistral-7B model wrapper for documentation generation.
**Contains**: Documentation creation, README generation, and explanation text creation.
**Used by**: AI orchestrator for generating comprehensive project documentation.

---

## 📁 **templates/ - Code Generation Templates**

### **`templates/fastapi_basic/`**
**Purpose**: Basic FastAPI project template with minimal dependencies.
**Contains**: Template configuration, file templates for simple CRUD APIs, and basic project structure.
**Used by**: Code generator for creating simple FastAPI projects without complex features.

### **`templates/fastapi_sqlalchemy/`**
**Purpose**: FastAPI template with SQLAlchemy ORM and PostgreSQL.
**Contains**: Database models, migrations, advanced CRUD operations, and production-ready configurations.
**Used by**: Code generator for creating database-backed APIs with ORM capabilities.

### **`templates/fastapi_mongo/`**
**Purpose**: FastAPI template with MongoDB and Beanie ODM.
**Contains**: Document models, MongoDB configurations, and NoSQL-specific operations.
**Used by**: Code generator for creating APIs that work with MongoDB databases.

### **`templates/*/template.yaml`**
**Purpose**: Template metadata and configuration files.
**Contains**: Template specifications, variable definitions, feature flags, and generation rules.
**Used by**: Code generator to understand template capabilities and configuration options.

### **`templates/*/files/`**
**Purpose**: Template file directories containing actual code templates.
**Contains**: Jinja2 templates for Python files, configuration files, and documentation.
**Used by**: Code generator to create actual project files with user-specific customizations.

---

## 📁 **infra/ - Infrastructure and Deployment**

### **`infra/docker-compose.yml`**
**Purpose**: Local development environment orchestration.
**Contains**: Service definitions for API, database, Redis, and background workers.
**Used by**: Developers for setting up consistent local development environments.

### **`infra/Dockerfile`**
**Purpose**: Production container image definition.
**Contains**: Multi-stage build, dependency installation, security configurations, and runtime setup.
**Used by**: Container orchestration platforms and deployment pipelines for running the application.

### **`infra/.env.example`**
**Purpose**: Template for environment variable configuration.
**Contains**: Required environment variables, example values, and configuration documentation.
**Used by**: Developers and deployment systems for understanding required configuration.

### **`infra/nginx.conf`**
**Purpose**: Reverse proxy and load balancer configuration.
**Contains**: Routing rules, SSL configuration, rate limiting, and caching policies.
**Used by**: Production deployments for handling HTTP requests and load balancing.

---

## 📁 **docs/ - Documentation**

### **`docs/README.md`**
**Purpose**: Primary project documentation and getting started guide.
**Contains**: Project overview, installation instructions, usage examples, and contribution guidelines.
**Used by**: Developers, users, and contributors for understanding and using the project.

### **`docs/openapi.yaml`**
**Purpose**: API specification in OpenAPI 3.0 format.
**Contains**: Endpoint definitions, request/response schemas, authentication, and API documentation.
**Used by**: API consumers, frontend developers, and documentation generators.

### **`docs/architecture.md`**
**Purpose**: Technical architecture documentation.
**Contains**: System design, data flow, AI pipeline architecture, and technical decisions.
**Used by**: Engineers for understanding system architecture and making technical decisions.

### **`docs/deployment.md`**
**Purpose**: Deployment and operations guide.
**Contains**: Deployment instructions, environment setup, monitoring, and troubleshooting.
**Used by**: DevOps engineers and deployment systems for running the application in production.

---

## 📁 **tests/ - Test Suite**

### **`tests/__init__.py`**
**Purpose**: Tests package initialization.
**Contains**: Test utilities and common test imports.

### **`tests/conftest.py`**
**Purpose**: Pytest configuration and shared fixtures.
**Contains**: Database fixtures, authentication mocks, AI model mocks, and test utilities.
**Used by**: All test files for consistent test setup and shared testing utilities.

### **`tests/test_auth/`**
**Purpose**: Authentication system tests.
**Contains**: Login tests, OAuth flow tests, permission tests, and security validation tests.
**Used by**: CI/CD for ensuring authentication system reliability and security.

### **`tests/test_services/`**
**Purpose**: Business logic and service layer tests.
**Contains**: AI orchestrator tests, service integration tests, and business rule validation tests.
**Used by**: CI/CD for ensuring core business logic correctness and reliability.

### **`tests/test_ai/`**
**Purpose**: AI model and generation tests.
**Contains**: Model loading tests, generation quality tests, pipeline integration tests, and AI performance tests.
**Used by**: CI/CD for ensuring AI system reliability and generation quality.

### **`tests/test_integration/`**
**Purpose**: End-to-end integration tests.
**Contains**: Full workflow tests, API integration tests, and system behavior validation.
**Used by**: CI/CD for ensuring complete system functionality and user experience quality.

---

## 📁 **scripts/ - Utility Scripts**

### **`scripts/setup.py`**
**Purpose**: Initial project setup and configuration script.
**Contains**: Database initialization, model downloads, environment setup, and development tools installation.
**Used by**: Developers and deployment systems for initial project configuration.

### **`scripts/migrate.py`**
**Purpose**: Database migration and schema management script.
**Contains**: Migration execution, rollback capabilities, and database state management.
**Used by**: Deployment pipelines and developers for managing database changes.

### **`scripts/seed_data.py`**
**Purpose**: Development and testing data seeding script.
**Contains**: Sample data creation, test user setup, and development environment population.
**Used by**: Developers for creating consistent development and testing environments.

---

## 📁 **requirements/ - Dependency Management**

### **`requirements/base.txt`**
**Purpose**: Core application dependencies required for all environments.
**Contains**: FastAPI, SQLAlchemy, Pydantic, AI libraries, and essential runtime dependencies.
**Used by**: All environments for installing core application functionality.

### **`requirements/dev.txt`**
**Purpose**: Development-specific dependencies and tools.
**Contains**: Testing frameworks, code formatters, linters, debugging tools, and development utilities.
**Used by**: Development environments for enhanced development experience and code quality tools.

### **`requirements/prod.txt`**
**Purpose**: Production-optimized dependencies with specific versions.
**Contains**: Pinned versions, production ASGI servers, monitoring tools, and performance optimizations.
**Used by**: Production deployments for stable, secure, and optimized application runtime.

---

## 📁 **alembic/ - Database Migrations**

### **`alembic/versions/`**
**Purpose**: Database migration scripts directory.
**Contains**: Versioned migration files for database schema changes.
**Used by**: Migration system for tracking and applying database changes over time.

### **`alembic/env.py`**
**Purpose**: Alembic environment configuration.
**Contains**: Database connection setup, migration context configuration, and environment-specific settings.
**Used by**: Alembic migration system for connecting to databases and managing migration context.

### **`alembic/script.py.mako`**
**Purpose**: Template for generating new migration scripts.
**Contains**: Migration script template with standard structure and common patterns.
**Used by**: Alembic for generating consistent migration files when schema changes are made.

---

## 🎯 **Key Integration Points**

### **For AI Agents (Copilot/Claude/Cursor):**
- **Main entry point**: `app/main.py` - Start here for understanding application structure
- **AI pipeline**: `app/services/ai_orchestrator.py` - Core AI functionality coordination
- **API endpoints**: `app/routers/` - User-facing functionality and request handling
- **Data models**: `app/models/` - Database structure and relationships
- **Configuration**: `app/core/config.py` - Environment and feature configuration

### **For Senior Engineers:**
- Focus on service layer (`app/services/`) for business logic architecture
- Review AI model integration (`ai_models/`) for understanding AI capabilities
- Examine infrastructure (`infra/`) for deployment and scaling considerations
- Check test structure (`tests/`) for quality assurance and testing strategy

### **For Junior Engineers:**
- Start with schemas (`app/schemas/`) to understand data structures
- Review routers (`app/routers/`) for API endpoint patterns
- Study repositories (`app/repositories/`) for data access patterns
- Examine utilities (`app/utils/`) for reusable helper functions

This structure provides a scalable, maintainable foundation for an AI-powered FastAPI backend generator that can evolve with user needs and technology advances.