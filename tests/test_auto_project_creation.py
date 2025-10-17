"""
Tests for Auto-Project Creation Feature

Tests the intelligent automatic project creation system that analyzes
user prompts and creates meaningful projects.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prompt_analysis_service import PromptAnalysisService, prompt_analysis_service
from app.services.auto_project_service import AutoProjectService
from app.models.project import Project


class TestPromptAnalysisService:
    """Test suite for prompt analysis functionality"""
    
    @pytest.fixture
    def service(self):
        return PromptAnalysisService()
    
    @pytest.mark.asyncio
    async def test_ecommerce_domain_detection(self, service):
        """Test e-commerce domain is correctly detected"""
        prompt = "Build an online store with products, cart, and checkout"
        result = await service.analyze_prompt(prompt)
        
        assert result.domain == "ecommerce"
        assert result.confidence > 0.5
        assert "store" in result.suggested_name.lower() or "commerce" in result.suggested_name.lower()
    
    @pytest.mark.asyncio
    async def test_social_media_domain_detection(self, service):
        """Test social media domain detection"""
        prompt = "Create a social network with posts, comments, and likes"
        result = await service.analyze_prompt(prompt)
        
        assert result.domain == "social_media"
        assert "post" in result.entities or "Post" in result.entities
    
    @pytest.mark.asyncio
    async def test_task_management_domain(self, service):
        """Test task management domain"""
        prompt = "Build a kanban board for managing tasks and projects"
        result = await service.analyze_prompt(prompt)
        
        assert result.domain == "task_management"
        assert "Task" in result.entities or "Project" in result.entities
    
    @pytest.mark.asyncio
    async def test_fintech_domain(self, service):
        """Test fintech domain detection"""
        prompt = "Create a payment processing API with transactions and accounts"
        result = await service.analyze_prompt(prompt)
        
        assert result.domain == "fintech"
        assert "payment" in result.features or "Transaction" in result.entities
    
    @pytest.mark.asyncio
    async def test_healthcare_domain(self, service):
        """Test healthcare domain detection"""
        prompt = "Build a patient management system with appointments"
        result = await service.analyze_prompt(prompt)
        
        assert result.domain == "healthcare"
        assert "Patient" in result.entities
    
    @pytest.mark.asyncio
    async def test_entity_extraction(self, service):
        """Test entity extraction from prompts"""
        prompt = "Create an API to manage products, orders, and customers"
        result = await service.analyze_prompt(prompt)
        
        entities_lower = [e.lower() for e in result.entities]
        assert "product" in entities_lower
        assert "order" in entities_lower
        assert "customer" in entities_lower
    
    @pytest.mark.asyncio
    async def test_tech_stack_detection_fastapi(self, service):
        """Test FastAPI tech stack detection"""
        prompt = "Build a FastAPI backend with PostgreSQL"
        result = await service.analyze_prompt(prompt)
        
        assert "fastapi" in result.tech_stack
        assert "postgresql" in result.tech_stack or "postgres" in result.tech_stack
    
    @pytest.mark.asyncio
    async def test_tech_stack_detection_django(self, service):
        """Test Django detection"""
        prompt = "Create a Django REST API"
        result = await service.analyze_prompt(prompt)
        
        assert "django" in result.tech_stack
    
    @pytest.mark.asyncio
    async def test_feature_detection_auth(self, service):
        """Test authentication feature detection"""
        prompt = "Build an API with user login and registration"
        result = await service.analyze_prompt(prompt)
        
        assert "authentication" in result.features
    
    @pytest.mark.asyncio
    async def test_feature_detection_file_upload(self, service):
        """Test file upload feature detection"""
        prompt = "Create a system for uploading and managing documents"
        result = await service.analyze_prompt(prompt)
        
        assert "file_upload" in result.features
    
    @pytest.mark.asyncio
    async def test_feature_detection_search(self, service):
        """Test search feature detection"""
        prompt = "Build an API with full-text search functionality"
        result = await service.analyze_prompt(prompt)
        
        assert "search" in result.features
    
    @pytest.mark.asyncio
    async def test_feature_detection_payments(self, service):
        """Test payment feature detection"""
        prompt = "Create an e-commerce API with Stripe integration"
        result = await service.analyze_prompt(prompt)
        
        assert "payments" in result.features
    
    @pytest.mark.asyncio
    async def test_project_name_from_quoted_text(self, service):
        """Test project name extraction from quoted text"""
        prompt = 'Build a system called "TaskMaster Pro" for managing tasks'
        result = await service.analyze_prompt(prompt)
        
        assert "TaskMaster Pro" in result.suggested_name
    
    @pytest.mark.asyncio
    async def test_project_name_from_named_pattern(self, service):
        """Test project name from 'named X' pattern"""
        prompt = "Create an API named BlogPlatform for content management"
        result = await service.analyze_prompt(prompt)
        
        assert "BlogPlatform" in result.suggested_name or "Blog Platform" in result.suggested_name
    
    @pytest.mark.asyncio
    async def test_project_name_from_entity(self, service):
        """Test project name from primary entity"""
        prompt = "Build a product management API"
        result = await service.analyze_prompt(prompt)
        
        assert "product" in result.suggested_name.lower()
    
    @pytest.mark.asyncio
    async def test_complexity_simple(self, service):
        """Test simple complexity estimation"""
        prompt = "Build a basic CRUD API for users"
        result = await service.analyze_prompt(prompt)
        
        assert result.complexity in ["simple", "moderate"]
    
    @pytest.mark.asyncio
    async def test_complexity_moderate(self, service):
        """Test moderate complexity estimation"""
        prompt = "Create an API with users, posts, comments, authentication, and file uploads"
        result = await service.analyze_prompt(prompt)
        
        assert result.complexity in ["moderate", "complex"]
    
    @pytest.mark.asyncio
    async def test_complexity_complex(self, service):
        """Test complex complexity estimation"""
        prompt = """
        Build a microservices-based platform with user management, product catalog,
        order processing, payment integration, real-time notifications, advanced
        search with Elasticsearch, caching with Redis, and distributed architecture
        """
        result = await service.analyze_prompt(prompt)
        
        assert result.complexity == "complex"
    
    @pytest.mark.asyncio
    async def test_confidence_high(self, service):
        """Test high confidence when clear indicators present"""
        prompt = "Build an e-commerce store with products, cart, and Stripe payments"
        result = await service.analyze_prompt(prompt)
        
        assert result.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_confidence_low(self, service):
        """Test lower confidence with vague prompts"""
        prompt = "Build something"
        result = await service.analyze_prompt(prompt)
        
        assert result.confidence < 0.7
    
    @pytest.mark.asyncio
    async def test_description_generation(self, service):
        """Test project description is generated"""
        prompt = "Create a task management system for teams"
        result = await service.analyze_prompt(prompt)
        
        assert result.description is not None
        assert len(result.description) > 0
        assert "task" in result.description.lower() or "Task" in result.description
    
    @pytest.mark.asyncio
    async def test_context_override_domain(self, service):
        """Test that explicit context overrides detection"""
        prompt = "Build an API"
        context = {"domain": "fintech"}
        result = await service.analyze_prompt(prompt, context)
        
        assert result.domain == "fintech"
    
    @pytest.mark.asyncio
    async def test_context_override_tech_stack(self, service):
        """Test tech stack from context"""
        prompt = "Build an API"
        context = {"tech_stack": "django_postgres"}
        result = await service.analyze_prompt(prompt, context)
        
        assert "django" in result.tech_stack or "postgres" in result.tech_stack


class TestAutoProjectService:
    """Test suite for auto project service"""
    
    @pytest.fixture
    async def db_session(self):
        """Mock database session"""
        # In real tests, use a test database
        # For now, this is a placeholder
        pass
    
    @pytest.mark.asyncio
    async def test_create_project_from_analysis(self, db_session):
        """Test project creation from analysis results"""
        # This would be a full integration test
        # Requires test database setup
        pass
    
    @pytest.mark.asyncio
    async def test_project_deduplication(self, db_session):
        """Test that similar projects are reused"""
        # Test that creating same project twice within time window reuses first one
        pass
    
    @pytest.mark.asyncio
    async def test_tech_stack_formatting(self):
        """Test tech stack formatting logic"""
        service = AutoProjectService(None)
        
        # Test framework + database
        result = service._format_tech_stack(["fastapi", "postgresql"])
        assert result == "fastapi_postgres"
        
        # Test only framework
        result = service._format_tech_stack(["django"])
        assert result == "django_postgres"  # Default to postgres
        
        # Test only database
        result = service._format_tech_stack(["mongodb"])
        assert result == "fastapi_mongo"  # Default to fastapi
        
        # Test normalization
        result = service._format_tech_stack(["fastapi", "postgres"])
        assert result == "fastapi_postgres"
    
    @pytest.mark.asyncio
    async def test_no_duplicate_projects_different_names(self, db_session):
        """Test that different prompts create different projects"""
        # Create project for "e-commerce"
        # Create project for "blog"
        # Assert both exist
        pass


class TestIntegrationAutoProjectCreation:
    """Integration tests for auto-project creation in generation flow"""
    
    @pytest.mark.asyncio
    async def test_generation_without_project_creates_project(self):
        """Test that generation without project_id creates one"""
        # Make request to /generate without project_id
        # Assert project was created
        # Assert generation is linked to project
        pass
    
    @pytest.mark.asyncio
    async def test_response_includes_project_info(self):
        """Test that response includes auto-created project info"""
        # Make request to /generate
        # Assert response has auto_created_project=True
        # Assert response has project_name
        # Assert response has project_domain
        pass
    
    @pytest.mark.asyncio
    async def test_project_marked_as_auto_created(self):
        """Test that created project has auto_created flag"""
        # Create generation without project_id
        # Query project from database
        # Assert auto_created == True
        # Assert creation_source is set
        # Assert original_prompt is stored
        pass


# Example test data
SAMPLE_PROMPTS = [
    {
        "prompt": "Build a RESTful API for managing blog posts with user authentication",
        "expected_domain": "content_management",
        "expected_entities": ["Post", "User"],
        "expected_features": ["authentication", "api"]
    },
    {
        "prompt": "Create an e-commerce platform with products, shopping cart, and payment processing",
        "expected_domain": "ecommerce",
        "expected_entities": ["Product", "Cart"],
        "expected_features": ["payments"]
    },
    {
        "prompt": "Build a social media app with user profiles, posts, comments, and likes",
        "expected_domain": "social_media",
        "expected_entities": ["User", "Post", "Comment"],
        "expected_features": ["authentication"]
    },
    {
        "prompt": "Create a task tracking system with kanban boards and team collaboration",
        "expected_domain": "task_management",
        "expected_entities": ["Task", "Team"],
        "expected_features": []
    }
]


@pytest.mark.parametrize("test_case", SAMPLE_PROMPTS)
@pytest.mark.asyncio
async def test_prompt_analysis_samples(test_case):
    """Parameterized test for various prompt samples"""
    service = PromptAnalysisService()
    result = await service.analyze_prompt(test_case["prompt"])
    
    assert result.domain == test_case["expected_domain"]
    
    # Check entities
    for expected_entity in test_case["expected_entities"]:
        assert expected_entity in result.entities, f"Expected entity '{expected_entity}' not found"
    
    # Check features
    for expected_feature in test_case["expected_features"]:
        assert expected_feature in result.features, f"Expected feature '{expected_feature}' not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
