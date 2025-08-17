# codebegen Backend Structure - Complete Implementation Guide

## 📁 Project Overview

This document outlines the complete backend structure for **codebegen: AI-Powered FastAPI Backend Generator**. The architecture supports a multi-model AI pipeline for transforming natural language prompts into production-ready FastAPI projects.

---

## 🏗️ Architecture Overview

```
codebegen/
├── app/                    # Main application code
├── infra/                  # Infrastructure & deployment
├── docs/                   # Documentation & API specs
├── tests/                  # Test suite
├── ai_models/              # AI model management
├── templates/              # Code generation templates
├── scripts/                # Utility scripts
└── requirements/           # Dependencies
```

---

## 📂 Complete File Structure

```
codebegen/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── database.py
│   │   └── exceptions.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── handlers.py
│   │   └── models.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── generation.py
│   │   └── organization.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── generation.py
│   │   └── ai.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── projects.py
│   │   ├── generations.py
│   │   ├── ai.py
│   │   └── webhooks.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_orchestrator.py
│   │   ├── schema_parser.py
│   │   ├── code_generator.py
│   │   ├── code_reviewer.py
│   │   ├── docs_generator.py
│   │   ├── github_service.py
│   │   └── billing_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user_repository.py
│   │   ├── project_repository.py
│   │   └── generation_repository.py
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py
│       ├── validators.py
│       └── formatters.py
├── ai_models/
│   ├── __init__.py
│   ├── model_loader.py
│   ├── qwen_generator.py
│   ├── llama_parser.py
│   ├── starcoder_reviewer.py
│   └── mistral_docs.py
├── templates/
│   ├── fastapi_basic/
│   │   ├── template.yaml
│   │   └── files/
│   ├── fastapi_sqlalchemy/
│   │   ├── template.yaml
│   │   └── files/
│   └── fastapi_mongo/
│       ├── template.yaml
│       └── files/
├── infra/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── .env.example
│   └── nginx.conf
├── docs/
│   ├── README.md
│   ├── openapi.yaml
│   ├── architecture.md
│   └── deployment.md
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth/
│   ├── test_services/
│   ├── test_ai/
│   └── test_integration/
├── scripts/
│   ├── setup.py
│   ├── migrate.py
│   └── seed_data.py
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── pyproject.toml
└── .gitignore
```

---

## 📄 File Implementation Details

### **app/main.py** - FastAPI Application Entry Point
```python
"""
Main FastAPI application with middleware, routers, and startup/shutdown events.
Configures CORS, authentication, rate limiting, and model loading.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.routers import auth, projects, generations, ai, webhooks
from app.services.ai_orchestrator import AIOrchestrator

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="codebegen API",
    description="AI-Powered FastAPI Backend Generator",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Exception handlers
setup_exception_handlers(app)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(generations.router, prefix="/generations", tags=["Generations"])
app.include_router(ai.router, prefix="/ai", tags=["AI Services"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

@app.on_event("startup")
async def startup_event():
    """Load AI models and initialize services"""
    app.state.ai_orchestrator = AIOrchestrator()
    await app.state.ai_orchestrator.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources"""
    if hasattr(app.state, 'ai_orchestrator'):
        await app.state.ai_orchestrator.cleanup()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "codebegen-api"}
```

### **app/core/config.py** - Application Configuration
```python
"""
Centralized configuration management using Pydantic settings.
Handles environment variables, database URLs, AI model configs, etc.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    # App
    APP_NAME: str = "codebegen"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # AI Models
    QWEN_MODEL_PATH: str = "Qwen/Qwen2.5-Coder-32B"
    LLAMA_MODEL_PATH: str = "meta-llama/Llama-3.1-8B"
    STARCODER_MODEL_PATH: str = "bigcode/starcoder2-15b"
    MISTRAL_MODEL_PATH: str = "mistralai/Mistral-7B-Instruct-v0.1"
    
    # External Services
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    STRIPE_SECRET_KEY: Optional[str] = None
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # File Storage
    STORAGE_BACKEND: str = "local"  # local, s3
    LOCAL_STORAGE_PATH: str = "./storage"
    S3_BUCKET: Optional[str] = None
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
```

### **app/services/ai_orchestrator.py** - Main AI Pipeline Coordinator
```python
"""
Orchestrates the multi-model AI pipeline:
1. Schema extraction (Llama-8B)
2. Code generation (Qwen2.5-Coder-32B)
3. Code review (Starcoder2-15B)
4. Documentation (Mistral-7B)
"""

import asyncio
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

from app.core.config import settings
from ai_models.qwen_generator import QwenGenerator
from ai_models.llama_parser import LlamaParser
from ai_models.starcoder_reviewer import StarcoderReviewer
from ai_models.mistral_docs import MistralDocsGenerator

@dataclass
class GenerationRequest:
    prompt: str
    context: Dict[str, Any]
    user_id: str
    project_id: Optional[str] = None

@dataclass
class GenerationResult:
    files: Dict[str, str]
    schema: Dict[str, Any]
    review_feedback: Dict[str, Any]
    documentation: Dict[str, str]
    quality_score: float

class AIOrchestrator:
    def __init__(self):
        self.schema_parser: Optional[LlamaParser] = None
        self.code_generator: Optional[QwenGenerator] = None
        self.code_reviewer: Optional[StarcoderReviewer] = None
        self.docs_generator: Optional[MistralDocsGenerator] = None
        self.initialized = False

    async def initialize(self):
        """Load all AI models"""
        if self.initialized:
            return
            
        # Load models in parallel for faster startup
        await asyncio.gather(
            self._load_schema_parser(),
            self._load_code_generator(),
            self._load_code_reviewer(),
            self._load_docs_generator()
        )
        self.initialized = True

    async def _load_schema_parser(self):
        self.schema_parser = LlamaParser(settings.LLAMA_MODEL_PATH)
        await self.schema_parser.load()

    async def _load_code_generator(self):
        self.code_generator = QwenGenerator(settings.QWEN_MODEL_PATH)
        await self.code_generator.load()

    async def _load_code_reviewer(self):
        self.code_reviewer = StarcoderReviewer(settings.STARCODER_MODEL_PATH)
        await self.code_reviewer.load()

    async def _load_docs_generator(self):
        self.docs_generator = MistralDocsGenerator(settings.MISTRAL_MODEL_PATH)
        await self.docs_generator.load()

    async def generate_project(self, request: GenerationRequest) -> GenerationResult:
        """
        Main pipeline: prompt → schema → code → review → docs
        """
        if not self.initialized:
            raise RuntimeError("AI models not initialized")

        # Step 1: Extract schema from natural language
        schema = await self.schema_parser.extract_schema(
            request.prompt, request.context
        )

        # Step 2: Generate code using Qwen
        files = await self.code_generator.generate_project(
            request.prompt, schema, request.context
        )

        # Step 3: Review code for quality/security
        review_feedback = await self.code_reviewer.review_code(files)

        # Step 4: Apply review suggestions
        if review_feedback.get("suggestions"):
            files = await self.code_generator.apply_suggestions(
                files, review_feedback["suggestions"]
            )

        # Step 5: Generate documentation
        documentation = await self.docs_generator.generate_docs(
            files, schema, request.context
        )

        # Calculate quality score
        quality_score = self._calculate_quality_score(
            files, schema, review_feedback
        )

        return GenerationResult(
            files=files,
            schema=schema,
            review_feedback=review_feedback,
            documentation=documentation,
            quality_score=quality_score
        )

    def _calculate_quality_score(
        self, files: Dict[str, str], schema: Dict[str, Any], review: Dict[str, Any]
    ) -> float:
        """Calculate overall quality score for generated project"""
        base_score = 0.8
        
        # Bonus for comprehensive files
        if len(files) >= 10:
            base_score += 0.1
            
        # Penalty for review issues
        issues = review.get("issues", [])
        if issues:
            base_score -= min(0.3, len(issues) * 0.05)
            
        return max(0.0, min(1.0, base_score))

    async def iterate_project(
        self, existing_files: Dict[str, str], modification_prompt: str
    ) -> Dict[str, str]:
        """Handle iterative modifications to existing projects"""
        return await self.code_generator.modify_project(
            existing_files, modification_prompt
        )

    async def cleanup(self):
        """Cleanup model resources"""
        cleanup_tasks = []
        
        if self.schema_parser:
            cleanup_tasks.append(self.schema_parser.cleanup())
        if self.code_generator:
            cleanup_tasks.append(self.code_generator.cleanup())
        if self.code_reviewer:
            cleanup_tasks.append(self.code_reviewer.cleanup())
        if self.docs_generator:
            cleanup_tasks.append(self.docs_generator.cleanup())
            
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
```

### **app/routers/ai.py** - AI Generation Endpoints
```python
"""
API endpoints for AI-powered code generation.
Handles project generation, iteration, and status tracking.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import json
import asyncio

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.schemas.ai import (
    GenerationRequest,
    GenerationResponse,
    IterationRequest,
    StreamingGenerationEvent
)
from app.schemas.user import User
from app.services.ai_orchestrator import AIOrchestrator
from app.repositories.generation_repository import GenerationRepository

router = APIRouter()

@router.post("/generate", response_model=GenerationResponse)
async def generate_project(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Generate a new FastAPI project from natural language prompt"""
    
    # Create generation record
    gen_repo = GenerationRepository(db)
    generation = await gen_repo.create(
        user_id=current_user.id,
        prompt=request.prompt,
        context=request.context,
        status="processing"
    )
    
    # Start generation in background
    background_tasks.add_task(
        _process_generation,
        generation.id,
        request,
        current_user.id
    )
    
    return GenerationResponse(
        generation_id=generation.id,
        status="processing",
        message="Project generation started"
    )

@router.get("/generate/{generation_id}/stream")
async def stream_generation_progress(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stream real-time generation progress"""
    
    async def event_stream():
        # Stream events from Redis or in-memory queue
        while True:
            # Get progress update from queue/cache
            event = await _get_generation_event(generation_id)
            if event:
                yield f"data: {json.dumps(event.dict())}\n\n"
                if event.status in ["completed", "failed"]:
                    break
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/iterate", response_model=GenerationResponse)
async def iterate_project(
    request: IterationRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Modify an existing generated project"""
    
    # Get original generation
    gen_repo = GenerationRepository(db)
    original = await gen_repo.get_by_id(request.original_generation_id)
    
    if not original or original.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    # Apply modifications
    orchestrator = AIOrchestrator()
    modified_files = await orchestrator.iterate_project(
        existing_files=original.output_files,
        modification_prompt=request.modification_prompt
    )
    
    # Create new generation record
    new_generation = await gen_repo.create(
        user_id=current_user.id,
        prompt=request.modification_prompt,
        context={"iteration_of": request.original_generation_id},
        status="completed",
        output_files=modified_files
    )
    
    return GenerationResponse(
        generation_id=new_generation.id,
        status="completed",
        files=modified_files
    )

async def _process_generation(
    generation_id: str,
    request: GenerationRequest,
    user_id: str
):
    """Background task to process AI generation"""
    try:
        orchestrator = AIOrchestrator()
        
        # Update status to "schema_extraction"
        await _update_generation_status(generation_id, "schema_extraction")
        
        result = await orchestrator.generate_project(
            request
        )
        
        # Save completed generation
        await _save_generation_result(generation_id, result)
        
    except Exception as e:
        await _update_generation_status(generation_id, "failed", str(e))

async def _update_generation_status(
    generation_id: str, 
    status: str, 
    error: str = None
):
    """Update generation status in database and notify via events"""
    # Implementation for status updates
    pass

async def _get_generation_event(generation_id: str) -> StreamingGenerationEvent:
    """Get latest generation event from queue/cache"""
    # Implementation for event streaming
    pass

async def _save_generation_result(generation_id: str, result):
    """Save final generation result to database"""
    # Implementation for saving results
    pass
```

### **app/schemas/ai.py** - AI Service Schemas
```python
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
    schema: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None

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
```

### **ai_models/qwen_generator.py** - Qwen Code Generator
```python
"""
Qwen2.5-Coder-32B model wrapper for FastAPI code generation.
Handles LoRA loading, prompt formatting, and project generation.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

from app.core.config import settings

class QwenGenerator:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[AutoModelForCausalLM] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    async def load(self):
        """Load Qwen model with LoRA adapter"""
        # Load in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model)

    def _load_model(self):
        """Synchronous model loading"""
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, 
            trust_remote_code=True
        )
        
        # Load base model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            device_map="auto",
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            trust_remote_code=True
        )
        
        # Load LoRA adapter if exists
        lora_path = "./models/qwen_fastapi_lora"
        try:
            self.model = PeftModel.from_pretrained(self.model, lora_path)
            print(f"Loaded LoRA adapter from {lora_path}")
        except:
            print("No LoRA adapter found, using base model")

    async def generate_project(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate complete FastAPI project from prompt and schema"""
        
        formatted_prompt = self._format_generation_prompt(prompt, schema, context)
        
        # Generate in thread pool
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._generate, formatted_prompt)
        
        # Parse output to extract files
        files = self._parse_generated_output(output)
        return files

    def _format_generation_prompt(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Format prompt for Qwen model"""
        
        system_prompt = """You are Codebegen, an AI backend engineer that builds production-ready FastAPI backends from natural language requests.

You must:
- Follow PEP8 and use `black` formatting.
- Use the requested tech stack exactly.
- Generate ALL required files for a working project.
- Include Dockerfile and docker-compose.yml when requested.
- Ensure code runs without syntax errors.
- Never invent package names.
- Always separate concerns into models, schemas, routers, services, and repositories.
- Include basic tests and README.md.

Your output must be in JSON with keys: files (dict of file paths → contents)."""

        user_prompt = f"""### API Description:
{prompt}

### Extracted Schema:
{json.dumps(schema, indent=2)}

### Technical Context:
Domain: {context.get('domain', 'general')}
Tech Stack: {context.get('tech_stack', 'fastapi_postgres')}
Constraints: {', '.join(context.get('constraints', []))}

### Output Format:
Return JSON with:
{{
  "files": {{ "path/to/file.py": "<full code>", ... }}
}}"""

        return f"{system_prompt}\n\n{user_prompt}"

    def _generate(self, prompt: str) -> str:
        """Synchronous generation"""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=8192,
                temperature=0.1,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        generated = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], 
            skip_special_tokens=True
        )
        
        return generated

    def _parse_generated_output(self, output: str) -> Dict[str, str]:
        """Parse model output to extract file dictionary"""
        try:
            # Find JSON in the output
            start_idx = output.find('{"files":')
            if start_idx == -1:
                start_idx = output.find('{')
            
            # Extract JSON portion
            json_str = output[start_idx:]
            
            # Parse JSON
            result = json.loads(json_str)
            return result.get("files", {})
            
        except json.JSONDecodeError:
            # Fallback: try to extract files manually
            return self._manual_file_extraction(output)

    def _manual_file_extraction(self, output: str) -> Dict[str, str]:
        """Fallback file extraction if JSON parsing fails"""
        files = {}
        # Implementation for manual extraction
        # Look for file markers, code blocks, etc.
        return files

    async def modify_project(
        self, 
        existing_files: Dict[str, str], 
        modification_prompt: str
    ) -> Dict[str, str]:
        """Modify existing project based on user request"""
        
        # Format prompt for iteration
        prompt = f"""### Existing Project Files:
{json.dumps(existing_files, indent=2)}

### Modification Request:
{modification_prompt}

### Instructions:
Modify the existing files as requested. Return the complete updated files dictionary.
Only include files that need to be changed or added.

### Output Format:
Return JSON with:
{{
  "files": {{ "path/to/file.py": "<updated code>", ... }}
}}"""

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._generate, prompt)
        
        modified_files = self._parse_generated_output(output)
        
        # Merge with existing files
        result = existing_files.copy()
        result.update(modified_files)
        
        return result

    async def cleanup(self):
        """Cleanup model resources"""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        torch.cuda.empty_cache()
```

### **app/models/project.py** - Project Database Model
```python
"""
SQLAlchemy model for storing user projects and metadata.
Tracks project details, generation history, and settings.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Project configuration
    domain = Column(String(50), nullable=True)  # ecommerce, social_media, etc.
    tech_stack = Column(String(50), nullable=False)  # fastapi_postgres, etc.
    constraints = Column(JSON, nullable=True)  # ["dockerized", "tested"]
    
    # Status
    status = Column(String(20), default="draft")  # draft, active, archived
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="projects")
    organization = relationship("Organization", back_populates="projects")
    generations = relationship("Generation", back_populates="project", cascade="all, delete-orphan")

class Generation(Base):
    __tablename__ = "generations"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Generation details
    prompt = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)
    
    # AI pipeline results
    extracted_schema = Column(JSON, nullable=True)
    output_files = Column(JSON, nullable=True)  # file_path -> content
    review_feedback = Column(JSON, nullable=True)
    documentation = Column(JSON, nullable=True)
    
    # Quality metrics
    quality_score = Column(Float, nullable=True)
    
    # Status tracking
    status = Column(String(20), default="processing")  # processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Processing times
    schema_extraction_time = Column(Float, nullable=True)
    code_generation_time = Column(Float, nullable=True)
    review_time = Column(Float, nullable=True)
    docs_generation_time = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="generations")
    user = relationship("User", back_populates="generations")
    artifacts = relationship("Artifact", back_populates="generation", cascade="all, delete-orphan")

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String, primary_key=True)
    generation_id = Column(String, ForeignKey("generations.id"), nullable=False)
    
    # Artifact details
    type = Column(String(20), nullable=False)  # zip, openapi, diff, github_pr
    storage_url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    metadata = Column(JSON, nullable=True)  # PR URL, download count, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    generation = relationship("Generation", back_populates="artifacts")
```

### **tests/conftest.py** - Test Configuration
```python
"""
Pytest configuration and fixtures for testing the codebegen application.
Provides database, authentication, and AI model mocks.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.core.database import get_db, Base
from app.core.config import Settings, get_settings
from app.auth.dependencies import get_current_user
from app.schemas.user import User

# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_test_settings():
    return Settings(
        DATABASE_URL=TEST_DATABASE_URL,
        SECRET_KEY="test-secret-key",
        ENVIRONMENT="testing"
    )

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def db() -> Generator:
    """Create a test database session"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user() -> User:
    """Create a test user"""
    return User(
        id="test-user-123",
        email="test@example.com",
        username="testuser",
        is_active=True
    )

@pytest.fixture
def client(db, test_user) -> Generator:
    """Create a test client with overrides"""
    
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_settings] = get_test_settings
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()

@pytest.fixture
async def async_client(db, test_user) -> AsyncGenerator:
    """Create an async test client"""
    
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_settings] = get_test_settings
    
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
    
    app.dependency_overrides.clear()

# Mock AI models for testing
class MockAIOrchestrator:
    async def initialize(self):
        pass
    
    async def generate_project(self, request):
        return {
            "files": {
                "app/main.py": "# Mock FastAPI app\nfrom fastapi import FastAPI\napp = FastAPI()",
                "app/models/user.py": "# Mock user model",
                "README.md": "# Mock Project\nGenerated by codebegen"
            },
            "schema": {"User": {"fields": {"id": "int", "email": "str"}}},
            "review_feedback": {"issues": [], "suggestions": []},
            "documentation": {"readme": "Mock documentation"},
            "quality_score": 0.95
        }
    
    async def cleanup(self):
        pass

@pytest.fixture
def mock_ai_orchestrator(monkeypatch):
    """Mock the AI orchestrator for testing"""
    mock = MockAIOrchestrator()
    monkeypatch.setattr("app.main.AIOrchestrator", lambda: mock)
    return mock
```

### **infra/docker-compose.yml** - Development Environment
```yaml
# Docker Compose configuration for local development
# Includes PostgreSQL, Redis, and the codebegen API service

version: '3.8'

services:
  api:
    build:
      context: ..
      dockerfile: infra/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://codebegen:password@db:5432/codebegen
      - REDIS_URL=redis://redis:6379
      - ENVIRONMENT=development
    volumes:
      - ../app:/app/app
      - ../ai_models:/app/ai_models
      - ../templates:/app/templates
      - model_cache:/app/models
    depends_on:
      - db
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: codebegen
      POSTGRES_USER: codebegen
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Background worker for AI generation
  worker:
    build:
      context: ..
      dockerfile: infra/Dockerfile
    environment:
      - DATABASE_URL=postgresql://codebegen:password@db:5432/codebegen
      - REDIS_URL=redis://redis:6379
      - ENVIRONMENT=development
    volumes:
      - ../app:/app/app
      - ../ai_models:/app/ai_models
      - model_cache:/app/models
    depends_on:
      - db
      - redis
    command: celery -A app.worker worker --loglevel=info

volumes:
  postgres_data:
  redis_data:
  model_cache:
```

### **infra/Dockerfile** - Production Container
```dockerfile
# Multi-stage Docker build for production deployment
# Optimized for AI model loading and FastAPI serving

FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements/ requirements/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements/prod.txt

# Copy application code
COPY app/ app/
COPY ai_models/ ai_models/
COPY templates/ templates/
COPY alembic/ alembic/
COPY alembic.ini .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Create directories for models and storage
RUN mkdir -p /app/models /app/storage

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🎯 Key Implementation Notes

### **1. AI Model Management**
- Models are loaded asynchronously on startup to prevent blocking
- LoRA adapters are loaded separately for fine-tuned capabilities
- Thread pool execution prevents blocking the FastAPI event loop
- Resource cleanup ensures proper memory management

### **2. Clean Architecture**
- **Models**: SQLAlchemy ORM models for database entities
- **Schemas**: Pydantic models for API request/response validation
- **Repositories**: Data access layer abstractions
- **Services**: Business logic and AI orchestration
- **Routers**: API endpoint definitions

### **3. Multi-Model Pipeline**
- Each AI model is wrapped in its own service class
- AIOrchestrator coordinates the entire generation pipeline
- Streaming support for real-time progress updates
- Background task processing for long-running generations

### **4. Scalability Considerations**
- Redis for caching and job queues
- Background workers for AI processing
- Database connection pooling
- Model inference optimization with vLLM (future)

### **5. Testing Strategy**
- Comprehensive test fixtures with mocked AI models
- Database isolation per test
- Async testing support
- Mock data generators for consistent testing

This structure provides a solid foundation for building codebegen as a production-ready, AI-powered FastAPI backend generator that can scale with user demand while maintaining code quality and performance.