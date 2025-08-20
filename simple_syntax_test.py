#!/usr/bin/env python3
"""
Simple syntax check for configurable_qwen_service
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing imports...")
    from app.services.configurable_qwen_service import ConfigurableQwenGenerator, QwenMode
    print("✅ Import successful!")
    
    # Try creating an instance
    print("Creating generator instance...")
    generator = ConfigurableQwenGenerator(mode=QwenMode.INFERENCE_API)
    print("✅ Generator created successfully!")
    
    # Check attributes
    print(f"Mode: {generator.mode}")
    print(f"Model path: {generator.model_path}")
    print(f"Local model path: {generator.local_model_path}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Other error: {e}")
    import traceback
    traceback.print_exc()
