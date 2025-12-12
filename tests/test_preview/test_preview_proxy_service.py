# Unit tests for PreviewProxyService
"""
Unit tests for PreviewProxyService class.
Tests HTTP proxy functionality for preview instances.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.preview_proxy_service import PreviewProxyService
from app.models.preview import PreviewInstance


@pytest.mark.asyncio
class TestPreviewProxyService:
    """Unit tests for PreviewProxyService."""

    @pytest.fixture
    def proxy_service(self):
        """Create PreviewProxyService instance."""
        return PreviewProxyService()

    @pytest.fixture
    def mock_preview_instance(self):
        """Create mock preview instance."""
        preview = MagicMock(spec=PreviewInstance)
        preview.id = "test_preview_id"
        preview.base_url = "http://localhost:3001"
        preview.preview_token = "test_token"
        preview.status = "running"
        return preview

    async def test_proxy_request_success(
        self,
        proxy_service: PreviewProxyService,
        mock_preview_instance: PreviewInstance
    ):
        """Test successful proxy request."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.text = '{"users": []}'
            mock_response.json.return_value = {"users": []}
            mock_client.request.return_value = mock_response

            result = await proxy_service.proxy_request(
                base_url="http://localhost:3001",
                method="GET",
                path="/api/users",
                query={"limit": "10"},
                headers={"X-Preview-Token": "test_token"}
            )

            assert result["status_code"] == 200
            assert result["headers"]["content-type"] == "application/json"
            assert result["data"] == {"users": []}

            mock_client.request.assert_called_once_with(
                method="GET",
                url="http://localhost:3001/api/users",
                params={"limit": "10"},
                content=None,
                headers={"User-Agent": "CodeBEGen-Preview-Proxy/1.0"}
            )

    async def test_proxy_request_with_body(
        self,
        proxy_service: PreviewProxyService,
        mock_preview_instance: PreviewInstance
    ):
        """Test proxy request with JSON body."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.headers = {"content-type": "application/json"}
            mock_response.text = '{"id": 1, "name": "John"}'
            mock_response.json.return_value = {"id": 1, "name": "John"}
            mock_client.request.return_value = mock_response

            result = await proxy_service.proxy_request(
                base_url="http://localhost:3001",
                method="POST",
                path="/api/users",
                body={"name": "John", "email": "john@example.com"},
                headers={"X-Preview-Token": "test_token", "Content-Type": "application/json"}
            )

            assert result["status_code"] == 201
            assert result["data"] == {"id": 1, "name": "John"}

            mock_client.request.assert_called_once_with(
                method="POST",
                url="http://localhost:3001/api/users",
                params=None,
                content={"name": "John", "email": "john@example.com"},
                headers={"Content-Type": "application/json", "User-Agent": "CodeBEGen-Preview-Proxy/1.0"}
            )

    async def test_proxy_request_error(
        self,
        proxy_service: PreviewProxyService,
        mock_preview_instance: PreviewInstance
    ):
        """Test proxy request with HTTP error."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.request.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                await proxy_service.proxy_request(
                    base_url="http://localhost:3001",
                    method="GET",
                    path="/api/users"
                )

    async def test_proxy_request_timeout(
        self,
        proxy_service: PreviewProxyService,
        mock_preview_instance: PreviewInstance
    ):
        """Test proxy request timeout."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            import httpx
            mock_client.request.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(httpx.TimeoutException, match="Request timeout"):
                await proxy_service.proxy_request(
                    base_url="http://localhost:3001",
                    method="GET",
                    path="/api/users"
                )

    async def test_health_check_success(self, proxy_service: PreviewProxyService):
        """Test successful health check."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            result = await proxy_service.health_check("http://localhost:3001")

            assert result is True
            mock_client.get.assert_called_once_with("http://localhost:3001/health")

    async def test_health_check_failure(self, proxy_service: PreviewProxyService):
        """Test health check failure."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.get.side_effect = Exception("Connection failed")

            result = await proxy_service.health_check("http://localhost:3001")

            assert result is False

    async def test_health_check_timeout(self, proxy_service: PreviewProxyService):
        """Test health check timeout."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            import httpx
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")

            result = await proxy_service.health_check("http://localhost:3001")

            assert result is False