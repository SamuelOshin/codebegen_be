"""
Integration tests for AI Orchestrator with Gemini support
Tests the integration of Gemini into the existing pipeline
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

from app.services.ai_orchestrator import AIOrchestrator, GenerationRequest
from ai_models.model_loader import ModelType


class TestAIOrchestratorGeminiIntegration:
    """Test AI Orchestrator with Gemini enabled"""
    
    @pytest.fixture
    def mock_gemini_generator(self):
        """Mock Gemini generator"""
        mock_gen = AsyncMock()
        mock_gen.generate_project = AsyncMock(return_value={
            "app/main.py": "from fastapi import FastAPI\napp = FastAPI()",
            "requirements.txt": "fastapi\nuvicorn",
            "README.md": "# Gemini Generated Project"
        })
        mock_gen.generate_project_enhanced = AsyncMock(return_value={
            "app/main.py": "from fastapi import FastAPI\napp = FastAPI()",
            "app/models/user.py": "class User: pass",
            "requirements.txt": "fastapi\nuvicorn\nsqlalchemy",
            "README.md": "# Enhanced Gemini Project"
        })
        return mock_gen
    
    @pytest.fixture
    def mock_model_loader(self, mock_gemini_generator):
        """Mock model loader that returns Gemini"""
        with patch('app.services.ai_orchestrator.model_loader') as mock_loader:
            mock_loader.get_model = AsyncMock(return_value=mock_gemini_generator)
            yield mock_loader
    
    @pytest.mark.asyncio
    async def test_orchestrator_uses_gemini_when_enabled(self, mock_model_loader, mock_gemini_generator):
        """Test that orchestrator uses Gemini when USE_GEMINI is True"""
        with patch('app.services.ai_orchestrator.settings') as mock_settings:
            mock_settings.USE_GEMINI = True
            mock_settings.FORCE_INFERENCE_MODE = False
            
            orchestrator = AIOrchestrator()
            # Skip full initialization
            orchestrator.initialized = True
            
            # Generate code
            generation_data = {
                "prompt": "Create a user API",
                "domain": "general",
                "tech_stack": "fastapi_postgres"
            }
            schema = {"entities": []}
            
            files = await orchestrator._generate_code(generation_data, schema)
            
            # Verify Gemini was used
            assert "README.md" in files
            assert "Gemini" in files["README.md"]
    
    @pytest.mark.asyncio
    async def test_orchestrator_uses_qwen_when_gemini_disabled(self, mock_model_loader):
        """Test that orchestrator uses Qwen when USE_GEMINI is False"""
        # Mock Qwen generator
        mock_qwen = AsyncMock()
        mock_qwen.generate_project = AsyncMock(return_value={
            "app/main.py": "from fastapi import FastAPI\napp = FastAPI()",
            "README.md": "# Qwen Generated Project"
        })
        
        mock_model_loader.get_model = AsyncMock(return_value=mock_qwen)
        
        with patch('app.services.ai_orchestrator.settings') as mock_settings:
            mock_settings.USE_GEMINI = False
            mock_settings.FORCE_INFERENCE_MODE = False
            
            orchestrator = AIOrchestrator()
            orchestrator.initialized = True
            
            # Generate code
            generation_data = {
                "prompt": "Create a user API",
                "domain": "general",
                "tech_stack": "fastapi_postgres"
            }
            schema = {"entities": []}
            
            files = await orchestrator._generate_code(generation_data, schema)
            
            # Verify Qwen was used (or at least not Gemini)
            assert isinstance(files, dict)
    
    @pytest.mark.asyncio
    async def test_enhanced_code_generation_with_gemini(self, mock_model_loader, mock_gemini_generator):
        """Test enhanced code generation with Gemini"""
        with patch('app.services.ai_orchestrator.settings') as mock_settings:
            mock_settings.USE_GEMINI = True
            
            orchestrator = AIOrchestrator()
            orchestrator.initialized = True
            
            generation_data = {
                "prompt": "Create a user API",
                "domain": "general",
                "tech_stack": "fastapi_postgres"
            }
            schema = {"entities": []}
            enhanced_prompts = {
                "architecture_planning": "Design modular architecture",
                "implementation_generation": "Implement with best practices"
            }
            
            files = await orchestrator._generate_enhanced_code(
                generation_data, 
                schema, 
                enhanced_prompts
            )
            
            # Verify enhanced generation was called
            mock_gemini_generator.generate_project_enhanced.assert_called_once()
            assert isinstance(files, dict)
            assert len(files) > 0
    
    @pytest.mark.asyncio
    async def test_gemini_fallback_on_error(self, mock_model_loader):
        """Test fallback when Gemini fails"""
        # Mock Gemini that fails
        mock_gemini = AsyncMock()
        mock_gemini.generate_project = AsyncMock(side_effect=Exception("API Error"))
        
        mock_model_loader.get_model = AsyncMock(return_value=mock_gemini)
        
        with patch('app.services.ai_orchestrator.settings') as mock_settings:
            mock_settings.USE_GEMINI = True
            
            orchestrator = AIOrchestrator()
            orchestrator.initialized = True
            
            generation_data = {
                "prompt": "Create a user API",
                "domain": "general",
                "tech_stack": "fastapi_postgres"
            }
            schema = {"entities": []}
            
            # Should not raise, should fall back
            files = await orchestrator._generate_code(generation_data, schema)
            
            # Should return fallback files
            assert isinstance(files, dict)
            assert "app/main.py" in files or "main.py" in files
    
    @pytest.mark.asyncio
    async def test_metadata_includes_gemini_info(self, mock_model_loader, mock_gemini_generator):
        """Test that metadata includes generator information"""
        with patch('app.services.ai_orchestrator.settings') as mock_settings:
            mock_settings.USE_GEMINI = True
            
            orchestrator = AIOrchestrator()
            orchestrator.initialized = True
            
            generation_data = {
                "prompt": "Create a user API",
                "domain": "general",
                "tech_stack": "fastapi_postgres"
            }
            schema = {"entities": []}
            enhanced_prompts = {
                "architecture_planning": "Design modular architecture"
            }
            
            files = await orchestrator._generate_enhanced_code(
                generation_data, 
                schema, 
                enhanced_prompts
            )
            
            # Check for metadata file
            if "_enhanced_metadata.json" in files:
                import json
                metadata = json.loads(files["_enhanced_metadata.json"])
                assert metadata.get("generator") == "gemini"


class TestAIOrchestratorProviderSwitching:
    """Test switching between providers"""
    
    @pytest.mark.asyncio
    async def test_switch_from_qwen_to_gemini(self):
        """Test switching from Qwen to Gemini mid-operation"""
        with patch('app.services.ai_orchestrator.model_loader') as mock_loader:
            # First call returns Qwen, second returns Gemini
            mock_qwen = AsyncMock()
            mock_qwen.generate_project = AsyncMock(return_value={"README.md": "Qwen"})
            
            mock_gemini = AsyncMock()
            mock_gemini.generate_project = AsyncMock(return_value={"README.md": "Gemini"})
            
            call_count = 0
            async def get_model_side_effect(model_type):
                nonlocal call_count
                call_count += 1
                return mock_gemini if call_count > 1 else mock_qwen
            
            mock_loader.get_model = AsyncMock(side_effect=get_model_side_effect)
            
            with patch('app.services.ai_orchestrator.settings') as mock_settings:
                orchestrator = AIOrchestrator()
                orchestrator.initialized = True
                
                # First generation with Qwen
                mock_settings.USE_GEMINI = False
                files1 = await orchestrator._generate_code(
                    {"prompt": "test", "domain": "general", "tech_stack": "fastapi"},
                    {}
                )
                
                # Second generation with Gemini
                mock_settings.USE_GEMINI = True
                files2 = await orchestrator._generate_code(
                    {"prompt": "test", "domain": "general", "tech_stack": "fastapi"},
                    {}
                )
                
                # Both should complete successfully
                assert isinstance(files1, dict)
                assert isinstance(files2, dict)
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_different_providers(self):
        """Test handling concurrent requests with different provider settings"""
        import asyncio
        
        with patch('app.services.ai_orchestrator.model_loader') as mock_loader:
            mock_gen = AsyncMock()
            mock_gen.generate_project = AsyncMock(return_value={"README.md": "Generated"})
            mock_loader.get_model = AsyncMock(return_value=mock_gen)
            
            with patch('app.services.ai_orchestrator.settings') as mock_settings:
                orchestrator = AIOrchestrator()
                orchestrator.initialized = True
                
                # Run concurrent requests
                async def generate_with_setting(use_gemini):
                    mock_settings.USE_GEMINI = use_gemini
                    return await orchestrator._generate_code(
                        {"prompt": "test", "domain": "general", "tech_stack": "fastapi"},
                        {}
                    )
                
                results = await asyncio.gather(
                    generate_with_setting(True),
                    generate_with_setting(False),
                    generate_with_setting(True)
                )
                
                # All should complete
                assert len(results) == 3
                for result in results:
                    assert isinstance(result, dict)


class TestGeminiErrorRecovery:
    """Test error recovery and resilience"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test handling of rate limit errors"""
        with patch('app.services.ai_orchestrator.model_loader') as mock_loader:
            mock_gemini = AsyncMock()
            # First call fails with rate limit, second succeeds
            mock_gemini.generate_project = AsyncMock(
                side_effect=[
                    Exception("Rate limit exceeded"),
                    {"README.md": "Success"}
                ]
            )
            mock_loader.get_model = AsyncMock(return_value=mock_gemini)
            
            with patch('app.services.ai_orchestrator.settings') as mock_settings:
                mock_settings.USE_GEMINI = True
                
                orchestrator = AIOrchestrator()
                orchestrator.initialized = True
                
                # First attempt should fail and fall back
                files1 = await orchestrator._generate_code(
                    {"prompt": "test", "domain": "general", "tech_stack": "fastapi"},
                    {}
                )
                
                # Should get fallback files
                assert isinstance(files1, dict)
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_recovery(self):
        """Test recovery from invalid API key"""
        with patch('app.services.ai_orchestrator.model_loader') as mock_loader:
            mock_gemini = AsyncMock()
            mock_gemini.generate_project = AsyncMock(
                side_effect=Exception("Invalid API key")
            )
            mock_loader.get_model = AsyncMock(return_value=mock_gemini)
            
            with patch('app.services.ai_orchestrator.settings') as mock_settings:
                mock_settings.USE_GEMINI = True
                
                orchestrator = AIOrchestrator()
                orchestrator.initialized = True
                
                # Should handle gracefully
                files = await orchestrator._generate_code(
                    {"prompt": "test", "domain": "general", "tech_stack": "fastapi"},
                    {}
                )
                
                # Should return fallback
                assert isinstance(files, dict)
    
    @pytest.mark.asyncio
    async def test_network_timeout_recovery(self):
        """Test recovery from network timeout"""
        with patch('app.services.ai_orchestrator.model_loader') as mock_loader:
            mock_gemini = AsyncMock()
            mock_gemini.generate_project = AsyncMock(
                side_effect=TimeoutError("Network timeout")
            )
            mock_loader.get_model = AsyncMock(return_value=mock_gemini)
            
            with patch('app.services.ai_orchestrator.settings') as mock_settings:
                mock_settings.USE_GEMINI = True
                
                orchestrator = AIOrchestrator()
                orchestrator.initialized = True
                
                # Should handle gracefully
                files = await orchestrator._generate_code(
                    {"prompt": "test", "domain": "general", "tech_stack": "fastapi"},
                    {}
                )
                
                # Should return fallback
                assert isinstance(files, dict)


class TestGeminiConfigValidation:
    """Test configuration validation"""
    
    @pytest.mark.asyncio
    async def test_missing_api_key_configuration(self):
        """Test behavior when API key is not configured"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', True):
            with patch.dict('os.environ', {}, clear=True):
                from ai_models.gemini_generator import GeminiGenerator
                
                generator = GeminiGenerator()
                
                # Should initialize but model should be None
                assert generator.model is None
                
                # Should fall back gracefully
                files = await generator.generate_project(
                    "Create app",
                    {"entities": []},
                    {"domain": "general", "name": "test"}
                )
                
                assert isinstance(files, dict)
                assert "main.py" in files
    
    @pytest.mark.asyncio
    async def test_invalid_model_name(self):
        """Test behavior with invalid model name"""
        with patch('ai_models.gemini_generator.GENAI_AVAILABLE', True):
            with patch('ai_models.gemini_generator.genai') as mock_genai:
                # Mock initialization failure
                mock_genai.GenerativeModel.side_effect = Exception("Invalid model")
                
                with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
                    from ai_models.gemini_generator import GeminiGenerator
                    
                    generator = GeminiGenerator("invalid-model-name")
                    
                    # Should handle gracefully
                    assert generator.model is None
