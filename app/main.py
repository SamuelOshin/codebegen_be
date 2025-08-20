# Entry point for the FastAPI application
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
from app.routers import auth, projects, generations, ai, webhooks, ab_testing, unified_generation
from app.services.ai_orchestrator import ai_orchestrator, AIOrchestrator

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

# Unified Generation Router (Recommended)
app.include_router(unified_generation.router, prefix="/api/v2/generation", tags=["Generation (Unified)"])

app.include_router(generations.router, prefix="/generations", tags=["Generations"])
# app.include_router(ai.router, prefix="/ai", tags=["AI Services (Legacy)"], deprecated=True)

app.include_router(ab_testing.router, prefix="/api/v1", tags=["A/B Testing"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

@app.on_event("startup")
async def startup_event():
    """Load AI models and initialize services"""
    # Initialize AI orchestrator
    try:
        app.state.ai_orchestrator = ai_orchestrator
        await app.state.ai_orchestrator.initialize()
        print("AI Orchestrator initialized successfully")
    except Exception as e:
        print(f"Failed to initialize AI orchestrator: {e}")
        # Set a None value so we can handle it gracefully
        app.state.ai_orchestrator = None

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources"""
    if hasattr(app.state, 'ai_orchestrator'):
        await app.state.ai_orchestrator.cleanup()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "codebegen-api"}