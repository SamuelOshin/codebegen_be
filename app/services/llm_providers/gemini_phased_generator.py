"""
Phased Code Generation Strategy for Gemini

Breaks down code generation into multiple phases to stay within token limits
while maintaining high code quality and architectural patterns.

This approach mirrors how production AI coding assistants (Cursor, v0.dev, Replit AI)
generate code - in focused phases rather than all at once.
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .gemini_provider import GeminiProvider

from .base_provider import LLMTask

logger = logging.getLogger(__name__)


class GeminiPhasedGenerator:
    """
    Multi-phase code generator that produces high-quality code
    while respecting token limitations.
    
    Phases:
    1. Core Infrastructure (config, database, security) - ~4K tokens
    2. Models & Schemas (per entity) - ~2K tokens each
    3. Repository Layer (per entity) - ~3K tokens each
    4. API Routers (per entity) - ~4K tokens each
    5. Support Files (requirements, README, Docker) - ~4K tokens
    6. Main Application (integration) - ~2K tokens
    
    Total: Scales with number of entities, never hits 8K limit per call
    """
    
    def __init__(self, provider: 'GeminiProvider', file_manager: Optional[Any] = None, event_callback: Optional[Any] = None):
        self.provider = provider
        self.file_manager = file_manager
        self.event_callback = event_callback
        self.generation_id = None
    
    async def _emit_event(self, event_data: Dict[str, Any]) -> None:
        """Emit event to frontend if callback is available"""
        if self.event_callback and self.generation_id:
            try:
                await self.event_callback(self.generation_id, event_data)
            except Exception as e:
                logger.warning(f"Failed to emit event: {e}")
    
    async def _save_phase_files(self, phase_name: str, files: Dict[str, str]) -> None:
        """Save files from a phase to storage"""
        if self.file_manager and self.generation_id and files:
            try:
                await self.file_manager.save_generation_files(self.generation_id, files)
                logger.info(f"💾 Saved {len(files)} files from {phase_name} to storage/{self.generation_id}")
                print(f"   💾 Files saved to storage/{self.generation_id}")
            except Exception as e:
                logger.error(f"Failed to save {phase_name} files: {e}")
                print(f"   ⚠️  Failed to save files: {e}")
    
    async def generate_complete_project(
        self,
        prompt: str,
        schema: Dict[str, Any],
        context: Dict[str, Any],
        generation_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate complete project using phased approach"""
        
        # Store generation_id for file saving
        self.generation_id = generation_id
        
        # Extract entities first
        all_files = {}
        entities = schema.get('entities', [])
        tech_stack = context.get('tech_stack', 'fastapi_postgres')
        
        # Emit initial event
        await self._emit_event({
            "status": "processing",
            "stage": "phased_generation_started",
            "message": f"Starting phased generation for {len(entities)} entities",
            "progress": 5,
            "generation_mode": "classic",
            "phase_info": {
                "total_phases": 6,
                "current_phase": 0,
                "entities_count": len(entities)
            }
        })
        
        print(f"\n{'='*80}")
        print(f"🏗️  PHASED GENERATION STARTED")
        print(f"{'='*80}")
        print(f"📝 Prompt: {prompt[:80]}...")
        print(f"📊 Total Entities: {len(entities)}")
        print(f"⚙️  Tech Stack: {tech_stack}")
        print(f"📋 Total Phases: 6")
        print(f"🎯 Strategy: Generate high-quality code with repository pattern")
        if self.generation_id:
            print(f"💾 Storage: ./storage/projects/{self.generation_id}")
        print(f"{'='*80}\n")
        
        logger.info(f"Starting phased generation for {len(entities)} entities")
        
        # Phase 1: Core Infrastructure
        print(f"📦 Phase 1/6: Generating core infrastructure...")
        logger.info("Phase 1: Core infrastructure")
        core_files = await self._generate_core_infrastructure(schema, context)
        if core_files and isinstance(core_files, dict):
            all_files.update(core_files)
            print(f"✅ Generated {len(core_files)} core files")
            print(f"   Files: {', '.join(core_files.keys())}")
            await self._save_phase_files("Phase 1 - Core Infrastructure", all_files)
            
            # Emit Phase 1 completion event
            await self._emit_event({
                "status": "processing",
                "stage": "phase_1_complete",
                "message": f"Phase 1 complete: Generated {len(core_files)} core infrastructure files",
                "progress": 20,
                "generation_mode": "classic",
                "phase_info": {
                    "phase": 1,
                    "name": "Core Infrastructure",
                    "files_generated": len(core_files),
                    "total_files": len(all_files)
                }
            })
            print()
        else:
            logger.error("Failed to generate core infrastructure files")
            raise ValueError("Core infrastructure generation returned invalid result")
        
        # Phase 2-4: Per-Entity Generation
        total_entities = len(entities)
        for idx, entity in enumerate(entities, 1):
            entity_name = entity.get('name', f'Entity{idx}')
            print(f"🔧 Phase 2-4 ({idx}/{len(entities)}): Processing entity '{entity_name}'...")
            logger.info(f"Processing entity: {entity_name}")
            
            # Emit entity processing start event
            entity_progress = 20 + (idx / total_entities * 40)  # 20-60% range for entities
            await self._emit_event({
                "status": "processing",
                "stage": f"entity_processing_{idx}",
                "message": f"Processing entity {idx}/{total_entities}: {entity_name}",
                "progress": int(entity_progress),
                "generation_mode": "classic",
                "phase_info": {
                    "phase": f"2-4 ({idx}/{total_entities})",
                    "name": f"Entity: {entity_name}",
                    "current_entity": idx,
                    "total_entities": total_entities,
                    "files_generated": len(all_files)
                }
            })
            
            # Generate model
            try:
                model_file = await self._generate_model(entity, schema, context)
                if model_file and isinstance(model_file, dict):
                    all_files.update(model_file)
                else:
                    logger.warning(f"Model generation for {entity_name} returned invalid result")
            except Exception as e:
                logger.error(f"Failed to generate model for {entity_name}: {e}")
                model_file = None
            
            # Generate schema
            try:
                schema_file = await self._generate_schema(entity, context)
                if schema_file and isinstance(schema_file, dict):
                    all_files.update(schema_file)
                else:
                    logger.warning(f"Schema generation for {entity_name} returned invalid result")
            except Exception as e:
                logger.error(f"Failed to generate schema for {entity_name}: {e}")
                schema_file = None
            
            # Generate repository
            try:
                repo_file = await self._generate_repository(entity, context)
                if repo_file and isinstance(repo_file, dict):
                    all_files.update(repo_file)
                else:
                    logger.warning(f"Repository generation for {entity_name} returned invalid result")
            except Exception as e:
                logger.error(f"Failed to generate repository for {entity_name}: {e}")
                repo_file = None
            
            # Generate router
            try:
                router_file = await self._generate_router(entity, schema, context)
                if router_file and isinstance(router_file, dict):
                    all_files.update(router_file)
                else:
                    logger.warning(f"Router generation for {entity_name} returned invalid result")
            except Exception as e:
                logger.error(f"Failed to generate router for {entity_name}: {e}")
                router_file = None
            
            # Count successful files
            entity_files = [f for f in [model_file, schema_file, repo_file, router_file] if f and isinstance(f, dict)]
            print(f"✅ Generated {len(entity_files)}/4 files for {entity_name}")
            if len(entity_files) < 4:
                print(f"   ⚠️  Some files failed to generate")
            print(f"   Target files: model, schema, repository, router")
            
            # Emit entity completion event
            await self._emit_event({
                "status": "processing",
                "stage": f"entity_complete_{idx}",
                "message": f"Completed {idx}/{total_entities} entities: {entity_name} ({len(entity_files)}/4 files)",
                "progress": int(entity_progress + (40 / total_entities)),
                "generation_mode": "classic",
                "phase_info": {
                    "phase": f"2-4 ({idx}/{total_entities})",
                    "name": f"Entity Complete: {entity_name}",
                    "entity_files_generated": len(entity_files),
                    "total_files": len(all_files)
                }
            })
            
            # Save files after each entity
            await self._save_phase_files(f"Phase 2-4 - Entity {entity_name}", all_files)
            print()
        
        # Phase 5: Support Files
        print(f"📝 Phase 5/6: Generating support files...")
        logger.info("Phase 5: Support files")
        
        # Emit Phase 5 start event
        await self._emit_event({
            "status": "processing",
            "stage": "phase_5_start",
            "message": "Generating support files (requirements, README, etc.)",
            "progress": 65,
            "generation_mode": "classic",
            "phase_info": {
                "phase": 5,
                "name": "Support Files",
                "total_files": len(all_files)
            }
        })
        
        support_files = await self._generate_support_files(schema, context, entities)
        if support_files and isinstance(support_files, dict):
            all_files.update(support_files)
            print(f"✅ Generated {len(support_files)} support files")
            print(f"   Files: {', '.join(support_files.keys())}")
            await self._save_phase_files("Phase 5 - Support Files", all_files)
            
            # Emit Phase 5 completion event
            await self._emit_event({
                "status": "processing",
                "stage": "phase_5_complete",
                "message": f"Phase 5 complete: Generated {len(support_files)} support files",
                "progress": 75,
                "generation_mode": "classic",
                "phase_info": {
                    "phase": 5,
                    "name": "Support Files Complete",
                    "files_generated": len(support_files),
                    "total_files": len(all_files)
                }
            })
            print()
        else:
            logger.warning("Failed to generate support files, continuing...")
        
        # Phase 6: Integration & Main App
        print(f"🚀 Phase 6/6: Generating main application...")
        logger.info("Phase 6: Main application")
        
        # Emit Phase 6 start event
        await self._emit_event({
            "status": "processing",
            "stage": "phase_6_start",
            "message": "Generating main application entry point",
            "progress": 80,
            "generation_mode": "classic",
            "phase_info": {
                "phase": 6,
                "name": "Main Application",
                "total_files": len(all_files)
            }
        })
        
        main_files = await self._generate_main_app(entities, context)
        if main_files and isinstance(main_files, dict):
            all_files.update(main_files)
            print(f"✅ Generated application entry point")
            print(f"   Files: {', '.join(main_files.keys())}")
            await self._save_phase_files("Phase 6 - Main Application", all_files)
            
            # Emit Phase 6 completion event
            await self._emit_event({
                "status": "processing",
                "stage": "phase_6_complete",
                "message": f"Phase 6 complete: Main application ready",
                "progress": 90,
                "generation_mode": "classic",
                "phase_info": {
                    "phase": 6,
                    "name": "Main Application Complete",
                    "files_generated": len(main_files),
                    "total_files": len(all_files)
                }
            })
            print()
        else:
            logger.warning("Failed to generate main application files, continuing...")
        
        print(f"{'='*80}")
        print(f"✨ PHASED GENERATION COMPLETE")
        print(f"{'='*80}")
        print(f"📊 Total Files Generated: {len(all_files)}")
        
        if not all_files:
            logger.error("Phased generation failed: No files were generated")
            raise ValueError("Phased generation produced no files")
        
        # Emit final completion event
        await self._emit_event({
            "status": "completed",
            "stage": "phased_generation_complete",
            "message": f"Generation complete: {len(all_files)} files created",
            "progress": 100,
            "generation_mode": "classic",
            "phase_info": {
                "phase": 6,
                "name": "Complete",
                "total_files": len(all_files),
                "total_entities": len(entities)
            }
        })
        
        print(f"📁 Project Structure:")
        self._print_file_tree(all_files)
        print(f"{'='*80}\n")
        
        logger.info(f"Phased generation completed successfully: {len(all_files)} files")
        
        return all_files
    
    async def _generate_core_infrastructure(
        self,
        schema: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Phase 1: Generate core infrastructure files"""
        
        prompt = f"""Generate core infrastructure files for a FastAPI project.

DATABASE: PostgreSQL with SQLAlchemy async
AUTHENTICATION: JWT tokens
TECH STACK: FastAPI, Pydantic v2, SQLAlchemy 2.0

Generate these files as a JSON object:

{{
  "app/__init__.py": "",
  "app/core/__init__.py": "",
  "app/core/config.py": "Pydantic Settings class with DATABASE_URL, SECRET_KEY (from secrets.token_urlsafe), ALGORITHM='HS256', ACCESS_TOKEN_EXPIRE_MINUTES=30, CORS_ORIGINS=['*']",
  "app/core/database.py": "SQLAlchemy async engine (create_async_engine), AsyncSessionLocal (async_sessionmaker), Base (declarative_base), get_db() dependency that yields session",
  "app/core/security.py": "pwd_context (CryptContext with bcrypt), verify_password(), get_password_hash(), create_access_token(), decode_access_token(), get_current_user() dependency"
}}

Requirements:
- Use pydantic-settings BaseSettings with model_config
- Use sqlalchemy.ext.asyncio for async database operations
- Use passlib[bcrypt] for password hashing
- Use python-jose[cryptography] for JWT (HS256 algorithm)
- Include proper type hints (from typing import Optional, List)
- Add comprehensive docstrings
- Use async/await throughout
- Include error handling with HTTPException
- Make get_current_user raise 401 if token invalid

Return ONLY the JSON object with complete, production-ready code."""

        response = await self.provider.generate_completion(
            prompt,
            task=LLMTask.CODE_GENERATION,
            temperature=0.2,
            max_tokens=4096
        )
        
        return self.provider._extract_json(response)
    
    async def _generate_model(
        self,
        entity: Dict[str, Any],
        schema: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate SQLAlchemy model for an entity"""
        
        entity_name = entity.get('name', 'Entity')
        fields = entity.get('fields', [])
        relationships = entity.get('relationships', [])
        
        prompt = f"""Generate a SQLAlchemy async model for the {entity_name} entity.

ENTITY: {entity_name}

FIELDS:
{self._format_fields(fields)}

RELATIONSHIPS:
{self._format_relationships(relationships)}

Generate as JSON:
{{
  "app/models/{entity_name.lower()}.py": "Complete SQLAlchemy async model code"
}}

Requirements:
- Import: from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
- Import: from sqlalchemy.orm import relationship
- Import: from app.core.database import Base
- Import: from datetime import datetime
- Class {entity_name}(Base) with __tablename__ = "{entity_name.lower()}s"
- Add id = Column(Integer, primary_key=True, index=True)
- Map each field to appropriate Column type
- Add created_at = Column(DateTime, default=datetime.utcnow)
- Add updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
- Add relationships with back_populates
- Include __repr__ method showing id and primary field
- Add table args with indexes for frequently queried fields
- Use proper cascade rules for delete (cascade="all, delete-orphan")
- Add comprehensive docstring
- Use proper type hints

Return ONLY valid JSON with complete code."""

        response = await self.provider.generate_completion(
            prompt,
            task=LLMTask.CODE_GENERATION,
            temperature=0.2,
            max_tokens=2048
        )
        
        return self.provider._extract_json(response)
    
    async def _generate_schema(
        self,
        entity: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate Pydantic schemas for an entity"""
        
        entity_name = entity.get('name', 'Entity')
        fields = entity.get('fields', [])
        
        prompt = f"""Generate Pydantic v2 schemas for {entity_name}.

FIELDS:
{self._format_fields(fields)}

Generate as JSON:
{{
  "app/schemas/{entity_name.lower()}.py": "Complete Pydantic schema code"
}}

Create these 5 schemas:

1. {entity_name}Base(BaseModel):
   - All fields from FIELDS (except id, created_at, updated_at)
   - Mark required fields as required
   - Optional fields use: field_name: Optional[type] = None

2. {entity_name}Create({entity_name}Base):
   - Inherits all from Base
   - For POST requests
   - Add ConfigDict(json_schema_extra) with example

3. {entity_name}Update(BaseModel):
   - ALL fields Optional (for partial updates)
   - For PUT/PATCH requests

4. {entity_name}InDB({entity_name}Base):
   - Inherits from Base
   - Add: id: int
   - Add: created_at: datetime
   - Add: updated_at: datetime
   - Add: model_config = ConfigDict(from_attributes=True)

5. {entity_name}Response({entity_name}InDB):
   - Same as InDB
   - For API responses

Requirements:
- Import: from pydantic import BaseModel, Field, ConfigDict, field_validator
- Import: from typing import Optional, List
- Import: from datetime import datetime
- Add field validators for email, URL, length constraints where appropriate
- Add examples in ConfigDict(json_schema_extra) for OpenAPI docs
- Use Field(...) for required fields with description
- Add comprehensive docstrings
- Use proper type hints

Return ONLY valid JSON."""

        response = await self.provider.generate_completion(
            prompt,
            task=LLMTask.CODE_GENERATION,
            temperature=0.2,
            max_tokens=2048
        )
        
        return self.provider._extract_json(response)
    
    async def _generate_repository(
        self,
        entity: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate repository layer for an entity"""
        
        entity_name = entity.get('name', 'Entity')
        
        prompt = f"""Generate a repository class for {entity_name} following the Repository Pattern.

Generate as JSON:
{{
  "app/repositories/{entity_name.lower()}_repository.py": "Complete repository code"
}}

Create {entity_name}Repository class with these async methods:

1. get_by_id(db: AsyncSession, id: int) -> Optional[{entity_name}]
   - Use: result = await db.execute(select({entity_name}).filter({entity_name}.id == id))
   - Return: result.scalar_one_or_none()

2. get_multi(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[{entity_name}]
   - Use: result = await db.execute(select({entity_name}).offset(skip).limit(limit))
   - Return: result.scalars().all()

3. create(db: AsyncSession, obj_in: {entity_name}Create) -> {entity_name}
   - Create instance: db_obj = {entity_name}(**obj_in.model_dump())
   - Add: db.add(db_obj)
   - Commit: await db.commit()
   - Refresh: await db.refresh(db_obj)
   - Return: db_obj

4. update(db: AsyncSession, db_obj: {entity_name}, obj_in: {entity_name}Update) -> {entity_name}
   - Update only provided fields: obj_in.model_dump(exclude_unset=True)
   - Use setattr to update each field
   - Commit and refresh
   - Return updated object

5. delete(db: AsyncSession, id: int) -> Optional[{entity_name}]
   - Get object first
   - If exists: await db.delete(db_obj), await db.commit()
   - Return deleted object or None

6. count(db: AsyncSession) -> int
   - Use: result = await db.execute(select(func.count({entity_name}.id)))
   - Return: result.scalar()

Requirements:
- Import: from sqlalchemy.ext.asyncio import AsyncSession
- Import: from sqlalchemy import select, func
- Import: from typing import Optional, List
- Import: from app.models.{entity_name.lower()} import {entity_name}
- Import: from app.schemas.{entity_name.lower()} import {entity_name}Create, {entity_name}Update
- All methods are class methods or static methods
- Include proper error handling
- Add comprehensive docstrings
- Use type hints

Return ONLY valid JSON."""

        response = await self.provider.generate_completion(
            prompt,
            task=LLMTask.CODE_GENERATION,
            temperature=0.2,
            max_tokens=3072
        )
        
        return self.provider._extract_json(response)
    
    async def _generate_router(
        self,
        entity: Dict[str, Any],
        schema: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate API router for an entity"""
        
        entity_name = entity.get('name', 'Entity')
        entity_lower = entity_name.lower()
        entity_plural = f"{entity_lower}s"
        endpoints = [ep for ep in schema.get('endpoints', []) if ep.get('entity') == entity_name]
        requires_auth = context.get('requires_auth', True)
        
        prompt = f"""Generate FastAPI router for {entity_name}.

ENDPOINTS:
{self._format_endpoints(endpoints) if endpoints else 'Standard CRUD endpoints'}

Generate as JSON:
{{
  "app/routers/{entity_plural}.py": "Complete FastAPI router code"
}}

Create APIRouter with tag="{entity_name}" and these 5 endpoints:

1. @router.get("/{entity_plural}", response_model=List[{entity_name}Response])
   async def list_{entity_plural}(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db))
   - Call repository.get_multi()
   - Return list of {entity_name}

2. @router.get("/{entity_plural}/{{id}}", response_model={entity_name}Response)
   async def get_{entity_lower}(id: int, db: AsyncSession = Depends(get_db))
   - Call repository.get_by_id()
   - Raise HTTPException(404) if not found
   - Return {entity_name}

3. @router.post("/{entity_plural}", response_model={entity_name}Response, status_code=201)
   async def create_{entity_lower}(obj_in: {entity_name}Create, db: AsyncSession = Depends(get_db))
   - Call repository.create()
   - Return created {entity_name}

4. @router.put("/{entity_plural}/{{id}}", response_model={entity_name}Response)
   async def update_{entity_lower}(id: int, obj_in: {entity_name}Update, db: AsyncSession = Depends(get_db))
   - Get existing object
   - Raise 404 if not found
   - Call repository.update()
   - Return updated {entity_name}

5. @router.delete("/{entity_plural}/{{id}}", status_code=204)
   async def delete_{entity_lower}(id: int, db: AsyncSession = Depends(get_db))
   - Call repository.delete()
   - Raise 404 if not found
   - Return None (status 204)

Requirements:
- Import: from fastapi import APIRouter, Depends, HTTPException, status
- Import: from sqlalchemy.ext.asyncio import AsyncSession
- Import: from typing import List
- Import: from app.core.database import get_db
{"- Import: from app.core.security import get_current_user" if requires_auth else ""}
- Import: from app.repositories.{entity_lower}_repository import {entity_name}Repository as repository
- Import: from app.schemas.{entity_lower} import {entity_name}Response, {entity_name}Create, {entity_name}Update
- Create: router = APIRouter(prefix="/{entity_plural}", tags=["{entity_name}"])
{"- Add current_user: User = Depends(get_current_user) to all endpoints" if requires_auth else ""}
- Add summary and description to each endpoint
- Use proper status codes
- Raise HTTPException with detail message
- Use type hints

Return ONLY valid JSON."""

        response = await self.provider.generate_completion(
            prompt,
            task=LLMTask.CODE_GENERATION,
            temperature=0.2,
            max_tokens=4096
        )
        
        return self.provider._extract_json(response)
    
    async def _generate_support_files(
        self,
        schema: Dict[str, Any],
        context: Dict[str, Any],
        entities: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Generate support files (requirements, README, etc.)"""
        
        entity_names = [e.get('name', '') for e in entities]
        tech_stack = context.get('tech_stack', 'fastapi_postgres')
        
        prompt = f"""Generate support files for a FastAPI project.

ENTITIES: {', '.join(entity_names)}
TECH STACK: {tech_stack}

Generate as JSON:
{{
  "requirements.txt": "All dependencies with pinned versions",
  ".env.example": "Example environment variables with comments",
  ".gitignore": "Python/FastAPI gitignore patterns",
  "README.md": "Comprehensive project README with setup instructions",
  "Dockerfile": "Multi-stage Docker build for production"
}}

requirements.txt must include:
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
alembic==1.13.0

.env.example must include:
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname

# Security
SECRET_KEY=your-secret-key-here-use-secrets-token-urlsafe
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# Server
DEBUG=True

.gitignore must include:
__pycache__/
*.py[cod]
*$py.class
.env
.venv/
venv/
*.log
.DS_Store
.pytest_cache/
.coverage
htmlcov/

README.md must include:
# Project Title
Brief description

## Features
- List of main features ({', '.join(entity_names)})

## Tech Stack
- FastAPI, PostgreSQL, SQLAlchemy, etc.

## Setup
1. Clone repo
2. Create virtual environment
3. Install dependencies
4. Set up database
5. Run migrations
6. Start server

## Environment Variables
Description of each variable

## API Endpoints
Brief overview of available endpoints

## Running the Application
```bash
uvicorn main:app --reload
```

Dockerfile must be multi-stage build with:
- Stage 1: Python 3.11 slim, install dependencies
- Stage 2: Copy app, expose port 8000
- CMD: uvicorn main:app --host 0.0.0.0 --port 8000

Return ONLY valid JSON with complete file contents."""

        response = await self.provider.generate_completion(
            prompt,
            task=LLMTask.CODE_GENERATION,
            temperature=0.3,
            max_tokens=4096
        )
        
        return self.provider._extract_json(response)
    
    async def _generate_main_app(
        self,
        entities: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate main application entry point"""
        
        entity_names = [e.get('name', '').lower() + 's' for e in entities]
        
        prompt = f"""Generate main FastAPI application files.

ROUTERS: {', '.join(entity_names)}

Generate as JSON:
{{
  "main.py": "Complete FastAPI application entry point",
  "app/models/__init__.py": "Import all models",
  "app/schemas/__init__.py": "Import all schemas",
  "app/repositories/__init__.py": "Import all repositories",
  "app/routers/__init__.py": "Import and export all routers"
}}

main.py requirements:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.routers import {', '.join([f'{name}_router' for name in entity_names])}

app = FastAPI(
    title="Generated API",
    description="Auto-generated FastAPI application",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
{chr(10).join([f'app.include_router({name}_router, prefix="/api/v1")' for name in entity_names])}

# Health check
@app.get("/")
async def root():
    return {{"message": "API is running", "version": "1.0.0"}}

@app.get("/health")
async def health():
    return {{"status": "healthy"}}

# Database initialization
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
```

app/routers/__init__.py requirements:
{chr(10).join([f'from app.routers.{name} import router as {name}_router' for name in entity_names])}

__all__ = [{', '.join([f'"{name}_router"' for name in entity_names])}]

app/models/__init__.py requirements:
Import all model classes from their respective files

app/schemas/__init__.py requirements:
Import all schema classes from their respective files

app/repositories/__init__.py requirements:
Import all repository classes from their respective files

Return ONLY valid JSON with complete code."""

        response = await self.provider.generate_completion(
            prompt,
            task=LLMTask.CODE_GENERATION,
            temperature=0.2,
            max_tokens=3072
        )
        
        return self.provider._extract_json(response)
    
    # Helper methods for formatting
    def _format_fields(self, fields: List[Dict]) -> str:
        """Format fields for prompt"""
        if not fields:
            return "No specific fields defined"
        
        result = []
        for f in fields:
            field_name = f.get('name', 'field')
            field_type = f.get('type', 'string')
            required = 'required' if f.get('required', False) else 'optional'
            description = f" - {f.get('description')}" if f.get('description') else ''
            result.append(f"- {field_name}: {field_type} ({required}){description}")
        return '\n'.join(result)
    
    def _format_relationships(self, relationships: List[Dict]) -> str:
        """Format relationships for prompt"""
        if not relationships:
            return "None"
        
        result = []
        for r in relationships:
            rel_type = r.get('type', 'one_to_many')
            target = r.get('target', 'Unknown')
            description = f" - {r.get('description')}" if r.get('description') else ''
            result.append(f"- {rel_type} with {target}{description}")
        return '\n'.join(result)
    
    def _format_endpoints(self, endpoints: List[Dict]) -> str:
        """Format endpoints for prompt"""
        if not endpoints:
            return "Standard CRUD endpoints"
        
        return '\n'.join([
            f"- {e.get('method', 'GET')} {e.get('path', '/')}: {e.get('description', 'No description')}"
            for e in endpoints
        ])
    
    def _print_file_tree(self, files: Dict[str, str]) -> None:
        """Print a nice file tree structure"""
        # Group files by directory
        dirs = {}
        for filepath in sorted(files.keys()):
            if '/' in filepath:
                dir_path = '/'.join(filepath.split('/')[:-1])
                filename = filepath.split('/')[-1]
                if dir_path not in dirs:
                    dirs[dir_path] = []
                dirs[dir_path].append(filename)
            else:
                if 'root' not in dirs:
                    dirs['root'] = []
                dirs['root'].append(filepath)
        
        # Print tree
        for dir_path in sorted(dirs.keys()):
            if dir_path != 'root':
                print(f"   📂 {dir_path}/")
                for filename in sorted(dirs[dir_path]):
                    print(f"      📄 {filename}")
            else:
                for filename in sorted(dirs[dir_path]):
                    print(f"   📄 {filename}")
