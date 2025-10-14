"""
Tests for Gemini Generator
Tests both success and error scenarios for production readiness
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

# Import the Gemini generator
from ai_models.gemini_generator import GeminiGenerator


class TestGeminiGeneratorSuccess:
    """Test successful generation scenarios"""
    
    @pytest.fixture
    def mock_genai(self):
        """Mock google.generativeai module"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', True):
            with patch('ai_models.gemini_generator.genai') as mock_genai:
                # Mock the model and chat
                mock_model = MagicMock()
                mock_chat = MagicMock()
                mock_response = MagicMock()
                
                # Setup response with valid JSON
                mock_response.text = '''```json
{
  "files": {
    "main.py": "from fastapi import FastAPI\\n\\napp = FastAPI()\\n\\n@app.get('/')\\nasync def root():\\n    return {'message': 'Hello'}",
    "requirements.txt": "fastapi>=0.104.0\\nuvicorn>=0.24.0",
    "README.md": "# Test Project\\n\\nA test FastAPI project."
  }
}
```'''
                
                mock_chat.send_message.return_value = mock_response
                mock_model.start_chat.return_value = mock_chat
                mock_genai.GenerativeModel.return_value = mock_model
                
                yield mock_genai
    
    @pytest.mark.asyncio
    async def test_initialization_with_api_key(self, mock_genai):
        """Test successful initialization with API key"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            generator = GeminiGenerator()
            
            # Verify configure was called with API key
            mock_genai.configure.assert_called_once_with(api_key='test-key')
            
            # Verify model was created
            assert generator.model is not None
    
    @pytest.mark.asyncio
    async def test_load_method(self, mock_genai):
        """Test load method completes successfully"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            generator = GeminiGenerator()
            await generator.load()
            
            # Should complete without error
            assert generator.model is not None
    
    @pytest.mark.asyncio
    async def test_generate_project_success(self, mock_genai):
        """Test successful project generation"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            generator = GeminiGenerator()
            await generator.load()
            
            # Generate a project
            prompt = "Create a simple FastAPI todo app"
            schema = {
                "entities": [{"name": "Todo", "fields": []}],
                "endpoints": []
            }
            context = {
                "domain": "productivity",
                "tech_stack": "fastapi_postgres"
            }
            
            files = await generator.generate_project(prompt, schema, context)
            
            # Verify files were generated
            assert isinstance(files, dict)
            assert len(files) > 0
            assert "main.py" in files
            assert "requirements.txt" in files
            assert "README.md" in files
    
    @pytest.mark.asyncio
    async def test_generate_project_with_enhanced_prompts(self, mock_genai):
        """Test project generation with enhanced prompts"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            generator = GeminiGenerator()
            await generator.load()
            
            architecture_prompt = "Design a modular FastAPI app"
            implementation_prompt = "Implement user authentication"
            schema = {"entities": [], "endpoints": []}
            
            files = await generator.generate_project_enhanced(
                architecture_prompt=architecture_prompt,
                implementation_prompt=implementation_prompt,
                schema=schema,
                domain="general",
                tech_stack="fastapi_postgres"
            )
            
            # Verify files were generated
            assert isinstance(files, dict)
            assert len(files) > 0
    
    @pytest.mark.asyncio
    async def test_modify_project_success(self, mock_genai):
        """Test successful project modification"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            generator = GeminiGenerator()
            await generator.load()
            
            existing_files = {
                "main.py": "from fastapi import FastAPI\napp = FastAPI()"
            }
            modification_prompt = "Add a /health endpoint"
            
            modified_files = await generator.modify_project(
                existing_files, 
                modification_prompt
            )
            
            # Verify modification succeeded
            assert isinstance(modified_files, dict)
            assert len(modified_files) > 0
    
    @pytest.mark.asyncio
    async def test_parse_json_without_markdown(self, mock_genai):
        """Test parsing JSON output without markdown markers"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            generator = GeminiGenerator()
            
            output = '{"files": {"test.py": "print(\\"hello\\")"}}'
            files = generator._parse_generated_output(output)
            
            assert isinstance(files, dict)
            assert "test.py" in files
    
    @pytest.mark.asyncio
    async def test_parse_json_with_markdown(self, mock_genai):
        """Test parsing JSON output with markdown code blocks"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            generator = GeminiGenerator()
            
            output = '''```json
{"files": {"test.py": "print(\\"hello\\")"}}
```'''
            files = generator._parse_generated_output(output)
            
            assert isinstance(files, dict)
            assert "test.py" in files
    
    @pytest.mark.asyncio
    async def test_cleanup(self, mock_genai):
        """Test cleanup method"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            generator = GeminiGenerator()
            await generator.load()
            
            # Should not raise any errors
            await generator.cleanup()


class TestGeminiGeneratorErrors:
    """Test error scenarios and edge cases"""
    
    @pytest.mark.asyncio
    async def test_initialization_without_api_key(self):
        """Test initialization fails gracefully without API key"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', True):
            with patch.dict('os.environ', {}, clear=True):
                generator = GeminiGenerator()
                
                # Should initialize but model should be None
                assert generator.model is None
    
    @pytest.mark.asyncio
    async def test_initialization_without_genai_library(self):
        """Test initialization when google-generativeai is not installed"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            
            # Should initialize but model should be None
            assert generator.model is None
    
    @pytest.mark.asyncio
    async def test_load_without_genai_library(self):
        """Test load method when library is not available"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            await generator.load()
            
            # Should complete without error
            assert generator.model is None
    
    @pytest.mark.asyncio
    async def test_generate_project_api_error(self):
        """Test generation with API error"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', True):
            with patch('ai_models.gemini_generator.genai') as mock_genai:
                # Mock API error
                mock_model = MagicMock()
                mock_chat = MagicMock()
                mock_chat.send_message.side_effect = Exception("API Error")
                mock_model.start_chat.return_value = mock_chat
                mock_genai.GenerativeModel.return_value = mock_model
                
                with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
                    generator = GeminiGenerator()
                    await generator.load()
                    
                    # Should fall back to fallback generation
                    files = await generator.generate_project(
                        "Create an app",
                        {"entities": []},
                        {"domain": "general"}
                    )
                    
                    # Should return fallback files
                    assert isinstance(files, dict)
                    assert "main.py" in files
    
    @pytest.mark.asyncio
    async def test_generate_project_without_model(self):
        """Test generation when model is not available"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            
            files = await generator.generate_project(
                "Create an app",
                {"entities": []},
                {"domain": "general", "name": "test_project"}
            )
            
            # Should return fallback files
            assert isinstance(files, dict)
            assert "main.py" in files
            assert "test_project" in files["main.py"]
    
    @pytest.mark.asyncio
    async def test_parse_invalid_json(self):
        """Test parsing invalid JSON output"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            
            # Invalid JSON
            output = '{"files": {"test.py": "unclosed string'
            files = generator._parse_generated_output(output)
            
            # Should return fallback files
            assert isinstance(files, dict)
            assert "main.py" in files
    
    @pytest.mark.asyncio
    async def test_parse_malformed_output(self):
        """Test parsing completely malformed output"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            
            output = "This is not JSON at all"
            files = generator._parse_generated_output(output)
            
            # Should return fallback files
            assert isinstance(files, dict)
            assert len(files) > 0
    
    @pytest.mark.asyncio
    async def test_modify_project_api_error(self):
        """Test project modification with API error"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', True):
            with patch('ai_models.gemini_generator.genai') as mock_genai:
                # Mock API error
                mock_model = MagicMock()
                mock_chat = MagicMock()
                mock_chat.send_message.side_effect = Exception("API Error")
                mock_model.start_chat.return_value = mock_chat
                mock_genai.GenerativeModel.return_value = mock_model
                
                with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
                    generator = GeminiGenerator()
                    
                    result = await generator.modify_project(
                        {"main.py": "code"},
                        "Add feature"
                    )
                    
                    # Should return empty dict (fallback)
                    assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_modify_project_without_model(self):
        """Test modification when model is not available"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            
            result = await generator.modify_project(
                {"main.py": "code"},
                "Add feature"
            )
            
            # Should return empty dict (fallback)
            assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_api_rate_limit_handling(self):
        """Test handling of rate limit errors"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', True):
            with patch('ai_models.gemini_generator.genai') as mock_genai:
                # Mock rate limit error
                mock_model = MagicMock()
                mock_chat = MagicMock()
                mock_chat.send_message.side_effect = Exception("Rate limit exceeded")
                mock_model.start_chat.return_value = mock_chat
                mock_genai.GenerativeModel.return_value = mock_model
                
                with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
                    generator = GeminiGenerator()
                    
                    files = await generator.generate_project(
                        "Create app",
                        {"entities": []},
                        {"domain": "general"}
                    )
                    
                    # Should handle gracefully with fallback
                    assert isinstance(files, dict)
    
    @pytest.mark.asyncio
    async def test_invalid_response_format(self):
        """Test handling of invalid response format from API"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', True):
            with patch('ai_models.gemini_generator.genai') as mock_genai:
                # Mock response with invalid format
                mock_model = MagicMock()
                mock_chat = MagicMock()
                mock_response = MagicMock()
                mock_response.text = "Just some text, not JSON"
                mock_chat.send_message.return_value = mock_response
                mock_model.start_chat.return_value = mock_chat
                mock_genai.GenerativeModel.return_value = mock_model
                
                with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
                    generator = GeminiGenerator()
                    await generator.load()
                    
                    files = await generator.generate_project(
                        "Create app",
                        {"entities": []},
                        {"domain": "general"}
                    )
                    
                    # Should handle with fallback
                    assert isinstance(files, dict)
                    assert "main.py" in files


class TestGeminiGeneratorEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_empty_prompt(self):
        """Test generation with empty prompt"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            
            files = await generator.generate_project(
                "",
                {"entities": []},
                {"domain": "general", "name": "empty_project"}
            )
            
            # Should still return valid files
            assert isinstance(files, dict)
            assert len(files) > 0
    
    @pytest.mark.asyncio
    async def test_very_large_schema(self):
        """Test generation with very large schema"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            
            # Create a large schema
            large_schema = {
                "entities": [
                    {"name": f"Entity{i}", "fields": [{"name": f"field{j}", "type": "str"} for j in range(20)]}
                    for i in range(50)
                ]
            }
            
            files = await generator.generate_project(
                "Create app",
                large_schema,
                {"domain": "general"}
            )
            
            # Should handle gracefully
            assert isinstance(files, dict)
    
    @pytest.mark.asyncio
    async def test_special_characters_in_prompt(self):
        """Test generation with special characters"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            
            prompt = "Create app with 'quotes' and \"double quotes\" and \n newlines"
            files = await generator.generate_project(
                prompt,
                {"entities": []},
                {"domain": "general"}
            )
            
            # Should handle gracefully
            assert isinstance(files, dict)
    
    @pytest.mark.asyncio
    async def test_concurrent_generations(self):
        """Test multiple concurrent generation requests"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            
            # Run multiple generations concurrently
            tasks = [
                generator.generate_project(
                    f"Create app {i}",
                    {"entities": []},
                    {"domain": "general", "name": f"project_{i}"}
                )
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should complete successfully
            assert len(results) == 5
            for files in results:
                assert isinstance(files, dict)
                assert len(files) > 0
    
    @pytest.mark.asyncio
    async def test_cleanup_multiple_times(self):
        """Test calling cleanup multiple times"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', False):
            generator = GeminiGenerator()
            
            # Should not raise error
            await generator.cleanup()
            await generator.cleanup()
            await generator.cleanup()


class TestGeminiGeneratorIntegration:
    """Integration tests for Gemini generator"""
    
    @pytest.mark.asyncio
    async def test_full_generation_workflow(self):
        """Test complete generation workflow"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', True):
            with patch('ai_models.gemini_generator.genai') as mock_genai:
                # Setup complete mock
                mock_model = MagicMock()
                mock_chat = MagicMock()
                mock_response = MagicMock()
                mock_response.text = '''```json
{
  "files": {
    "app/main.py": "from fastapi import FastAPI\\napp = FastAPI()",
    "app/models/user.py": "from sqlalchemy import Column\\nclass User: pass",
    "app/schemas/user.py": "from pydantic import BaseModel\\nclass UserSchema(BaseModel): pass",
    "requirements.txt": "fastapi\\nsqlalchemy\\npydantic",
    "README.md": "# Test App",
    "tests/test_main.py": "def test_root(): pass"
  }
}
```'''
                mock_chat.send_message.return_value = mock_response
                mock_model.start_chat.return_value = mock_chat
                mock_genai.GenerativeModel.return_value = mock_model
                
                with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
                    generator = GeminiGenerator()
                    await generator.load()
                    
                    # Generate project
                    files = await generator.generate_project(
                        "Create a user management API",
                        {
                            "entities": [{"name": "User", "fields": []}],
                            "endpoints": ["/users"]
                        },
                        {
                            "domain": "general",
                            "tech_stack": "fastapi_postgres"
                        }
                    )
                    
                    # Verify complete project structure
                    assert "app/main.py" in files
                    assert "app/models/user.py" in files
                    assert "app/schemas/user.py" in files
                    assert "requirements.txt" in files
                    assert "README.md" in files
                    assert "tests/test_main.py" in files
                    
                    # Cleanup
                    await generator.cleanup()
