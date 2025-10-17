"""
Tests for GenerationService - version tracking and generation management.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.generation import Generation
from app.models.project import Project
from app.models.user import User
from app.services.generation_service import (
    GenerationService, 
    GenerationServiceError,
    GenerationNotFoundError,
    ProjectNotFoundError
)
from app.services.file_manager import FileManager


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_engine():
    """Create async test engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def async_db(async_engine):
    """Create async test session"""
    async_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def file_manager(temp_storage, monkeypatch):
    """Create FileManager with temp storage"""
    # Patch settings to use temp directory
    monkeypatch.setattr("app.services.file_manager.settings.FILE_STORAGE_PATH", temp_storage)
    monkeypatch.setattr("app.services.file_manager.settings.TEMP_STORAGE_PATH", temp_storage)
    return FileManager()


@pytest.fixture
async def test_user(async_db):
    """Create test user"""
    user = User(
        id=str(uuid4()),
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        is_active=True
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest.fixture
async def test_project(async_db, test_user):
    """Create test project"""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        description="Test project for generation versioning",
        user_id=test_user.id
    )
    async_db.add(project)
    await async_db.commit()
    await async_db.refresh(project)
    return project


class TestGenerationService:
    """Test suite for GenerationService"""
    
    @pytest.mark.asyncio
    async def test_create_generation_auto_versioning(self, async_db, file_manager, test_project, test_user):
        """Test that create_generation auto-assigns version numbers"""
        service = GenerationService(async_db, file_manager)
        
        # Create first generation
        gen1 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="Create a REST API"
        )
        
        assert gen1.version == 1
        assert gen1.project_id == test_project.id
        assert gen1.is_active == False
        
        # Create second generation
        gen2 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="Add authentication"
        )
        
        assert gen2.version == 2
        assert gen2.project_id == test_project.id
        
        # Create third generation
        gen3 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="Add database"
        )
        
        assert gen3.version == 3
    
    @pytest.mark.asyncio
    async def test_save_generation_output_hierarchical_storage(
        self, async_db, file_manager, test_project, test_user, temp_storage
    ):
        """Test save_generation_output creates hierarchical storage"""
        service = GenerationService(async_db, file_manager)
        
        # Create generation
        generation = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="Create a REST API"
        )
        
        # Save output
        files = {
            "app/main.py": "from fastapi import FastAPI\napp = FastAPI()",
            "app/models.py": "# Models",
            "README.md": "# Project"
        }
        
        saved_gen = await service.save_generation_output(
            generation_id=str(generation.id),
            files=files,
            extracted_schema={"models": ["User", "Post"]},
            documentation={"readme": "API documentation"},
            auto_activate=True
        )
        
        # Verify database updates
        assert saved_gen.status == "completed"
        assert saved_gen.file_count == 3
        assert saved_gen.total_size_bytes > 0
        assert saved_gen.is_active == True
        assert saved_gen.storage_path is not None
        
        # Verify hierarchical path structure
        expected_path = f"{test_project.id}/generations/v1__{generation.id}"
        assert expected_path in saved_gen.storage_path
        
        # Verify files exist on disk
        storage_path = Path(temp_storage) / test_project.id / "generations" / f"v1__{generation.id}"
        assert storage_path.exists()
        assert (storage_path / "source" / "app" / "main.py").exists()
        assert (storage_path / "manifest.json").exists()
        
        # Verify manifest content
        import json
        with open(storage_path / "manifest.json") as f:
            manifest = json.load(f)
        
        assert manifest["version"] == 1
        assert manifest["generation_id"] == str(generation.id)
        assert manifest["file_count"] == 3
        assert "files" in manifest
    
    @pytest.mark.asyncio
    async def test_save_generation_creates_diff(
        self, async_db, file_manager, test_project, test_user
    ):
        """Test that second generation creates diff from first"""
        service = GenerationService(async_db, file_manager)
        
        # Create and save first generation
        gen1 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="Create initial API"
        )
        
        files_v1 = {
            "app/main.py": "from fastapi import FastAPI\napp = FastAPI()",
            "README.md": "# Version 1"
        }
        
        await service.save_generation_output(
            generation_id=str(gen1.id),
            files=files_v1,
            auto_activate=True
        )
        
        # Create and save second generation
        gen2 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="Add authentication"
        )
        
        files_v2 = {
            "app/main.py": "from fastapi import FastAPI\nfrom app.auth import router\napp = FastAPI()\napp.include_router(router)",
            "app/auth.py": "# Authentication module",
            "README.md": "# Version 2"
        }
        
        saved_gen2 = await service.save_generation_output(
            generation_id=str(gen2.id),
            files=files_v2,
            auto_activate=True
        )
        
        # Verify diff was created
        assert saved_gen2.diff_from_previous is not None
        assert len(saved_gen2.diff_from_previous) > 0
        
        # Verify changes summary
        assert saved_gen2.changes_summary is not None
        assert "files_added" in saved_gen2.changes_summary
        assert "files_modified" in saved_gen2.changes_summary
    
    @pytest.mark.asyncio
    async def test_set_active_generation(self, async_db, file_manager, test_project, test_user):
        """Test set_active_generation updates DB and creates symlink"""
        service = GenerationService(async_db, file_manager)
        
        # Create two generations
        gen1 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="Version 1"
        )
        gen1.status = "completed"
        await async_db.commit()
        
        gen2 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="Version 2"
        )
        gen2.status = "completed"
        await async_db.commit()
        
        # Activate gen1
        await service.set_active_generation(test_project.id, str(gen1.id))
        
        await async_db.refresh(gen1)
        await async_db.refresh(gen2)
        await async_db.refresh(test_project)
        
        assert gen1.is_active == True
        assert gen2.is_active == False
        assert test_project.active_generation_id == gen1.id
        
        # Switch to gen2
        await service.set_active_generation(test_project.id, str(gen2.id))
        
        await async_db.refresh(gen1)
        await async_db.refresh(gen2)
        await async_db.refresh(test_project)
        
        assert gen1.is_active == False
        assert gen2.is_active == True
        assert test_project.active_generation_id == gen2.id
    
    @pytest.mark.asyncio
    async def test_get_generation_by_version(self, async_db, file_manager, test_project, test_user):
        """Test retrieving generation by version number"""
        service = GenerationService(async_db, file_manager)
        
        # Create multiple generations
        gen1 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="V1"
        )
        
        gen2 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="V2"
        )
        
        gen3 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="V3"
        )
        
        # Test retrieval
        retrieved_v1 = await service.get_generation_by_version(test_project.id, 1)
        assert retrieved_v1.id == gen1.id
        assert retrieved_v1.version == 1
        
        retrieved_v2 = await service.get_generation_by_version(test_project.id, 2)
        assert retrieved_v2.id == gen2.id
        assert retrieved_v2.version == 2
        
        retrieved_v3 = await service.get_generation_by_version(test_project.id, 3)
        assert retrieved_v3.id == gen3.id
        assert retrieved_v3.version == 3
        
        # Test non-existent version
        with pytest.raises(GenerationNotFoundError):
            await service.get_generation_by_version(test_project.id, 99)
    
    @pytest.mark.asyncio
    async def test_get_active_generation(self, async_db, file_manager, test_project, test_user):
        """Test retrieving active generation"""
        service = GenerationService(async_db, file_manager)
        
        # No active generation initially
        active = await service.get_active_generation(test_project.id)
        assert active is None
        
        # Create and activate generation
        gen1 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="Active version"
        )
        gen1.status = "completed"
        await async_db.commit()
        
        await service.set_active_generation(test_project.id, str(gen1.id))
        
        # Retrieve active generation
        active = await service.get_active_generation(test_project.id)
        assert active is not None
        assert active.id == gen1.id
        assert active.is_active == True
    
    @pytest.mark.asyncio
    async def test_list_project_generations(self, async_db, file_manager, test_project, test_user):
        """Test listing all generations for a project"""
        service = GenerationService(async_db, file_manager)
        
        # Create multiple generations with different statuses
        gen1 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="V1"
        )
        gen1.status = "completed"
        
        gen2 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="V2"
        )
        gen2.status = "failed"
        
        gen3 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="V3"
        )
        gen3.status = "completed"
        
        await async_db.commit()
        
        # List all generations (excluding failed)
        generations = await service.list_project_generations(test_project.id, include_failed=False)
        assert len(generations) == 2
        assert all(g.status != "failed" for g in generations)
        
        # List all generations (including failed)
        all_generations = await service.list_project_generations(test_project.id, include_failed=True)
        assert len(all_generations) == 3
        
        # Verify ordering (newest first)
        assert all_generations[0].version == 3
        assert all_generations[1].version == 2
        assert all_generations[2].version == 1
    
    @pytest.mark.asyncio
    async def test_compare_generations(self, async_db, file_manager, test_project, test_user, temp_storage):
        """Test comparing two generations"""
        service = GenerationService(async_db, file_manager)
        
        # Create first generation
        gen1 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="V1"
        )
        
        files_v1 = {
            "app/main.py": "print('v1')",
            "app/utils.py": "def util(): pass"
        }
        
        await service.save_generation_output(
            generation_id=str(gen1.id),
            files=files_v1
        )
        
        # Create second generation
        gen2 = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="V2"
        )
        
        files_v2 = {
            "app/main.py": "print('v2')",  # Modified
            "app/models.py": "# New file"   # Added
            # utils.py removed
        }
        
        await service.save_generation_output(
            generation_id=str(gen2.id),
            files=files_v2
        )
        
        # Compare versions
        comparison = await service.compare_generations(test_project.id, 1, 2)
        
        assert comparison is not None
        assert "from_generation" in comparison
        assert "to_generation" in comparison
        assert comparison["from_generation"].version == 1
        assert comparison["to_generation"].version == 2
        
        # Verify change detection
        assert "files_added" in comparison
        assert "files_removed" in comparison
        assert "files_modified" in comparison
        
        assert "app/models.py" in comparison["files_added"]
        assert "app/utils.py" in comparison["files_removed"]
        assert "app/main.py" in comparison["files_modified"]
    
    @pytest.mark.asyncio
    async def test_update_generation_status(self, async_db, file_manager, test_project, test_user):
        """Test updating generation status"""
        service = GenerationService(async_db, file_manager)
        
        gen = await service.create_generation(
            project_id=test_project.id,
            user_id=test_user.id,
            prompt="Test"
        )
        
        assert gen.status == "pending"
        
        # Update to processing
        await service.update_generation_status(str(gen.id), "processing")
        await async_db.refresh(gen)
        assert gen.status == "processing"
        
        # Update to completed
        await service.update_generation_status(str(gen.id), "completed")
        await async_db.refresh(gen)
        assert gen.status == "completed"
        
        # Update to failed with error message
        await service.update_generation_status(str(gen.id), "failed", "Test error")
        await async_db.refresh(gen)
        assert gen.status == "failed"
        assert gen.error_message == "Test error"
    
    @pytest.mark.asyncio
    async def test_error_handling_nonexistent_project(self, async_db, file_manager, test_user):
        """Test error handling for non-existent project"""
        service = GenerationService(async_db, file_manager)
        
        with pytest.raises(ProjectNotFoundError):
            await service.create_generation(
                project_id="non-existent-project-id",
                user_id=test_user.id,
                prompt="Test"
            )
    
    @pytest.mark.asyncio
    async def test_error_handling_nonexistent_generation(self, async_db, file_manager):
        """Test error handling for non-existent generation"""
        service = GenerationService(async_db, file_manager)
        
        with pytest.raises(GenerationNotFoundError):
            await service.update_generation_status("non-existent-gen-id", "completed")
    
    @pytest.mark.asyncio
    async def test_version_persistence_across_sessions(self, async_engine, file_manager, test_project, test_user):
        """Test that version numbers persist across sessions"""
        
        # Session 1: Create gen1
        async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            service = GenerationService(session, file_manager)
            gen1 = await service.create_generation(
                project_id=test_project.id,
                user_id=test_user.id,
                prompt="V1"
            )
            assert gen1.version == 1
        
        # Session 2: Create gen2
        async with async_session() as session:
            service = GenerationService(session, file_manager)
            gen2 = await service.create_generation(
                project_id=test_project.id,
                user_id=test_user.id,
                prompt="V2"
            )
            assert gen2.version == 2
        
        # Session 3: Verify both exist with correct versions
        async with async_session() as session:
            service = GenerationService(session, file_manager)
            all_gens = await service.list_project_generations(test_project.id, include_failed=True)
            assert len(all_gens) == 2
            versions = [g.version for g in all_gens]
            assert 1 in versions
            assert 2 in versions
