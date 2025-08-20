"""
Enhanced Qwen Generator with Configurable Model Loading

Supports both HuggingFace Inference API and local model loading
based on configuration settings.
"""

import asyncio
import json
import os
import psutil
from typing import Dict, Any, Optional, Union
from enum import Enum

try:
    from huggingface_hub import InferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("Warning: huggingface_hub not available. Inference API will be disabled.")

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers/torch not available. Local model loading will be disabled.")

from app.core.config import settings


class QwenMode(Enum):
    """Qwen generation modes"""
    INFERENCE_API = "inference_api"
    LOCAL_MODEL = "local_model"
    AUTO = "auto"


class ConfigurableQwenGenerator:
    """
    Qwen generator that can use either HuggingFace Inference API or local model
    based on configuration settings and system capabilities.
    """
    
    def __init__(self, mode: Optional[QwenMode] = None):
        self.mode = mode or (QwenMode.INFERENCE_API if settings.USE_QWEN_INFERENCE_API else QwenMode.LOCAL_MODEL)
        self.model_path = settings.QWEN_LARGE_MODEL_PATH
        self.local_model_path = settings.QWEN_SMALL_MODEL_PATH  # Use small model for local loading
        
        # API components
        self.inference_client = None
        
        # Local model components
        self.tokenizer = None
        self.model = None
        self.device = None
        
        # Status tracking
        self.initialized = False
        self.active_mode = None
        self.current_model_name = None
        
        print(f"🚀 Initializing Configurable Qwen Generator")
        print(f"   Mode: {self.mode.value}")
        print(f"   Large Model: {self.model_path}")
        print(f"   Fallback Model: {self.local_model_path}")
    
    async def initialize(self) -> bool:
        """Initialize the generator based on configuration and capabilities"""
        if self.initialized:
            return True
            
        print("🔧 Initializing Qwen Generator...")
        
        # Check system capabilities
        memory_info = await self._check_system_resources()
        print(f"💾 Available Memory: {memory_info['available_mb']:,}MB")
        
        success = False
        
        if self.mode == QwenMode.AUTO:
            # Auto mode: Try API first, then local if memory allows
            success = await self._initialize_auto_mode(memory_info)
        elif self.mode == QwenMode.INFERENCE_API:
            success = await self._initialize_inference_api()
        elif self.mode == QwenMode.LOCAL_MODEL:
            success = await self._initialize_local_model(memory_info)
        
        self.initialized = success
        
        if success:
            print(f"✅ Qwen Generator initialized successfully in {self.active_mode.value} mode")
        else:
            print("❌ Failed to initialize Qwen Generator")
        
        return success
    
    async def _initialize_auto_mode(self, memory_info: Dict[str, Any]) -> bool:
        """Auto mode: Try API first, then local if possible"""
        print("🤖 Auto mode: Trying Inference API first...")
        
        # Try Inference API first
        if await self._initialize_inference_api():
            return True
        
        # If API fails and we have enough memory, try local
        if memory_info["can_load_large_model"]:
            print("📝 API failed, trying local large model...")
            return await self._initialize_local_model(memory_info, use_large_model=True)
        elif memory_info["can_load_small_model"]:
            print("📝 API failed, trying local small model...")
            return await self._initialize_local_model(memory_info, use_large_model=False)
        
        print("❌ Auto mode failed: No viable options available")
        return False
    
    async def _initialize_inference_api(self) -> bool:
        """Initialize HuggingFace Inference API"""
        if not HF_AVAILABLE:
            print("❌ HuggingFace Hub not available")
            return False
        
        try:
            hf_token = os.environ.get("HF_TOKEN") or settings.HF_TOKEN
            
            if not hf_token:
                print("❌ HF_TOKEN not found")
                return False
            
            self.inference_client = InferenceClient(
                model=self.model_path,
                token=hf_token
            )
            
            # Test the API connection
            test_result = await self._test_inference_api()
            
            if test_result:
                self.active_mode = QwenMode.INFERENCE_API
                self.current_model_name = self.model_path
                print("✅ Inference API initialized successfully")
                return True
            else:
                print("❌ Inference API test failed")
                return False
                
        except Exception as e:
            print(f"❌ Inference API initialization failed: {e}")
            return False
    
    async def _initialize_local_model(self, memory_info: Dict[str, Any], use_large_model: bool = None) -> bool:
        """Initialize local model"""
        if not TRANSFORMERS_AVAILABLE:
            print("❌ Transformers not available for local model")
            return False
        
        try:
            # Determine which model to use
            if use_large_model is None:
                use_large_model = memory_info["can_load_large_model"]
            
            model_path = self.model_path if use_large_model else self.local_model_path
            
            print(f"🔄 Loading local model: {model_path}")
            print(f"   Large model: {use_large_model}")
            
            # Configure quantization for memory efficiency
            quantization_config = None
            if memory_info["available_mb"] < 32000:  # Less than 32GB
                print("🔧 Using 4-bit quantization for memory efficiency")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
            
            # Load tokenizer
            print("📝 Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True
            )
            
            # Load model
            print("🧠 Loading model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16 if quantization_config is None else torch.float32
            )
            
            self.device = next(self.model.parameters()).device
            self.active_mode = QwenMode.LOCAL_MODEL
            self.current_model_name = model_path
            
            print(f"✅ Local model loaded on {self.device}")
            return True
            
        except Exception as e:
            print(f"❌ Local model initialization failed: {e}")
            return False
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources for model loading"""
        memory = psutil.virtual_memory()
        available_mb = memory.available // (1024 * 1024)
        
        # Memory requirements (approximate)
        large_model_memory_mb = 960000  # 480B model needs ~960GB
        small_model_memory_mb = 4096    # 32B model needs ~4GB
        
        return {
            "available_mb": available_mb,
            "can_load_large_model": available_mb >= large_model_memory_mb,
            "can_load_small_model": available_mb >= small_model_memory_mb,
            "memory_usage_percent": memory.percent
        }
    
    async def _test_inference_api(self) -> bool:
        """Test Inference API connection"""
        try:
            # Use chat completion without model parameter (already set in client)
            response = self.inference_client.chat_completion(
                messages=[{"role": "user", "content": "Hello, write a simple Python function."}],
                max_tokens=50,
                temperature=0.1
            )
            
            return bool(response and response.choices)
            
        except Exception as e:
            print(f"⚠️ API test failed: {e}")
            return False
    
    async def generate_code(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate code using the active mode"""
        if not self.initialized:
            raise RuntimeError("Generator not initialized. Call initialize() first.")
        
        try:
            if self.active_mode == QwenMode.INFERENCE_API:
                return await self._generate_with_api(prompt, max_tokens, temperature, **kwargs)
            elif self.active_mode == QwenMode.LOCAL_MODEL:
                return await self._generate_with_local(prompt, max_tokens, temperature, **kwargs)
            else:
                raise RuntimeError(f"Unknown active mode: {self.active_mode}")
                
        except Exception as e:
            print(f"❌ Generation failed with {self.active_mode.value}: {e}")
            
            # Try fallback if enabled
            if settings.ENABLE_LOCAL_QWEN_FALLBACK and self.active_mode == QwenMode.INFERENCE_API:
                print("🔄 Attempting fallback to local model...")
                return await self._attempt_fallback(prompt, max_tokens, temperature, **kwargs)
            
            raise
    
    async def _generate_with_api(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate using Inference API"""
        print(f"🌐 Generating with Inference API...")
        
        try:
            # Use chat completion format without model parameter (already set in client)
            response = self.inference_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            generated_text = response.choices[0].message.content if response.choices else ""
            
            return {
                "success": True,
                "generated_text": generated_text,
                "mode": "inference_api",
                "model": self.model_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "mode": "inference_api"
            }
    
    async def _generate_with_local(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate using local model"""
        print(f"💻 Generating with local model...")
        
        try:
            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    pad_token_id=self.tokenizer.eos_token_id,
                    **kwargs
                )
            
            # Decode response
            generated_text = self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )
            
            return {
                "success": True,
                "generated_text": generated_text,
                "mode": "local_model",
                "model": self.model_path if self.active_mode == QwenMode.LOCAL_MODEL else self.local_model_path,
                "device": str(self.device)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "mode": "local_model"
            }
    
    async def _attempt_fallback(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Attempt fallback to alternative generation method"""
        memory_info = await self._check_system_resources()
        
        if memory_info["can_load_small_model"] and not self.model:
            print("🔄 Initializing local model for fallback...")
            if await self._initialize_local_model(memory_info, use_large_model=False):
                return await self._generate_with_local(prompt, max_tokens, temperature, **kwargs)
        
        # If all else fails, return minimal response
        return {
            "success": False,
            "error": "All generation methods failed",
            "fallback_used": True
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current generator status"""
        return {
            "initialized": self.initialized,
            "active_mode": self.active_mode.value if self.active_mode else None,
            "configured_mode": self.mode.value,
            "large_model_path": self.model_path,
            "small_model_path": self.local_model_path,
            "has_inference_client": self.inference_client is not None,
            "has_local_model": self.model is not None,
            "settings": {
                "use_inference_api": settings.USE_QWEN_INFERENCE_API,
                "enable_fallback": settings.ENABLE_LOCAL_QWEN_FALLBACK
            }
        }
    
    def get_current_mode(self) -> Optional[str]:
        """Get the current active mode"""
        return self.active_mode.value if self.active_mode else None
    
    def get_current_model(self) -> Optional[str]:
        """Get the current model name"""
        return self.current_model_name
    
    def is_api_mode(self) -> bool:
        """Check if currently using API mode"""
        return self.active_mode == QwenMode.INFERENCE_API
    
    def is_local_mode(self) -> bool:
        """Check if currently using local model mode"""
        return self.active_mode == QwenMode.LOCAL_MODEL
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information"""
        return {
            "mode": self.get_current_mode(),
            "model_name": self.get_current_model(),
            "initialized": self.initialized,
            "api_available": self.inference_client is not None,
            "local_loaded": self.model is not None
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.model:
            del self.model
            self.model = None
        
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        
        if torch and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.initialized = False
        self.active_mode = None
        print("🧹 Qwen Generator cleanup completed")


    async def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Alias for generate_code for compatibility"""
        return await self.generate_code(prompt, max_tokens, temperature, **kwargs)


# Convenience function for creating generator with settings
def create_qwen_generator() -> ConfigurableQwenGenerator:
    """Create Qwen generator based on current settings"""
    if settings.USE_QWEN_INFERENCE_API:
        mode = QwenMode.INFERENCE_API
    else:
        mode = QwenMode.LOCAL_MODEL
    
    return ConfigurableQwenGenerator(mode=mode)


# Auto-mode generator
def create_auto_qwen_generator() -> ConfigurableQwenGenerator:
    """Create Qwen generator in auto mode"""
    return ConfigurableQwenGenerator(mode=QwenMode.AUTO)
