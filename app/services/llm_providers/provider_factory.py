"""
Provider Factory for LLM Provider Selection

Handles dynamic selection and instantiation of LLM providers based on
configuration settings and task requirements.
"""

import logging
from typing import Optional, Dict
from .base_provider import BaseLLMProvider, LLMTask
from app.core.config import settings


logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """
    Factory class for creating and managing LLM providers.
    
    Provides centralized provider selection based on:
    - Global LLM_PROVIDER setting
    - Task-specific provider overrides
    - Hybrid mode configuration
    
    Caches provider instances to avoid redundant initialization.
    """
    
    # Cache for provider instances
    _providers: Dict[str, BaseLLMProvider] = {}
    _initialization_errors: Dict[str, str] = {}
    
    @classmethod
    async def get_provider(
        cls,
        task: Optional[LLMTask] = None
    ) -> BaseLLMProvider:
        """
        Get appropriate provider for the specified task.
        
        Args:
            task: The type of task (None for general use)
            
        Returns:
            Initialized provider instance
            
        Raises:
            ValueError: If provider configuration is invalid
            ImportError: If provider dependencies are missing
            Exception: If provider initialization fails
        """
        # Determine which provider to use
        provider_name = cls._get_provider_name_for_task(task)
        
        # Check for previous initialization errors
        if provider_name in cls._initialization_errors:
            error_msg = cls._initialization_errors[provider_name]
            logger.warning(f"Provider {provider_name} previously failed: {error_msg}")
            # Try to use fallback
            if provider_name == "gemini":
                logger.info("Falling back to HuggingFace provider")
                provider_name = "huggingface"
            else:
                raise ValueError(f"Provider {provider_name} unavailable: {error_msg}")
        
        # Return cached provider or create new one
        if provider_name not in cls._providers:
            cls._providers[provider_name] = await cls._create_provider(provider_name)
        
        return cls._providers[provider_name]
    
    @classmethod
    def _get_provider_name_for_task(cls, task: Optional[LLMTask]) -> str:
        """
        Determine provider based on task and configuration.
        
        Priority:
        1. Task-specific override (if task provided and override configured)
        2. Global LLM_PROVIDER setting
        
        Args:
            task: The type of task being performed
            
        Returns:
            Provider name ("huggingface" or "gemini")
        """
        # Check task-specific overrides
        if task is not None:
            override = None
            
            if task == LLMTask.SCHEMA_EXTRACTION:
                override = settings.SCHEMA_EXTRACTION_PROVIDER
            elif task == LLMTask.CODE_GENERATION:
                override = settings.CODE_GENERATION_PROVIDER
            elif task == LLMTask.CODE_REVIEW:
                override = settings.CODE_REVIEW_PROVIDER
            elif task == LLMTask.DOCUMENTATION:
                override = settings.DOCUMENTATION_PROVIDER
            
            if override:
                logger.debug(f"Using task-specific provider '{override}' for {task.value}")
                return override
        
        # Default to global provider
        provider = settings.LLM_PROVIDER
        logger.debug(f"Using global provider '{provider}' for task {task.value if task else 'general'}")
        return provider
    
    @classmethod
    async def _create_provider(cls, provider_name: str) -> BaseLLMProvider:
        """
        Create and initialize a provider instance.
        
        Args:
            provider_name: Name of the provider to create
            
        Returns:
            Initialized provider instance
            
        Raises:
            ValueError: If provider name is unknown
            Exception: If initialization fails
        """
        try:
            if provider_name == "huggingface":
                from .huggingface_provider import HuggingFaceProvider
                provider = HuggingFaceProvider()
                logger.info("Creating HuggingFace provider")
                
            elif provider_name == "gemini":
                from .gemini_provider import GeminiProvider
                provider = GeminiProvider()
                logger.info("Creating Gemini provider")
                
            else:
                raise ValueError(
                    f"Unknown provider: {provider_name}. "
                    f"Valid options: 'huggingface', 'gemini'"
                )
            
            # Initialize the provider
            await provider.initialize()
            logger.info(f"✅ {provider_name} provider initialized successfully")
            
            return provider
            
        except Exception as e:
            error_msg = f"Failed to initialize {provider_name} provider: {e}"
            logger.error(error_msg)
            cls._initialization_errors[provider_name] = str(e)
            raise
    
    @classmethod
    async def initialize_all_providers(cls):
        """
        Pre-initialize all configured providers.
        
        This method initializes:
        1. The global LLM_PROVIDER
        2. Any task-specific provider overrides
        
        Useful for:
        - Application startup
        - Testing
        - Warming up providers
        
        Errors during initialization are logged but don't stop the process.
        """
        providers_to_init = {settings.LLM_PROVIDER}
        
        # Add task-specific providers
        if settings.SCHEMA_EXTRACTION_PROVIDER:
            providers_to_init.add(settings.SCHEMA_EXTRACTION_PROVIDER)
        if settings.CODE_GENERATION_PROVIDER:
            providers_to_init.add(settings.CODE_GENERATION_PROVIDER)
        if settings.CODE_REVIEW_PROVIDER:
            providers_to_init.add(settings.CODE_REVIEW_PROVIDER)
        if settings.DOCUMENTATION_PROVIDER:
            providers_to_init.add(settings.DOCUMENTATION_PROVIDER)
        
        logger.info(f"Initializing providers: {', '.join(providers_to_init)}")
        
        for provider_name in providers_to_init:
            try:
                await cls._create_provider(provider_name)
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_name}: {e}")
                # Continue with other providers
                continue
        
        logger.info(f"Provider initialization complete. Active providers: {len(cls._providers)}")
    
    @classmethod
    def get_active_providers(cls) -> Dict[str, Dict[str, any]]:
        """
        Get information about all active (initialized) providers.
        
        Returns:
            Dictionary mapping provider names to their info
        """
        active = {}
        for name, provider in cls._providers.items():
            try:
                # Try to get provider info synchronously if available
                info = {
                    "name": name,
                    "initialized": True,
                    "type": provider.__class__.__name__
                }
                active[name] = info
            except Exception as e:
                logger.warning(f"Failed to get info for {name}: {e}")
        
        return active
    
    @classmethod
    def clear_cache(cls):
        """
        Clear all cached provider instances.
        
        Useful for:
        - Testing
        - Configuration changes
        - Memory management
        - Error recovery
        """
        logger.info(f"Clearing provider cache ({len(cls._providers)} providers)")
        cls._providers.clear()
        cls._initialization_errors.clear()
    
    @classmethod
    def get_provider_for_config(cls) -> str:
        """
        Get the configured primary provider name.
        
        Returns:
            The name of the primary LLM provider
        """
        return settings.LLM_PROVIDER
    
    @classmethod
    def is_hybrid_mode(cls) -> bool:
        """
        Check if hybrid mode is enabled.
        
        Hybrid mode uses different providers for different tasks.
        
        Returns:
            True if any task-specific overrides are configured
        """
        return any([
            settings.SCHEMA_EXTRACTION_PROVIDER,
            settings.CODE_GENERATION_PROVIDER,
            settings.CODE_REVIEW_PROVIDER,
            settings.DOCUMENTATION_PROVIDER
        ]) or settings.ENABLE_HYBRID_LLM_MODE
    
    @classmethod
    def get_task_provider_mapping(cls) -> Dict[str, str]:
        """
        Get the mapping of tasks to providers.
        
        Returns:
            Dictionary mapping task names to provider names
        """
        return {
            "schema_extraction": settings.SCHEMA_EXTRACTION_PROVIDER or settings.LLM_PROVIDER,
            "code_generation": settings.CODE_GENERATION_PROVIDER or settings.LLM_PROVIDER,
            "code_review": settings.CODE_REVIEW_PROVIDER or settings.LLM_PROVIDER,
            "documentation": settings.DOCUMENTATION_PROVIDER or settings.LLM_PROVIDER,
            "default": settings.LLM_PROVIDER,
            "hybrid_mode": cls.is_hybrid_mode()
        }
