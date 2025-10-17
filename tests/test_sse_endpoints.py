"""
Integration Tests for SSE Token Endpoints

Tests the secure SSE token generation and streaming endpoints.
"""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.models.project import Project
from app.models.generation import Generation
from app.services.sse_token_service import SSETokenService


class TestSSETokenEndpoints:
    """Test SSE token generation and streaming endpoints"""
    
    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """Create a test user"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_pass_123"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    @pytest.fixture
    async def test_project(self, db_session: AsyncSession, test_user: User):
        """Create a test project"""
        project = Project(
            name="Test Project",
            domain="Testing",
            owner_id=test_user.id
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        return project
    
    @pytest.fixture
    async def test_generation(
        self, 
        db_session: AsyncSession, 
        test_user: User, 
        test_project: Project
    ):
        """Create a test generation"""
        generation = Generation(
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="Test prompt",
            status="in_progress",
            original_prompt="Test prompt"
        )
        db_session.add(generation)
        await db_session.commit()
        await db_session.refresh(generation)
        return generation
    
    @pytest.fixture
    def auth_headers(self, test_user: User):
        """Create auth headers with JWT token"""
        from app.core.security import create_access_token
        
        token = create_access_token({"sub": str(test_user.id)})
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.asyncio
    async def test_generate_sse_token_success(
        self,
        async_client: AsyncClient,
        test_generation: Generation,
        auth_headers: dict
    ):
        """Test successful SSE token generation"""
        response = await async_client.post(
            f"/api/generate/{test_generation.id}/stream-token",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sse_token" in data
        assert "expires_in" in data
        assert "generation_id" in data
        
        assert isinstance(data["sse_token"], str)
        assert len(data["sse_token"]) > 0
        assert data["expires_in"] == 60
        assert data["generation_id"] == str(test_generation.id)
    
    @pytest.mark.asyncio
    async def test_generate_sse_token_unauthorized(
        self,
        async_client: AsyncClient,
        test_generation: Generation
    ):
        """Test SSE token generation without authentication"""
        response = await async_client.post(
            f"/api/generate/{test_generation.id}/stream-token"
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_generate_sse_token_generation_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test SSE token generation for nonexistent generation"""
        response = await async_client.post(
            "/api/generate/99999/stream-token",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_sse_token_forbidden(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_generation: Generation
    ):
        """Test SSE token generation for generation owned by another user"""
        # Create another user
        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password="hashed_pass_456"
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)
        
        # Create token for other user
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(other_user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await async_client.post(
            f"/api/generate/{test_generation.id}/stream-token",
            headers=headers
        )
        
        assert response.status_code == 403
        assert "access" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_stream_with_valid_sse_token(
        self,
        async_client: AsyncClient,
        test_generation: Generation,
        auth_headers: dict
    ):
        """Test streaming with valid SSE token"""
        # First, get an SSE token
        token_response = await async_client.post(
            f"/api/generate/{test_generation.id}/stream-token",
            headers=auth_headers
        )
        
        assert token_response.status_code == 200
        sse_token = token_response.json()["sse_token"]
        
        # Now try to stream with the SSE token
        response = await async_client.get(
            f"/api/generate/{test_generation.id}/stream",
            params={"sse_token": sse_token}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    @pytest.mark.asyncio
    async def test_stream_with_invalid_sse_token(
        self,
        async_client: AsyncClient,
        test_generation: Generation
    ):
        """Test streaming with invalid SSE token"""
        response = await async_client.get(
            f"/api/generate/{test_generation.id}/stream",
            params={"sse_token": "invalid-token-123"}
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_stream_with_expired_sse_token(
        self,
        async_client: AsyncClient,
        test_generation: Generation,
        auth_headers: dict
    ):
        """Test streaming with expired SSE token"""
        # Get SSE token with very short TTL
        service = SSETokenService()
        sse_token = service.generate_sse_token(
            str(test_generation.user_id),
            str(test_generation.id),
            ttl_seconds=1
        )
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Try to stream with expired token
        response = await async_client.get(
            f"/api/generate/{test_generation.id}/stream",
            params={"sse_token": sse_token}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower() or \
               "invalid" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_stream_token_single_use(
        self,
        async_client: AsyncClient,
        test_generation: Generation,
        auth_headers: dict
    ):
        """Test that SSE tokens can only be used once"""
        # Get SSE token
        token_response = await async_client.post(
            f"/api/generate/{test_generation.id}/stream-token",
            headers=auth_headers
        )
        
        sse_token = token_response.json()["sse_token"]
        
        # First stream should work
        response1 = await async_client.get(
            f"/api/generate/{test_generation.id}/stream",
            params={"sse_token": sse_token}
        )
        
        assert response1.status_code == 200
        
        # Second stream with same token should fail
        response2 = await async_client.get(
            f"/api/generate/{test_generation.id}/stream",
            params={"sse_token": sse_token}
        )
        
        assert response2.status_code == 401
    
    @pytest.mark.asyncio
    async def test_stream_with_mismatched_generation_id(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_project: Project,
        auth_headers: dict
    ):
        """Test streaming with token for different generation"""
        # Create two generations
        gen1 = Generation(
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="Gen 1",
            status="in_progress",
            original_prompt="Gen 1"
        )
        gen2 = Generation(
            user_id=test_user.id,
            project_id=test_project.id,
            prompt="Gen 2",
            status="in_progress",
            original_prompt="Gen 2"
        )
        db_session.add_all([gen1, gen2])
        await db_session.commit()
        await db_session.refresh(gen1)
        await db_session.refresh(gen2)
        
        # Get token for gen1
        token_response = await async_client.post(
            f"/api/generate/{gen1.id}/stream-token",
            headers=auth_headers
        )
        
        sse_token = token_response.json()["sse_token"]
        
        # Try to use token for gen2
        response = await async_client.get(
            f"/api/generate/{gen2.id}/stream",
            params={"sse_token": sse_token}
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_multiple_token_generation(
        self,
        async_client: AsyncClient,
        test_generation: Generation,
        auth_headers: dict
    ):
        """Test generating multiple tokens for same generation"""
        tokens = []
        
        # Generate 5 tokens
        for _ in range(5):
            response = await async_client.post(
                f"/api/generate/{test_generation.id}/stream-token",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            tokens.append(response.json()["sse_token"])
        
        # All tokens should be unique
        assert len(set(tokens)) == 5
        
        # Each token should work once
        for token in tokens[:3]:  # Test first 3
            response = await async_client.get(
                f"/api/generate/{test_generation.id}/stream",
                params={"sse_token": token}
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_stream_event_format(
        self,
        async_client: AsyncClient,
        test_generation: Generation,
        auth_headers: dict
    ):
        """Test that stream returns proper SSE event format"""
        # Get SSE token
        token_response = await async_client.post(
            f"/api/generate/{test_generation.id}/stream-token",
            headers=auth_headers
        )
        
        sse_token = token_response.json()["sse_token"]
        
        # Stream and read first chunk
        async with async_client.stream(
            "GET",
            f"/api/generate/{test_generation.id}/stream",
            params={"sse_token": sse_token}
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            
            # Read first chunk
            chunk = None
            async for line in response.aiter_lines():
                if line.strip():
                    chunk = line
                    break
            
            # Verify SSE format (should start with "data:" or "event:")
            if chunk:
                assert chunk.startswith(("data:", "event:"))
    
    @pytest.mark.asyncio
    async def test_concurrent_sse_token_generation(
        self,
        async_client: AsyncClient,
        test_generation: Generation,
        auth_headers: dict
    ):
        """Test concurrent SSE token generation"""
        async def generate_token():
            return await async_client.post(
                f"/api/generate/{test_generation.id}/stream-token",
                headers=auth_headers
            )
        
        # Generate tokens concurrently
        tasks = [generate_token() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)
        
        # All tokens should be unique
        tokens = [r.json()["sse_token"] for r in responses]
        assert len(set(tokens)) == 10


class TestSSETokenServiceIntegration:
    """Test SSE token service integration with endpoints"""
    
    @pytest.mark.asyncio
    async def test_token_cleanup_after_stream(
        self,
        async_client: AsyncClient,
        test_generation: Generation,
        auth_headers: dict
    ):
        """Test that tokens are cleaned up after streaming"""
        service = SSETokenService()
        initial_count = service.get_active_token_count()
        
        # Generate token
        token_response = await async_client.post(
            f"/api/generate/{test_generation.id}/stream-token",
            headers=auth_headers
        )
        
        sse_token = token_response.json()["sse_token"]
        
        # Token should exist
        assert service.get_active_token_count() == initial_count + 1
        
        # Stream with token
        response = await async_client.get(
            f"/api/generate/{test_generation.id}/stream",
            params={"sse_token": sse_token}
        )
        
        assert response.status_code == 200
        
        # Token should be marked as used
        stats = service.get_token_stats()
        assert stats["used"] >= 1
    
    @pytest.mark.asyncio
    async def test_token_statistics(self, async_client: AsyncClient):
        """Test token service statistics tracking"""
        service = SSETokenService()
        
        # Clear existing tokens
        service.clear_all_tokens()
        
        # Generate some tokens
        for i in range(5):
            service.generate_sse_token(f"user-{i}", f"gen-{i}")
        
        # Use some tokens
        token = service.generate_sse_token("user-test", "gen-test")
        service.validate_sse_token(token, "gen-test")
        
        stats = service.get_token_stats()
        
        assert stats["total"] == 6
        assert stats["used"] == 1
        assert stats["active"] == 5
        assert "last_cleanup" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
