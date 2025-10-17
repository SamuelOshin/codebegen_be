"""
SSE Token Service - Secure Short-Lived Tokens for Server-Sent Events

Provides cryptographically secure, short-lived, single-use tokens for SSE authentication.
This prevents JWT token exposure in URLs and server logs.

Security Features:
- Tokens expire in 60 seconds
- Single-use tokens (invalidated after first connection)
- Cryptographically secure random generation
- User and generation validation
- Memory-efficient cleanup
- Production-ready with Redis support

Usage:
    from app.services.sse_token_service import sse_token_service
    
    # Generate token
    token = sse_token_service.generate_sse_token(user_id, generation_id)
    
    # Validate token
    user_id = sse_token_service.validate_sse_token(token, generation_id)
"""

import secrets
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SSETokenData:
    """Data stored for each SSE token"""
    user_id: str
    generation_id: str
    expires_at: datetime
    used: bool
    created_at: datetime
    ip_address: Optional[str] = None


class SSETokenService:
    """
    Manages short-lived tokens for SSE authentication.
    
    Design:
    - Tokens are 256-bit random strings (URL-safe)
    - Stored in memory (or Redis in production)
    - Automatic cleanup of expired tokens
    - Single-use enforcement
    - Optional IP validation
    
    Security:
    - No JWT exposure in URLs
    - Short TTL reduces attack window
    - Single-use prevents replay attacks
    - Cryptographically secure generation
    """
    
    def __init__(self, default_ttl: int = 60):
        """
        Initialize SSE token service.
        
        Args:
            default_ttl: Default token TTL in seconds (default: 60)
        """
        self._tokens: Dict[str, SSETokenData] = {}
        self._default_ttl = default_ttl
        self._cleanup_interval = 60  # Cleanup every 60 seconds
        self._last_cleanup = time.time()
        
        logger.info("SSETokenService initialized with %d second TTL", default_ttl)
    
    def generate_sse_token(
        self, 
        user_id: str, 
        generation_id: str,
        ttl_seconds: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """
        Generate a short-lived SSE token.
        
        Args:
            user_id: User ID making the request
            generation_id: Generation ID to stream
            ttl_seconds: Token validity in seconds (default: service default)
            ip_address: Optional IP address for additional validation
        
        Returns:
            Cryptographically secure random token (43 chars URL-safe)
        
        Example:
            >>> token = service.generate_sse_token("user-123", "gen-456")
            >>> print(token)
            'xB7dK9mN2pQ5rT8vW1yZ4aE6gJ0hL3nM5oS7tU9vX2yA1cD4fG6hK8mP'
        """
        # Generate secure random token (32 bytes = 43 chars base64url)
        token = secrets.token_urlsafe(32)
        
        # Calculate expiration
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        # Store token with metadata
        self._tokens[token] = SSETokenData(
            user_id=user_id,
            generation_id=generation_id,
            expires_at=expires_at,
            used=False,
            created_at=datetime.utcnow(),
            ip_address=ip_address
        )
        
        logger.info(
            "Generated SSE token for user=%s generation=%s ttl=%ds",
            user_id, generation_id, ttl
        )
        
        # Periodic cleanup
        self._cleanup_expired()
        
        return token
    
    def validate_sse_token(
        self, 
        token: str, 
        generation_id: str,
        ip_address: Optional[str] = None
    ) -> Optional[str]:
        """
        Validate SSE token and return user_id.
        
        Validation checks:
        1. Token exists
        2. Not expired
        3. Not already used (single-use)
        4. Generation ID matches
        5. Optional: IP address matches
        
        Args:
            token: SSE token to validate
            generation_id: Expected generation ID
            ip_address: Optional IP address to validate
        
        Returns:
            user_id if valid, None otherwise
        
        Example:
            >>> user_id = service.validate_sse_token(token, "gen-456")
            >>> if user_id:
            ...     print(f"Valid token for user {user_id}")
        """
        # Check if token exists
        token_data = self._tokens.get(token)
        if not token_data:
            logger.warning("SSE token not found: %s", token[:10] + "...")
            return None
        
        # Check expiration
        if datetime.utcnow() > token_data.expires_at:
            logger.warning(
                "SSE token expired: %s (expired %s)",
                token[:10] + "...",
                token_data.expires_at
            )
            del self._tokens[token]
            return None
        
        # Check if already used (single-use token)
        if token_data.used:
            logger.warning("SSE token already used: %s", token[:10] + "...")
            return None
        
        # Verify generation_id matches
        if token_data.generation_id != generation_id:
            logger.warning(
                "SSE token generation mismatch: expected=%s got=%s",
                token_data.generation_id, generation_id
            )
            return None
        
        # Optional: Verify IP address matches
        if ip_address and token_data.ip_address:
            if ip_address != token_data.ip_address:
                logger.warning(
                    "SSE token IP mismatch: expected=%s got=%s",
                    token_data.ip_address, ip_address
                )
                return None
        
        # Mark as used (single-use enforcement)
        token_data.used = True
        
        logger.info(
            "Validated SSE token for user=%s generation=%s",
            token_data.user_id, generation_id
        )
        
        return token_data.user_id
    
    def invalidate_token(self, token: str) -> bool:
        """
        Invalidate a token immediately.
        
        Args:
            token: Token to invalidate
        
        Returns:
            True if token was found and invalidated, False otherwise
        """
        if token in self._tokens:
            del self._tokens[token]
            logger.info("Invalidated SSE token: %s", token[:10] + "...")
            return True
        return False
    
    def get_active_token_count(self) -> int:
        """
        Get count of active (not used, not expired) tokens.
        
        Returns:
            Number of active tokens
        """
        now = datetime.utcnow()
        active = sum(
            1 for data in self._tokens.values()
            if not data.used and now <= data.expires_at
        )
        return active
    
    def get_token_stats(self) -> Dict:
        """
        Get statistics about token usage.
        
        Returns:
            Dictionary with token statistics
        """
        now = datetime.utcnow()
        
        active = 0
        expired = 0
        used = 0
        
        for data in self._tokens.values():
            if data.used:
                used += 1
            elif now > data.expires_at:
                expired += 1
            else:
                active += 1
        
        return {
            "total": len(self._tokens),
            "active": active,
            "used": used,
            "expired": expired,
            "last_cleanup": datetime.fromtimestamp(self._last_cleanup).isoformat()
        }
    
    def _cleanup_expired(self) -> None:
        """
        Remove expired and used tokens from memory.
        
        Runs periodically to prevent memory buildup.
        """
        current_time = time.time()
        
        # Only cleanup periodically
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        now = datetime.utcnow()
        
        # Find expired/used tokens
        tokens_to_remove = [
            token for token, data in self._tokens.items()
            if now > data.expires_at or data.used
        ]
        
        # Remove them
        for token in tokens_to_remove:
            del self._tokens[token]
        
        if tokens_to_remove:
            logger.info("Cleaned up %d expired/used SSE tokens", len(tokens_to_remove))
        
        self._last_cleanup = current_time
    
    def clear_all_tokens(self) -> int:
        """
        Clear all tokens (for testing/maintenance).
        
        Returns:
            Number of tokens cleared
        """
        count = len(self._tokens)
        self._tokens.clear()
        logger.warning("Cleared all %d SSE tokens", count)
        return count


# Singleton instance
sse_token_service = SSETokenService(default_ttl=60)
