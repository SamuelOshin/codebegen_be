"""
Test Suite for Gemini Provider

Tests the GeminiProvider implementation including initialization,
schema extraction, code generation, code review, and documentation generation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from app.services.llm_providers.gemini_provider import GeminiProvider
from app.services.llm_providers.base_provider import LLMTask


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    with patch('app.services.llm_providers.gemini_provider.settings') as mock:
        mock.GOOGLE_API_KEY = "test_api_key"
        mock.GEMINI_MODEL = "gemini-2.0-flash-exp"
        mock.GEMINI_TEMPERATURE = 0.7
        mock.GEMINI_MAX_OUTPUT_TOKENS = 8192
        mock.GEMINI_TOP_P = 0.95
        mock.GEMINI_TOP_K = 40
        yield mock


@pytest.fixture
def mock_genai():
    """Mock google.generativeai module"""
    with patch('app.services.llm_providers.gemini_provider.genai') as mock:
        mock.configure = Mock()
        mock.types.GenerationConfig = Mock()
        mock.types.HarmCategory = Mock()
        mock.types.HarmBlockThreshold = Mock()
        mock.GenerativeModel = Mock()
        yield mock


@pytest.fixture
def gemini_provider():
    """Create GeminiProvider instance for testing"""
    return GeminiProvider()


class TestGeminiProviderInitialization:
    """Test provider initialization"""
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, gemini_provider, mock_settings, mock_genai):
        """Test successful initialization"""
        # Mock model
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Initialize
        await gemini_provider.initialize()
        
        # Verify
        assert gemini_provider.initialized is True
        assert gemini_provider.model is not None
        mock_genai.configure.assert_called_once_with(api_key="test_api_key")
    
    @pytest.mark.asyncio
    async def test_initialization_no_api_key(self, gemini_provider, mock_genai):
        """Test initialization fails without API key"""
        with patch('app.services.llm_providers.gemini_provider.settings') as mock_settings:
            mock_settings.GOOGLE_API_KEY = None
            
            with pytest.raises(ValueError, match="GOOGLE_API_KEY not configured"):
                await gemini_provider.initialize()
    
    @pytest.mark.asyncio
    async def test_initialization_already_initialized(self, gemini_provider, mock_settings, mock_genai):
        """Test that re-initialization is skipped"""
        # First initialization
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        await gemini_provider.initialize()
        
        # Reset mock
        mock_genai.configure.reset_mock()
        
        # Second initialization should skip
        await gemini_provider.initialize()
        mock_genai.configure.assert_not_called()


class TestSchemaExtraction:
    """Test schema extraction functionality"""
    
    @pytest.mark.asyncio
    async def test_extract_schema_success(self, gemini_provider, mock_settings, mock_genai):
        """Test successful schema extraction"""
        # Setup
        gemini_provider.initialized = True
        
        mock_response = Mock()
        mock_response.text = '''
        {
            "entities": [
                {
                    "name": "User",
                    "description": "User model",
                    "fields": [
                        {"name": "id", "type": "integer", "required": true},
                        {"name": "email", "type": "string", "required": true}
                    ],
                    "relationships": []
                }
            ],
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "GET",
                    "description": "List users",
                    "entity": "User"
                }
            ],
            "tech_stack": "fastapi_postgres"
        }
        '''
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        gemini_provider.model = mock_model
        
        # Execute
        result = await gemini_provider.extract_schema(
            prompt="Create a user management system",
            context={"tech_stack": "fastapi_postgres"}
        )
        
        # Verify
        assert "entities" in result
        assert len(result["entities"]) == 1
        assert result["entities"][0]["name"] == "User"
        assert "endpoints" in result
        assert len(result["endpoints"]) == 1
    
    @pytest.mark.asyncio
    async def test_extract_schema_with_markdown(self, gemini_provider, mock_settings, mock_genai):
        """Test schema extraction handles markdown code blocks"""
        gemini_provider.initialized = True
        
        mock_response = Mock()
        mock_response.text = '''```json
        {
            "entities": [{"name": "Product"}],
            "endpoints": [],
            "tech_stack": "fastapi_postgres"
        }
        ```'''
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        gemini_provider.model = mock_model
        
        result = await gemini_provider.extract_schema(
            prompt="Create a product catalog",
            context={}
        )
        
        assert "entities" in result
        assert result["entities"][0]["name"] == "Product"


class TestCodeGeneration:
    """Test code generation functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_code_success(self, gemini_provider, mock_settings, mock_genai):
        """Test successful code generation"""
        gemini_provider.initialized = True
        
        mock_response = Mock()
        mock_response.text = '''
        {
            "main.py": "from fastapi import FastAPI\\n\\napp = FastAPI()",
            "app/__init__.py": "",
            "app/models/user.py": "from sqlalchemy import Column, Integer, String",
            "requirements.txt": "fastapi==0.104.1\\nuvicorn==0.24.0"
        }
        '''
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        gemini_provider.model = mock_model
        
        schema = {
            "entities": [{"name": "User", "fields": []}],
            "endpoints": []
        }
        
        result = await gemini_provider.generate_code(
            prompt="Create a user API",
            schema=schema,
            context={"tech_stack": "fastapi_postgres"}
        )
        
        assert "main.py" in result
        assert "app/models/user.py" in result
        assert "requirements.txt" in result
        assert "fastapi" in result["main.py"]


class TestCodeReview:
    """Test code review functionality"""
    
    @pytest.mark.asyncio
    async def test_review_code_success(self, gemini_provider, mock_settings, mock_genai):
        """Test successful code review"""
        gemini_provider.initialized = True
        
        mock_response = Mock()
        mock_response.text = '''
        {
            "issues": [
                {
                    "file": "main.py",
                    "line": 10,
                    "severity": "medium",
                    "category": "security",
                    "message": "Missing input validation",
                    "code": "NO_INPUT_VALIDATION"
                }
            ],
            "suggestions": [
                {
                    "file": "main.py",
                    "category": "improvement",
                    "message": "Add type hints"
                }
            ],
            "scores": {
                "security": 0.7,
                "maintainability": 0.85,
                "performance": 0.9,
                "overall": 0.82
            },
            "summary": "Code quality is good with minor security concerns"
        }
        '''
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        gemini_provider.model = mock_model
        
        files = {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()"
        }
        
        result = await gemini_provider.review_code(files)
        
        assert "issues" in result
        assert len(result["issues"]) == 1
        assert result["issues"][0]["severity"] == "medium"
        assert "scores" in result
        assert result["scores"]["overall"] == 0.82
    
    @pytest.mark.asyncio
    async def test_review_code_failure_returns_default(self, gemini_provider, mock_settings, mock_genai):
        """Test code review returns default scores on failure"""
        gemini_provider.initialized = True
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(side_effect=Exception("API Error"))
        gemini_provider.model = mock_model
        
        files = {"main.py": "code"}
        
        result = await gemini_provider.review_code(files)
        
        # Should return default values
        assert "scores" in result
        assert result["scores"]["overall"] == 0.7
        assert "summary" in result


class TestDocumentationGeneration:
    """Test documentation generation functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_documentation_success(self, gemini_provider, mock_settings, mock_genai):
        """Test successful documentation generation"""
        gemini_provider.initialized = True
        
        mock_model = Mock()
        
        # Mock responses for each documentation type
        readme_response = Mock(text="# Project\n\nThis is a test project")
        api_response = Mock(text="# API Documentation\n\n## Endpoints")
        setup_response = Mock(text="# Setup Guide\n\n## Installation")
        
        mock_model.generate_content_async = AsyncMock(
            side_effect=[readme_response, api_response, setup_response]
        )
        gemini_provider.model = mock_model
        
        files = {"main.py": "code"}
        schema = {"entities": [], "endpoints": []}
        context = {"tech_stack": "fastapi_postgres"}
        
        result = await gemini_provider.generate_documentation(files, schema, context)
        
        assert "README.md" in result
        assert "API_DOCUMENTATION.md" in result
        assert "SETUP_GUIDE.md" in result
        assert "# Project" in result["README.md"]


class TestProviderInfo:
    """Test provider information"""
    
    @pytest.mark.asyncio
    async def test_get_provider_info(self, gemini_provider, mock_settings):
        """Test getting provider information"""
        gemini_provider.initialized = True
        
        info = await gemini_provider.get_provider_info()
        
        assert info["name"] == "GeminiProvider"
        assert info["type"] == "gemini"
        assert info["initialized"] is True
        assert "schema_extraction" in info["capabilities"]
        assert "code_generation" in info["capabilities"]
        assert info["unified_model"] is True


class TestJSONExtraction:
    """Test JSON extraction helper"""
    
    def test_extract_json_clean(self, gemini_provider):
        """Test extracting clean JSON"""
        response = '{"key": "value"}'
        result = gemini_provider._extract_json(response)
        assert result == {"key": "value"}
    
    def test_extract_json_with_markdown(self, gemini_provider):
        """Test extracting JSON from markdown code block"""
        response = '''```json
        {"key": "value"}
        ```'''
        result = gemini_provider._extract_json(response)
        assert result == {"key": "value"}
    
    def test_extract_json_with_text_around(self, gemini_provider):
        """Test extracting JSON with surrounding text"""
        response = 'Here is the JSON: {"key": "value"} as requested'
        result = gemini_provider._extract_json(response)
        assert result == {"key": "value"}
    
    def test_extract_json_invalid(self, gemini_provider):
        """Test extracting invalid JSON raises error"""
        response = 'This is not JSON'
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            gemini_provider._extract_json(response)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
