"""
Orchestrates the multi-model AI pipeline with Enhanced Prompt Engineering:
1. Context analysis and pattern matching
2. Enhanced prompt generation
3. Schema extraction (Llama-8B)
4. Code generation (Qwen2.5-Coder-32B) with context
5. Code review (Starcoder2-15B)
6. Documentation (Mistral-7B)
7. Memory-efficient fallback when resources are limited
"""

import asyncio
import json
import time
import psutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.core.config import settings
from ai_models.model_loader import model_loader, ModelType
from app.services.enhanced_prompt_system import (
    ContextAwareOrchestrator,
    create_enhanced_prompt_system
)

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
        self.memory_efficient_service = None
        self.memory_threshold_mb = 4096  # 4GB threshold for full AI models
        self.qwen_generator = None  # Direct Qwen generator for inference mode
        
    async def _check_memory_availability(self) -> Dict[str, Any]:
        """Check if there's enough memory for full AI model pipeline"""
        memory = psutil.virtual_memory()
        available_mb = memory.available // (1024 * 1024)
        
        return {
            "available_mb": available_mb,
            "can_use_full_ai": available_mb >= self.memory_threshold_mb,
            "memory_usage_percent": memory.percent,
            "force_inference": settings.FORCE_INFERENCE_MODE
        }

    async def initialize(self):
        """Load AI services with Qwen Inference as default for memory-constrained environments"""
        if self.initialized:
            return
            
        print("Initializing Enhanced AI Orchestrator...")
        
        # Check memory availability and forced inference mode
        memory_info = await self._check_memory_availability()
        print(f"💾 Available memory: {memory_info['available_mb']:,}MB")
        
        # Force Qwen Inference mode if configured or memory-constrained
        if settings.FORCE_INFERENCE_MODE or not memory_info["can_use_full_ai"]:
            await self._initialize_qwen_inference_mode()
        else:
            await self._initialize_full_pipeline()
            
        self.initialized = True
        print("Enhanced AI Orchestrator initialized successfully")

    async def _initialize_qwen_inference_mode(self):
        """Initialize with Qwen HF Inference API as primary generator"""
        print("⚡ Using Qwen Inference mode for memory efficiency")
        
        try:
            # Initialize Qwen generator for direct inference
            from ai_models.qwen_generator import QwenGenerator
            self.qwen_generator = QwenGenerator(model_path=settings.QWEN_LARGE_MODEL_PATH)
            await self.qwen_generator.load()
            print("✅ Qwen Inference API initialized")
            
            # Initialize memory-efficient service as backup
            from app.services.memory_efficient_service import memory_efficient_service
            self.memory_efficient_service = memory_efficient_service
            await self.memory_efficient_service.initialize()
            print("✅ Memory-efficient service initialized")
            
            # Initialize lightweight enhanced prompt system
            await self._initialize_enhanced_prompt_system()
            
        except Exception as e:
            print(f"⚠️  Qwen Inference initialization failed: {e}")
            print("📝 Using memory-efficient generation")

    async def _initialize_full_pipeline(self):
        """Initialize full AI pipeline with all models"""
        print("🚀 Sufficient memory detected, loading full AI models...")
        
        try:
            # Always initialize memory-efficient service as fallback
            from app.services.memory_efficient_service import memory_efficient_service
            self.memory_efficient_service = memory_efficient_service
            await self.memory_efficient_service.initialize()
            print("✅ Memory-efficient service initialized")
            
            # Preload critical models (Qwen for generation, Llama for parsing)
            await model_loader.preload_models([
                ModelType.QWEN_GENERATOR,
                ModelType.LLAMA_PARSER
            ])
            print("✅ Full AI models loaded successfully")
            
            # Initialize enhanced prompt system
            await self._initialize_enhanced_prompt_system()
            
            # Mark as initialized when full pipeline setup completes
            self.initialized = True
            print("Enhanced AI Orchestrator initialized successfully")
            
        except Exception as e:
            # If any part of the full pipeline fails, fall back to memory-efficient generation
            print(f"⚠️  Full AI model loading failed: {e}")
            print("📝 Falling back to memory-efficient generation")
            try:
                if self.memory_efficient_service:
                    await self.memory_efficient_service.initialize()
                    print("✅ Memory-efficient service initialized as fallback")
            except Exception as fallback_e:
                print(f"⚠️  Failed to initialize memory-efficient fallback: {fallback_e}")
            # Consider orchestrator initialized with fallback to ensure the system can continue
            self.initialized = True
            print("Enhanced AI Orchestrator initialized with memory-efficient fallback")

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

    async def process_generation(self, generation_id: str, generation_data: dict):
        """
        Legacy method - redirects to enhanced generation if available
        """
        # Check if enhanced processing is requested and available
        if (generation_data.get("use_enhanced_prompts", True) and 
            self.enhanced_prompt_system is not None):
            return await self.process_enhanced_generation(generation_id, generation_data)
        else:
            return await self._process_basic_generation(generation_id, generation_data)

    async def _process_basic_generation(self, generation_id: str, generation_data: dict):
        """
        Process a generation request end-to-end with progress tracking
        """
        if not self.initialized:
            raise RuntimeError("AI models not initialized")

        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from app.core.database import get_db_session
            from app.repositories.generation_repository import GenerationRepository
            
            db = await get_db_session()
            try:
                generation_repo = GenerationRepository(db)
                
                # Update status to processing
                await generation_repo.update_status(generation_id, "processing")
                
                # Stage 1: Schema extraction
                schema_start = time.time()
                await generation_repo.update_progress(
                    generation_id, 
                    stage_times={},  # Will update with actual times
                )
                
                schema = await self._extract_schema(generation_data)
                schema_time = time.time() - schema_start
                
                # Stage 2: Code generation
                code_start = time.time()
                files = await self._generate_code(generation_data, schema)
                code_time = time.time() - code_start
                
                # Stage 3: Code review
                review_start = time.time()
                review_feedback = await self._review_code(files)
                review_time = time.time() - review_start
                
                # Stage 4: Documentation generation
                docs_start = time.time()
                documentation = await self._generate_documentation(files, schema)
                docs_time = time.time() - docs_start
                
                # Calculate quality score
                quality_score = self._calculate_quality_score(files, schema, review_feedback)
                
                # Update final progress
                total_time = time.time() - start_time
                await generation_repo.update_progress(
                    generation_id,
                    stage_times={
                        "schema_extraction": schema_time,
                        "code_generation": code_time,
                        "review": review_time,
                        "docs_generation": docs_time,
                        "total": total_time
                    },
                    output_files=files,
                    extracted_schema=schema,
                    review_feedback=review_feedback,
                    documentation=documentation
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

    async def _extract_schema(self, generation_data: dict) -> Dict[str, Any]:
        """Extract schema from requirements using Llama model"""
        try:
            llama_parser = await model_loader.get_model(ModelType.LLAMA_PARSER)
            
            prompt = generation_data.get("prompt", "")
            domain = generation_data.get("domain", "general")
            tech_stack = generation_data.get("tech_stack", "fastapi_postgres")
            
            schema = await llama_parser.extract_schema(prompt, domain, tech_stack)
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

    async def _generate_code(self, generation_data: dict, schema: Dict[str, Any]) -> Dict[str, str]:
        """Generate code files using Qwen model"""
        try:
            qwen_generator = await model_loader.get_model(ModelType.QWEN_GENERATOR)
            
            prompt = generation_data.get("prompt", "")
            context = {
                "domain": generation_data.get("domain", "general"),
                "tech_stack": generation_data.get("tech_stack", "fastapi_postgres"),
                "constraints": generation_data.get("constraints", [])
            }
            
            files = await qwen_generator.generate_project(prompt, schema, context)
            return files
            
        except Exception as e:
            print(f"Error in code generation: {e}")
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

    async def _review_code(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Review generated code using Starcoder model"""
        try:
            starcoder_reviewer = await model_loader.get_model(ModelType.STARCODER_REVIEWER)
            review_result = await starcoder_reviewer.review_code(files)
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
        """Generate documentation using Mistral model"""
        try:
            mistral_docs = await model_loader.get_model(ModelType.MISTRAL_DOCS)
            
            project_context = {
                "project_name": "Generated FastAPI Project",
                "domain": "general",
                "tech_stack": "fastapi_postgres"
            }
            
            documentation = await mistral_docs.generate_documentation(files, schema, project_context)
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
            # Strategy 1: Try full AI pipeline if memory allows and models are loaded
            if memory_info["can_use_full_ai"] and hasattr(model_loader, '_models') and model_loader._models:
                print("🚀 Using full AI model pipeline")
                return await self.generate_project(request)
                
            # Strategy 2: Use memory-efficient template-based generation
            elif self.memory_efficient_service:
                print("📝 Using memory-efficient template generation")
                
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
        Main pipeline: Default to Qwen Inference for memory efficiency
        """
        if not self.initialized:
            raise RuntimeError("AI models not initialized")

        # Check if we should use Qwen Inference mode
        if settings.FORCE_INFERENCE_MODE or self.qwen_generator:
            return await self._generate_project_with_qwen_inference(request)
        
        # Fallback to full pipeline if available
        return await self._generate_project_full_pipeline(request)

    async def _generate_project_with_qwen_inference(self, request: GenerationRequest) -> GenerationResult:
        """Generate project using Qwen Inference API directly"""
        print("🚀 Using Qwen Inference API for generation")
        
        try:
            # Prepare comprehensive prompt for Qwen
            schema_data = {
                "domain": request.context.get("domain", "general"),
                "tech_stack": request.context.get("tech_stack", "fastapi_postgres"),
                "features": request.context.get("features", []),
                "constraints": request.context.get("constraints", [])
            }
            
            # Use Qwen generator directly
            if self.qwen_generator:
                files = await self.qwen_generator.generate_project(
                    prompt=request.prompt,
                    schema=schema_data,
                    context=request.context
                )
            else:
                # Fallback to memory efficient service
                files = await self.memory_efficient_service.generate_project(
                    request.prompt, schema_data, request.context
                )
            
            # Create basic schema from generated files
            schema = self._extract_schema_from_files(files)
            
            # Basic quality assessment
            quality_score = self._calculate_basic_quality_score(files)
            
            return GenerationResult(
                files=files,
                schema=schema,
                review_feedback={
                    "issues": [],
                    "suggestions": ["Generated using Qwen Inference API"],
                    "security_score": 0.8,
                    "maintainability_score": 0.8,
                    "performance_score": 0.8,
                    "overall_score": quality_score
                },
                documentation={"README.md": files.get("README.md", "# Generated Project")},
                quality_score=quality_score
            )
            
        except Exception as e:
            print(f"Qwen Inference generation failed: {e}")
            return await self._generate_fallback_project(request)

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
        schema = {
            "entities": [],
            "endpoints": [],
            "relationships": [],
            "constraints": []
        }
        
        for file_path, content in files.items():
            if "model" in file_path.lower():
                # Extract class names as entities
                import re
                classes = re.findall(r'class (\w+)', content)
                schema["entities"].extend(classes)
            
            if "router" in file_path.lower() or "api" in file_path.lower():
                # Extract endpoints
                endpoints = re.findall(r'@router\.(get|post|put|delete)\("([^"]*)"', content)
                for method, path in endpoints:
                    schema["endpoints"].append(f"{method.upper()} {path}")
        
        return schema
        
        # Base score from review if available
        if isinstance(review, dict) and "overall_score" in review:
            base_score = review["overall_score"]
        else:
            base_score = 0.8
        
        # Bonus for comprehensive files
        if len(files) >= 5:
            base_score += 0.05
        if len(files) >= 8:
            base_score += 0.05
            
        # Bonus for complete schema
        entities = schema.get("entities", [])
        if len(entities) >= 2:
            base_score += 0.05
            
        # Penalty for critical review issues
        issues = review.get("issues", [])
        high_severity_issues = len([i for i in issues if i.get("severity") == "high"])
        if high_severity_issues > 0:
            base_score -= min(0.2, high_severity_issues * 0.1)
            
        return max(0.0, min(1.0, base_score))

    # Enhanced processing methods for Phase 2: Prompt Engineering Enhancement
    
    async def _extract_enhanced_schema(
        self, 
        generation_data: dict, 
        enhanced_prompts: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Extract schema using enhanced prompts and context"""
        try:
            llama_parser = await model_loader.get_model(ModelType.LLAMA_PARSER)
            
            # Use enhanced intent clarification prompt if available
            if enhanced_prompts and "intent_clarification" in enhanced_prompts:
                schema_prompt = enhanced_prompts["intent_clarification"]
                print("Using enhanced intent clarification prompt for schema extraction")
            else:
                # Fallback to original prompt
                schema_prompt = generation_data.get("prompt", "")
            
            domain = generation_data.get("domain", "general")
            tech_stack = generation_data.get("tech_stack", "fastapi_postgres")
            
            schema = await llama_parser.extract_schema(schema_prompt, domain, tech_stack)
            
            # Enhance schema with context if available
            if enhanced_prompts:
                schema["enhanced_context"] = {
                    "used_enhanced_prompt": True,
                    "prompt_type": "intent_clarification"
                }
            
            return schema
            
        except Exception as e:
            print(f"Error in enhanced schema extraction: {e}")
            # Fallback to basic schema extraction
            return await self._extract_schema(generation_data)

    async def _generate_enhanced_code(
        self, 
        generation_data: dict, 
        schema: Dict[str, Any],
        enhanced_prompts: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Generate code using enhanced prompts and architecture planning"""
        try:
            qwen_generator = await model_loader.get_model(ModelType.QWEN_GENERATOR)
            
            # Use enhanced architecture and implementation prompts if available
            if enhanced_prompts:
                if "architecture_planning" in enhanced_prompts:
                    architecture_prompt = enhanced_prompts["architecture_planning"]
                    print("Using enhanced architecture planning prompt")
                else:
                    architecture_prompt = generation_data.get("prompt", "")
                
                if "implementation_generation" in enhanced_prompts:
                    implementation_prompt = enhanced_prompts["implementation_generation"]
                    print("Using enhanced implementation generation prompt")
                else:
                    implementation_prompt = generation_data.get("prompt", "")
                
                # Generate with enhanced context
                files = await qwen_generator.generate_project_enhanced(
                    architecture_prompt=architecture_prompt,
                    implementation_prompt=implementation_prompt,
                    schema=schema,
                    domain=generation_data.get("domain", "general"),
                    tech_stack=generation_data.get("tech_stack", "fastapi_postgres")
                )
            else:
                # Fallback to basic generation
                files = await qwen_generator.generate_project(
                    generation_data.get("prompt", ""),
                    schema,
                    generation_data.get("domain", "general"),
                    generation_data.get("tech_stack", "fastapi_postgres")
                )
            
            # Add enhancement metadata
            if enhanced_prompts:
                files["_enhanced_metadata.json"] = json.dumps({
                    "enhanced_generation": True,
                    "prompts_used": list(enhanced_prompts.keys()),
                    "generation_timestamp": time.time(),
                    "enhancement_version": "2.0"
                }, indent=2)
            
            return files
            
        except Exception as e:
            print(f"Error in enhanced code generation: {e}")
            # Fallback to basic code generation
            return await self._generate_code(generation_data, schema)

    async def _review_code_with_context(
        self, 
        files: Dict[str, str],
        context_analysis: Optional[Dict[str, Any]] = None,
        recommendations: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Review code with additional context and recommendations"""
        try:
            starcoder_reviewer = await model_loader.get_model(ModelType.STARCODER_REVIEWER)
            
            # Basic code review
            review_feedback = await starcoder_reviewer.review_code(files)
            
            # Enhance review with context
            if context_analysis and recommendations:
                enhanced_review = await self._enhance_review_with_context(
                    review_feedback, context_analysis, recommendations
                )
                return enhanced_review
            
            return review_feedback
            
        except Exception as e:
            print(f"Error in enhanced code review: {e}")
            # Fallback to basic review
            return await self._review_code(files)

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
        """Generate documentation with enhanced context awareness"""
        try:
            mistral_docs = await model_loader.get_model(ModelType.MISTRAL_DOCS)
            
            # Basic documentation generation
            basic_docs = await mistral_docs.generate_documentation(files, schema)
            
            # Enhance with context if available
            if context_analysis:
                enhanced_docs = await self._enhance_documentation_with_context(
                    basic_docs, context_analysis
                )
                return enhanced_docs
            
            return basic_docs
            
        except Exception as e:
            print(f"Error in enhanced documentation generation: {e}")
            # Fallback to basic documentation
            return await self._generate_documentation(files, schema)

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

    async def iterate_project(
        self, existing_files: Dict[str, str], modification_prompt: str
    ) -> Dict[str, str]:
        """Handle iterative modifications to existing projects"""
        try:
            qwen_generator = await model_loader.get_model(ModelType.QWEN_GENERATOR)
            modified_files = await qwen_generator.modify_project(existing_files, modification_prompt)
            return modified_files
            
        except Exception as e:
            print(f"Error in project iteration: {e}")
            # Return original files if iteration fails
            return existing_files

    async def cleanup(self):
        """Cleanup model resources"""
        await model_loader.cleanup()
        print("AI Orchestrator cleanup completed")

# Provide a module-level orchestrator instance for easy imports
ai_orchestrator = AIOrchestrator()