"""
HuggingFace Provider Wrapper

Wraps existing HuggingFace model implementations (Llama, Qwen, Starcoder, Mistral)
to implement the BaseLLMProvider interface, enabling seamless provider switching.
"""

from loguru import logger
from typing import Dict, Any, Optional

from .base_provider import BaseLLMProvider, LLMTask
from app.core.config import settings


logger = logger


class HuggingFaceProvider(BaseLLMProvider):
    """
    HuggingFace models provider - wraps existing implementations.
    
    This provider maintains backward compatibility with the existing
    multi-model pipeline:
    - Llama-3.1-8B for schema extraction
    - Qwen2.5-Coder-32B for code generation
    - Starcoder2-15B for code review
    - Mistral-7B-Instruct for documentation
    """
    
    def __init__(self):
        self.llama_parser = None
        self.qwen_generator = None
        self.starcoder_reviewer = None
        self.mistral_docs = None
        self.initialized = False
        self._init_errors = []
    
    async def initialize(self) -> None:
        """Initialize all HuggingFace models"""
        if self.initialized:
            return
        
        logger.info("Initializing HuggingFace provider with multiple models...")
        
        # Import models (lazy import to avoid issues if not used)
        try:
            from ai_models.llama_parser import LlamaParser
            from ai_models.qwen_generator import QwenGenerator
            from ai_models.starcoder_reviewer import StarcoderReviewer
            from ai_models.mistral_docs import MistralDocsGenerator
        except ImportError as e:
            error_msg = f"Failed to import HuggingFace models: {e}"
            logger.error(error_msg)
            raise ImportError(
                "HuggingFace models not available. "
                "Ensure transformers and required packages are installed."
            )
        
        # Initialize Llama for schema extraction
        try:
            self.llama_parser = LlamaParser(settings.LLAMA_MODEL_PATH)
            await self.llama_parser.load()
            logger.info("✅ Llama parser loaded")
        except Exception as e:
            error_msg = f"Failed to load Llama parser: {e}"
            logger.warning(error_msg)
            self._init_errors.append(error_msg)
        
        # Initialize Qwen for code generation
        try:
            self.qwen_generator = QwenGenerator(settings.QWEN_LARGE_MODEL_PATH)
            await self.qwen_generator.load()
            logger.info("✅ Qwen generator loaded")
        except Exception as e:
            error_msg = f"Failed to load Qwen generator: {e}"
            logger.warning(error_msg)
            self._init_errors.append(error_msg)
        
        # Initialize Starcoder for code review
        try:
            self.starcoder_reviewer = StarcoderReviewer(settings.STARCODER_MODEL_PATH)
            await self.starcoder_reviewer.load()
            logger.info("✅ Starcoder reviewer loaded")
        except Exception as e:
            error_msg = f"Failed to load Starcoder reviewer: {e}"
            logger.warning(error_msg)
            self._init_errors.append(error_msg)
        
        # Initialize Mistral for documentation
        try:
            self.mistral_docs = MistralDocsGenerator(settings.MISTRAL_MODEL_PATH)
            await self.mistral_docs.load()
            logger.info("✅ Mistral docs generator loaded")
        except Exception as e:
            error_msg = f"Failed to load Mistral docs generator: {e}"
            logger.warning(error_msg)
            self._init_errors.append(error_msg)
        
        # Check if at least one model loaded successfully
        models_loaded = sum([
            self.llama_parser is not None,
            self.qwen_generator is not None,
            self.starcoder_reviewer is not None,
            self.mistral_docs is not None
        ])
        
        if models_loaded == 0:
            raise Exception(
                "Failed to load any HuggingFace models. Errors: " + 
                "; ".join(self._init_errors)
            )
        
        self.initialized = True
        logger.info(
            f"✅ HuggingFace provider initialized: "
            f"{models_loaded}/4 models loaded successfully"
        )
        
        if self._init_errors:
            logger.warning(f"Initialization warnings: {'; '.join(self._init_errors)}")
    
    async def generate_completion(
        self,
        prompt: str,
        task: LLMTask,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate completion using appropriate HuggingFace model.
        
        Note: This is a low-level method. For most use cases,
        use the specialized methods (extract_schema, etc.)
        """
        if not self.initialized:
            await self.initialize()
        
        # Route to appropriate model based on task
        if task == LLMTask.SCHEMA_EXTRACTION and self.llama_parser:
            # Use Llama's internal generation method
            return await self.llama_parser._generate_text(prompt, max_tokens, temperature)
        elif task == LLMTask.CODE_GENERATION and self.qwen_generator:
            # Use Qwen's internal generation method
            return await self.qwen_generator._generate_text(prompt, max_tokens, temperature)
        elif task == LLMTask.CODE_REVIEW and self.starcoder_reviewer:
            # Use Starcoder's internal generation method
            return await self.starcoder_reviewer._generate_text(prompt, max_tokens, temperature)
        elif task == LLMTask.DOCUMENTATION and self.mistral_docs:
            # Use Mistral's internal generation method
            return await self.mistral_docs._generate_text(prompt, max_tokens, temperature)
        else:
            raise ValueError(
                f"No model available for task {task}. "
                f"Initialization errors: {self._init_errors}"
            )
    
    async def extract_schema(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delegate to Llama parser"""
        if not self.initialized:
            await self.initialize()
        
        if not self.llama_parser:
            raise RuntimeError(
                "Llama parser not available for schema extraction. "
                "Error: " + next((e for e in self._init_errors if "Llama" in e), "Unknown")
            )
        
        try:
            return await self.llama_parser.extract_schema(prompt, context)
        except Exception as e:
            logger.error(f"Schema extraction failed: {e}")
            # Return minimal schema as fallback
            return {
                "entities": [],
                "endpoints": [],
                "tech_stack": context.get('tech_stack', 'fastapi_postgres'),
                "error": str(e)
            }
    
    async def generate_code(
        self,
        prompt: str,
        schema: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Delegate to Qwen generator"""
        if not self.initialized:
            await self.initialize()
        
        if not self.qwen_generator:
            raise RuntimeError(
                "Qwen generator not available for code generation. "
                "Error: " + next((e for e in self._init_errors if "Qwen" in e), "Unknown")
            )
        
        try:
            return await self.qwen_generator.generate_code(prompt, schema, context)
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise
    
    async def review_code(
        self,
        files: Dict[str, str]
    ) -> Dict[str, Any]:
        """Delegate to Starcoder reviewer"""
        if not self.initialized:
            await self.initialize()
        
        if not self.starcoder_reviewer:
            raise RuntimeError(
                "Starcoder reviewer not available for code review. "
                "Error: " + next((e for e in self._init_errors if "Starcoder" in e), "Unknown")
            )
        
        try:
            return await self.starcoder_reviewer.review_code(files)
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            # Return minimal review on failure
            return {
                "issues": [],
                "suggestions": [],
                "security_score": 0.7,
                "maintainability_score": 0.7,
                "performance_score": 0.7,
                "overall_score": 0.7,
                "metrics": {
                    "total_lines": sum(len(content.split('\n')) for content in files.values()),
                    "total_files": len(files),
                    "complexity_score": 0.7
                },
                "error": str(e)
            }
    
    async def generate_documentation(
        self,
        files: Dict[str, str],
        schema: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Delegate to Mistral docs generator"""
        if not self.initialized:
            await self.initialize()
        
        if not self.mistral_docs:
            raise RuntimeError(
                "Mistral docs generator not available for documentation. "
                "Error: " + next((e for e in self._init_errors if "Mistral" in e), "Unknown")
            )
        
        try:
            return await self.mistral_docs.generate_documentation(files, schema, context)
        except Exception as e:
            logger.error(f"Documentation generation failed: {e}")
            # Return minimal documentation on failure
            return {
                "README.md": f"# Generated Project\n\nError generating documentation: {e}",
                "error": str(e)
            }
    
    async def get_provider_info(self) -> Dict[str, Any]:
        """Get information about HuggingFace provider"""
        return {
            "name": "HuggingFaceProvider",
            "type": "huggingface",
            "models": {
                "schema_extraction": settings.LLAMA_MODEL_PATH if self.llama_parser else None,
                "code_generation": settings.QWEN_LARGE_MODEL_PATH if self.qwen_generator else None,
                "code_review": settings.STARCODER_MODEL_PATH if self.starcoder_reviewer else None,
                "documentation": settings.MISTRAL_MODEL_PATH if self.mistral_docs else None
            },
            "capabilities": ["schema_extraction", "code_generation", "code_review", "documentation"],
            "initialized": self.initialized,
            "models_loaded": {
                "llama": self.llama_parser is not None,
                "qwen": self.qwen_generator is not None,
                "starcoder": self.starcoder_reviewer is not None,
                "mistral": self.mistral_docs is not None
            },
            "initialization_errors": self._init_errors,
            "unified_model": False,  # Uses multiple specialized models
            "memory_mode": "inference_api" if settings.FORCE_INFERENCE_MODE else "local"
        }
