# Configuration settings
"""
Centralized configuration management using Pydantic settings.
Handles environment variables, database URLs, AI model configs, etc.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

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
    
    @property  
    def async_database_url(self) -> str:
        """Convert DATABASE_URL to async version if needed"""
        if "postgresql://" in self.DATABASE_URL:
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # AI Models
    QWEN_MODEL_PATH: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"  # Smaller model for local use
    LLAMA_MODEL_PATH: str = "meta-llama/Llama-3.1-8B"
    STARCODER_MODEL_PATH: str = "bigcode/starcoder2-15b"
    MISTRAL_MODEL_PATH: str = "mistralai/Mistral-7B-Instruct-v0.1"
    
    # Qwen Model Configuration
    QWEN_LARGE_MODEL_PATH: str = "Qwen/Qwen3-Coder-480B-A35B-Instruct"
    QWEN_SMALL_MODEL_PATH: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"  # For local fallback (much smaller)
    USE_QWEN_INFERENCE_API: bool = True  # True: Use HF Inference API, False: Load model locally
    ENABLE_LOCAL_QWEN_FALLBACK: bool = False  # Disable local fallback due to memory constraints
    FORCE_INFERENCE_MODE: bool = True  # Force HF Inference API for all generations
    QWEN_MEMORY_THRESHOLD_MB: int = 4096  # Memory threshold for local model loading
    
    # Default AI Generation Method
    DEFAULT_AI_BACKEND: str = "qwen_inference"  # qwen_inference, local_models, hybrid
    
    # HuggingFace API
    HF_TOKEN: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = Field(None, alias="HF_TOKEN")  # Alias for compatibility
    
    # LLM Provider Configuration
    LLM_PROVIDER: str = "huggingface"  # Options: "huggingface", "gemini", "hybrid"
    
    # Task-specific provider overrides (None = use LLM_PROVIDER)
    SCHEMA_EXTRACTION_PROVIDER: Optional[str] = None  # Override for schema extraction
    CODE_GENERATION_PROVIDER: Optional[str] = None  # Override for code generation
    CODE_REVIEW_PROVIDER: Optional[str] = None  # Override for code review
    DOCUMENTATION_PROVIDER: Optional[str] = None  # Override for documentation
    
    # Google Gemini Configuration
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"  # or "gemini-2.5-pro" when available
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192
    GEMINI_TOP_P: float = 0.95
    GEMINI_TOP_K: int = 40
    
    # Gemini Safety Settings (BLOCK_NONE for code generation)
    GEMINI_SAFETY_HARASSMENT: str = "BLOCK_NONE"
    GEMINI_SAFETY_HATE_SPEECH: str = "BLOCK_NONE"
    GEMINI_SAFETY_SEXUALLY_EXPLICIT: str = "BLOCK_NONE"
    GEMINI_SAFETY_DANGEROUS_CONTENT: str = "BLOCK_NONE"
    
    # Phased Generation Configuration
    USE_PHASED_GENERATION: bool = True  # Enable phased generation for complex projects
    PHASED_GENERATION_ENTITY_THRESHOLD: int = 3  # Use phased if entity count >= this
    FORCE_REPOSITORY_PATTERN: bool = True  # Always use repository pattern in phased mode
    PHASED_GENERATION_TIMEOUT: int = 300  # Timeout per phase in seconds
    
    # Hybrid Mode Configuration
    ENABLE_HYBRID_LLM_MODE: bool = False  # Use different providers for different tasks
    
    # AI Model Configuration
    MAX_NEW_TOKENS: int = 4096
    TEMPERATURE: float = 0.7
    TOP_P: float = 0.9
    DEVICE: str = "auto"  # auto, cpu, cuda
    TORCH_DTYPE: str = "auto"  # auto, float16, bfloat16
    
    # File Storage Paths
    FILE_STORAGE_PATH: str = "./storage/projects"
    TEMP_STORAGE_PATH: str = "./storage/temp"
    TEMPLATE_PATH: str = "./templates"
    API_BASE_URL: str = "http://localhost:8000"
    
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
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()