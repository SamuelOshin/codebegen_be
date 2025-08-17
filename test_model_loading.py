#!/usr/bin/env python3
"""
Test script to validate AI model loading with PyTorch
"""

import asyncio
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from ai_models.model_loader import ModelLoader, ModelType


async def test_pytorch_installation():
    """Test PyTorch installation and basic functionality"""
    print("🧪 Testing PyTorch Installation...")
    
    try:
        print(f"✅ PyTorch version: {torch.__version__}")
        print(f"✅ CUDA available: {torch.cuda.is_available()}")
        print(f"✅ MPS available: {torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else False}")
        
        # Test basic tensor operations
        x = torch.randn(2, 3)
        y = torch.randn(3, 2)
        z = torch.mm(x, y)
        print(f"✅ Basic tensor operations working: {z.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ PyTorch test failed: {e}")
        return False


async def test_transformers_basic():
    """Test basic transformers functionality"""
    print("\n🧪 Testing Transformers Basic Functionality...")
    
    try:
        # Test with a small model to verify transformers works
        model_name = "microsoft/DialoGPT-small"
        print(f"Loading tokenizer for {model_name}...")
        
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        print(f"✅ Tokenizer loaded successfully")
        
        # Test tokenization
        text = "Hello, how are you?"
        tokens = tokenizer.encode(text)
        decoded = tokenizer.decode(tokens)
        print(f"✅ Tokenization working: '{text}' -> {len(tokens)} tokens -> '{decoded}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Transformers test failed: {e}")
        return False


async def test_model_loader():
    """Test our custom model loader"""
    print("\n🧪 Testing Custom Model Loader...")
    
    try:
        # Initialize model loader
        model_loader = ModelLoader()
        
        print("Available model types:")
        for model_type in ModelType:
            print(f"  - {model_type.value}")
        
        # Test getting model info
        for model_type in [ModelType.QWEN_GENERATOR, ModelType.LLAMA_PARSER]:
            try:
                model = await model_loader.get_model(model_type)
                print(f"✅ {model_type.value}: Model loaded successfully")
                print(f"   Type: {type(model)}")
                print(f"   Has generate method: {hasattr(model, 'generate')}")
            except Exception as e:
                print(f"⚠️ {model_type.value}: {e}")
        
        # Test model status
        status = model_loader.get_model_status()
        print(f"\nModel Status: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model loader test failed: {e}")
        return False


async def test_model_download():
    """Test downloading a small model from Hugging Face"""
    print("\n🧪 Testing Model Download from Hugging Face...")
    
    try:
        # Use a very small model for testing
        model_name = "distilbert-base-uncased"
        print(f"Attempting to download {model_name}...")
        
        # This will download the model if not cached
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name, 
            torch_dtype=torch.float32,  # Use float32 for CPU
            device_map="auto" if torch.cuda.is_available() else None
        )
        
        print(f"✅ Model downloaded and loaded successfully")
        print(f"   Model parameters: {sum(p.numel() for p in model.parameters()):,}")
        print(f"   Model device: {next(model.parameters()).device}")
        
        # Test inference
        text = "The future of AI is"
        inputs = tokenizer.encode(text, return_tensors="pt")
        
        with torch.no_grad():
            outputs = model.generate(
                inputs, 
                max_length=inputs.shape[1] + 10,
                do_sample=True,
                temperature=0.7,
                pad_token_id=tokenizer.eos_token_id
            )
        
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"✅ Model inference working: '{generated_text}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Model download test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🎯 Testing AI Model Loading Infrastructure")
    print("=" * 60)
    
    tests = [
        ("PyTorch Installation", test_pytorch_installation),
        ("Transformers Basic", test_transformers_basic),
        ("Model Loader", test_model_loader),
        ("Model Download", test_model_download)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All AI model infrastructure tests passed!")
        print("🚀 Ready for full model loading and generation testing!")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
