#!/usr/bin/env python3
"""
Test HuggingFace Inference API directly to validate connection
"""

import asyncio
from huggingface_hub import InferenceClient
from app.core.config import settings

async def test_hf_api_direct():
    """Test HF Inference API directly"""
    print("🧪 Testing HuggingFace Inference API directly...")
    
    try:
        # Initialize client
        client = InferenceClient(
            model="Qwen/Qwen2.5-Coder-7B-Instruct",
            token=settings.HF_TOKEN
        )
        
        # Test simple generation
        prompt = "def hello_world():"
        
        print(f"📝 Testing with prompt: {prompt}")
        print(f"🔑 Using token: {settings.HF_TOKEN[:10]}...")
        
        # Try chat completion
        messages = [
            {"role": "user", "content": f"Complete this Python function: {prompt}"}
        ]
        
        response = client.chat_completion(
            messages=messages,
            max_tokens=100,
            temperature=0.7
        )
        
        print("✅ HF API Response received!")
        print(f"📖 Response: {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ HF API Error: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        return False

async def main():
    success = await test_hf_api_direct()
    if success:
        print("\n🎉 HuggingFace API connection successful!")
    else:
        print("\n⚠️ HuggingFace API connection failed - may need to upgrade to paid plan or check model availability")

if __name__ == "__main__":
    asyncio.run(main())
