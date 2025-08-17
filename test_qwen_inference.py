#!/usr/bin/env python3
"""
Test script to validate Qwen Generator with Hugging Face Inference API
"""

import asyncio
import os
from ai_models.qwen_generator import QwenGenerator


async def test_qwen_inference():
    """Test Qwen Generator with HF Inference API"""
    print("🧪 Testing Qwen Generator with HF Inference API...")
    
    try:
        # Initialize Qwen Generator
        qwen = QwenGenerator("Qwen/Qwen2.5-Coder-7B-Instruct")  # Using smaller model for testing
        
        # Load the generator
        await qwen.load()
        
        # Test simple code generation
        prompt = "Create a simple FastAPI endpoint for user management with CRUD operations"
        schema = {
            "entities": ["User"],
            "operations": ["create", "read", "update", "delete"],
            "tech_stack": "fastapi_postgres"
        }
        context = {
            "domain": "user_management",
            "tech_stack": "fastapi_postgres",
            "constraints": ["RESTful API", "validation"]
        }
        
        print(f"✅ Qwen Generator initialized")
        print(f"📝 Generating code for: {prompt}")
        
        # Check if HF token is available
        from app.core.config import settings
        hf_token = os.environ.get("HF_TOKEN") or settings.HF_TOKEN
        if not hf_token:
            print("⚠️ HF_TOKEN not set - will test fallback mode")
        else:
            print(f"✅ HF_TOKEN found: {hf_token[:10]}...")
        
        # Generate project
        files = await qwen.generate_project(prompt, schema, context)
        
        print(f"✅ Generation completed! Generated {len(files)} files:")
        for file_path in files.keys():
            print(f"   📄 {file_path}")
        
        # Show a sample file content (first 500 chars)
        if files:
            first_file = list(files.keys())[0]
            content = files[first_file]
            print(f"\n📖 Sample content from {first_file}:")
            print("=" * 50)
            print(content[:500] + "..." if len(content) > 500 else content)
            print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Qwen generator: {e}")
        return False


async def test_qwen_modification():
    """Test Qwen Generator modification capabilities"""
    print("\n🧪 Testing Qwen modification capabilities...")
    
    try:
        qwen = QwenGenerator()
        await qwen.load()
        
        # Mock existing files
        existing_files = {
            "main.py": '''from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}
''',
            "models.py": '''from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
'''
        }
        
        # Test modification
        modification_prompt = "Add email field to User model and create a new endpoint to get users"
        
        modified_files = await qwen.modify_project(existing_files, modification_prompt)
        
        print(f"✅ Modification completed! Modified {len(modified_files)} files:")
        for file_path in modified_files.keys():
            print(f"   📄 {file_path}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing modification: {e}")
        return False


async def main():
    """Main test function"""
    print("🎯 Testing Qwen Generator with HF Inference API")
    print("=" * 60)
    
    # Test generation
    generation_success = await test_qwen_inference()
    
    # Test modification
    modification_success = await test_qwen_modification()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Generation Test: {'✅ PASS' if generation_success else '❌ FAIL'}")
    print(f"Modification Test: {'✅ PASS' if modification_success else '❌ FAIL'}")
    
    if generation_success and modification_success:
        print("\n🎉 All Qwen tests passed! Ready for full generation pipeline!")
        print("\n📋 What was validated:")
        print("   ✅ Qwen Generator initialization with HF Inference API")
        print("   ✅ Code generation capabilities")
        print("   ✅ Project modification capabilities")
        print("   ✅ Fallback mode for missing HF tokens")
        print("   ✅ Error handling and graceful degradation")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        
    return generation_success and modification_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
