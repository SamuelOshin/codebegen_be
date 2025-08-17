"""
Model loader and manager for AI models.
Handles model initialization, caching, and resource management.
"""

import asyncio
import os
import gc
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

try:
    import torch  # type: ignore
    TORCH_AVAILABLE = True
except Exception as _e:  # Catch broader exceptions (e.g., binary incompatibility)
    TORCH_AVAILABLE = False
    print("Warning: PyTorch not available or incompatible. AI features will be limited.")

from app.core.config import settings
from .qwen_generator import QwenGenerator
from .llama_parser import LlamaParser
from .starcoder_reviewer import StarcoderReviewer
from .mistral_docs import MistralDocsGenerator


class ModelType(Enum):
    QWEN_GENERATOR = "qwen_generator"
    LLAMA_PARSER = "llama_parser"
    STARCODER_REVIEWER = "starcoder_reviewer"
    MISTRAL_DOCS = "mistral_docs"


@dataclass
class ModelInfo:
    model_type: ModelType
    model_path: str
    instance: Optional[Any] = None
    loaded: bool = False
    memory_usage: float = 0.0


class ModelLoader:
    """Manages loading and unloading of AI models"""
    
    def __init__(self):
        self.models: Dict[ModelType, ModelInfo] = {}
        self.max_concurrent_models = 2  # Limit concurrent models to manage memory
        self.currently_loaded = set()
        
        # Initialize model configurations
        self._initialize_model_configs()

    def _initialize_model_configs(self):
        """Initialize model configurations from settings"""
        self.models = {
            ModelType.QWEN_GENERATOR: ModelInfo(
                model_type=ModelType.QWEN_GENERATOR,
                model_path=settings.QWEN_MODEL_PATH
            ),
            ModelType.LLAMA_PARSER: ModelInfo(
                model_type=ModelType.LLAMA_PARSER,
                model_path=settings.LLAMA_MODEL_PATH
            ),
            ModelType.STARCODER_REVIEWER: ModelInfo(
                model_type=ModelType.STARCODER_REVIEWER,
                model_path=settings.STARCODER_MODEL_PATH
            ),
            ModelType.MISTRAL_DOCS: ModelInfo(
                model_type=ModelType.MISTRAL_DOCS,
                model_path=settings.MISTRAL_MODEL_PATH
            )
        }

    async def get_model(self, model_type: ModelType) -> Any:
        """Get a loaded model instance, loading if necessary"""
        model_info = self.models.get(model_type)
        if not model_info:
            raise ValueError(f"Unknown model type: {model_type}")
        
        # Load model if not already loaded
        if not model_info.loaded:
            await self._load_model(model_type)
        
        return model_info.instance

    async def _load_model(self, model_type: ModelType):
        """Load a specific model"""
        model_info = self.models[model_type]
        
        if model_info.loaded:
            return
        
        # Manage memory by unloading other models if necessary
        await self._manage_memory_for_loading(model_type)
        
        print(f"Loading {model_type.value} model...")
        
        try:
            # Create model instance
            if model_type == ModelType.QWEN_GENERATOR:
                model_info.instance = QwenGenerator(model_info.model_path)
            elif model_type == ModelType.LLAMA_PARSER:
                model_info.instance = LlamaParser(model_info.model_path)
            elif model_type == ModelType.STARCODER_REVIEWER:
                model_info.instance = StarcoderReviewer(model_info.model_path)
            elif model_type == ModelType.MISTRAL_DOCS:
                model_info.instance = MistralDocsGenerator(model_info.model_path)
            
            # Load the model
            await model_info.instance.load()
            
            model_info.loaded = True
            self.currently_loaded.add(model_type)
            
            # Update memory usage (approximate)
            model_info.memory_usage = self._estimate_memory_usage(model_type)
            
            print(f"Successfully loaded {model_type.value} model")
            
        except Exception as e:
            print(f"Error loading {model_type.value} model: {e}")
            model_info.instance = None
            model_info.loaded = False
            raise

    async def _manage_memory_for_loading(self, model_type: ModelType):
        """Manage memory by unloading models if necessary"""
        # If we're at the concurrent limit, unload the least recently used model
        if len(self.currently_loaded) >= self.max_concurrent_models:
            # For now, unload the first loaded model (FIFO)
            # In production, implement LRU cache
            oldest_model = next(iter(self.currently_loaded))
            if oldest_model != model_type:  # Don't unload the model we're about to load
                await self._unload_model(oldest_model)

    async def _unload_model(self, model_type: ModelType):
        """Unload a specific model to free memory"""
        model_info = self.models.get(model_type)
        if not model_info or not model_info.loaded:
            return
        
        print(f"Unloading {model_type.value} model...")
        
        try:
            if model_info.instance and hasattr(model_info.instance, 'cleanup'):
                await model_info.instance.cleanup()
            
            model_info.instance = None
            model_info.loaded = False
            model_info.memory_usage = 0.0
            
            if model_type in self.currently_loaded:
                self.currently_loaded.remove(model_type)
            
            # Force garbage collection
            gc.collect()
            # Safely clear CUDA cache only if torch is usable
            if TORCH_AVAILABLE and hasattr(torch, "cuda"):
                try:
                    if torch.cuda.is_available():  # type: ignore[attr-defined]
                        torch.cuda.empty_cache()  # type: ignore[attr-defined]
                except Exception:
                    pass
            
            print(f"Successfully unloaded {model_type.value} model")
            
        except Exception as e:
            print(f"Error unloading {model_type.value} model: {e}")

    def _estimate_memory_usage(self, model_type: ModelType) -> float:
        """Estimate memory usage of a model (in GB)"""
        # Rough estimates based on model sizes
        memory_estimates = {
            ModelType.QWEN_GENERATOR: 32.0,  # 32B parameters
            ModelType.LLAMA_PARSER: 8.0,     # 8B parameters
            ModelType.STARCODER_REVIEWER: 15.0,  # 15B parameters
            ModelType.MISTRAL_DOCS: 7.0      # 7B parameters
        }
        return memory_estimates.get(model_type, 5.0)

    async def preload_models(self, model_types: list[ModelType] = None):
        """Preload specified models or all models"""
        if model_types is None:
            model_types = list(ModelType)
        
        print("Preloading AI models...")
        
        for model_type in model_types:
            try:
                await self._load_model(model_type)
            except Exception as e:
                print(f"Failed to preload {model_type.value}: {e}")
        
        print(f"Preloaded {len(self.currently_loaded)} models")

    async def unload_all_models(self):
        """Unload all models to free memory"""
        print("Unloading all AI models...")
        
        for model_type in list(self.currently_loaded):
            await self._unload_model(model_type)
        
        print("All models unloaded")

    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all models"""
        status = {
            "currently_loaded": [mt.value for mt in self.currently_loaded],
            "total_memory_usage": sum(
                info.memory_usage for info in self.models.values() if info.loaded
            ),
            "models": {}
        }
        
        for model_type, model_info in self.models.items():
            status["models"][model_type.value] = {
                "loaded": model_info.loaded,
                "memory_usage_gb": model_info.memory_usage,
                "model_path": model_info.model_path
            }
        
        return status

    def is_model_loaded(self, model_type: ModelType) -> bool:
        """Check if a model is currently loaded"""
        model_info = self.models.get(model_type)
        return model_info is not None and model_info.loaded

    async def cleanup(self):
        """Cleanup all resources"""
        await self.unload_all_models()


# Global model loader instance
model_loader = ModelLoader()
