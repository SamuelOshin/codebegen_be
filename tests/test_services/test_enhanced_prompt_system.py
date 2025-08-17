"""
Tests for Enhanced Prompt Engineering System (Phase 2)

These tests verify the functionality of the enhanced prompt system
including context analysis, user pattern recognition, and prompt optimization.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, List, Any

from app.services.enhanced_prompt_system import (
    UserContext,
    PromptContext,
    IntentClarificationTemplate,
    ArchitecturePlanningTemplate,
    ImplementationGenerationTemplate,
    PromptChain,
    UserPatternAnalyzer,
    ProjectSimilarityMatcher,
    ContextAwareOrchestrator,
    create_enhanced_prompt_system
)
from app.models.project import Project
from app.models.user import User
from app.models.generation import Generation


class TestUserContext:
    """Test UserContext data structure"""
    
    def test_user_context_creation(self):
        """Test UserContext can be created with default values"""
        context = UserContext(user_id="test_user")
        
        assert context.user_id == "test_user"
        assert context.successful_projects == []
        assert context.preferences == {}
        assert context.architecture_style == "microservices"
        assert context.complexity_preference == "moderate"
    
    def test_user_context_with_data(self):
        """Test UserContext with populated data"""
        context = UserContext(
            user_id="test_user",
            frequent_features=["authentication", "payments"],
            tech_stack_history=["fastapi", "django"],
            architecture_style="modular_monolith",
            complexity_preference="high"
        )
        
        assert context.frequent_features == ["authentication", "payments"]
        assert context.tech_stack_history == ["fastapi", "django"]
        assert context.architecture_style == "modular_monolith"
        assert context.complexity_preference == "high"


class TestPromptTemplates:
    """Test prompt template implementations"""
    
    def test_intent_clarification_template(self):
        """Test intent clarification prompt generation"""
        template = IntentClarificationTemplate()
        
        user_context = UserContext(
            user_id="test_user",
            frequent_features=["authentication", "file_upload"],
            tech_stack_history=["fastapi", "fastapi"],
            architecture_style="microservices"
        )
        
        prompt_context = PromptContext(
            original_prompt="Build an e-commerce API",
            user_context=user_context,
            similar_projects=[
                {"description": "Online store API", "features": ["payments", "inventory"]}
            ]
        )
        
        generated_prompt = template.generate_prompt(prompt_context)
        
        assert "Build an e-commerce API" in generated_prompt
        assert "authentication" in generated_prompt
        assert "file_upload" in generated_prompt
        assert "microservices" in generated_prompt
        assert "Online store API" in generated_prompt
        assert template.get_template_type() == "intent_clarification"
    
    def test_architecture_planning_template(self):
        """Test architecture planning prompt generation"""
        template = ArchitecturePlanningTemplate()
        
        user_context = UserContext(
            user_id="test_user",
            architecture_style="modular_monolith",
            complexity_preference="high",
            frequent_features=["caching", "search"]
        )
        
        prompt_context = PromptContext(
            original_prompt="Clarified requirements for e-commerce API",
            user_context=user_context
        )
        
        generated_prompt = template.generate_prompt(prompt_context)
        
        assert "modular_monolith" in generated_prompt
        assert "high" in generated_prompt
        assert "caching" in generated_prompt
        assert "search" in generated_prompt
        assert "DATABASE SCHEMA" in generated_prompt
        assert "API ENDPOINTS" in generated_prompt
        assert template.get_template_type() == "architecture_planning"
    
    def test_implementation_generation_template(self):
        """Test implementation generation prompt"""
        template = ImplementationGenerationTemplate()
        
        user_context = UserContext(
            user_id="test_user",
            common_modifications=["Add logging", "Custom validation"],
            tech_stack_history=["fastapi", "django", "fastapi"],
            frequent_features=["authentication", "payments"]
        )
        
        prompt_context = PromptContext(
            original_prompt="Architecture specification",
            user_context=user_context
        )
        
        generated_prompt = template.generate_prompt(prompt_context)
        
        assert "Add logging" in generated_prompt
        assert "Custom validation" in generated_prompt
        assert "fastapi" in generated_prompt
        assert "JWT-based authentication" in generated_prompt  # From authentication feature
        assert "Stripe" in generated_prompt  # From payments feature
        assert template.get_template_type() == "implementation_generation"


class TestPromptChain:
    """Test prompt chain processing"""
    
    def test_prompt_chain_processing(self):
        """Test full prompt chain processing"""
        chain = PromptChain()
        
        user_context = UserContext(
            user_id="test_user",
            frequent_features=["authentication"],
            architecture_style="microservices"
        )
        
        similar_projects = [
            {"description": "Similar API", "features": ["auth"]}
        ]
        
        results = chain.process_prompt_chain(
            "Build a user management API",
            user_context,
            similar_projects
        )
        
        assert "intent_clarification" in results
        assert "architecture_planning" in results
        assert "implementation_generation" in results
        
        # Check that each stage contains relevant information
        intent_prompt = results["intent_clarification"]
        assert "Build a user management API" in intent_prompt
        assert "authentication" in intent_prompt
        
        arch_prompt = results["architecture_planning"]
        assert "microservices" in arch_prompt
        
        impl_prompt = results["implementation_generation"]
        assert "JWT-based authentication" in impl_prompt


class TestUserPatternAnalyzer:
    """Test user pattern analysis functionality"""
    
    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories for testing"""
        project_repo = Mock()
        user_repo = Mock()
        generation_repo = Mock()
        
        # Mock successful projects
        mock_projects = [
            Mock(
                id="proj1",
                name="E-commerce API",
                description="Online store backend",
                status="completed",
                template_used="fastapi_sqlalchemy",
                created_at=datetime.now(),
                features_used=["authentication", "payments"],
                entities=["Product", "Order", "User"]
            ),
            Mock(
                id="proj2", 
                name="Blog API",
                description="Content management",
                status="completed",
                template_used="fastapi_basic",
                created_at=datetime.now(),
                features_used=["authentication", "file_upload"],
                entities=["Post", "User"]
            )
        ]
        
        project_repo.get_user_projects.return_value = mock_projects
        
        # Mock generations
        mock_generations = [
            Mock(
                id="gen1",
                status="completed",
                created_at=datetime.now() - timedelta(minutes=30),
                completed_at=datetime.now() - timedelta(minutes=25)
            ),
            Mock(
                id="gen2",
                status="failed",
                created_at=datetime.now() - timedelta(minutes=20),
                completed_at=None
            )
        ]
        
        generation_repo.get_user_generations.return_value = mock_generations
        
        return project_repo, user_repo, generation_repo
    
    def test_analyze_user_patterns(self, mock_repositories):
        """Test user pattern analysis"""
        project_repo, user_repo, generation_repo = mock_repositories
        
        analyzer = UserPatternAnalyzer(project_repo, user_repo, generation_repo)
        
        user_context = analyzer.analyze_user_patterns("test_user")
        
        assert user_context.user_id == "test_user"
        assert len(user_context.successful_projects) == 2
        assert "fastapi_sqlalchemy" in user_context.tech_stack_history
        assert "fastapi_basic" in user_context.tech_stack_history
        assert "authentication" in user_context.frequent_features
        
        # Check generation patterns
        patterns = user_context.generation_patterns
        assert patterns["total_generations"] == 2
        assert patterns["success_rate"] == 0.5  # 1 success out of 2
    
    def test_architecture_preference_determination(self, mock_repositories):
        """Test architecture preference logic"""
        project_repo, user_repo, generation_repo = mock_repositories
        
        analyzer = UserPatternAnalyzer(project_repo, user_repo, generation_repo)
        
        # Test with few projects (should prefer simple structure)
        mock_projects = [Mock(entities=["User"])]
        project_repo.get_user_projects.return_value = mock_projects
        
        user_context = analyzer.analyze_user_patterns("test_user")
        assert user_context.architecture_style == "simple_structure"
    
    def test_complexity_preference_analysis(self, mock_repositories):
        """Test complexity preference analysis"""
        project_repo, user_repo, generation_repo = mock_repositories
        
        # Mock projects with many entities (high complexity)
        complex_projects = [
            Mock(entities=["User", "Product", "Order", "Payment", "Inventory", 
                          "Category", "Review", "Cart", "Shipping", "Coupon"])
        ]
        project_repo.get_user_projects.return_value = complex_projects
        
        analyzer = UserPatternAnalyzer(project_repo, user_repo, generation_repo)
        user_context = analyzer.analyze_user_patterns("test_user")
        
        assert user_context.complexity_preference == "high"


class TestProjectSimilarityMatcher:
    """Test project similarity matching"""
    
    @pytest.fixture
    def mock_project_repo(self):
        """Create mock project repository"""
        repo = Mock()
        
        # Mock successful projects
        mock_projects = [
            Mock(
                id="proj1",
                description="E-commerce platform with payments",
                features_used=["authentication", "payments", "inventory"],
                template_used="fastapi_sqlalchemy",
                domain="ecommerce"
            ),
            Mock(
                id="proj2",
                description="Blog API with user management",
                features_used=["authentication", "file_upload"],
                template_used="fastapi_basic",
                domain="content"
            ),
            Mock(
                id="proj3",
                description="Financial dashboard API",
                features_used=["authentication", "payments", "analytics"],
                template_used="fastapi_sqlalchemy",
                domain="fintech"
            )
        ]
        
        repo.get_successful_projects.return_value = mock_projects
        return repo
    
    def test_find_similar_projects(self, mock_project_repo):
        """Test finding similar projects"""
        matcher = ProjectSimilarityMatcher(mock_project_repo)
        
        user_context = UserContext(
            user_id="test_user",
            frequent_features=["authentication", "payments"],
            tech_stack_history=["fastapi_sqlalchemy"],
            domain_expertise=["ecommerce"]
        )
        
        similar_projects = matcher.find_similar_projects(
            "Build an online store with payment processing",
            user_context,
            limit=3
        )
        
        # Should find the e-commerce project as most similar
        assert len(similar_projects) > 0
        
        # Check that e-commerce project is highly ranked
        project_descriptions = [p["description"] for p in similar_projects]
        assert any("E-commerce" in desc for desc in project_descriptions)
    
    def test_similarity_scoring(self, mock_project_repo):
        """Test similarity scoring logic"""
        matcher = ProjectSimilarityMatcher(mock_project_repo)
        
        user_context = UserContext(
            user_id="test_user",
            frequent_features=["payments"],
            tech_stack_history=["fastapi_sqlalchemy"],
            domain_expertise=["fintech"]
        )
        
        # Get the first mock project (e-commerce)
        projects = mock_project_repo.get_successful_projects()
        ecommerce_project = projects[0]
        fintech_project = projects[2]
        
        # Fintech project should score higher due to domain match
        fintech_score = matcher._calculate_similarity_score(
            "payment processing API", fintech_project, user_context
        )
        ecommerce_score = matcher._calculate_similarity_score(
            "payment processing API", ecommerce_project, user_context
        )
        
        assert fintech_score > 0
        assert ecommerce_score > 0
        # Fintech should score higher due to domain expertise match
        assert fintech_score > ecommerce_score
    
    def test_keyword_extraction(self, mock_project_repo):
        """Test keyword extraction from text"""
        matcher = ProjectSimilarityMatcher(mock_project_repo)
        
        keywords = matcher._extract_keywords("Build an e-commerce API with payments and authentication")
        
        assert "e-commerce" in keywords or "ecommerce" in keywords
        assert "payments" in keywords
        assert "authentication" in keywords
        # Common words should be filtered out
        assert "the" not in keywords
        assert "an" not in keywords


class TestContextAwareOrchestrator:
    """Test the main orchestrator functionality"""
    
    @pytest.fixture
    def mock_orchestrator_components(self):
        """Create mock components for orchestrator"""
        pattern_analyzer = Mock()
        similarity_matcher = Mock()
        prompt_chain = Mock()
        
        # Mock user context
        user_context = UserContext(
            user_id="test_user",
            frequent_features=["authentication", "payments"],
            architecture_style="microservices"
        )
        
        pattern_analyzer.analyze_user_patterns.return_value = user_context
        
        # Mock similar projects
        similar_projects = [
            {"description": "Similar API", "features": ["auth", "payments"]}
        ]
        similarity_matcher.find_similar_projects.return_value = similar_projects
        
        # Mock prompt chain results
        enhanced_prompts = {
            "intent_clarification": "Enhanced intent prompt",
            "architecture_planning": "Enhanced architecture prompt",
            "implementation_generation": "Enhanced implementation prompt"
        }
        prompt_chain.process_prompt_chain.return_value = enhanced_prompts
        
        return pattern_analyzer, similarity_matcher, prompt_chain, user_context, similar_projects
    
    def test_generate_with_context(self, mock_orchestrator_components):
        """Test context-aware generation"""
        (pattern_analyzer, similarity_matcher, prompt_chain, 
         expected_user_context, expected_similar_projects) = mock_orchestrator_components
        
        orchestrator = ContextAwareOrchestrator(
            pattern_analyzer, similarity_matcher, prompt_chain
        )
        
        result = orchestrator.generate_with_context(
            "Build a payment API", "test_user"
        )
        
        # Verify all components were called
        pattern_analyzer.analyze_user_patterns.assert_called_once_with("test_user")
        similarity_matcher.find_similar_projects.assert_called_once()
        prompt_chain.process_prompt_chain.assert_called_once()
        
        # Verify result structure
        assert "original_prompt" in result
        assert "user_context" in result
        assert "similar_projects" in result
        assert "enhanced_prompts" in result
        assert "recommendations" in result
        
        assert result["original_prompt"] == "Build a payment API"
        assert result["user_context"] == expected_user_context
        assert result["similar_projects"] == expected_similar_projects
    
    def test_generate_recommendations(self, mock_orchestrator_components):
        """Test recommendation generation"""
        (pattern_analyzer, similarity_matcher, prompt_chain, 
         user_context, similar_projects) = mock_orchestrator_components
        
        orchestrator = ContextAwareOrchestrator(
            pattern_analyzer, similarity_matcher, prompt_chain
        )
        
        recommendations = orchestrator._generate_recommendations(
            user_context, similar_projects
        )
        
        assert "suggested_features" in recommendations
        assert "tech_stack_recommendation" in recommendations
        assert "architecture_advice" in recommendations
        assert "potential_issues" in recommendations
        assert "optimization_suggestions" in recommendations
        
        # Should suggest user's frequent features
        assert recommendations["suggested_features"] == ["authentication", "payments"]


class TestFactoryFunction:
    """Test the factory function for creating enhanced prompt system"""
    
    def test_create_enhanced_prompt_system(self):
        """Test factory function creates complete system"""
        project_repo = Mock()
        user_repo = Mock()
        generation_repo = Mock()
        
        orchestrator = create_enhanced_prompt_system(
            project_repo, user_repo, generation_repo
        )
        
        assert isinstance(orchestrator, ContextAwareOrchestrator)
        assert orchestrator.pattern_analyzer is not None
        assert orchestrator.similarity_matcher is not None
        assert orchestrator.prompt_chain is not None


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for the enhanced prompt system"""
    
    async def test_full_enhanced_prompt_flow(self):
        """Test complete flow from prompt to enhanced generation context"""
        # This would be an integration test that tests the full flow
        # In a real test environment with actual database connections
        
        # Mock the dependencies
        with patch('app.services.enhanced_prompt_system.ProjectRepository') as MockProjectRepo, \
             patch('app.services.enhanced_prompt_system.UserRepository') as MockUserRepo, \
             patch('app.services.enhanced_prompt_system.GenerationRepository') as MockGenRepo:
            
            # Set up mocks
            project_repo = MockProjectRepo.return_value
            user_repo = MockUserRepo.return_value
            generation_repo = MockGenRepo.return_value
            
            # Mock successful projects
            project_repo.get_user_projects.return_value = []
            project_repo.get_successful_projects.return_value = []
            generation_repo.get_user_generations.return_value = []
            
            # Create orchestrator
            orchestrator = create_enhanced_prompt_system(
                project_repo, user_repo, generation_repo
            )
            
            # Test generation
            result = orchestrator.generate_with_context(
                "Build a simple user management API", "test_user"
            )
            
            # Verify result structure
            assert "original_prompt" in result
            assert "user_context" in result
            assert "enhanced_prompts" in result
            assert result["original_prompt"] == "Build a simple user management API"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
