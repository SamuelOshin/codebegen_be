"""
Base Provider Interface for LLM Providers

Defines the abstract interface that all LLM providers must implement.
This enables switching between different providers (HuggingFace, Gemini, etc.)
while maintaining a consistent API.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum


class LLMTask(Enum):
    """Enumeration of LLM task types"""
    SCHEMA_EXTRACTION = "schema_extraction"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All LLM providers (HuggingFace, Gemini, etc.) must implement this interface
    to ensure consistent behavior across different providers.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the provider (load models, setup API clients, etc.)
        
        This method should be called before using any other provider methods.
        It handles all necessary setup including:
        - Loading models into memory
        - Initializing API clients
        - Verifying credentials
        - Setting up configuration
        
        Raises:
            ValueError: If configuration is invalid
            Exception: If initialization fails
        """
        pass
    
    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        task: LLMTask,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate a text completion for the given prompt.
        
        This is a low-level method that provides direct access to the LLM.
        For specific tasks, use the specialized methods (extract_schema, etc.)
        
        Args:
            prompt: The input prompt
            task: The type of task being performed (used for provider optimization)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text completion
            
        Raises:
            Exception: If generation fails
        """
        pass
    
    @abstractmethod
    async def extract_schema(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract database schema and API structure from natural language description.
        
        This method analyzes the project requirements and generates:
        - Database entities with fields and types
        - Relationships between entities
        - API endpoints with methods and paths
        - Tech stack recommendations
        
        Args:
            prompt: Natural language project description
            context: Additional context (tech_stack, domain, constraints, etc.)
            
        Returns:
            Dictionary containing:
            {
                "entities": [
                    {
                        "name": str,
                        "fields": [{"name": str, "type": str, "required": bool}],
                        "relationships": [{"type": str, "target": str}]
                    }
                ],
                "endpoints": [
                    {
                        "path": str,
                        "method": str,
                        "description": str,
                        "entity": str
                    }
                ],
                "tech_stack": str
            }
            
        Raises:
            ValueError: If schema extraction fails
            Exception: If LLM call fails
        """
        pass
    
    @abstractmethod
    async def generate_code(
        self,
        prompt: str,
        schema: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate complete project code based on schema and requirements.
        
        This method produces production-ready code including:
        - FastAPI application structure
        - SQLAlchemy models
        - Pydantic schemas
        - API routers/endpoints
        - Repository pattern implementations
        - Configuration files
        - Documentation
        
        Args:
            prompt: Enhanced prompt with project requirements
            schema: Database schema from extract_schema()
            context: Additional context (tech_stack, domain, constraints)
            
        Returns:
            Dictionary mapping file paths to file contents:
            {
                "main.py": str,
                "app/models/user.py": str,
                "app/schemas/user.py": str,
                "app/routers/users.py": str,
                "requirements.txt": str,
                "README.md": str,
                ...
            }
            
        Raises:
            ValueError: If code generation fails
            Exception: If LLM call fails
        """
        pass
    
    @abstractmethod
    async def review_code(
        self,
        files: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive code review on generated files.
        
        Analyzes code for:
        - Security vulnerabilities (SQL injection, XSS, etc.)
        - Performance issues (N+1 queries, inefficient algorithms)
        - Code quality (naming, structure, duplication)
        - Best practices violations
        - Missing error handling
        - Type safety issues
        
        Args:
            files: Dictionary of file paths to file contents
            
        Returns:
            Dictionary containing:
            {
                "issues": [
                    {
                        "file": str,
                        "line": int,
                        "severity": "high|medium|low",
                        "category": "security|performance|quality|style",
                        "message": str,
                        "code": str
                    }
                ],
                "suggestions": [
                    {
                        "file": str,
                        "message": str
                    }
                ],
                "scores": {
                    "security": float (0-1),
                    "maintainability": float (0-1),
                    "performance": float (0-1),
                    "overall": float (0-1)
                }
            }
            
        Raises:
            Exception: If review fails
        """
        pass
    
    @abstractmethod
    async def generate_documentation(
        self,
        files: Dict[str, str],
        schema: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate comprehensive project documentation.
        
        Creates documentation files including:
        - README.md with setup instructions
        - API_DOCUMENTATION.md with endpoint details
        - SETUP_GUIDE.md for deployment
        - ARCHITECTURE.md explaining design decisions
        
        Args:
            files: Generated code files
            schema: Database schema
            context: Project context
            
        Returns:
            Dictionary mapping documentation file names to contents:
            {
                "README.md": str,
                "API_DOCUMENTATION.md": str,
                "SETUP_GUIDE.md": str,
                "ARCHITECTURE.md": str
            }
            
        Raises:
            Exception: If documentation generation fails
        """
        pass
    
    async def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider.
        
        Returns:
            Dictionary containing:
            {
                "name": str,
                "type": str,
                "models": Dict[str, str],
                "capabilities": List[str],
                "initialized": bool
            }
        """
        return {
            "name": self.__class__.__name__,
            "type": "base",
            "models": {},
            "capabilities": ["schema_extraction", "code_generation", "code_review", "documentation"],
            "initialized": False
        }
