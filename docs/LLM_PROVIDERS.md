# LLM Providers Configuration Guide

## 📋 Overview

CodeBeGen supports multiple LLM providers for AI-powered code generation:

- **Google Gemini** - Single powerful model (Gemini 2.5 Pro / 2.0 Flash)
- **HuggingFace** - Multiple specialized models (Llama, Qwen, Starcoder, Mistral)
- **Hybrid Mode** - Use different providers for different tasks

This guide explains how to configure and use each provider.

---

## 🚀 Quick Start

### Option 1: Use Gemini (Recommended)

```bash
# .env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp
```

Get your API key: https://aistudio.google.com/app/apikey

### Option 2: Use HuggingFace

```bash
# .env
LLM_PROVIDER=huggingface
HF_TOKEN=your_hf_token_here
FORCE_INFERENCE_MODE=true
```

Get your token: https://huggingface.co/settings/tokens

---

## 🔧 Configuration Options

### Global Provider Selection

Set your primary LLM provider:

```bash
LLM_PROVIDER=gemini  # Options: huggingface, gemini
```

### Task-Specific Overrides

Use different providers for different tasks:

```bash
# Use HuggingFace by default, but Gemini for code generation
LLM_PROVIDER=huggingface
CODE_GENERATION_PROVIDER=gemini

# Available overrides:
SCHEMA_EXTRACTION_PROVIDER=huggingface
CODE_GENERATION_PROVIDER=gemini
CODE_REVIEW_PROVIDER=gemini
DOCUMENTATION_PROVIDER=gemini
```

### Hybrid Mode

```bash
ENABLE_HYBRID_LLM_MODE=true
```

---

## 🤖 Provider Details

### Google Gemini Provider

**Advantages:**
- ✅ Single model handles all tasks (simpler architecture)
- ✅ Large context window (1M tokens)
- ✅ Fast response times
- ✅ High-quality code generation
- ✅ No local model downloads required
- ✅ Latest AI capabilities

**Configuration:**

```bash
# Required
GOOGLE_API_KEY=your_api_key

# Model Selection
GEMINI_MODEL=gemini-2.0-flash-exp  # Fast, cheaper
# or
GEMINI_MODEL=gemini-2.5-pro  # Better quality, more expensive

# Generation Parameters
GEMINI_TEMPERATURE=0.7  # 0.0-1.0, higher = more creative
GEMINI_MAX_OUTPUT_TOKENS=8192  # Maximum tokens
GEMINI_TOP_P=0.95
GEMINI_TOP_K=40

# Safety Settings (BLOCK_NONE for code generation)
GEMINI_SAFETY_HARASSMENT=BLOCK_NONE
GEMINI_SAFETY_HATE_SPEECH=BLOCK_NONE
GEMINI_SAFETY_SEXUALLY_EXPLICIT=BLOCK_NONE
GEMINI_SAFETY_DANGEROUS_CONTENT=BLOCK_NONE
```

**Cost Estimate:**
- Input: $1.25 per 1M tokens
- Output: $5.00 per 1M tokens
- Typical generation: $0.05-$0.15 per project

---

### HuggingFace Provider

**Advantages:**
- ✅ Free tier available
- ✅ Specialized models for each task
- ✅ Can run locally (if you have resources)
- ✅ Full control over model selection

**Models Used:**
- **Schema Extraction**: Llama-3.1-8B
- **Code Generation**: Qwen2.5-Coder-32B
- **Code Review**: Starcoder2-15B
- **Documentation**: Mistral-7B-Instruct

**Configuration:**

```bash
# Required
HF_TOKEN=your_hf_token

# Model Paths
LLAMA_MODEL_PATH=meta-llama/Llama-3.1-8B
QWEN_LARGE_MODEL_PATH=Qwen/Qwen3-Coder-480B-A35B-Instruct
STARCODER_MODEL_PATH=bigcode/starcoder2-15b
MISTRAL_MODEL_PATH=mistralai/Mistral-7B-Instruct-v0.1

# Inference Mode (Recommended)
FORCE_INFERENCE_MODE=true
USE_QWEN_INFERENCE_API=true
ENABLE_LOCAL_QWEN_FALLBACK=false
```

**Cost:**
- Free tier: Limited inference calls per month
- Pro: $9/month for faster inference

---

## 📊 Provider Comparison

| Feature | Gemini | HuggingFace |
|---------|--------|-------------|
| **Setup Complexity** | ⭐ Simple | ⭐⭐⭐ Complex |
| **Number of Models** | 1 | 4 |
| **Context Window** | 1M tokens | 4-32K tokens |
| **Speed** | ⚡⚡⚡ Fast | ⚡⚡ Moderate |
| **Quality** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Good |
| **Free Tier** | ❌ No | ✅ Yes (limited) |
| **Local Execution** | ❌ No | ✅ Yes (memory intensive) |
| **Best For** | Production | Development/Testing |

---

## 🔀 Hybrid Mode Examples

### Example 1: Fast Schema + Quality Code

```bash
LLM_PROVIDER=huggingface
SCHEMA_EXTRACTION_PROVIDER=huggingface  # Fast with Llama
CODE_GENERATION_PROVIDER=gemini  # Quality with Gemini
```

### Example 2: Cost Optimization

```bash
LLM_PROVIDER=huggingface  # Free for most tasks
CODE_GENERATION_PROVIDER=gemini  # Pay only for code generation
GOOGLE_API_KEY=your_key
HF_TOKEN=your_token
```

### Example 3: Quality Focus

```bash
LLM_PROVIDER=gemini  # Gemini for everything
GEMINI_MODEL=gemini-2.5-pro  # Highest quality model
```

---

## 🧪 Testing Your Configuration

### Test Gemini Provider

```python
# test_gemini_manual.py
import asyncio
from app.services.llm_providers import GeminiProvider

async def test():
    provider = GeminiProvider()
    await provider.initialize()
    
    result = await provider.extract_schema(
        prompt="Create a blog platform with users and posts",
        context={"tech_stack": "fastapi_postgres"}
    )
    
    print(result)

asyncio.run(test())
```

### Test Provider Switching

```python
from app.services.llm_providers import LLMProviderFactory, LLMTask

async def test():
    # Get provider for code generation
    provider = await LLMProviderFactory.get_provider(LLMTask.CODE_GENERATION)
    info = await provider.get_provider_info()
    print(f"Using: {info['name']}")

asyncio.run(test())
```

### Check Active Configuration

```bash
curl http://localhost:8000/api/v1/generations/config/YOUR_USER_ID
```

---

## 🛠️ Troubleshooting

### Gemini Issues

**"GOOGLE_API_KEY not configured"**
- Get key from https://aistudio.google.com/app/apikey
- Add to `.env`: `GOOGLE_API_KEY=your_key`

**"Failed to parse JSON from response"**
- Check safety settings (should be BLOCK_NONE)
- Try lower temperature (0.3-0.5)
- Check model name is correct

**Rate limit errors**
- Reduce concurrent requests
- Use exponential backoff
- Consider upgrading API quota

### HuggingFace Issues

**"HF_TOKEN not configured"**
- Get token from https://huggingface.co/settings/tokens
- Add to `.env`: `HF_TOKEN=your_token`

**"Failed to load model"**
- Enable inference mode: `FORCE_INFERENCE_MODE=true`
- Check model paths are correct
- Verify HF token has proper permissions

**Out of memory errors**
- Use inference API: `USE_QWEN_INFERENCE_API=true`
- Disable local fallback: `ENABLE_LOCAL_QWEN_FALLBACK=false`
- Reduce `MAX_NEW_TOKENS`

---

## 📈 Performance Tips

### For Best Speed

```bash
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.0-flash-exp  # Faster than Pro
GEMINI_TEMPERATURE=0.4  # Lower = faster, more consistent
```

### For Best Quality

```bash
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-pro
GEMINI_TEMPERATURE=0.7
GEMINI_MAX_OUTPUT_TOKENS=8192
```

### For Cost Optimization

```bash
# Use HuggingFace for schema/review (free)
LLM_PROVIDER=huggingface
# Use Gemini only for code generation (quality matters most)
CODE_GENERATION_PROVIDER=gemini
GEMINI_MODEL=gemini-2.0-flash-exp  # Cheaper than Pro
```

---

## 🔐 Security Best Practices

1. **Never commit `.env` file**
   ```bash
   # Add to .gitignore
   .env
   .env.local
   ```

2. **Rotate API keys regularly**
   - Gemini: https://aistudio.google.com/app/apikey
   - HuggingFace: https://huggingface.co/settings/tokens

3. **Use environment-specific keys**
   ```bash
   # Development
   GOOGLE_API_KEY=dev_key
   # Production
   GOOGLE_API_KEY=prod_key
   ```

4. **Monitor API usage**
   - Set up billing alerts
   - Track generation costs
   - Implement rate limiting

---

## 📚 Additional Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [HuggingFace Inference API](https://huggingface.co/docs/api-inference/index)
- [CodeBeGen API Documentation](./API_DOCUMENTATION.md)
- [Deployment Guide](./DEPLOYMENT.md)

---

## 🆘 Support

Having issues? Check:

1. [Troubleshooting section](#-troubleshooting) above
2. [GitHub Issues](https://github.com/SamuelOshin/codebegen_be/issues)
3. Configuration examples in `.env.example`
4. Server logs in `logs/` directory

---

**Last Updated**: October 14, 2025  
**Version**: 2.0.0 (Gemini Integration)
