#!/usr/bin/env python3
"""
Debug test to see what Qwen Generator is actually generating
"""

import asyncio
import json
from ai_models.qwen_generator import QwenGenerator


async def debug_qwen_generation():
    """Debug Qwen generation with detailed output"""
    print("🔍 Debugging Qwen Generation...")
    
    try:
        # Initialize Qwen Generator
        qwen = QwenGenerator("Qwen/Qwen2.5-Coder-7B-Instruct")
        await qwen.load()
        
        # Test with a very simple prompt
        prompt = "Create a simple FastAPI hello world endpoint"
        schema = {
            "entities": [],
            "operations": ["get"],
            "tech_stack": "fastapi"
        }
        context = {
            "domain": "hello_world",
            "tech_stack": "fastapi"
        }
        
        print(f"📝 Using prompt: {prompt}")
        
        # Check if we have HF client
        if hasattr(qwen, 'client') and qwen.client:
            print("✅ HF Client available - will use Inference API")
            
            # Format prompt
            formatted_prompt = qwen._format_generation_prompt(prompt, schema, context)
            print(f"📋 Formatted prompt (first 200 chars):")
            print(formatted_prompt[:200] + "...")
            
            # Generate with HF
            print("\n🚀 Calling HF Inference API...")
            output = await qwen._generate_with_hf(formatted_prompt)
            
            print(f"\n📖 Raw HF Output length: {len(output)} chars")
            print(f"📖 Raw HF Output (first 500 chars):")
            print("=" * 50)
            print(output[:500] + "..." if len(output) > 500 else output)
            print("=" * 50)
            
            # Show the last part too
            if len(output) > 500:
                print(f"📖 Raw HF Output (last 200 chars):")
                print("=" * 50)
                print("..." + output[-200:])
                print("=" * 50)
            
            # Try to parse output
            print("\n🔍 Parsing output...")
            files = qwen._parse_generated_output(output)
            print(f"📁 Parsed files: {list(files.keys())}")
            
            # Show file contents if any
            for filename, content in files.items():
                print(f"\n📄 {filename}:")
                print(content[:200] + "..." if len(content) > 200 else content)
            
        else:
            print("❌ No HF Client - using fallback")
            
        return True
        
    except Exception as e:
        print(f"❌ Error in debug: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    success = await debug_qwen_generation()
    print(f"\n🎯 Debug test: {'✅ COMPLETED' if success else '❌ FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())
