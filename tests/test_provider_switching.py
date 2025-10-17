"""
Test Suite for Provider Switching and Factory

Tests the LLMProviderFactory implementation including provider selection,
task-specific overrides, and hybrid mode functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from app.services.llm_providers.provider_factory import LLMProviderFactory
from app.services.llm_providers.base_provider import LLMTask
from app.services.llm_providers.gemini_provider import GeminiProvider
from app.services.llm_providers.huggingface_provider import HuggingFaceProvider


@pytest.fixture(autouse=True)
def reset_factory():
    """Reset factory state before each test"""
    LLMProviderFactory._providers = {}
    LLMProviderFactory._initialized = False
    yield
    LLMProviderFactory._providers = {}
    LLMProviderFactory._initialized = False


@pytest.fixture
def mock_settings_huggingface():
    """Mock settings for HuggingFace provider"""
    with patch('app.services.llm_providers.provider_factory.settings') as mock:
        mock.LLM_PROVIDER = "huggingface"
        mock.SCHEMA_EXTRACTION_PROVIDER = None
        mock.CODE_GENERATION_PROVIDER = None
        mock.CODE_REVIEW_PROVIDER = None
        mock.DOCUMENTATION_PROVIDER = None
        mock.HF_TOKEN = "test_hf_token"
        yield mock


@pytest.fixture
def mock_settings_gemini():
    """Mock settings for Gemini provider"""
    with patch('app.services.llm_providers.provider_factory.settings') as mock:
        mock.LLM_PROVIDER = "gemini"
        mock.SCHEMA_EXTRACTION_PROVIDER = None
        mock.CODE_GENERATION_PROVIDER = None
        mock.CODE_REVIEW_PROVIDER = None
        mock.DOCUMENTATION_PROVIDER = None
        mock.GOOGLE_API_KEY = "test_api_key"
        mock.GEMINI_MODEL = "gemini-2.0-flash-exp"
        mock.GEMINI_TEMPERATURE = 0.7
        mock.GEMINI_MAX_OUTPUT_TOKENS = 8192
        mock.GEMINI_TOP_P = 0.95
        mock.GEMINI_TOP_K = 40
        yield mock


@pytest.fixture
def mock_settings_hybrid():
    """Mock settings for hybrid mode"""
    with patch('app.services.llm_providers.provider_factory.settings') as mock:
        mock.LLM_PROVIDER = "huggingface"
        mock.SCHEMA_EXTRACTION_PROVIDER = "huggingface"
        mock.CODE_GENERATION_PROVIDER = "gemini"
        mock.CODE_REVIEW_PROVIDER = "gemini"
        mock.DOCUMENTATION_PROVIDER = "huggingface"
        mock.HF_TOKEN = "test_hf_token"
        mock.GOOGLE_API_KEY = "test_api_key"
        mock.GEMINI_MODEL = "gemini-2.0-flash-exp"
        mock.GEMINI_TEMPERATURE = 0.7
        mock.GEMINI_MAX_OUTPUT_TOKENS = 8192
        mock.GEMINI_TOP_P = 0.95
        mock.GEMINI_TOP_K = 40
        yield mock


class TestProviderSelection:
    """Test provider selection logic"""
    
    @pytest.mark.asyncio
    async def test_get_huggingface_provider(self, mock_settings_huggingface):
        """Test getting HuggingFace provider"""
        with patch('app.services.llm_providers.huggingface_provider.HuggingFaceProvider.initialize', new_callable=AsyncMock):
            provider = await LLMProviderFactory.get_provider()
            
            assert isinstance(provider, HuggingFaceProvider)
            assert LLMProviderFactory._providers.get("huggingface") is provider
    
    @pytest.mark.asyncio
    async def test_get_gemini_provider(self, mock_settings_gemini):
        """Test getting Gemini provider"""
        with patch('app.services.llm_providers.gemini_provider.genai'):
            with patch('app.services.llm_providers.gemini_provider.GeminiProvider.initialize', new_callable=AsyncMock):
                provider = await LLMProviderFactory.get_provider()
                
                assert isinstance(provider, GeminiProvider)
                assert LLMProviderFactory._providers.get("gemini") is provider
    
    @pytest.mark.asyncio
    async def test_provider_caching(self, mock_settings_gemini):
        """Test that providers are cached"""
        with patch('app.services.llm_providers.gemini_provider.genai'):
            with patch('app.services.llm_providers.gemini_provider.GeminiProvider.initialize', new_callable=AsyncMock) as mock_init:
                # First call
                provider1 = await LLMProviderFactory.get_provider()
                # Second call
                provider2 = await LLMProviderFactory.get_provider()
                
                # Should be the same instance
                assert provider1 is provider2
                # Initialize should only be called once
                assert mock_init.call_count == 1
    
    @pytest.mark.asyncio
    async def test_invalid_provider_raises_error(self):
        """Test that invalid provider name raises error"""
        with patch('app.services.llm_providers.provider_factory.settings') as mock:
            mock.LLM_PROVIDER = "invalid_provider"
            
            with pytest.raises(ValueError, match="Unknown provider"):
                await LLMProviderFactory.get_provider()


class TestTaskSpecificProviders:
    """Test task-specific provider overrides"""
    
    @pytest.mark.asyncio
    async def test_task_specific_schema_extraction(self, mock_settings_hybrid):
        """Test task-specific provider for schema extraction"""
        with patch('app.services.llm_providers.huggingface_provider.HuggingFaceProvider.initialize', new_callable=AsyncMock):
            provider = await LLMProviderFactory.get_provider(LLMTask.SCHEMA_EXTRACTION)
            
            assert isinstance(provider, HuggingFaceProvider)
    
    @pytest.mark.asyncio
    async def test_task_specific_code_generation(self, mock_settings_hybrid):
        """Test task-specific provider for code generation"""
        with patch('app.services.llm_providers.gemini_provider.genai'):
            with patch('app.services.llm_providers.gemini_provider.GeminiProvider.initialize', new_callable=AsyncMock):
                provider = await LLMProviderFactory.get_provider(LLMTask.CODE_GENERATION)
                
                assert isinstance(provider, GeminiProvider)
    
    @pytest.mark.asyncio
    async def test_task_specific_code_review(self, mock_settings_hybrid):
        """Test task-specific provider for code review"""
        with patch('app.services.llm_providers.gemini_provider.genai'):
            with patch('app.services.llm_providers.gemini_provider.GeminiProvider.initialize', new_callable=AsyncMock):
                provider = await LLMProviderFactory.get_provider(LLMTask.CODE_REVIEW)
                
                assert isinstance(provider, GeminiProvider)
    
    @pytest.mark.asyncio
    async def test_task_specific_documentation(self, mock_settings_hybrid):
        """Test task-specific provider for documentation"""
        with patch('app.services.llm_providers.huggingface_provider.HuggingFaceProvider.initialize', new_callable=AsyncMock):
            provider = await LLMProviderFactory.get_provider(LLMTask.DOCUMENTATION)
            
            assert isinstance(provider, HuggingFaceProvider)


class TestHybridMode:
    """Test hybrid mode functionality"""
    
    @pytest.mark.asyncio
    async def test_hybrid_mode_uses_different_providers(self, mock_settings_hybrid):
        """Test that hybrid mode can use different providers for different tasks"""
        with patch('app.services.llm_providers.huggingface_provider.HuggingFaceProvider.initialize', new_callable=AsyncMock):
            with patch('app.services.llm_providers.gemini_provider.genai'):
                with patch('app.services.llm_providers.gemini_provider.GeminiProvider.initialize', new_callable=AsyncMock):
                    # Get providers for different tasks
                    schema_provider = await LLMProviderFactory.get_provider(LLMTask.SCHEMA_EXTRACTION)
                    code_provider = await LLMProviderFactory.get_provider(LLMTask.CODE_GENERATION)
                    review_provider = await LLMProviderFactory.get_provider(LLMTask.CODE_REVIEW)
                    docs_provider = await LLMProviderFactory.get_provider(LLMTask.DOCUMENTATION)
                    
                    # Verify correct providers
                    assert isinstance(schema_provider, HuggingFaceProvider)
                    assert isinstance(code_provider, GeminiProvider)
                    assert isinstance(review_provider, GeminiProvider)
                    assert isinstance(docs_provider, HuggingFaceProvider)
                    
                    # Verify both providers are cached
                    assert "huggingface" in LLMProviderFactory._providers
                    assert "gemini" in LLMProviderFactory._providers


class TestProviderInitialization:
    """Test provider initialization"""
    
    @pytest.mark.asyncio
    async def test_initialize_all_providers_single(self, mock_settings_gemini):
        """Test initializing all providers when only one is configured"""
        with patch('app.services.llm_providers.gemini_provider.genai'):
            with patch('app.services.llm_providers.gemini_provider.GeminiProvider.initialize', new_callable=AsyncMock) as mock_init:
                await LLMProviderFactory.initialize_all_providers()
                
                assert LLMProviderFactory._initialized is True
                assert "gemini" in LLMProviderFactory._providers
                mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_all_providers_hybrid(self, mock_settings_hybrid):
        """Test initializing all providers in hybrid mode"""
        with patch('app.services.llm_providers.huggingface_provider.HuggingFaceProvider.initialize', new_callable=AsyncMock) as mock_hf_init:
            with patch('app.services.llm_providers.gemini_provider.genai'):
                with patch('app.services.llm_providers.gemini_provider.GeminiProvider.initialize', new_callable=AsyncMock) as mock_gemini_init:
                    await LLMProviderFactory.initialize_all_providers()
                    
                    assert LLMProviderFactory._initialized is True
                    assert "huggingface" in LLMProviderFactory._providers
                    assert "gemini" in LLMProviderFactory._providers
                    mock_hf_init.assert_called_once()
                    mock_gemini_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_all_providers_idempotent(self, mock_settings_gemini):
        """Test that initializing all providers is idempotent"""
        with patch('app.services.llm_providers.gemini_provider.genai'):
            with patch('app.services.llm_providers.gemini_provider.GeminiProvider.initialize', new_callable=AsyncMock) as mock_init:
                # First initialization
                await LLMProviderFactory.initialize_all_providers()
                # Second initialization
                await LLMProviderFactory.initialize_all_providers()
                
                # Initialize should only be called once per provider
                assert mock_init.call_count == 1


class TestProviderErrors:
    """Test error handling in provider factory"""
    
    @pytest.mark.asyncio
    async def test_provider_initialization_error(self, mock_settings_gemini):
        """Test handling of provider initialization errors"""
        with patch('app.services.llm_providers.gemini_provider.genai'):
            with patch('app.services.llm_providers.gemini_provider.GeminiProvider.initialize', new_callable=AsyncMock) as mock_init:
                mock_init.side_effect = Exception("Initialization failed")
                
                with pytest.raises(Exception, match="Initialization failed"):
                    await LLMProviderFactory.get_provider()
    
    @pytest.mark.asyncio
    async def test_get_provider_name_for_task_no_override(self, mock_settings_gemini):
        """Test getting provider name when no override is set"""
        provider_name = LLMProviderFactory._get_provider_name_for_task(LLMTask.CODE_GENERATION)
        assert provider_name == "gemini"
    
    @pytest.mark.asyncio
    async def test_get_provider_name_for_task_with_override(self, mock_settings_hybrid):
        """Test getting provider name with task override"""
        provider_name = LLMProviderFactory._get_provider_name_for_task(LLMTask.CODE_GENERATION)
        assert provider_name == "gemini"
        
        provider_name = LLMProviderFactory._get_provider_name_for_task(LLMTask.SCHEMA_EXTRACTION)
        assert provider_name == "huggingface"


class TestProviderInfo:
    """Test getting provider information"""
    
    @pytest.mark.asyncio
    async def test_get_provider_info_gemini(self, mock_settings_gemini):
        """Test getting Gemini provider info"""
        with patch('app.services.llm_providers.gemini_provider.genai'):
            with patch('app.services.llm_providers.gemini_provider.GeminiProvider.initialize', new_callable=AsyncMock):
                provider = await LLMProviderFactory.get_provider()
                info = await provider.get_provider_info()
                
                assert info["type"] == "gemini"
                assert "capabilities" in info
                assert len(info["capabilities"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_provider_info_huggingface(self, mock_settings_huggingface):
        """Test getting HuggingFace provider info"""
        with patch('app.services.llm_providers.huggingface_provider.HuggingFaceProvider.initialize', new_callable=AsyncMock):
            provider = await LLMProviderFactory.get_provider()
            info = await provider.get_provider_info()
            
            assert info["type"] == "huggingface"
            assert "models" in info
            assert len(info["models"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
