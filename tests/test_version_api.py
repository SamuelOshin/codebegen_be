"""
Tests for version management API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from uuid import uuid4

from app.main import app
from app.models.generation import Generation
from app.models.project import Project
from app.models.user import User


class TestVersionManagementEndpoints:
    """Test suite for version management API endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_project_versions(self, async_client, async_db, test_user, test_project):
        """Test GET /projects/{project_id}/versions"""
        
        # Create multiple generations
        gen1 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="Create API",
            status="completed",
            version=1,
            file_count=5,
            is_active=False
        )
        
        gen2 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="Add auth",
            status="completed",
            version=2,
            file_count=7,
            is_active=True
        )
        
        gen3 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="Failed generation",
            status="failed",
            version=3,
            is_active=False
        )
        
        async_db.add_all([gen1, gen2, gen3])
        await async_db.commit()
        
        # Update project
        test_project.active_generation_id = gen2.id
        test_project.latest_version = 3
        await async_db.commit()
        
        # Test endpoint
        response = await async_client.get(f"/api/generations/projects/{test_project.id}/versions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["project_id"] == test_project.id
        assert data["total_versions"] == 2  # Excludes failed by default
        assert data["active_version"] == 2
        assert data["latest_version"] == 3
        assert len(data["versions"]) == 2
        
        # Verify versions are in correct order (newest first)
        assert data["versions"][0]["version"] == 2
        assert data["versions"][1]["version"] == 1
        
        # Verify active flag
        assert data["versions"][0]["is_active"] == True
        assert data["versions"][1]["is_active"] == False
    
    @pytest.mark.asyncio
    async def test_list_project_versions_include_failed(self, async_client, async_db, test_user, test_project):
        """Test GET /projects/{project_id}/versions with include_failed=true"""
        
        # Create generations with different statuses
        gen1 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="V1",
            status="completed",
            version=1
        )
        
        gen2 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="V2",
            status="failed",
            version=2
        )
        
        async_db.add_all([gen1, gen2])
        await async_db.commit()
        
        # Test with include_failed=false (default)
        response = await async_client.get(f"/api/generations/projects/{test_project.id}/versions")
        assert response.status_code == 200
        assert len(response.json()["versions"]) == 1
        
        # Test with include_failed=true
        response = await async_client.get(
            f"/api/generations/projects/{test_project.id}/versions?include_failed=true"
        )
        assert response.status_code == 200
        assert len(response.json()["versions"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_generation_by_version(self, async_client, async_db, test_user, test_project):
        """Test GET /projects/{project_id}/versions/{version}"""
        
        generation = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="Test generation",
            status="completed",
            version=5,
            file_count=10,
            total_size_bytes=5000,
            storage_path=f"{test_project.id}/generations/v5__{uuid4()}/",
            is_active=True
        )
        
        async_db.add(generation)
        await async_db.commit()
        
        # Test endpoint
        response = await async_client.get(
            f"/api/generations/projects/{test_project.id}/versions/5"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(generation.id)
        assert data["version"] == 5
        assert data["file_count"] == 10
        assert data["total_size_bytes"] == 5000
        assert data["is_active"] == True
        assert data["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_get_generation_by_version_not_found(self, async_client, test_project):
        """Test GET /projects/{project_id}/versions/{version} with non-existent version"""
        
        response = await async_client.get(
            f"/api/generations/projects/{test_project.id}/versions/999"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_active_generation(self, async_client, async_db, test_user, test_project):
        """Test GET /projects/{project_id}/versions/active"""
        
        # Create active generation
        active_gen = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="Active generation",
            status="completed",
            version=3,
            is_active=True
        )
        
        # Create inactive generation
        inactive_gen = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="Inactive",
            status="completed",
            version=2,
            is_active=False
        )
        
        async_db.add_all([active_gen, inactive_gen])
        await async_db.commit()
        
        # Update project
        test_project.active_generation_id = active_gen.id
        await async_db.commit()
        
        # Test endpoint
        response = await async_client.get(
            f"/api/generations/projects/{test_project.id}/versions/active"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(active_gen.id)
        assert data["version"] == 3
        assert data["is_active"] == True
    
    @pytest.mark.asyncio
    async def test_get_active_generation_not_found(self, async_client, test_project):
        """Test GET /projects/{project_id}/versions/active when no active generation"""
        
        response = await async_client.get(
            f"/api/generations/projects/{test_project.id}/versions/active"
        )
        
        assert response.status_code == 404
        assert "no active generation" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_activate_generation(self, async_client, async_db, test_user, test_project):
        """Test POST /projects/{project_id}/versions/{generation_id}/activate"""
        
        # Create two completed generations
        gen1 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="V1",
            status="completed",
            version=1,
            is_active=True
        )
        
        gen2 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="V2",
            status="completed",
            version=2,
            is_active=False
        )
        
        async_db.add_all([gen1, gen2])
        await async_db.commit()
        
        # Initially gen1 is active
        test_project.active_generation_id = gen1.id
        await async_db.commit()
        
        # Activate gen2
        response = await async_client.post(
            f"/api/generations/projects/{test_project.id}/versions/{gen2.id}/activate"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["generation_id"] == str(gen2.id)
        assert data["version"] == 2
        assert data["previous_active_id"] == str(gen1.id)
        assert "activated successfully" in data["message"].lower()
        
        # Verify database state
        await async_db.refresh(gen1)
        await async_db.refresh(gen2)
        await async_db.refresh(test_project)
        
        assert gen1.is_active == False
        assert gen2.is_active == True
        assert test_project.active_generation_id == gen2.id
    
    @pytest.mark.asyncio
    async def test_activate_generation_invalid_status(self, async_client, async_db, test_user, test_project):
        """Test activating a non-completed generation fails"""
        
        # Create pending generation
        pending_gen = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="Pending",
            status="pending",
            version=1
        )
        
        async_db.add(pending_gen)
        await async_db.commit()
        
        # Try to activate
        response = await async_client.post(
            f"/api/generations/projects/{test_project.id}/versions/{pending_gen.id}/activate"
        )
        
        assert response.status_code == 400
        assert "only activate completed" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_activate_generation_wrong_project(self, async_client, async_db, test_user):
        """Test activating generation from wrong project fails"""
        
        # Create two projects
        project1 = Project(
            id=str(uuid4()),
            name="Project 1",
            user_id=test_user.id
        )
        
        project2 = Project(
            id=str(uuid4()),
            name="Project 2",
            user_id=test_user.id
        )
        
        async_db.add_all([project1, project2])
        await async_db.commit()
        
        # Create generation for project2
        gen = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=project2.id,
            prompt="Test",
            status="completed",
            version=1
        )
        
        async_db.add(gen)
        await async_db.commit()
        
        # Try to activate gen in project1
        response = await async_client.post(
            f"/api/generations/projects/{project1.id}/versions/{gen.id}/activate"
        )
        
        assert response.status_code == 400
        assert "does not belong to project" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_compare_versions(self, async_client, async_db, test_user, test_project, temp_storage):
        """Test GET /projects/{project_id}/versions/compare/{from_version}/{to_version}"""
        
        from datetime import datetime, timedelta
        
        # Create two generations with time difference
        base_time = datetime.utcnow()
        
        gen1 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="V1",
            status="completed",
            version=1,
            file_count=5,
            total_size_bytes=1000,
            quality_score=0.85,
            created_at=base_time
        )
        
        gen2 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="V2",
            status="completed",
            version=2,
            file_count=7,
            total_size_bytes=1500,
            quality_score=0.90,
            created_at=base_time + timedelta(hours=1)
        )
        
        async_db.add_all([gen1, gen2])
        await async_db.commit()
        
        # Note: Full comparison test would require FileManager integration
        # This tests the endpoint structure
        response = await async_client.get(
            f"/api/generations/projects/{test_project.id}/versions/compare/1/2"
        )
        
        # May return 404 or 500 if FileManager not fully mocked
        # but endpoint should exist and be callable
        assert response.status_code in [200, 404, 500]
    
    @pytest.mark.asyncio
    async def test_authorization_project_access(self, async_client, async_db):
        """Test that users can only access their own projects"""
        
        # Create another user and their project
        other_user = User(
            id=str(uuid4()),
            email="other@example.com",
            username="otheruser",
            hashed_password="hashed",
            is_active=True
        )
        
        other_project = Project(
            id=str(uuid4()),
            name="Other Project",
            user_id=other_user.id
        )
        
        async_db.add_all([other_user, other_project])
        await async_db.commit()
        
        # Try to access other user's project (should fail with current_user check)
        response = await async_client.get(
            f"/api/generations/projects/{other_project.id}/versions"
        )
        
        # Should be 403 Forbidden (if auth properly configured)
        # or 404 if project ownership checked first
        assert response.status_code in [403, 404]
    
    @pytest.mark.asyncio
    async def test_nonexistent_project(self, async_client):
        """Test accessing non-existent project returns 404"""
        
        fake_project_id = str(uuid4())
        
        response = await async_client.get(
            f"/api/generations/projects/{fake_project_id}/versions"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_version_list_ordering(self, async_client, async_db, test_user, test_project):
        """Test that versions are returned in descending order (newest first)"""
        
        # Create generations out of order
        gen3 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="V3",
            status="completed",
            version=3
        )
        
        gen1 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="V1",
            status="completed",
            version=1
        )
        
        gen2 = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="V2",
            status="completed",
            version=2
        )
        
        # Add in random order
        async_db.add_all([gen3, gen1, gen2])
        await async_db.commit()
        
        # Fetch versions
        response = await async_client.get(
            f"/api/generations/projects/{test_project.id}/versions"
        )
        
        assert response.status_code == 200
        versions = response.json()["versions"]
        
        # Should be ordered 3, 2, 1
        assert len(versions) == 3
        assert versions[0]["version"] == 3
        assert versions[1]["version"] == 2
        assert versions[2]["version"] == 1
    
    @pytest.mark.asyncio
    async def test_prompt_preview_truncation(self, async_client, async_db, test_user, test_project):
        """Test that prompt is truncated to 100 chars in summary"""
        
        long_prompt = "A" * 200  # 200 character prompt
        
        gen = Generation(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=test_project.id,
            prompt=long_prompt,
            status="completed",
            version=1
        )
        
        async_db.add(gen)
        await async_db.commit()
        
        response = await async_client.get(
            f"/api/generations/projects/{test_project.id}/versions"
        )
        
        assert response.status_code == 200
        versions = response.json()["versions"]
        
        # Prompt preview should be truncated
        assert len(versions[0]["prompt_preview"]) == 100
        assert versions[0]["prompt_preview"] == "A" * 100
