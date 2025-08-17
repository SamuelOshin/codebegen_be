"""
Tests for Enhanced Generation Service

Tests the integration of:
1. Advanced Template System
2. Enhanced Prompt Engineering System  
3. Context-aware AI orchestration
4. Hybrid generation strategies
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from typing import Dict, Any

from app.services.enhanced_generation_service import (
    EnhancedGenerationService,
    create_enhanced_generation_service
)


class TestEnhancedGenerationService:
    """Test Enhanced Generation Service functionality"""
    
    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories"""
        project_repo = Mock()
        user_repo = Mock()
        generation_repo = Mock()
        
        # Mock user data
        user_repo.get_by_id = AsyncMock(return_value={
            "id": "user123",
            "preferences": {"tech_stack": "fastapi", "architecture": "microservices"}
        })
        
        # Mock project history
        project_repo.get_user_projects = AsyncMock(return_value=[
            {
                "id": "proj1",
                "name": "E-commerce API",
                "tech_stack": ["fastapi", "postgresql"],
                "domain": "ecommerce",
                "successful": True
            },
            {
                "id": "proj2", 
                "name": "User Management System",
                "tech_stack": ["fastapi", "mongodb"],
                "domain": "user_management",
                "successful": True
            }
        ])
        
        # Mock generation history
        generation_repo.get_user_generations = AsyncMock(return_value=[
            {
                "id": "gen1",
                "prompt": "Create user authentication",
                "successful": True,
                "quality_score": 0.85,
                "modifications": ["Add logging", "Custom validation"]
            }
        ])
        
        return project_repo, user_repo, generation_repo
    
    @pytest.fixture
    def enhanced_service(self, mock_repositories):
        """Create Enhanced Generation Service with mocked dependencies"""
        project_repo, user_repo, generation_repo = mock_repositories
        
        service = EnhancedGenerationService(
            project_repository=project_repo,
            user_repository=user_repo,
            generation_repository=generation_repo
        )
        
        return service
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, enhanced_service):
        """Test service initialization"""
        
        # Mock the subsystem initialization
        with patch.object(enhanced_service, 'ai_orchestrator') as mock_orchestrator:
            mock_orchestrator.initialize = AsyncMock()
            
            await enhanced_service.initialize()
            
            assert enhanced_service.enable_enhanced_prompts is True
            assert enhanced_service.enable_template_fallback is True
            assert enhanced_service.enable_hybrid_mode is True
    
    @pytest.mark.asyncio
    async def test_strategy_determination_simple_prompt(self, enhanced_service):
        """Test strategy determination for simple prompts"""
        
        # Mock template system analysis
        enhanced_service.template_system.analyze_prompt_for_templates = Mock(return_value={
            "suitable": True,
            "confidence": 0.9,
            "recommended_template": "fastapi_basic"
        })
        
        strategy = await enhanced_service._determine_generation_strategy(
            prompt="Create a simple FastAPI app with user endpoints",
            user_id="user123",
            domain="web_api",
            tech_stack="fastapi",
            use_enhanced_prompts=False,
            use_templates=True
        )
        
        assert strategy["approach"] == "template_only"
        assert strategy["template_suitable"] is True
        assert "Simple project suitable for templates" in strategy["reasoning"]
    
    @pytest.mark.asyncio
    async def test_strategy_determination_complex_prompt(self, enhanced_service):
        """Test strategy determination for complex prompts"""
        
        # Mock template system analysis
        enhanced_service.template_system.analyze_prompt_for_templates = Mock(return_value={
            "suitable": False,
            "confidence": 0.3,
            "missing_features": ["complex workflows", "machine learning"]
        })
        
        strategy = await enhanced_service._determine_generation_strategy(
            prompt="Create a complex e-commerce platform with AI recommendations, real-time analytics, and microservices architecture",
            user_id="user123",
            domain="ecommerce",
            tech_stack="fastapi",
            use_enhanced_prompts=True,
            use_templates=True
        )
        
        assert strategy["approach"] == "ai_only"
        assert strategy["template_suitable"] is False
        assert "Complex requirements need AI generation" in strategy["reasoning"]
    
    @pytest.mark.asyncio
    async def test_strategy_determination_hybrid(self, enhanced_service):
        """Test strategy determination for hybrid generation"""
        
        # Mock template system analysis
        enhanced_service.template_system.analyze_prompt_for_templates = Mock(return_value={
            "suitable": True,
            "confidence": 0.7,
            "recommended_template": "fastapi_sqlalchemy"
        })
        
        strategy = await enhanced_service._determine_generation_strategy(
            prompt="Create a user management system with custom authentication and reporting",
            user_id="user123",
            domain="user_management",
            tech_stack="fastapi",
            use_enhanced_prompts=True,
            use_templates=True
        )
        
        assert strategy["approach"] == "hybrid"
        assert strategy["template_suitable"] is True
        assert "Hybrid approach for optimal results" in strategy["reasoning"]
    
    def test_complexity_analysis_simple(self, enhanced_service):
        """Test complexity analysis for simple prompts"""
        
        analysis = enhanced_service._analyze_prompt_complexity(
            "Create a basic REST API with user CRUD operations"
        )
        
        assert analysis["complexity_score"] < 0.5
        assert analysis["assessment"] in ["simple", "moderate"]
        assert analysis["indicators"]["technical_terms"] <= 2
    
    def test_complexity_analysis_complex(self, enhanced_service):
        """Test complexity analysis for complex prompts"""
        
        analysis = enhanced_service._analyze_prompt_complexity(
            "Build a comprehensive e-commerce platform with microservices architecture, "
            "real-time analytics, machine learning recommendations, payment processing, "
            "third-party integrations, custom workflow engine, and advanced reporting dashboard"
        )
        
        assert analysis["complexity_score"] > 0.7
        assert analysis["assessment"] in ["complex", "very_complex"]
        assert analysis["indicators"]["technical_terms"] >= 3
        assert analysis["indicators"]["integration_words"] >= 1
    
    @pytest.mark.asyncio
    async def test_template_only_generation(self, enhanced_service):
        """Test template-only generation"""
        
        # Mock template system
        enhanced_service.template_system.generate_project_from_prompt = Mock(return_value={
            "files": {
                "main.py": "# FastAPI application\nfrom fastapi import FastAPI\napp = FastAPI()",
                "models.py": "# User model\nfrom sqlalchemy import Column, Integer, String"
            },
            "schema": {"entities": ["User"], "endpoints": ["/users"]},
            "template_info": {"name": "fastapi_basic", "version": "1.0"},
            "quality_score": 0.8
        })
        
        result = await enhanced_service._generate_with_templates_only(
            prompt="Create a user management API",
            user_id="user123",
            domain="user_management",
            tech_stack="fastapi"
        )
        
        assert result["generation_method"] == "template_only"
        assert "main.py" in result["files"]
        assert "models.py" in result["files"]
        assert result["quality_score"] == 0.8
    
    @pytest.mark.asyncio
    async def test_hybrid_generation(self, enhanced_service):
        """Test hybrid generation with template + AI enhancement"""
        
        # Mock template generation
        enhanced_service._generate_with_templates_only = AsyncMock(return_value={
            "files": {
                "main.py": "# Basic FastAPI app",
                "models.py": "# Basic models"
            },
            "quality_score": 0.8,
            "generation_method": "template_only"
        })
        
        # Mock enhanced prompt system
        enhanced_service.enhanced_prompt_system = Mock()
        enhanced_service.enhanced_prompt_system.generate_with_context = Mock(return_value={
            "user_context": {
                "common_modifications": ["Add logging", "Custom validation"],
                "successful_projects": 5
            },
            "recommendations": {
                "suggested_features": ["authentication", "caching"],
                "potential_issues": []
            }
        })
        
        result = await enhanced_service._generate_hybrid(
            prompt="Create a user management system",
            user_id="user123",
            domain="user_management",
            tech_stack="fastapi",
            use_enhanced_prompts=True
        )
        
        assert result["generation_method"] == "hybrid_enhanced"
        assert "context_analysis" in result
        assert result["quality_score"] > 0.8  # Should be enhanced
    
    @pytest.mark.asyncio
    async def test_feature_enhancement(self, enhanced_service):
        """Test AI enhancement of template features"""
        
        template_files = {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()",
            "models.py": "from sqlalchemy import Column, Integer, String"
        }
        
        context_analysis = {
            "user_context": {
                "common_modifications": ["Add logging"],
                "successful_projects": 3
            },
            "recommendations": {
                "suggested_features": ["authentication", "caching"]
            }
        }
        
        enhanced_files = await enhanced_service._enhance_template_with_ai(
            template_files, context_analysis, "Create user management API"
        )
        
        # Should have original files plus enhancements
        assert "main.py" in enhanced_files
        assert "models.py" in enhanced_files
        
        # Should add suggested features
        auth_files = [f for f in enhanced_files.keys() if "authentication" in f]
        caching_files = [f for f in enhanced_files.keys() if "caching" in f]
        
        assert len(auth_files) > 0 or len(caching_files) > 0
    
    def test_user_pattern_application(self, enhanced_service):
        """Test application of user patterns to generated code"""
        
        original_content = "from fastapi import FastAPI\n\napp = FastAPI()"
        
        user_context = {
            "common_modifications": ["Add logging", "Custom validation"]
        }
        
        enhanced_content = enhanced_service._apply_user_patterns(original_content, user_context)
        
        # Should add logging
        assert "import logging" in enhanced_content
        assert "logger = logging.getLogger(__name__)" in enhanced_content
        
        # Should add validation function
        assert "def validate_input" in enhanced_content
    
    def test_quality_metrics_calculation(self, enhanced_service):
        """Test quality metrics calculation"""
        
        result = {
            "files": {
                "main.py": "# Main file with\n# multiple lines\n# of code",
                "models.py": "# Models file",
                "features/auth.py": "# Authentication feature"
            },
            "quality_score": 0.8
        }
        
        strategy = {
            "approach": "hybrid",
            "enhanced_prompts_used": True
        }
        
        metrics = enhanced_service._calculate_quality_metrics(result, strategy)
        
        assert metrics["file_count"] == 3
        assert metrics["total_lines"] > 0
        assert metrics["base_quality_score"] == 0.8
        assert metrics["strategy_bonus"] == 0.05  # Hybrid bonus
        assert metrics["enhanced_features"] == 1  # auth feature
        assert metrics["final_quality_score"] == 0.85
    
    def test_improvement_suggestions(self, enhanced_service):
        """Test generation of improvement suggestions"""
        
        result = {
            "files": {
                "main.py": "# Main application file",
                "models.py": "# Database models"
            }
        }
        
        strategy = {"approach": "template_only"}
        
        suggestions = enhanced_service._generate_improvement_suggestions(result, strategy)
        
        # Should suggest adding tests
        test_suggestion = any("test" in s.lower() for s in suggestions)
        assert test_suggestion
        
        # Should suggest adding README
        readme_suggestion = any("readme" in s.lower() for s in suggestions)
        assert readme_suggestion
    
    @pytest.mark.asyncio
    async def test_fallback_generation(self, enhanced_service):
        """Test fallback generation when enhanced systems fail"""
        
        # Mock template system to work for fallback
        enhanced_service.template_system.generate_project_from_prompt = Mock(return_value={
            "files": {"main.py": "# Fallback FastAPI app"},
            "quality_score": 0.7
        })
        
        result = await enhanced_service._fallback_generation(
            prompt="Create an API",
            user_id="user123",
            domain="api",
            tech_stack="fastapi"
        )
        
        assert result["generation_method"] == "fallback_template"
        assert result["quality_score"] == 0.7
        assert "main.py" in result["files"]
    
    @pytest.mark.asyncio
    async def test_complete_generation_workflow(self, enhanced_service):
        """Test complete generation workflow end-to-end"""
        
        # Mock all dependencies for successful generation
        enhanced_service.template_system.analyze_prompt_for_templates = Mock(return_value={
            "suitable": True,
            "confidence": 0.7
        })
        
        enhanced_service.template_system.generate_project_from_prompt = Mock(return_value={
            "files": {"main.py": "# Generated app"},
            "quality_score": 0.8
        })
        
        enhanced_service.enhanced_prompt_system = Mock()
        enhanced_service.enhanced_prompt_system.generate_with_context = Mock(return_value={
            "user_context": {"successful_projects": 3},
            "recommendations": {"suggested_features": []}
        })
        
        await enhanced_service.initialize()
        
        result = await enhanced_service.generate_project(
            prompt="Create a user management API with authentication",
            user_id="user123",
            domain="user_management",
            tech_stack="fastapi",
            use_enhanced_prompts=True,
            use_templates=True
        )
        
        # Verify comprehensive result
        assert "files" in result
        assert "generation_metadata" in result
        assert "strategy_used" in result
        assert "quality_metrics" in result
        assert "improvement_suggestions" in result
        assert result["generation_metadata"]["user_id"] == "user123"


class TestEnhancedGenerationServiceFactory:
    """Test Enhanced Generation Service factory function"""
    
    def test_factory_function(self):
        """Test factory function creates service correctly"""
        
        project_repo = Mock()
        user_repo = Mock()
        generation_repo = Mock()
        
        service = create_enhanced_generation_service(
            project_repository=project_repo,
            user_repository=user_repo,
            generation_repository=generation_repo
        )
        
        assert isinstance(service, EnhancedGenerationService)
        assert service.project_repo == project_repo
        assert service.user_repo == user_repo
        assert service.generation_repo == generation_repo


class TestEnhancedGenerationServiceIntegration:
    """Integration tests for Enhanced Generation Service"""
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self):
        """Test error handling and fallback behavior"""
        
        # Create service with mocked repositories
        project_repo = Mock()
        user_repo = Mock()
        generation_repo = Mock()
        
        service = EnhancedGenerationService(project_repo, user_repo, generation_repo)
        
        # Mock enhanced prompt system to fail
        service.enhanced_prompt_system = Mock()
        service.enhanced_prompt_system.generate_with_context = Mock(
            side_effect=Exception("Context analysis failed")
        )
        
        # Mock template system to work
        service.template_system.generate_project_from_prompt = Mock(return_value={
            "files": {"main.py": "# Fallback app"},
            "quality_score": 0.7
        })
        
        # Should not raise exception, should fallback gracefully
        result = await service.generate_project(
            prompt="Create an API",
            user_id="user123"
        )
        
        assert "files" in result
        assert result.get("generation_method") in ["fallback_template", "minimal_fallback"]
    
    @pytest.mark.asyncio 
    async def test_performance_metrics_tracking(self, enhanced_service):
        """Test that performance metrics are properly tracked"""
        
        # Mock successful generation
        enhanced_service._determine_generation_strategy = AsyncMock(return_value={
            "approach": "hybrid",
            "confidence": 0.9,
            "reasoning": ["Best approach"]
        })
        
        enhanced_service._generate_hybrid = AsyncMock(return_value={
            "files": {"main.py": "# Test app"},
            "quality_score": 0.85,
            "generation_method": "hybrid"
        })
        
        await enhanced_service.initialize()
        
        result = await enhanced_service.generate_project(
            prompt="Test prompt",
            user_id="user123"
        )
        
        # Verify timing is tracked
        assert "total_time" in result["generation_metadata"]
        assert result["generation_metadata"]["total_time"] >= 0
        
        # Verify quality metrics
        assert "quality_metrics" in result
        assert "final_quality_score" in result["quality_metrics"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
