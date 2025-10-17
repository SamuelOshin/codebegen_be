"""
Tests for SSE Token Service

Tests the secure short-lived token generation and validation
for Server-Sent Events authentication.
"""

import pytest
from datetime import datetime, timedelta
import time

from app.services.sse_token_service import SSETokenService, SSETokenData


class TestSSETokenService:
    """Test suite for SSE token service"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service instance for each test"""
        return SSETokenService(default_ttl=60)
    
    def test_generate_token_returns_valid_string(self, service):
        """Test that generated tokens are valid URL-safe strings"""
        token = service.generate_sse_token("user-123", "gen-456")
        
        assert isinstance(token, str)
        assert len(token) > 0
        # URL-safe base64 should only contain these characters
        assert all(c.isalnum() or c in ('-', '_') for c in token)
    
    def test_generate_token_is_unique(self, service):
        """Test that each generated token is unique"""
        tokens = set()
        
        for i in range(100):
            token = service.generate_sse_token(f"user-{i}", f"gen-{i}")
            tokens.add(token)
        
        # All tokens should be unique
        assert len(tokens) == 100
    
    def test_validate_token_success(self, service):
        """Test successful token validation"""
        user_id = "user-123"
        generation_id = "gen-456"
        
        token = service.generate_sse_token(user_id, generation_id)
        
        # Validate token
        validated_user_id = service.validate_sse_token(token, generation_id)
        
        assert validated_user_id == user_id
    
    def test_validate_token_with_wrong_generation_id(self, service):
        """Test that validation fails with wrong generation_id"""
        token = service.generate_sse_token("user-123", "gen-456")
        
        # Try to validate with different generation_id
        result = service.validate_sse_token(token, "gen-999")
        
        assert result is None
    
    def test_validate_nonexistent_token(self, service):
        """Test that validation fails for nonexistent token"""
        result = service.validate_sse_token("fake-token-123", "gen-456")
        
        assert result is None
    
    def test_token_single_use(self, service):
        """Test that tokens can only be used once"""
        user_id = "user-123"
        generation_id = "gen-456"
        
        token = service.generate_sse_token(user_id, generation_id)
        
        # First validation should succeed
        result1 = service.validate_sse_token(token, generation_id)
        assert result1 == user_id
        
        # Second validation should fail (token marked as used)
        result2 = service.validate_sse_token(token, generation_id)
        assert result2 is None
    
    def test_token_expiration(self, service):
        """Test that tokens expire after TTL"""
        # Create service with very short TTL
        short_ttl_service = SSETokenService(default_ttl=1)
        
        token = short_ttl_service.generate_sse_token("user-123", "gen-456", ttl_seconds=1)
        
        # Token should be valid immediately
        result1 = short_ttl_service.validate_sse_token(token, "gen-456")
        assert result1 == "user-123"
        
        # Wait for expiration
        time.sleep(2)
        
        # Token should be invalid after expiration
        token2 = short_ttl_service.generate_sse_token("user-123", "gen-456", ttl_seconds=1)
        time.sleep(2)
        result2 = short_ttl_service.validate_sse_token(token2, "gen-456")
        assert result2 is None
    
    def test_custom_ttl(self, service):
        """Test token generation with custom TTL"""
        token = service.generate_sse_token(
            "user-123", 
            "gen-456", 
            ttl_seconds=120  # 2 minutes
        )
        
        # Token should exist in service
        assert token in service._tokens
        
        # Check expiration is approximately 120 seconds in future
        token_data = service._tokens[token]
        time_diff = (token_data.expires_at - datetime.utcnow()).total_seconds()
        assert 115 < time_diff < 125  # Allow 5 second margin
    
    def test_invalidate_token(self, service):
        """Test manual token invalidation"""
        token = service.generate_sse_token("user-123", "gen-456")
        
        # Token should be valid
        assert token in service._tokens
        
        # Invalidate token
        result = service.invalidate_token(token)
        
        assert result is True
        assert token not in service._tokens
        
        # Validation should fail
        user_id = service.validate_sse_token(token, "gen-456")
        assert user_id is None
    
    def test_invalidate_nonexistent_token(self, service):
        """Test invalidating nonexistent token"""
        result = service.invalidate_token("fake-token")
        
        assert result is False
    
    def test_cleanup_expired_tokens(self, service):
        """Test automatic cleanup of expired tokens"""
        # Create service with short TTL and cleanup interval
        test_service = SSETokenService(default_ttl=1)
        test_service._cleanup_interval = 1  # Cleanup every second
        
        # Generate some tokens
        tokens = []
        for i in range(5):
            token = test_service.generate_sse_token(f"user-{i}", f"gen-{i}", ttl_seconds=1)
            tokens.append(token)
        
        assert len(test_service._tokens) == 5
        
        # Wait for expiration
        time.sleep(2)
        
        # Force cleanup
        test_service._last_cleanup = 0
        test_service._cleanup_expired()
        
        # All tokens should be cleaned up
        assert len(test_service._tokens) == 0
    
    def test_get_active_token_count(self, service):
        """Test getting count of active tokens"""
        # Generate some tokens
        for i in range(3):
            service.generate_sse_token(f"user-{i}", f"gen-{i}")
        
        assert service.get_active_token_count() == 3
        
        # Use one token
        token = service.generate_sse_token("user-test", "gen-test")
        service.validate_sse_token(token, "gen-test")
        
        # Active count should decrease (token marked as used)
        assert service.get_active_token_count() == 3
    
    def test_get_token_stats(self, service):
        """Test getting token statistics"""
        # Generate tokens with different states
        token1 = service.generate_sse_token("user-1", "gen-1")
        token2 = service.generate_sse_token("user-2", "gen-2")
        token3 = service.generate_sse_token("user-3", "gen-3")
        
        # Use one token
        service.validate_sse_token(token1, "gen-1")
        
        stats = service.get_token_stats()
        
        assert stats["total"] == 3
        assert stats["used"] == 1
        assert stats["active"] == 2
        assert stats["expired"] == 0
        assert "last_cleanup" in stats
    
    def test_clear_all_tokens(self, service):
        """Test clearing all tokens"""
        # Generate tokens
        for i in range(5):
            service.generate_sse_token(f"user-{i}", f"gen-{i}")
        
        assert len(service._tokens) == 5
        
        # Clear all
        count = service.clear_all_tokens()
        
        assert count == 5
        assert len(service._tokens) == 0
    
    def test_ip_address_validation(self, service):
        """Test IP address validation"""
        token = service.generate_sse_token(
            "user-123", 
            "gen-456",
            ip_address="192.168.1.1"
        )
        
        # Validate with correct IP
        result1 = service.validate_sse_token(token, "gen-456", ip_address="192.168.1.1")
        assert result1 == "user-123"
        
        # Create new token for second test (first one is used)
        token2 = service.generate_sse_token(
            "user-123",
            "gen-456",
            ip_address="192.168.1.1"
        )
        
        # Validate with wrong IP
        result2 = service.validate_sse_token(token2, "gen-456", ip_address="192.168.1.2")
        assert result2 is None
    
    def test_concurrent_token_generation(self, service):
        """Test that concurrent token generation works"""
        import concurrent.futures
        
        def generate_token(user_num):
            return service.generate_sse_token(f"user-{user_num}", f"gen-{user_num}")
        
        # Generate tokens concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_token, i) for i in range(50)]
            tokens = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All tokens should be unique
        assert len(set(tokens)) == 50
        assert len(service._tokens) == 50
    
    def test_token_data_structure(self, service):
        """Test that token data is stored correctly"""
        user_id = "user-123"
        generation_id = "gen-456"
        ip_address = "192.168.1.1"
        
        token = service.generate_sse_token(
            user_id, 
            generation_id,
            ttl_seconds=120,
            ip_address=ip_address
        )
        
        token_data = service._tokens[token]
        
        assert isinstance(token_data, SSETokenData)
        assert token_data.user_id == user_id
        assert token_data.generation_id == generation_id
        assert token_data.ip_address == ip_address
        assert token_data.used is False
        assert isinstance(token_data.created_at, datetime)
        assert isinstance(token_data.expires_at, datetime)
        assert token_data.expires_at > token_data.created_at
    
    def test_service_default_ttl(self):
        """Test service initialization with custom default TTL"""
        service = SSETokenService(default_ttl=300)  # 5 minutes
        
        token = service.generate_sse_token("user-123", "gen-456")
        token_data = service._tokens[token]
        
        # Check TTL is approximately 300 seconds
        time_diff = (token_data.expires_at - datetime.utcnow()).total_seconds()
        assert 295 < time_diff < 305


class TestSSETokenServiceEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def service(self):
        return SSETokenService()
    
    def test_empty_user_id(self, service):
        """Test token generation with empty user_id"""
        token = service.generate_sse_token("", "gen-456")
        
        # Should still work (validation happens at API level)
        assert token is not None
        assert len(token) > 0
    
    def test_very_long_ids(self, service):
        """Test with very long user and generation IDs"""
        long_user_id = "user-" + "x" * 1000
        long_gen_id = "gen-" + "y" * 1000
        
        token = service.generate_sse_token(long_user_id, long_gen_id)
        
        validated_user_id = service.validate_sse_token(token, long_gen_id)
        assert validated_user_id == long_user_id
    
    def test_special_characters_in_ids(self, service):
        """Test with special characters in IDs"""
        user_id = "user-123-!@#$%^&*()"
        generation_id = "gen-456-<>?{}[]|"
        
        token = service.generate_sse_token(user_id, generation_id)
        
        validated_user_id = service.validate_sse_token(token, generation_id)
        assert validated_user_id == user_id
    
    def test_zero_ttl(self, service):
        """Test token with zero TTL (should expire immediately)"""
        token = service.generate_sse_token("user-123", "gen-456", ttl_seconds=0)
        
        # Token should be expired immediately
        result = service.validate_sse_token(token, "gen-456")
        assert result is None
    
    def test_negative_ttl(self, service):
        """Test token with negative TTL"""
        token = service.generate_sse_token("user-123", "gen-456", ttl_seconds=-10)
        
        # Token should be expired
        result = service.validate_sse_token(token, "gen-456")
        assert result is None
    
    def test_memory_efficiency(self, service):
        """Test that service doesn't leak memory with many tokens"""
        service._cleanup_interval = 1
        
        # Generate many tokens
        for i in range(1000):
            service.generate_sse_token(f"user-{i}", f"gen-{i}", ttl_seconds=1)
        
        assert len(service._tokens) == 1000
        
        # Wait and force cleanup
        time.sleep(2)
        service._last_cleanup = 0
        service._cleanup_expired()
        
        # All tokens should be cleaned up
        assert len(service._tokens) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.sse_token_service"])
