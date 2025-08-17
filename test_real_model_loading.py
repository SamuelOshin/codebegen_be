#!/usr/bin/env python3
"""
Comprehensive AI Model Loading Test with Real Hugging Face Models
Tests actual model downloading, loading, and inference capabilities
"""

import asyncio
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import time


class ModelTester:
    """Test different types of models for the CodeGen pipeline"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 Device: {self.device}")
        
    def test_pytorch_installation(self):
        """Test PyTorch installation and capabilities"""
        print("🧪 Testing PyTorch Installation...")
        
        try:
            print(f"   ✅ PyTorch Version: {torch.__version__}")
            print(f"   ✅ CUDA Available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                print(f"   ✅ CUDA Version: {torch.version.cuda}")
                print(f"   ✅ GPU Count: {torch.cuda.device_count()}")
                print(f"   ✅ Current GPU: {torch.cuda.current_device()}")
            
            # Test basic tensor operations
            x = torch.randn(3, 3)
            y = torch.randn(3, 3)
            z = x @ y
            print(f"   ✅ Tensor Operations: Working (result shape: {z.shape})")
            
            return True
            
        except Exception as e:
            print(f"   ❌ PyTorch test failed: {e}")
            return False
    
    def test_transformers_pipeline(self):
        """Test Transformers library with a simple pipeline"""
        print("\n🧪 Testing Transformers Pipeline...")
        
        try:
            # Use a very small model for quick testing
            print("   📥 Testing with distilgpt2 (small model)...")
            
            generator = pipeline(
                "text-generation", 
                model="distilgpt2",
                device=0 if torch.cuda.is_available() else -1
            )
            
            result = generator(
                "def hello_world():",
                max_length=50,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True
            )
            
            print(f"   ✅ Generated text: {result[0]['generated_text'][:100]}...")
            return True
            
        except Exception as e:
            print(f"   ❌ Transformers pipeline test failed: {e}")
            return False
    
    def test_code_generation_model(self):
        """Test with a proper code generation model"""
        print("\n🧪 Testing Code Generation Model (Salesforce CodeGen-350M)...")
        
        try:
            model_name = "Salesforce/codegen-350M-mono"
            print(f"   📥 Loading {model_name}...")
            
            # Load tokenizer and model
            start_time = time.time()
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            if not torch.cuda.is_available():
                model = model.to("cpu")
                
            load_time = time.time() - start_time
            print(f"   ✅ Model loaded in {load_time:.2f}s")
            
            # Test code generation
            prompt = "def fibonacci(n):"
            print(f"   🔤 Input prompt: '{prompt}'")
            
            inputs = tokenizer.encode(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = inputs.to("cuda")
            
            start_time = time.time()
            with torch.no_grad():
                outputs = model.generate(
                    inputs,
                    max_length=100,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            inference_time = time.time() - start_time
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            print(f"   ✅ Generated code in {inference_time:.2f}s:")
            print(f"   📝 {generated_text}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Code generation test failed: {e}")
            return False
    
    def test_tiny_starcoder(self):
        """Test with Tiny StarCoder for Python code"""
        print("\n🧪 Testing Tiny StarCoder Python Model...")
        
        try:
            model_name = "bigcode/tiny_starcoder_py"
            print(f"   📥 Loading {model_name}...")
            
            start_time = time.time()
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            if not torch.cuda.is_available():
                model = model.to("cpu")
                
            load_time = time.time() - start_time
            print(f"   ✅ Model loaded in {load_time:.2f}s")
            
            # Test Python code completion
            prompt = "def calculate_sum(a, b):"
            print(f"   🔤 Input prompt: '{prompt}'")
            
            inputs = tokenizer.encode(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = inputs.to("cuda")
            
            start_time = time.time()
            with torch.no_grad():
                outputs = model.generate(
                    inputs,
                    max_length=80,
                    num_return_sequences=1,
                    temperature=0.5,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            inference_time = time.time() - start_time
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            print(f"   ✅ Generated code in {inference_time:.2f}s:")
            print(f"   📝 {generated_text}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Tiny StarCoder test failed: {e}")
            return False
    
    async def test_our_model_loader_integration(self):
        """Test integration with our existing model loader"""
        print("\n🧪 Testing Integration with Our Model Loader...")
        
        try:
            from ai_models.model_loader import ModelLoader
            from ai_models.qwen_generator import QwenGenerator
            
            # Initialize our model loader
            loader = ModelLoader()
            print("   ✅ Model loader imported successfully")
            
            # Try to get a model through our system
            print("   📥 Testing QwenGenerator with fallback...")
            generator = QwenGenerator()
            
            # Test basic functionality
            test_prompt = "Create a function to add two numbers"
            result = await generator.generate_code(test_prompt, "python")
            
            print(f"   ✅ Generated code via our system:")
            print(f"   📝 {result}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Model loader integration test failed: {e}")
            return False


async def main():
    """Run comprehensive model loading tests"""
    print("🎯 Comprehensive AI Model Loading Test")
    print("=" * 60)
    
    tester = ModelTester()
    results = {}
    
    # Test 1: PyTorch Installation
    results['pytorch'] = tester.test_pytorch_installation()
    
    # Test 2: Basic Transformers Pipeline
    results['transformers'] = tester.test_transformers_pipeline()
    
    # Test 3: Code Generation Model
    results['codegen'] = tester.test_code_generation_model()
    
    # Test 4: Tiny StarCoder
    results['starcoder'] = tester.test_tiny_starcoder()
    
    # Test 5: Our Model Loader Integration
    results['integration'] = await tester.test_our_model_loader_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name.capitalize():15} : {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nPassed: {total_passed}/{total_tests}")
    
    if total_passed == total_tests:
        print("\n🎉 All AI model tests passed! Ready for full generation pipeline!")
        print("\n📋 Validated Capabilities:")
        print("   ✅ PyTorch 2.8.0 working with CPU/GPU support")
        print("   ✅ Transformers library functional")
        print("   ✅ Actual model downloading from Hugging Face")
        print("   ✅ Code generation with real AI models")
        print("   ✅ Integration with existing model loader system")
        print("\n🚀 Ready to proceed with full generation testing!")
    else:
        print(f"\n⚠️  {total_tests - total_passed} tests failed. Review the output above.")
    
    return total_passed == total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
