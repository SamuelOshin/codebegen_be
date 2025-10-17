# Gemini 2.5 Pro - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
pip install google-generativeai
```

### 2. Get API Key

Visit [Google AI Studio](https://makersuite.google.com/app/apikey) and create an API key.

### 3. Configure Environment

Add to `.env`:

```bash
GEMINI_API_KEY=your_api_key_here
USE_GEMINI=true
```

### 4. Test Installation

```bash
python -c "import google.generativeai; print('✓ Gemini ready')"
```

### 5. Run Tests

```bash
pytest tests/test_services/test_gemini_generator.py -v
```

## 💡 Usage Examples

### Basic Generation

```python
from ai_models.gemini_generator import GeminiGenerator

generator = GeminiGenerator()
await generator.load()

files = await generator.generate_project(
    prompt="Create a FastAPI app with user authentication",
    schema={
        "entities": [{"name": "User", "fields": [...]}]
    },
    context={
        "domain": "general",
        "tech_stack": "fastapi_postgres"
    }
)

print(f"Generated {len(files)} files")
```

### Using in AI Orchestrator

```python
from app.services.ai_orchestrator import ai_orchestrator
from app.core.config import settings

# Enable Gemini
settings.USE_GEMINI = True

# Initialize and use
await ai_orchestrator.initialize()
result = await ai_orchestrator.generate_project(request)
```

### Switch Between Providers

```python
# Use Gemini
settings.USE_GEMINI = True
gemini_result = await ai_orchestrator.generate_project(request)

# Use Qwen
settings.USE_GEMINI = False
qwen_result = await ai_orchestrator.generate_project(request)
```

## 🔍 Check Which Provider Is Being Used

```python
from app.core.config import settings

if settings.USE_GEMINI:
    print("Using: Gemini 2.5 Pro")
else:
    print("Using: Qwen")
```

## ⚙️ Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | None | Your Google Gemini API key |
| `GEMINI_MODEL_NAME` | `gemini-2.5-pro` | Model version to use |
| `USE_GEMINI` | `false` | Enable/disable Gemini |

## 🧪 Testing

```bash
# Test Gemini generator
pytest tests/test_services/test_gemini_generator.py -v

# Test AI orchestrator integration
pytest tests/test_services/test_ai_orchestrator_gemini.py -v

# Run all tests
pytest tests/test_services/test_gemini* -v

# With coverage
pytest tests/test_services/test_gemini_generator.py --cov --cov-report=html
```

## ⚠️ Common Issues

### Issue: "API key not found"
```bash
# Solution: Set the environment variable
export GEMINI_API_KEY=your_key_here
```

### Issue: "Module not found: google.generativeai"
```bash
# Solution: Install the package
pip install google-generativeai
```

### Issue: "Rate limit exceeded"
```bash
# Solution: Wait and retry, or upgrade quota
# The system will automatically fall back to templates
```

## 📊 Quick Comparison

| Feature | Gemini 2.5 Pro | Qwen 3-Coder |
|---------|---------------|--------------|
| Setup | API key only | API key or Local |
| Memory | Minimal | ~32GB (local) |
| Speed | 3-4s | Variable |
| Cost | Pay per use | Free (self-hosted) |

## 🎯 When to Use Gemini

✅ **Use Gemini when:**
- You want latest model capabilities
- Memory is limited (no local GPU needed)
- You need consistent availability
- You prefer managed infrastructure

❌ **Use Qwen when:**
- You have GPU resources available
- You want full control over the model
- You need offline operation
- You want to minimize API costs

## 📚 Next Steps

1. ✅ Complete quick setup above
2. 📖 Read full documentation: `docs/GEMINI_INTEGRATION.md`
3. 🧪 Run tests to verify everything works
4. 🚀 Start generating projects!

## 🆘 Need Help?

- 📖 Full docs: `docs/GEMINI_INTEGRATION.md`
- 🐛 Issues: [GitHub Issues](https://github.com/SamuelOshin/codebegen_be/issues)
- 💬 Community: [Discussions](https://github.com/SamuelOshin/codebegen_be/discussions)

---

**Ready to generate code with Gemini? Let's go! 🚀**
