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
    QWEN_MODEL_PATH: str = "Qwen/Qwen2.5-Coder-32B"
    LLAMA_MODEL_PATH: str = "meta-llama/Llama-3.1-8B"
    STARCODER_MODEL_PATH: str = "bigcode/starcoder2-15b"
    MISTRAL_MODEL_PATH: str = "mistralai/Mistral-7B-Instruct-v0.1"
    
    # HuggingFace API
    HF_TOKEN: Optional[str] = None
    
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