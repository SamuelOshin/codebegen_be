
"""
Unit Tests for Gemini Phased Generator

Tests the phased generation strategy that breaks down code generation
into multiple phases to maintain quality while respecting token limits.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.llm_providers.gemini_phased_generator import GeminiPhasedGenerator
from app.services.llm_providers.base_provider import LLMTask


@pytest.fixture
def mock_gemini_provider():
    """Create a mock Gemini provider"""
    provider = AsyncMock()
    provider.generate_completion = AsyncMock()
    provider._extract_json = MagicMock()
    return provider


@pytest.fixture
def phased_generator(mock_gemini_provider):
    """Create a phased generator instance"""
    return GeminiPhasedGenerator(mock_gemini_provider)


@pytest.fixture
def sample_schema():
    """Sample schema with 3 entities"""
    return {
        "entities": [
            {
                "name": "User",
                "fields": [
                    {"name": "email", "type": "string", "required": True},
                    {"name": "password", "type": "string", "required": True},
                    {"name": "full_name", "type": "string", "required": False}
                ],
                "relationships": []
            },
            {
                "name": "Post",
                "fields": [
                    {"name": "title", "type": "string", "required": True},
                    {"name": "content", "type": "text", "required": True},
                    {"name": "user_id", "type": "integer", "required": True}
                ],
                "relationships": [
                    {"type": "many_to_one", "target": "User"}
                ]
            },
            {
                "name": "Comment",
                "fields": [
                    {"name": "content", "type": "text", "required": True},
                    {"name": "post_id", "type": "integer", "required": True},
                    {"name": "user_id", "type": "integer", "required": True}
                ],
                "relationships": [
                    {"type": "many_to_one", "target": "Post"},
                    {"type": "many_to_one", "target": "User"}
                ]
            }
        ],
        "endpoints": [
            {"path": "/users", "method": "GET", "entity": "User"},
            {"path": "/posts", "method": "GET", "entity": "Post"}
        ]
    }


@pytest.fixture
def sample_context():
    """Sample context"""
    return {
        "tech_stack": "fastapi_postgres",
        "domain": "social_media",
        "requires_auth": True
    }


class TestPhasedGeneratorInitialization:
    """Test phased generator initialization"""
    
    def test_create_generator(self, mock_gemini_provider):
        """Test creating a phased generator"""
        generator = GeminiPhasedGenerator(mock_gemini_provider)
        assert generator.provider == mock_gemini_provider


class TestCoreInfrastructureGeneration:
    """Test Phase 1: Core infrastructure generation"""
    
    @pytest.mark.asyncio
    async def test_generate_core_infrastructure(
        self,
        phased_generator,
        mock_gemini_provider,
        sample_schema,
        sample_context
    ):
        """Test generating core infrastructure files"""
        # Mock response
        mock_response = '{"app/core/config.py": "# Config code", "app/core/database.py": "# Database code"}'
        expected_files = {
            "app/core/config.py": "# Config code",
            "app/core/database.py": "# Database code"
        }
        
        mock_gemini_provider.generate_completion.return_value = mock_response
        mock_gemini_provider._extract_json.return_value = expected_files
        
        # Generate
        result = await phased_generator._generate_core_infrastructure(
            sample_schema,
            sample_context
        )
        
        # Verify
        assert result == expected_files
        mock_gemini_provider.generate_completion.assert_called_once()
        call_args = mock_gemini_provider.generate_completion.call_args
        assert call_args.kwargs['task'] == LLMTask.CODE_GENERATION
        assert call_args.kwargs['temperature'] == 0.2


class TestModelGeneration:
    """Test model generation for entities"""
    
    @pytest.mark.asyncio
    async def test_generate_model(
        self,
        phased_generator,
        mock_gemini_provider,
        sample_schema,
        sample_context
    ):
        """Test generating SQLAlchemy model"""
        entity = sample_schema['entities'][0]  # User entity
        
        mock_response = '{"app/models/user.py": "# User model code"}'
        expected_files = {"app/models/user.py": "# User model code"}
        
        mock_gemini_provider.generate_completion.return_value = mock_response
        mock_gemini_provider._extract_json.return_value = expected_files
        
        result = await phased_generator._generate_model(
            entity,
            sample_schema,
            sample_context
        )
        
        assert result == expected_files
        # Verify prompt contains entity name
        call_args = mock_gemini_provider.generate_completion.call_args
        assert "User" in call_args.args[0]


class TestSchemaGeneration:
    """Test Pydantic schema generation"""
    
    @pytest.mark.asyncio
    async def test_generate_schema(
        self,
        phased_generator,
        mock_gemini_provider,
        sample_schema,
        sample_context
    ):
        """Test generating Pydantic schemas"""
        entity = sample_schema['entities'][1]  # Post entity
        
        mock_response = '{"app/schemas/post.py": "# Post schemas"}'
        expected_files = {"app/schemas/post.py": "# Post schemas"}
        
        mock_gemini_provider.generate_completion.return_value = mock_response
        mock_gemini_provider._extract_json.return_value = expected_files
        
        result = await phased_generator._generate_schema(
            entity,
            sample_context
        )
        
        assert result == expected_files
        call_args = mock_gemini_provider.generate_completion.call_args
        assert "Post" in call_args.args[0]
        assert "PostBase" in call_args.args[0]


class TestRepositoryGeneration:
    """Test repository pattern generation"""
    
    @pytest.mark.asyncio
    async def test_generate_repository(
        self,
        phased_generator,
        mock_gemini_provider,
        sample_schema,
        sample_context
    ):
        """Test generating repository class"""
        entity = sample_schema['entities'][0]  # User entity
        
        mock_response = '{"app/repositories/user_repository.py": "# User repository"}'
        expected_files = {"app/repositories/user_repository.py": "# User repository"}
        
        mock_gemini_provider.generate_completion.return_value = mock_response
        mock_gemini_provider._extract_json.return_value = expected_files
        
        result = await phased_generator._generate_repository(
            entity,
            sample_context
        )
        
        assert result == expected_files
        call_args = mock_gemini_provider.generate_completion.call_args
        assert "UserRepository" in call_args.args[0]
        assert "get_by_id" in call_args.args[0]
        assert "create" in call_args.args[0]


class TestRouterGeneration:
    """Test API router generation"""
    
    @pytest.mark.asyncio
    async def test_generate_router(
        self,
        phased_generator,
        mock_gemini_provider,
        sample_schema,
        sample_context
    ):
        """Test generating FastAPI router"""
        entity = sample_schema['entities'][1]  # Post entity
        
        mock_response = '{"app/routers/posts.py": "# Posts router"}'
        expected_files = {"app/routers/posts.py": "# Posts router"}
        
        mock_gemini_provider.generate_completion.return_value = mock_response
        mock_gemini_provider._extract_json.return_value = expected_files
        
        result = await phased_generator._generate_router(
            entity,
            sample_schema,
            sample_context
        )
        
        assert result == expected_files
        call_args = mock_gemini_provider.generate_completion.call_args
        assert "/posts" in call_args.args[0]
        assert "get_post" in call_args.args[0] or "list_posts" in call_args.args[0]


class TestSupportFilesGeneration:
    """Test support files generation"""
    
    @pytest.mark.asyncio
    async def test_generate_support_files(
        self,
        phased_generator,
        mock_gemini_provider,
        sample_schema,
        sample_context
    ):
        """Test generating support files (requirements, README, etc.)"""
        entities = sample_schema['entities']
        
        mock_response = '''{
            "requirements.txt": "fastapi==0.104.1",
            "README.md": "# Project",
            ".env.example": "DATABASE_URL=..."
        }'''
        expected_files = {
            "requirements.txt": "fastapi==0.104.1",
            "README.md": "# Project",
            ".env.example": "DATABASE_URL=..."
        }
        
        mock_gemini_provider.generate_completion.return_value = mock_response
        mock_gemini_provider._extract_json.return_value = expected_files
        
        result = await phased_generator._generate_support_files(
            sample_schema,
            sample_context,
            entities
        )
        
        assert result == expected_files
        call_args = mock_gemini_provider.generate_completion.call_args
        assert "requirements.txt" in call_args.args[0]


class TestMainAppGeneration:
    """Test main application generation"""
    
    @pytest.mark.asyncio
    async def test_generate_main_app(
        self,
        phased_generator,
        mock_gemini_provider,
        sample_schema,
        sample_context
    ):
        """Test generating main application file"""
        entities = sample_schema['entities']
        
        mock_response = '{"main.py": "# FastAPI app", "app/routers/__init__.py": "# Routers"}'
        expected_files = {
            "main.py": "# FastAPI app",
            "app/routers/__init__.py": "# Routers"
        }
        
        mock_gemini_provider.generate_completion.return_value = mock_response
        mock_gemini_provider._extract_json.return_value = expected_files
        
        result = await phased_generator._generate_main_app(
            entities,
            sample_context
        )
        
        assert result == expected_files
        call_args = mock_gemini_provider.generate_completion.call_args
        assert "main.py" in call_args.args[0]


class TestCompleteProjectGeneration:
    """Test complete project generation flow"""
    
    @pytest.mark.asyncio
    async def test_generate_complete_project(
        self,
        phased_generator,
        mock_gemini_provider,
        sample_schema,
        sample_context
    ):
        """Test generating a complete project through all phases"""
        prompt = "Create a blog platform with users, posts, and comments"
        
        # Mock all phase responses
        mock_gemini_provider.generate_completion.return_value = '{}'
        mock_gemini_provider._extract_json.side_effect = [
            # Phase 1: Core
            {"app/core/config.py": "# Config"},
            # Phase 2-4: Per entity (User, Post, Comment) x 4 files each
            {"app/models/user.py": "# User model"},
            {"app/schemas/user.py": "# User schema"},
            {"app/repositories/user_repository.py": "# User repo"},
            {"app/routers/users.py": "# User router"},
            {"app/models/post.py": "# Post model"},
            {"app/schemas/post.py": "# Post schema"},
            {"app/repositories/post_repository.py": "# Post repo"},
            {"app/routers/posts.py": "# Post router"},
            {"app/models/comment.py": "# Comment model"},
            {"app/schemas/comment.py": "# Comment schema"},
            {"app/repositories/comment_repository.py": "# Comment repo"},
            {"app/routers/comments.py": "# Comment router"},
            # Phase 5: Support files
            {"requirements.txt": "fastapi==0.104.1"},
            # Phase 6: Main app
            {"main.py": "# FastAPI app"}
        ]
        
        result = await phased_generator.generate_complete_project(
            prompt,
            sample_schema,
            sample_context
        )
        
        # Should have files from all phases
        assert len(result) > 10
        assert "app/core/config.py" in result
        assert "app/models/user.py" in result
        assert "app/routers/posts.py" in result
        assert "requirements.txt" in result
        assert "main.py" in result


class TestHelperMethods:
    """Test helper/utility methods"""
    
    def test_format_fields(self, phased_generator):
        """Test field formatting"""
        fields = [
            {"name": "email", "type": "string", "required": True},
            {"name": "age", "type": "integer", "required": False}
        ]
        
        result = phased_generator._format_fields(fields)
        
        assert "email" in result
        assert "string" in result
        assert "required" in result
        assert "age" in result
        assert "optional" in result
    
    def test_format_relationships(self, phased_generator):
        """Test relationship formatting"""
        relationships = [
            {"type": "many_to_one", "target": "User"},
            {"type": "one_to_many", "target": "Post"}
        ]
        
        result = phased_generator._format_relationships(relationships)
        
        assert "User" in result
        assert "Post" in result
        assert "many_to_one" in result
    
    def test_format_relationships_empty(self, phased_generator):
        """Test formatting empty relationships"""
        result = phased_generator._format_relationships([])
        assert result == "None"
    
    def test_format_endpoints(self, phased_generator):
        """Test endpoint formatting"""
        endpoints = [
            {"method": "GET", "path": "/users", "description": "List users"},
            {"method": "POST", "path": "/users", "description": "Create user"}
        ]
        
        result = phased_generator._format_endpoints(endpoints)
        
        assert "GET" in result
        assert "/users" in result
        assert "List users" in result
