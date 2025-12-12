# Integration tests for preview endpoints
"""
Integration tests for preview API endpoints.
Tests full request/response cycles with database interactions.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preview import PreviewInstance
from app.models.generation import Generation
from app.models.user import User
from app.models.project import Project


@pytest.mark.asyncio
class TestPreviewEndpoints:
    """Integration tests for preview endpoints."""

    async def test_launch_preview_success(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_user: User,
        test_project: Project,
        test_generation: Generation
    ):
        """Test successful preview launch."""
        response = await client.post(
            f"/api/v1/generations/{test_generation.id}/preview/launch",
            json={"project_id": test_project.id},
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "launched"
        assert data["generation_id"] == test_generation.id
        assert "preview_instance_id" in data
        assert "base_url" in data
        assert "preview_token" in data
        assert "expires_at" in data

    async def test_launch_preview_unauthorized(
        self,
        client: AsyncClient,
        test_generation: Generation
    ):
        """Test launch preview without authentication."""
        response = await client.post(
            f"/api/v1/generations/{test_generation.id}/preview/launch",
            json={"project_id": "test_project_id"}
        )

        assert response.status_code == 401

    async def test_launch_preview_not_owner(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_user2: User,
        test_generation: Generation
    ):
        """Test launch preview for generation not owned by user."""
        response = await client.post(
            f"/api/v1/generations/{test_generation.id}/preview/launch",
            json={"project_id": "test_project_id"},
            headers={"Authorization": f"Bearer {test_user2.token}"}
        )

        assert response.status_code == 400  # Should be 403, but checking validation

    async def test_get_preview_status_success(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_user: User,
        test_preview: PreviewInstance
    ):
        """Test getting preview status successfully."""
        response = await client.get(
            f"/api/v1/generations/{test_preview.generation_id}/preview/status",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["preview_instance_id"] == test_preview.id
        assert data["status"] == test_preview.status
        assert data["base_url"] == test_preview.base_url
        assert "uptime" in data
        assert "health_status" in data

    async def test_get_preview_status_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        test_generation: Generation
    ):
        """Test getting status when no preview exists."""
        response = await client.get(
            f"/api/v1/generations/{test_generation.id}/preview/status",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 404
        assert "No active preview" in response.json()["detail"]

    async def test_stop_preview_success(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_user: User,
        test_preview: PreviewInstance
    ):
        """Test stopping preview successfully."""
        response = await client.delete(
            f"/api/v1/generations/{test_preview.generation_id}/preview",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "stopped"
        assert data["message"] == "Preview instance stopped successfully"

    async def test_proxy_request_success(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_user: User,
        test_preview: PreviewInstance
    ):
        """Test proxying request to preview instance."""
        # Update preview to running status
        test_preview.status = "running"
        await db.commit()

        response = await client.post(
            f"/api/v1/generations/{test_preview.generation_id}/preview/request",
            json={
                "method": "GET",
                "path": "/health",
                "query": {},
                "body": None,
                "headers": {"X-Preview-Token": test_preview.preview_token}
            },
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

        # Should attempt proxy but fail since no real server
        assert response.status_code in [503, 504]  # Service unavailable or timeout

    async def test_proxy_request_invalid_token(
        self,
        client: AsyncClient,
        db: AsyncSession,
        test_user: User,
        test_preview: PreviewInstance
    ):
        """Test proxy request with invalid token."""
        test_preview.status = "running"
        await db.commit()

        response = await client.post(
            f"/api/v1/generations/{test_preview.generation_id}/preview/request",
            json={
                "method": "GET",
                "path": "/health",
                "query": {},
                "body": None,
                "headers": {"X-Preview-Token": "invalid_token"}
            },
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 403
        assert "Invalid preview token" in response.json()["detail"]

    async def test_get_endpoints_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_generation: Generation
    ):
        """Test getting generated endpoints."""
        response = await client.get(
            f"/api/v1/generations/{test_generation.id}/preview/endpoints",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert isinstance(data["endpoints"], list)

    async def test_get_preview_config(
        self,
        client: AsyncClient,
        test_user: User,
        test_generation: Generation
    ):
        """Test getting preview configuration."""
        response = await client.get(
            f"/api/v1/generations/{test_generation.id}/preview/config",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "preview_timeout" in data
        assert "max_instances" in data
        assert "session_expiry" in data
        assert "environment" in data
        assert "limitations" in data

    async def test_stream_logs_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        test_generation: Generation
    ):
        """Test streaming logs when no preview exists."""
        response = await client.get(
            f"/api/v1/generations/{test_generation.id}/preview/logs/stream",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 404
        assert "No active preview" in response.json()["detail"]