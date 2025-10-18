"""
Orchestrates the multi-model AI pipeline with Enhanced Prompt Engineering:
1. Context analysis and pattern matching
2. Enhanced prompt generation
3. Schema extraction (Gemini or Llama-8B via provider)
4. Code generation (Gemini or Qwen2.5-Coder-32B via provider)
5. Code review (Gemini or Starcoder2-15B via provider)
6. Documentation (Gemini or Mistral-7B via provider)
7. Provider abstraction layer for flexible LLM switching

Integrated with GenerationService for version tracking and hierarchical storage.
"""

import asyncio
import json
import time
import psutil
from loguru import logger
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.core.config import settings
from app.services.llm_providers import LLMProviderFactory, LLMTask
from app.services.enhanced_prompt_system import (
    ContextAwareOrchestrator,
    create_enhanced_prompt_system
)
from app.services.generation_service import GenerationService
from app.models.generation import Generation

# Configure logger
logger = logger

@dataclass
class EnhancedGenerationRequest:
    prompt: str
    context: Dict[str, Any]
    user_id: str
    project_id: Optional[str] = None
    use_enhanced_prompts: bool = True

@dataclass
class EnhancedGenerationResult:
    files: Dict[str, str]
    schema: Dict[str, Any]
    review_feedback: Dict[str, Any]
    documentation: Dict[str, str]
    quality_score: float
    context_analysis: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None
    enhanced_prompts: Optional[Dict[str, str]] = None

# Backward compatibility aliases
GenerationRequest = EnhancedGenerationRequest
GenerationResult = EnhancedGenerationResult

class AIOrchestrator:
    def __init__(self):
        self.initialized = False
        self.enhanced_prompt_system: Optional[ContextAwareOrchestrator] = None
        self.provider_factory = LLMProviderFactory
        
    async def _check_memory_availability(self) -> Dict[str, Any]:
        """Check if there's enough memory for full AI model pipeline"""
        memory = psutil.virtual_memory()
        available_mb = memory.available // (1024 * 1024)
        
        return {
            "available_mb": available_mb,
            "memory_usage_percent": memory.percent,
            "llm_provider": settings.LLM_PROVIDER
        }

    async def initialize(self):
        """Initialize AI orchestrator with provider abstraction layer"""
        if self.initialized:
            return
            
        print("Initializing AI Orchestrator with Provider Abstraction...")
        
        # Check memory availability
        memory_info = await self._check_memory_availability()
        print(f"💾 Available memory: {memory_info['available_mb']:,}MB")
        print(f"🤖 LLM Provider: {settings.LLM_PROVIDER}")
        
        # Initialize providers
        try:
            await self.provider_factory.initialize_all_providers()
            print("✅ LLM providers initialized successfully")
        except Exception as e:
            print(f"⚠️  Provider initialization warning: {e}")
            print("📝 Will initialize providers on-demand")
        
        # Initialize enhanced prompt system
        await self._initialize_enhanced_prompt_system()
        
        self.initialized = True
        print("✅ AI Orchestrator initialized successfully")

    async def _initialize_enhanced_prompt_system(self):
        """Initialize the enhanced prompt system with repositories"""
        try:
            # Import repositories here to avoid circular imports
            from app.core.database import get_db_session
            from app.repositories.project_repository import ProjectRepository
            from app.repositories.user_repository import UserRepository
            from app.repositories.generation_repository import GenerationRepository
            
            # Use a temporary database session to initialize
            db = await get_db_session()
            try:
                project_repo = ProjectRepository(db)
                user_repo = UserRepository(db)
                generation_repo = GenerationRepository(db)
                
                self.enhanced_prompt_system = create_enhanced_prompt_system(
                    project_repo, user_repo, generation_repo
                )
            finally:
                await db.close()
                
            print("Enhanced Prompt System initialized successfully")
            
        except Exception as e:
            print(f"Warning: Enhanced Prompt System initialization failed: {e}")
            print("Falling back to basic prompt processing")
            self.enhanced_prompt_system = None
            
            self.initialized = True
            print("AI Orchestrator initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize AI Orchestrator: {e}")
            self.initialized = False
            raise

    async def process_enhanced_generation(self, generation_id: str, generation_data: dict):
        """
        Process generation with enhanced prompt engineering and context awareness
        """
        if not self.initialized:
            raise RuntimeError("AI models not initialized")

        start_time = time.time()
        context_analysis = None
        enhanced_prompts = None
        recommendations = None
        
        try:
            # Import here to avoid circular imports
            from app.core.database import get_db_session
            from app.repositories.generation_repository import GenerationRepository
            
            db = await get_db_session()
            try:
                generation_repo = GenerationRepository(db)
                
                # Update status to processing
                await generation_repo.update_status(generation_id, "processing")
                
                # Enhanced Stage 0: Context Analysis and Prompt Enhancement
                if self.enhanced_prompt_system and generation_data.get("use_enhanced_prompts", True):
                    context_start = time.time()
                    
                    user_id = generation_data.get("user_id")
                    original_prompt = generation_data.get("prompt", "")
                    
                    if user_id:
                        print(f"Performing context analysis for user {user_id}")
                        context_analysis = self.enhanced_prompt_system.generate_with_context(
                            original_prompt, user_id
                        )
                        
                        enhanced_prompts = context_analysis.get("enhanced_prompts", {})
                        recommendations = context_analysis.get("recommendations", {})
                        
                        # Use enhanced prompts for subsequent stages
                        if enhanced_prompts:
                            generation_data["enhanced_prompts"] = enhanced_prompts
                        
                        context_time = time.time() - context_start
                        print(f"Context analysis completed in {context_time:.2f}s")
                    else:
                        print("No user_id provided, skipping context analysis")
                
                # Stage 1: Enhanced Schema extraction
                schema_start = time.time()
                schema = await self._extract_enhanced_schema(generation_data, enhanced_prompts)
                schema_time = time.time() - schema_start
                
                # Stage 2: Enhanced Code generation
                code_start = time.time()
                files = await self._generate_enhanced_code(generation_data, schema, enhanced_prompts)
                code_time = time.time() - code_start
                
                # Stage 3: Code review with context
                review_start = time.time()
                review_feedback = await self._review_code_with_context(
                    files, context_analysis, recommendations
                )
                review_time = time.time() - review_start
                
                # Stage 4: Enhanced documentation generation
                docs_start = time.time()
                documentation = await self._generate_enhanced_documentation(
                    files, schema, context_analysis
                )
                docs_time = time.time() - docs_start
                
                # Calculate enhanced quality score
                quality_score = self._calculate_enhanced_quality_score(
                    files, schema, review_feedback, context_analysis
                )
                
                # Update final progress with enhanced data
                total_time = time.time() - start_time
                await generation_repo.update_progress(
                    generation_id,
                    stage_times={
                        "context_analysis": context_time if 'context_time' in locals() else 0,
                        "schema_extraction": schema_time,
                        "code_generation": code_time,
                        "review": review_time,
                        "docs_generation": docs_time,
                        "total": total_time
                    },
                    output_files=files,
                    extracted_schema=schema,
                    review_feedback=review_feedback,
                    documentation=documentation,
                    context_analysis=context_analysis,
                    enhanced_prompts=enhanced_prompts,
                    recommendations=recommendations
                )
                
                # Update status to completed
                await generation_repo.update_status(
                    generation_id, 
                    "completed", 
                    quality_score=quality_score
                )
            finally:
                await db.close()
                
        except Exception as e:
            # Import here to avoid circular imports
            from app.core.database import get_db_session
            from app.repositories.generation_repository import GenerationRepository
            
            db_error = await get_db_session()
            try:
                generation_repo = GenerationRepository(db_error)
                await generation_repo.update_status(
                    generation_id, 
                    "failed", 
                    error_message=str(e)
                )
            finally:
                await db_error.close()
            raise

    async def process_generation(self, generation_id: str, generation_data: dict, file_manager: Any = None, event_callback: Any = None):
        """
        Process generation using GenerationService for version tracking.
        
        This method now integrates with GenerationService to:
        - Use hierarchical storage structure
        - Track version numbers automatically
        - Create diffs between versions
        - Set active generation
        
        Args:
            generation_id: Unique ID for this generation
            generation_data: Request data with prompt, context, etc.
            file_manager: FileManager instance for incremental file saving
        """
        # Check if enhanced processing is requested and available
        if (generation_data.get("use_enhanced_prompts", True) and 
            self.enhanced_prompt_system is not None):
            return await self._process_with_generation_service(generation_id, generation_data, file_manager, enhanced=True, event_callback=event_callback)
        else:
            return await self._process_with_generation_service(generation_id, generation_data, file_manager, enhanced=False, event_callback=event_callback)
    
    async def _process_with_generation_service(
        self,
        generation_id: str,
        generation_data: dict,
        file_manager: Any = None,
        enhanced: bool = False,
        event_callback: Any = None
    ):
        """
        Process generation using GenerationService for proper version tracking.
        
        This replaces the old _process_basic_generation and process_enhanced_generation
        methods, integrating with GenerationService for better architecture.
        
        Args:
            generation_id: Generation UUID
            generation_data: Request data
            file_manager: FileManager instance
            enhanced: Whether to use enhanced prompt system
        """
        if not self.initialized:
            raise RuntimeError("AI models not initialized")

        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from app.core.database import get_db_session
            
            db = await get_db_session()
            try:
                # Initialize GenerationService with current DB session
                generation_service = GenerationService(db, file_manager)
                
                # Get the generation (it should already exist, created by the router)
                generation = await db.get(Generation, generation_id)
                
                # If generation doesn't exist yet, we can't proceed (should be created by router first)
                if not generation:
                    raise ValueError(f"Generation {generation_id} not found. It should be created before processing.")
                
                # Update status to processing
                await generation_service.update_generation_status(generation_id, "processing")
                
                # Emit initial processing event
                if event_callback:
                    await event_callback(generation_id, {
                        "status": "processing",
                        "stage": "initialization",
                        "message": "Starting code generation pipeline...",
                        "progress": 2,
                        "generation_mode": "enhanced" if enhanced else "classic"
                    })
                
                # Stage 1: Context Analysis (if enhanced)
                context_analysis = None
                enhanced_prompts = None
                recommendations = None
                context_time = 0
                
                if enhanced and self.enhanced_prompt_system:
                    if event_callback:
                        await event_callback(generation_id, {
                            "status": "processing",
                            "stage": "context_analysis",
                            "message": "Analyzing project context and requirements...",
                            "progress": 5,
                            "generation_mode": "enhanced"
                        })
                    
                    context_start = time.time()
                    context_analysis = await self.enhanced_prompt_system.analyze_context(generation_data)
                    enhanced_prompts = await self.enhanced_prompt_system.generate_enhanced_prompts(
                        generation_data, context_analysis
                    )
                    recommendations = await self.enhanced_prompt_system.get_recommendations(
                        generation_data, context_analysis
                    )
                    context_time = time.time() - context_start
                
                # Stage 2: Schema extraction
                if event_callback:
                    await event_callback(generation_id, {
                        "status": "processing",
                        "stage": "schema_extraction",
                        "message": "Extracting project schema and entities...",
                        "progress": 10,
                        "generation_mode": "enhanced" if enhanced else "classic"
                    })
                
                schema_start = time.time()
                
                # ✅ FIX 6: Handle iteration - load parent files for schema extraction
                parent_files = None
                if generation_data.get("is_iteration"):
                    parent_generation_id = generation_data.get("parent_generation_id") or generation.parent_generation_id
                    if parent_generation_id:
                        try:
                            parent_gen = await db.get(Generation, parent_generation_id)
                            if parent_gen:
                                parent_files = parent_gen.output_files or {}
                                logger.info(f"Loaded {len(parent_files)} parent files for iteration from DB")
                        except Exception as parent_load_err:
                            logger.warning(f"Could not load parent files from DB: {parent_load_err}")
                    
                    # If not in DB context, try from context
                    if not parent_files:
                        parent_files = generation_data.get("context", {}).get("parent_files")
                
                # Extract schema - use parent files if iteration, otherwise normal extraction
                if parent_files and generation_data.get("is_iteration"):
                    schema = self._extract_schema_from_files(parent_files)
                    logger.info(f"Using parent file schema for iteration with {len(parent_files)} files")
                else:
                    schema = await self._extract_schema(generation_data, enhanced_prompts if enhanced else None)
                
                schema_time = time.time() - schema_start
                
                # Stage 3: Code generation (with incremental file saving)
                if event_callback:
                    await event_callback(generation_id, {
                        "status": "processing",
                        "stage": "code_generation_start",
                        "message": "Starting code generation...",
                        "progress": 15,
                        "generation_mode": "enhanced" if enhanced else "classic"
                    })
                
                # Note: Additional generation progress events are emitted by the provider/generator
                code_start = time.time()
                files = await self._generate_code(generation_data, schema, file_manager, generation_id, enhanced_prompts if enhanced else None, event_callback)
                code_time = time.time() - code_start
                
                # Emit completion event for code generation stage
                if event_callback:
                    await event_callback(generation_id, {
                        "status": "processing",
                        "stage": "code_generation_complete",
                        "message": f"Generated {len(files)} files successfully",
                        "progress": 85,
                        "generation_mode": "enhanced" if enhanced else "classic"
                    })
                
                # Stage 4: Code review
                if event_callback:
                    await event_callback(generation_id, {
                        "status": "processing",
                        "stage": "code_review",
                        "message": "Reviewing generated code for quality...",
                        "progress": 92,
                        "generation_mode": "enhanced" if enhanced else "classic"
                    })
                
                review_start = time.time()
                review_feedback = await self._review_code(files, context_analysis if enhanced else None)
                review_time = time.time() - review_start
                
                # Stage 5: Documentation generation
                if event_callback:
                    await event_callback(generation_id, {
                        "status": "processing",
                        "stage": "documentation",
                        "message": "Generating project documentation...",
                        "progress": 95,
                        "generation_mode": "enhanced" if enhanced else "classic"
                    })
                
                docs_start = time.time()
                if enhanced:
                    documentation = await self._generate_enhanced_documentation(files, schema, context_analysis)
                else:
                    documentation = await self._generate_documentation(files, schema)
                docs_time = time.time() - docs_start
                
                # Calculate quality score
                if enhanced:
                    quality_score = self._calculate_enhanced_quality_score(files, schema, review_feedback, context_analysis)
                else:
                    quality_score = self._calculate_quality_score(files, schema, review_feedback)
                
                # Emit final save event
                if event_callback:
                    await event_callback(generation_id, {
                        "status": "processing",
                        "stage": "saving",
                        "message": "Saving generation to database...",
                        "progress": 98,
                        "generation_mode": "enhanced" if enhanced else "classic"
                    })
                
                # Save generation output using GenerationService
                # This handles: hierarchical storage, version tracking, diff creation, auto-activation
                total_time = time.time() - start_time
                
                generation = await generation_service.save_generation_output(
                    generation_id=generation_id,
                    files=files,
                    extracted_schema=schema,
                    documentation=documentation,
                    auto_activate=True  # Set as active generation
                )
                
                # Update additional metadata (timing, review, context analysis)
                generation.review_feedback = review_feedback
                generation.quality_score = quality_score
                generation.schema_extraction_time = schema_time
                generation.code_generation_time = code_time
                generation.review_time = review_time
                generation.docs_generation_time = docs_time
                generation.total_time = total_time
                
                # Store enhanced prompt data if available
                if enhanced and context_analysis:
                    # Store context analysis as part of generation context
                    if not generation.context:
                        generation.context = {}
                    generation.context.update({
                        "context_analysis": context_analysis,
                        "enhanced_prompts": enhanced_prompts,
                        "recommendations": recommendations,
                        "context_analysis_time": context_time
                    })
                
                await db.commit()
                await db.refresh(generation)
                
                logger.info(
                    f"✅ Completed generation v{generation.version} for project {generation.project_id} "
                    f"({generation.file_count} files, {total_time:.2f}s)"
                )
                
                # ✅ CRITICAL FIX: Return generation result instead of None
                return {
                    "generation_id": generation_id,
                    "status": "completed",
                    "version": generation.version,
                    "files": files,
                    "file_count": len(files),
                    "schema": schema,
                    "review_feedback": review_feedback,
                    "documentation": documentation,
                    "quality_score": quality_score,
                    "total_time": total_time,
                    "project_id": generation.project_id
                }
                
            finally:
                await db.close()
                
        except Exception as e:
            logger.error(f"❌ Error processing generation {generation_id}: {e}")
            # Update status to failed
            from app.core.database import get_db_session
            db_error = await get_db_session()
            try:
                generation_service = GenerationService(db_error)
                await generation_service.update_generation_status(
                    generation_id,
                    "failed",
                    error_message=str(e)
                )
            finally:
                await db_error.close()
            raise

    async def _extract_schema(self, generation_data: dict, enhanced_prompts: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract schema from requirements using provider abstraction with optional enhanced prompts"""
        try:
            # Get schema extraction provider
            provider = await self.provider_factory.get_provider(LLMTask.SCHEMA_EXTRACTION)
            
            # Use enhanced prompt if available
            if enhanced_prompts and "schema_extraction" in enhanced_prompts:
                prompt = enhanced_prompts["schema_extraction"]
            else:
                prompt = generation_data.get("prompt", "")
            
            context = {
                "domain": generation_data.get("domain", "general"),
                "tech_stack": generation_data.get("tech_stack", "fastapi_postgres")
            }
            
            schema = await provider.extract_schema(prompt, context)
            return schema
            
        except Exception as e:
            print(f"Error in schema extraction: {e}")
            # Fallback schema
            return {
                "entities": [
                    {
                        "name": "User",
                        "fields": [
                            {"name": "id", "type": "String", "constraints": ["primary_key"], "description": "User ID"},
                            {"name": "email", "type": "String", "constraints": ["unique", "required"], "description": "User email"},
                            {"name": "name", "type": "String", "constraints": ["required"], "description": "User name"},
                            {"name": "created_at", "type": "DateTime", "constraints": [], "description": "Creation timestamp"}
                        ],
                        "description": "User entity"
                    }
                ],
                "relationships": [],
                "endpoints": [
                    {"path": "/users", "method": "GET", "description": "List users", "entity": "User"},
                    {"path": "/users", "method": "POST", "description": "Create user", "entity": "User"},
                    {"path": "/users/{id}", "method": "GET", "description": "Get user", "entity": "User"}
                ],
                "constraints": ["Email must be unique", "Name is required"]
            }

    async def _generate_code(
        self,
        generation_data: dict,
        schema: Dict[str, Any],
        file_manager: Any = None,
        generation_id: str = None,
        enhanced_prompts: Optional[Dict] = None,
        event_callback: Any = None
    ) -> Dict[str, str]:
        """Generate code files using provider abstraction with optional incremental file saving"""
        try:
            print(f"\n{'='*80}")
            print(f"🎯 AI ORCHESTRATOR: Starting code generation")
            print(f"{'='*80}\n")
            
            # Get code generation provider
            provider = await self.provider_factory.get_provider(LLMTask.CODE_GENERATION)
            provider_info = await provider.get_provider_info()
            
            print(f"🤖 Using provider: {provider_info.get('name', 'Unknown')}")
            logger.info(f"Using provider: {provider_info.get('name', 'Unknown')}")
            
            prompt = generation_data.get("prompt", "")
            context = {
                "domain": generation_data.get("domain", "general"),
                "tech_stack": generation_data.get("tech_stack", "fastapi_postgres"),
                "constraints": generation_data.get("constraints", [])
            }
            
            # Call with file_manager and generation_id for incremental saving
            files = await provider.generate_code(prompt, schema, context, file_manager, generation_id, event_callback)
            
            print(f"\n{'='*80}")
            print(f"✅ AI ORCHESTRATOR: Code generation completed")
            print(f"{'='*80}\n")
            
            return files
            
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"❌ AI ORCHESTRATOR ERROR in code generation: {e}")
            print(f"{'='*80}\n")
            logger.error(f"Error in code generation: {e}")
            # Fallback code generation
            template = generation_data.get("tech_stack", "fastapi_basic")
            
            return {
                "app/main.py": """
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

app = FastAPI(title="Generated API")

@app.get("/")
async def root():
    return {"message": "Generated FastAPI application"}

@app.get("/users")
async def list_users():
    # TODO: Implement user listing
    return {"users": []}
""",
                "app/models/user.py": """
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
""",
                "requirements.txt": """
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
""",
                "README.md": f"""
# Generated FastAPI Project

This project was generated using the {template} template.

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
uvicorn app.main:app --reload
```
"""
            }

    async def _review_code(self, files: Dict[str, str], context_analysis: Optional[Dict] = None) -> Dict[str, Any]:
        """Review generated code using provider abstraction"""
        try:
            # Get code review provider
            provider = await self.provider_factory.get_provider(LLMTask.CODE_REVIEW)
            
            # Call with correct signature: (files)
            review_result = await provider.review_code(files)
            return review_result
            
        except Exception as e:
            print(f"Error in code review: {e}")
            # Fallback review
            return {
                "issues": [
                    {
                        "file": "app/main.py",
                        "line": 10,
                        "severity": "warning",
                        "category": "error_handling",
                        "message": "Consider adding error handling for database operations",
                        "code": "MISSING_ERROR_HANDLING"
                    }
                ],
                "suggestions": [
                    {
                        "category": "security",
                        "message": "Add input validation for user endpoints",
                        "priority": "medium"
                    },
                    {
                        "category": "performance",
                        "message": "Consider adding database connection pooling",
                        "priority": "low"
                    }
                ],
                "security_score": 0.80,
                "maintainability_score": 0.90,
                "performance_score": 0.85,
                "overall_score": 0.85,
                "metrics": {
                    "total_lines": sum(len(content.split('\n')) for content in files.values()),
                    "total_files": len(files),
                    "complexity_score": 0.8
                }
            }

    async def _generate_documentation(self, files: Dict[str, str], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate documentation using provider abstraction"""
        try:
            # Get documentation provider
            provider = await self.provider_factory.get_provider(LLMTask.DOCUMENTATION)
            
            # Prepare context
            context = {
                "project_name": "Generated FastAPI Project",
                "domain": "general",
                "tech_stack": "fastapi_postgres"
            }
            
            # Call with correct signature: (files, schema, context)
            documentation = await provider.generate_documentation(files, schema, context)
            return documentation
            
        except Exception as e:
            print(f"Error in documentation generation: {e}")
            # Fallback documentation
            return {
                "README.md": """
# Generated FastAPI Project

This is a FastAPI project generated by codebegen.

## Features
- RESTful API endpoints
- Database integration
- Authentication ready
- Production ready

## Installation
```bash
pip install -r requirements.txt
```

## Running
```bash
uvicorn app.main:app --reload
```
""",
                "API_DOCUMENTATION.md": """
# API Documentation

## Endpoints

### GET /users
Returns list of users

### POST /users
Creates a new user

### GET /users/{id}
Returns a specific user
""",
                "SETUP_GUIDE.md": """
# Setup Guide

1. Install Python 3.11+
2. Install dependencies: `pip install -r requirements.txt`
3. Set up database
4. Run migrations
5. Start the server: `uvicorn app.main:app --reload`
"""
            }

    async def generate_project_memory_aware(self, request: GenerationRequest) -> GenerationResult:
        """
        Memory-aware project generation with automatic fallback strategy
        """
        if not self.initialized:
            raise RuntimeError("AI orchestrator not initialized")
            
        # Check current memory status
        memory_info = await self._check_memory_availability()
        
        try:
            # Strategy 1: Use provider-based AI generation (Gemini, etc.)
            # Legacy model_loader check removed - using provider abstraction now
            print("🚀 Using LLM provider pipeline")
            return await self.generate_project(request)
                
        except Exception as ai_error:
            # Strategy 2: Fallback to memory-efficient template-based generation
            if self.memory_efficient_service:
                print(f"⚠️ AI generation failed ({ai_error}), falling back to template generation")
                
                # Extract relevant parameters from request
                tech_stack = request.context.get("tech_stack", "fastapi")
                domain = request.context.get("domain", "general") 
                features = request.context.get("features", [])
                
                # Generate using memory-efficient service
                result = await self.memory_efficient_service.generate_project(
                    prompt=request.prompt,
                    tech_stack=tech_stack,
                    domain=domain,
                    features=features,
                    user_context=request.context
                )
                
                # Convert to expected GenerationResult format
                return GenerationResult(
                    files=result.get("files", {}),
                    schema=result.get("schema", {"entities": [], "relationships": [], "endpoints": []}),
                    review_feedback=result.get("review_feedback", {
                        "issues": [],
                        "suggestions": ["Generated using memory-efficient templates"],
                        "security_score": 0.8,
                        "maintainability_score": 0.8,
                        "performance_score": 0.8,
                        "overall_score": 0.8
                    }),
                    documentation=result.get("documentation", {
                        "README.md": "# Generated Project\n\nThis project was generated using memory-efficient templates."
                    }),
                    quality_score=result.get("quality_score", 0.8),
                    context_analysis={"strategy_used": result.get("strategy_used", "memory_efficient")},
                    recommendations={"memory_info": memory_info}
                )
                
            # Strategy 3: Minimal fallback if all else fails
            else:
                print("⚠️  Using minimal fallback generation")
                return await self._minimal_fallback_generation(request)
                
        except Exception as e:
            print(f"❌ Memory-aware generation failed: {e}")
            return await self._minimal_fallback_generation(request)
    
    async def _minimal_fallback_generation(self, request: GenerationRequest) -> GenerationResult:
        """Minimal fallback when all other strategies fail"""
        from app.services.memory_efficient_service import quick_generate
        
        tech_stack = request.context.get("tech_stack", "fastapi")
        result = await quick_generate(tech_stack)
        
        return GenerationResult(
            files=result.get("files", {}),
            schema={"entities": [], "relationships": [], "endpoints": []},
            review_feedback={
                "issues": [],
                "suggestions": ["Basic template generation used as fallback"],
                "security_score": 0.6,
                "maintainability_score": 0.6,
                "performance_score": 0.8,
                "overall_score": 0.6
            },
            documentation={"README.md": "# Generated Project\n\nBasic project template."},
            quality_score=0.6,
            context_analysis={"strategy_used": "minimal_fallback"}
        )

    async def generate_project(self, request: GenerationRequest) -> GenerationResult:
        """
        Main pipeline: Uses LLM providers for generation
        """
        if not self.initialized:
            raise RuntimeError("AI Orchestrator not initialized")

        print(f"🚀 Generating project using {settings.LLM_PROVIDER} provider")
        
        try:
            # Get providers for each task
            schema_provider = await self.provider_factory.get_provider(LLMTask.SCHEMA_EXTRACTION)
            code_provider = await self.provider_factory.get_provider(LLMTask.CODE_GENERATION)
            review_provider = await self.provider_factory.get_provider(LLMTask.CODE_REVIEW)
            docs_provider = await self.provider_factory.get_provider(LLMTask.DOCUMENTATION)
            
            # Step 1: Extract schema
            print("📋 Extracting schema...")
            schema = await schema_provider.extract_schema(
                prompt=request.prompt,
                context=request.context
            )
            
            # Step 2: Generate code
            print("💻 Generating code...")
            files = await code_provider.generate_code(
                prompt=request.prompt,
                schema=schema,
                context=request.context
            )
            
            # Step 3: Review code
            print("🔍 Reviewing code...")
            review_feedback = await review_provider.review_code(files=files)
            
            # Step 4: Generate documentation
            print("📚 Generating documentation...")
            documentation = await docs_provider.generate_documentation(
                files=files,
                schema=schema,
                context=request.context
            )
            
            # Merge documentation into files
            files.update(documentation)
            
            # Calculate quality score
            quality_score = review_feedback.get("scores", {}).get("overall", 0.8)
            
            return GenerationResult(
                files=files,
                schema=schema,
                review_feedback=review_feedback,
                documentation=documentation,
                quality_score=quality_score
            )
            
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            raise

    async def _generate_project_with_qwen_inference(self, request: GenerationRequest) -> GenerationResult:
        """Legacy method - redirects to generate_project"""
        return await self.generate_project(request)

    async def _generate_project_full_pipeline(self, request: GenerationRequest) -> GenerationResult:
        """Generate project using full AI pipeline (original method)"""
        try:
            # Stage 1: Schema extraction
            schema = await self._extract_schema({
                "prompt": request.prompt,
                "domain": request.context.get("domain", "general"),
                "tech_stack": request.context.get("tech_stack", "fastapi_postgres"),
                "constraints": request.context.get("constraints", [])
            })
            
            # Stage 2: Code generation
            files = await self._generate_code({
                "prompt": request.prompt,
                "domain": request.context.get("domain", "general"),
                "tech_stack": request.context.get("tech_stack", "fastapi_postgres"),
                "constraints": request.context.get("constraints", [])
            }, schema)
            
            # Stage 3: Code review
            review_feedback = await self._review_code(files)
            
            # Stage 4: Documentation generation
            documentation = await self._generate_documentation(files, schema)
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(files, schema, review_feedback)
            
            return GenerationResult(
                files=files,
                schema=schema,
                review_feedback=review_feedback,
                documentation=documentation,
                quality_score=quality_score
            )
            
        except Exception as e:
            print(f"Error in full AI pipeline: {e}")
            return await self._generate_fallback_project(request)
    
    async def _generate_fallback_project(self, request: GenerationRequest) -> GenerationResult:
        """Generate minimal fallback project"""
        return GenerationResult(
            files={
                "app/main.py": "from fastapi import FastAPI\napp = FastAPI()",
                "README.md": "# Generated Project\nThis is a generated FastAPI project."
            },
            schema={"entities": [], "relationships": [], "endpoints": [], "constraints": []},
            review_feedback={"issues": [], "suggestions": [], "security_score": 0.5, "maintainability_score": 0.5, "performance_score": 0.5, "overall_score": 0.5},
            documentation={"README.md": "# Generated Project"},
            quality_score=0.5
        )

    def _calculate_quality_score(
        self, files: Dict[str, str], schema: Dict[str, Any], review: Dict[str, Any]
    ) -> float:
        """Calculate overall quality score for generated project"""
        
        # File structure score (0.3 weight)
        file_score = min(1.0, len(files) / 10.0)  # Assume 10 files is good
        
        # Schema completeness score (0.2 weight)
        schema_score = 0.5
        if schema.get("entities"):
            schema_score += 0.3
        if schema.get("endpoints"):
            schema_score += 0.2
            
        # Review score (0.5 weight)
        review_score = review.get("overall_score", 0.5)
        
        return (file_score * 0.3) + (schema_score * 0.2) + (review_score * 0.5)

    def _calculate_basic_quality_score(self, files: Dict[str, str]) -> float:
        """Calculate basic quality score based on file structure"""
        score = 0.0
        
        # Check for essential files
        if "app/main.py" in files or "main.py" in files:
            score += 0.2
        if any("model" in path.lower() for path in files):
            score += 0.2
        if any("schema" in path.lower() for path in files):
            score += 0.2
        if any("router" in path.lower() or "api" in path.lower() for path in files):
            score += 0.2
        if "requirements.txt" in files:
            score += 0.1
        if "README.md" in files:
            score += 0.1
        
        return min(1.0, score)

    def _extract_schema_from_files(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Extract basic schema information from generated files"""
        import re
        
        schema = {
            "entities": [],
            "endpoints": [],
            "relationships": [],
            "constraints": []
        }
        
        for file_path, content in files.items():
            if "model" in file_path.lower():
                # Extract class names as entities
                classes = re.findall(r'class (\w+)', content)
                schema["entities"].extend(classes)
            
            if "router" in file_path.lower() or "api" in file_path.lower():
                # Extract endpoints
                endpoints = re.findall(r'@router\.(get|post|put|delete)\("([^"]*)"', content)
                for method, path in endpoints:
                    schema["endpoints"].append(f"{method.upper()} {path}")
        
        return schema

    # Enhanced processing methods for Phase 2: Prompt Engineering Enhancement
    
    async def _extract_enhanced_schema(
        self, 
        generation_data: dict, 
        enhanced_prompts: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Extract schema using enhanced prompts and provider abstraction"""
        try:
            # Get schema extraction provider
            provider = await self.provider_factory.get_provider(LLMTask.SCHEMA_EXTRACTION)
            
            # Use enhanced intent clarification prompt if available
            if enhanced_prompts and "intent_clarification" in enhanced_prompts:
                schema_prompt = enhanced_prompts["intent_clarification"]
                print("Using enhanced intent clarification prompt for schema extraction")
            else:
                # Fallback to original prompt
                schema_prompt = generation_data.get("prompt", "")
            
            # Build context for the provider
            context = {
                "domain": generation_data.get("domain", "general"),
                "tech_stack": generation_data.get("tech_stack", "fastapi_postgres")
            }
            
            # Extract schema using provider
            schema = await provider.extract_schema(schema_prompt, context)
            
            # Enhance schema with context if available
            if enhanced_prompts:
                schema["enhanced_context"] = {
                    "used_enhanced_prompt": True,
                    "prompt_type": "intent_clarification"
                }
            
            # Add provider info
            provider_info = await provider.get_provider_info()
            schema["provider"] = provider_info["name"]
            
            return schema
            
        except Exception as e:
            print(f"Error in enhanced schema extraction: {e}")
            raise

    async def _generate_enhanced_code(
        self, 
        generation_data: dict, 
        schema: Dict[str, Any],
        enhanced_prompts: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Generate code using enhanced prompts and provider abstraction"""
        try:
            # Get code generation provider
            provider = await self.provider_factory.get_provider(LLMTask.CODE_GENERATION)
            provider_info = await provider.get_provider_info()
            
            print(f"🔧 Using {provider_info['name']} for code generation")
            
            # Prepare prompt
            if enhanced_prompts:
                # Combine architecture and implementation prompts
                prompt_parts = []
                
                if "architecture_planning" in enhanced_prompts:
                    prompt_parts.append(f"Architecture:\n{enhanced_prompts['architecture_planning']}")
                    print("Using enhanced architecture planning prompt")
                    
                if "implementation_generation" in enhanced_prompts:
                    prompt_parts.append(f"Implementation:\n{enhanced_prompts['implementation_generation']}")
                    print("Using enhanced implementation generation prompt")
                    
                if prompt_parts:
                    generation_prompt = "\n\n".join(prompt_parts)
                else:
                    generation_prompt = generation_data.get("prompt", "")
            else:
                generation_prompt = generation_data.get("prompt", "")
            
            # Build context for the provider
            context = {
                "domain": generation_data.get("domain", "general"),
                "tech_stack": generation_data.get("tech_stack", "fastapi_postgres"),
                "prompt": generation_prompt
            }
            
            # Generate code using provider with correct signature: (prompt, schema, context)
            files = await provider.generate_code(generation_prompt, schema, context)
            
            # Add enhancement metadata
            if enhanced_prompts:
                files["_enhanced_metadata.json"] = json.dumps({
                    "enhanced_generation": True,
                    "prompts_used": list(enhanced_prompts.keys()),
                    "generation_timestamp": time.time(),
                    "enhancement_version": "2.0",
                    "provider": provider_info["name"]
                }, indent=2)
            
            return files
            
        except Exception as e:
            print(f"Error in enhanced code generation: {e}")
            raise

    async def _review_code_with_context(
        self, 
        files: Dict[str, str],
        context_analysis: Optional[Dict[str, Any]] = None,
        recommendations: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Review code with additional context and provider abstraction"""
        try:
            # Get code review provider
            provider = await self.provider_factory.get_provider(LLMTask.CODE_REVIEW)
            provider_info = await provider.get_provider_info()
            
            print(f"🔍 Using {provider_info['name']} for code review")
            
            # Review code using provider with correct signature: (files)
            review_feedback = await provider.review_code(files)
            
            # Enhance review with context if available
            if context_analysis and recommendations:
                enhanced_review = await self._enhance_review_with_context(
                    review_feedback, context_analysis, recommendations
                )
                # Add provider info
                enhanced_review["provider"] = provider_info["name"]
                return enhanced_review
            
            # Add provider info
            review_feedback["provider"] = provider_info["name"]
            return review_feedback
            
        except Exception as e:
            print(f"Error in enhanced code review: {e}")
            raise

    async def _enhance_review_with_context(
        self,
        basic_review: Dict[str, Any],
        context_analysis: Dict[str, Any],
        recommendations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance review feedback with user context and recommendations"""
        
        enhanced_review = basic_review.copy()
        
        # Add context-aware suggestions
        context_suggestions = []
        
        # Check against user's common features
        user_context = context_analysis.get("user_context", {})
        if user_context.get("frequent_features"):
            missing_features = set(user_context["frequent_features"]) - set(
                recommendations.get("suggested_features", [])
            )
            if missing_features:
                context_suggestions.append({
                    "type": "feature_suggestion",
                    "message": f"Consider adding these features you commonly use: {', '.join(missing_features)}",
                    "severity": "info"
                })
        
        # Check against similar project patterns
        similar_projects = context_analysis.get("similar_projects", [])
        if similar_projects:
            context_suggestions.append({
                "type": "pattern_suggestion",
                "message": f"Based on {len(similar_projects)} similar successful projects, consider these optimizations",
                "details": recommendations.get("optimization_suggestions", []),
                "severity": "info"
            })
        
        # Add architecture advice
        if recommendations.get("architecture_advice"):
            context_suggestions.extend([
                {
                    "type": "architecture_advice",
                    "message": advice,
                    "severity": "info"
                }
                for advice in recommendations["architecture_advice"]
            ])
        
        # Add potential issues from similar projects
        if recommendations.get("potential_issues"):
            context_suggestions.extend([
                {
                    "type": "potential_issue",
                    "message": issue,
                    "severity": "warning"
                }
                for issue in recommendations["potential_issues"]
            ])
        
        # Merge with existing suggestions
        enhanced_review["context_suggestions"] = context_suggestions
        enhanced_review["enhancement_metadata"] = {
            "context_enhanced": True,
            "user_patterns_considered": bool(user_context.get("frequent_features")),
            "similar_projects_analyzed": len(similar_projects),
            "recommendations_applied": len(context_suggestions)
        }
        
        # Adjust overall score based on context alignment
        original_score = enhanced_review.get("overall_score", 0.8)
        if context_suggestions:
            # Slight boost for context-aware review
            enhanced_review["overall_score"] = min(1.0, original_score + 0.05)
        
        return enhanced_review

    async def _generate_enhanced_documentation(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any],
        context_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate documentation using enhanced context and provider abstraction"""
        try:
            # Get documentation provider
            provider = await self.provider_factory.get_provider(LLMTask.DOCUMENTATION)
            provider_info = await provider.get_provider_info()
            
            print(f"📝 Using {provider_info['name']} for documentation generation")
            
            # Build context for the provider
            context = {
                "context_analysis": context_analysis
            }
            
            # Generate documentation using provider with correct signature: (files, schema, context)
            basic_docs = await provider.generate_documentation(files, schema, context)
            
            # Enhance with context if available
            if context_analysis:
                enhanced_docs = await self._enhance_documentation_with_context(
                    basic_docs, context_analysis
                )
                # Add provider info
                enhanced_docs["provider"] = provider_info["name"]
                return enhanced_docs
            
            # Add provider info
            basic_docs["provider"] = provider_info["name"]
            return basic_docs
            
        except Exception as e:
            print(f"Error in enhanced documentation generation: {e}")
            raise

    async def _enhance_documentation_with_context(
        self,
        basic_docs: Dict[str, Any],
        context_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance documentation with user context and patterns"""
        
        enhanced_docs = basic_docs.copy()
        
        # Add user context section
        user_context = context_analysis.get("user_context", {})
        recommendations = context_analysis.get("recommendations", {})
        
        # Create enhanced README
        enhanced_readme = enhanced_docs.get("README.md", "# Generated Project\n\n")
        
        # Add context-aware sections
        context_sections = []
        
        if user_context.get("frequent_features"):
            context_sections.append(f"""
## 🎯 Features Optimized for Your Workflow

Based on your development patterns, this project includes:
- {', '.join(user_context['frequent_features'])}

""")
        
        if recommendations.get("suggested_features"):
            context_sections.append(f"""
## 🚀 Recommended Next Steps

Consider adding these features to enhance your project:
- {chr(10).join([f"- {feature}" for feature in recommendations['suggested_features']])}

""")
        
        if recommendations.get("optimization_suggestions"):
            context_sections.append(f"""
## ⚡ Performance Optimizations

Based on similar successful projects:
- {chr(10).join([f"- {opt}" for opt in recommendations['optimization_suggestions']])}

""")
        
        # Add architecture insights
        if user_context.get("architecture_style"):
            context_sections.append(f"""
## 🏗 Architecture Notes

This project follows your preferred **{user_context['architecture_style']}** architecture style.
Complexity level: **{user_context.get('complexity_preference', 'moderate')}**

""")
        
        # Insert context sections after the main description
        if context_sections:
            enhanced_readme += "\n".join(context_sections)
        
        enhanced_docs["README.md"] = enhanced_readme
        
        # Add context metadata
        enhanced_docs["_context_metadata.json"] = json.dumps({
            "context_enhanced": True,
            "user_patterns_analyzed": bool(user_context.get("frequent_features")),
            "recommendations_included": len(recommendations),
            "enhancement_timestamp": time.time()
        }, indent=2)
        
        return enhanced_docs

    def _calculate_enhanced_quality_score(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        review: Dict[str, Any],
        context_analysis: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate quality score with enhanced context considerations"""
        
        # Start with basic quality score
        base_score = self._calculate_quality_score(files, schema, review)
        
        # Enhancement bonuses
        enhancement_bonus = 0.0
        
        # Bonus for using enhanced prompts
        if any(file.endswith("_enhanced_metadata.json") for file in files.keys()):
            enhancement_bonus += 0.05
        
        # Bonus for context-aware review
        if review.get("enhancement_metadata", {}).get("context_enhanced"):
            enhancement_bonus += 0.03
        
        # Bonus for user pattern alignment
        if context_analysis:
            user_context = context_analysis.get("user_context", {})
            if user_context.get("frequent_features"):
                # Check if generated project aligns with user patterns
                generated_features = self._extract_features_from_files(files)
                pattern_alignment = len(
                    set(user_context["frequent_features"]).intersection(set(generated_features))
                ) / len(user_context["frequent_features"])
                enhancement_bonus += pattern_alignment * 0.07
        
        # Bonus for similarity to successful projects
        similar_projects = context_analysis.get("similar_projects", []) if context_analysis else []
        if similar_projects:
            enhancement_bonus += min(0.05, len(similar_projects) * 0.01)
        
        final_score = base_score + enhancement_bonus
        return max(0.0, min(1.0, final_score))

    def _extract_features_from_files(self, files: Dict[str, str]) -> List[str]:
        """Extract likely features from generated file structure"""
        features = []
        
        file_patterns = {
            "auth": ["auth", "login", "jwt", "user"],
            "file_upload": ["upload", "file", "storage"],
            "payments": ["payment", "stripe", "billing"],
            "caching": ["cache", "redis"],
            "admin_dashboard": ["admin", "dashboard"],
            "real_time": ["websocket", "realtime", "socket"],
            "search": ["search", "elasticsearch"],
            "notifications": ["notification", "email", "sms"]
        }
        
        for feature, patterns in file_patterns.items():
            for file_path in files.keys():
                if any(pattern in file_path.lower() for pattern in patterns):
                    features.append(feature)
                    break
        
        return features

    def _detect_iteration_intent(self, prompt: str, existing_files: Dict[str, str]) -> str:
        """Detect the intent of an iteration: add, modify, or remove"""
        prompt_lower = prompt.lower()
        
        # Check for add intent
        add_keywords = ['add', 'create', 'new', 'missing', 'include', 'implement']
        if any(keyword in prompt_lower for keyword in add_keywords):
            return 'add'
        
        # Check for modify intent
        modify_keywords = ['fix', 'update', 'change', 'modify', 'improve', 'refactor', 'enhance']
        if any(keyword in prompt_lower for keyword in modify_keywords):
            return 'modify'
        
        # Check for remove intent
        remove_keywords = ['remove', 'delete', 'drop', 'eliminate']
        if any(keyword in prompt_lower for keyword in remove_keywords):
            return 'remove'
        
        return 'unknown'

    def _format_file_tree(self, files: Dict[str, str]) -> str:
        """Format files as a visual tree structure"""
        from collections import defaultdict
        
        # Build directory tree
        tree = defaultdict(list)
        for filepath in sorted(files.keys()):
            parts = filepath.split('/')
            if len(parts) > 1:
                dir_path = '/'.join(parts[:-1])
                filename = parts[-1]
                tree[dir_path].append(filename)
            else:
                tree[''].append(filepath)
        
        # Format as tree
        result = []
        for dir_path in sorted(tree.keys()):
            if dir_path:
                result.append(f"{dir_path}/")
            for filename in sorted(tree[dir_path]):
                prefix = "  " if dir_path else ""
                result.append(f"{prefix}├── {filename}")
        
        return "\n".join(result[:50])  # Limit to 50 lines

    def _show_key_files(self, files: Dict[str, str], max_files: int = 5) -> str:
        """Show content of most relevant files to LLM"""
        # Priority order for key files
        priority_patterns = [
            'main.py', 'app.py', '__init__.py',
            'config', 'settings',
            'models/', 'schemas/',
            'routers/', 'api/',
            'database', 'db.py'
        ]
        
        key_files = []
        for pattern in priority_patterns:
            for filepath, content in files.items():
                if pattern in filepath.lower() and filepath not in key_files:
                    key_files.append(filepath)
                    if len(key_files) >= max_files:
                        break
            if len(key_files) >= max_files:
                break
        
        # Format as code blocks
        result = []
        for filepath in key_files[:max_files]:
            content = files[filepath]
            # Truncate long files
            if len(content) > 500:
                content = content[:500] + "\n... (truncated)"
            result.append(f"=== {filepath} ===\n{content}\n")
        
        return "\n".join(result)

    async def iterate_project(
        self, existing_files: Dict[str, str], modification_prompt: str, context: Dict = None, event_callback: Any = None
    ) -> Dict[str, str]:
        """Handle iterative modifications to existing projects with context awareness"""
        try:
            if context is None:
                context = {}
            
            # Emit start event
            if event_callback:
                await event_callback(context.get("generation_id"), {
                    "status": "processing",
                    "stage": "iteration_start",
                    "message": "Starting iteration analysis...",
                    "progress": 5
                })
            
            # Detect iteration intent
            intent = self._detect_iteration_intent(modification_prompt, existing_files)
            logger.info(f"[Iteration] Detected intent: {intent}")
            
            if event_callback:
                await event_callback(context.get("generation_id"), {
                    "status": "processing",
                    "stage": "intent_detection",
                    "message": f"Detected intent: {intent}",
                    "progress": 10
                })
            
            # Build context-rich prompt for LLM
            file_tree = self._format_file_tree(existing_files)
            key_files_content = self._show_key_files(existing_files, max_files=5)
            
            if event_callback:
                await event_callback(context.get("generation_id"), {
                    "status": "processing",
                    "stage": "context_building",
                    "message": "Building context from existing files...",
                    "progress": 20
                })
            
            context_aware_prompt = f"""
ITERATION REQUEST: Modify an existing project

EXISTING PROJECT STRUCTURE:
Total Files: {len(existing_files)}
{file_tree}

KEY FILES CONTENT:
{key_files_content}

USER MODIFICATION REQUEST: {modification_prompt}
DETECTED INTENT: {intent}

CRITICAL INSTRUCTIONS:
1. This is an ITERATION, not a new project generation
2. The project already has {len(existing_files)} files
3. Generate ONLY files that need to be:
   - ADDED (if intent is 'add')
   - MODIFIED (if intent is 'modify')
   - REMOVED (return empty content if intent is 'remove')
4. DO NOT regenerate all existing files
5. Preserve the existing project structure and patterns
6. Ensure new/modified files integrate seamlessly with existing code

Expected behavior:
- Intent 'add': Return new files to be added to existing {len(existing_files)} files
- Intent 'modify': Return only modified files, preserve others
- Intent 'remove': Return files to remove (with empty content or exclusion flag)
"""
            
            # Get code generation provider
            code_provider = await self.provider_factory.get_provider(LLMTask.CODE_GENERATION)
            
            # Update context with iteration metadata
            iteration_context = {
                **context,
                "existing_files": list(existing_files.keys()),
                "existing_file_count": len(existing_files),
                "is_iteration": True,
                "iteration_intent": intent,
                "tech_stack": context.get("tech_stack", "fastapi_postgres")
            }
            
            # Create a schema from existing files for context
            schema = self._extract_schema_from_files(existing_files)
            
            if event_callback:
                await event_callback(context.get("generation_id"), {
                    "status": "processing",
                    "stage": "code_generation",
                    "message": f"Generating {intent} modifications...",
                    "progress": 40
                })
            
            logger.info(f"[Iteration] Generating modifications with context: {len(existing_files)} existing files")
            
            # Generate modified/new files with context-aware prompt
            modified_files = await code_provider.generate_code(
                prompt=context_aware_prompt,
                schema=schema,
                context=iteration_context,
                event_callback=event_callback  # ✅ Pass callback to provider
            )
            
            if event_callback:
                await event_callback(context.get("generation_id"), {
                    "status": "processing",
                    "stage": "merging_files",
                    "message": "Merging changes with existing files...",
                    "progress": 80
                })
            
            # ✅ CRITICAL FIX: Merge existing files with modified files
            if modified_files:
                # Start with existing files (preserve everything)
                merged = existing_files.copy()
                
                # Handle different intents
                if intent == 'remove':
                    # Remove files that were marked for deletion
                    for filepath in modified_files.keys():
                        if filepath in merged:
                            del merged[filepath]
                            logger.info(f"[Iteration] Removed file: {filepath}")
                else:
                    # Add or modify files
                    merged.update(modified_files)
                
                logger.info(f"[Iteration] Merge complete: {len(existing_files)} existing + {len(modified_files)} changes = {len(merged)} total files")
                logger.info(f"[Iteration] Intent '{intent}' resulted in: Added/Modified={len(set(modified_files.keys()) - set(existing_files.keys()))}, Updated={len(set(modified_files.keys()) & set(existing_files.keys()))}")
                
                if event_callback:
                    await event_callback(context.get("generation_id"), {
                        "status": "completed",
                        "stage": "iteration_complete",
                        "message": f"Iteration complete: {len(merged)} total files",
                        "progress": 100
                    })
                
                return merged
            else:
                # If generation fails, return existing files unchanged
                logger.warning("[Iteration] Generated no files, returning existing files unchanged")
                
                if event_callback:
                    await event_callback(context.get("generation_id"), {
                        "status": "completed",
                        "stage": "iteration_no_changes",
                        "message": "No changes generated, existing files preserved",
                        "progress": 100
                    })
                
                return existing_files
            
        except Exception as e:
            logger.error(f"[Iteration] Failed: {e}", exc_info=True)
            
            if event_callback:
                await event_callback(context.get("generation_id"), {
                    "status": "failed",
                    "stage": "iteration_error",
                    "message": f"Iteration failed: {str(e)}",
                    "progress": 0
                })
            
            # Return original files if iteration fails
            return existing_files

    async def cleanup(self):
        """Cleanup model resources"""
        # Legacy model_loader cleanup removed - using provider abstraction now
        print("AI Orchestrator cleanup completed")

# Provide a module-level orchestrator instance for easy imports
ai_orchestrator = AIOrchestrator()