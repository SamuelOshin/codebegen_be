# 🚀 CodebeGen Backend - Rate Limiting Design for Production Scale

## 📋 Executive Summary

This document outlines a comprehensive rate limiting strategy for the CodebeGen AI-powered backend generator. The design ensures scalability, prevents abuse, maintains service quality, and provides different user experience tiers while protecting our AI infrastructure resources.

## 🎯 Rate Limiting Objectives

### Primary Goals
1. **Resource Protection**: Prevent AI model overload and infrastructure abuse
2. **Fair Usage**: Ensure equitable access across all users
3. **Revenue Protection**: Encourage upgrades to higher tiers
4. **Quality Assurance**: Maintain response times and service availability
5. **Cost Control**: Manage AI API costs and compute expenses

### Secondary Goals
- **Graceful Degradation**: Maintain partial functionality under high load
- **User Education**: Guide users toward optimal usage patterns
- **Analytics**: Track usage patterns for business insights
- **Security**: Prevent DDoS and malicious automation

## 🏗️ Current Architecture Analysis

### Current Rate Limiting Implementation
```python
# Current basic setup in main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### Key Endpoints Analysis

#### 1. **High-Impact Endpoints** (Resource Intensive)
- `POST /api/v2/generation/generate` - AI code generation
- `POST /ai/generate` - Legacy AI generation  
- `GET /api/v2/generation/generate/{id}/stream` - Real-time streaming
- `POST /generations/iterate` - Code iteration

#### 2. **Medium-Impact Endpoints** (Moderate Resources)
- `POST /projects/validate` - Project validation
- `POST /projects/preview` - Configuration preview
- `GET /generations/{id}/files` - File retrieval
- `POST /generations/{id}/export` - GitHub export

#### 3. **Low-Impact Endpoints** (Light Resources)
- `GET /projects/` - List projects
- `GET /generations/` - List generations
- `GET /auth/me` - User profile
- `GET /health` - Health check

#### 4. **Authentication Endpoints** (Security Critical)
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/refresh` - Token refresh

## 💡 Proposed Rate Limiting Strategy

### 1. **Multi-Tier Rate Limiting System**

#### Tier Structure
```yaml
Free Tier:
  ai_generations: 5/hour, 20/day
  project_validations: 50/hour
  file_operations: 100/hour
  api_requests: 1000/hour
  concurrent_streams: 1
  
Pro Tier ($9.99/month):
  ai_generations: 50/hour, 500/day
  project_validations: 500/hour
  file_operations: 1000/hour
  api_requests: 10000/hour
  concurrent_streams: 3
  
Business Tier ($29.99/month):
  ai_generations: 200/hour, 2000/day
  project_validations: 2000/hour
  file_operations: 5000/hour
  api_requests: 50000/hour
  concurrent_streams: 10
  
Enterprise Tier (Custom):
  ai_generations: unlimited*
  project_validations: unlimited
  file_operations: unlimited
  api_requests: unlimited
  concurrent_streams: unlimited
  custom_sla: true
```

### 2. **Endpoint-Specific Rate Limiting**

#### AI Generation Endpoints
```python
# Heavy AI processing endpoints
@limiter.limit("5/hour", key_func=get_user_tier_limit)
@router.post("/api/v2/generation/generate")
async def generate_project(...)

@limiter.limit("3/minute", key_func=get_user_id)  
@router.post("/generations/iterate")
async def create_iteration(...)

# Streaming endpoints
@limiter.limit("1/second", key_func=get_user_id)
@router.get("/api/v2/generation/generate/{id}/stream") 
async def stream_generation_progress(...)
```

#### Project Management Endpoints
```python
@limiter.limit("50/hour", key_func=get_user_tier_limit)
@router.post("/projects/validate")
async def validate_project_configuration(...)

@limiter.limit("20/hour", key_func=get_user_tier_limit)
@router.post("/projects/preview")
async def preview_project_configuration(...)

@limiter.limit("100/hour", key_func=get_user_tier_limit)
@router.get("/projects/")
async def list_user_projects(...)
```

#### File Operations
```python
@limiter.limit("100/hour", key_func=get_user_tier_limit)
@router.get("/generations/{id}/files")
async def get_generation_files(...)

@limiter.limit("10/hour", key_func=get_user_tier_limit)
@router.get("/generations/{id}/download")
async def download_generation(...)

@limiter.limit("5/hour", key_func=get_user_tier_limit)
@router.post("/generations/{id}/export")
async def export_to_github(...)
```

#### Authentication & Security
```python
@limiter.limit("5/minute", key_func=get_remote_address)
@router.post("/auth/login")
async def login(...)

@limiter.limit("3/hour", key_func=get_remote_address)
@router.post("/auth/register")
async def register(...)

@limiter.limit("10/minute", key_func=get_user_id)
@router.post("/auth/refresh")
async def refresh_token(...)
```

### 3. **Advanced Rate Limiting Features**

#### Dynamic Rate Limiting
```python
class DynamicRateLimiter:
    """
    Adjusts limits based on:
    - Current system load
    - User behavior patterns
    - Time of day/week
    - Geographic location
    """
    
    async def get_dynamic_limit(self, user_id: str, endpoint: str) -> str:
        base_limit = self.get_base_limit(user_id, endpoint)
        
        # Adjust for system load
        system_load = await self.get_system_load()
        if system_load > 0.8:
            base_limit = int(base_limit * 0.7)  # Reduce by 30%
        
        # Adjust for user reputation
        user_reputation = await self.get_user_reputation(user_id)
        if user_reputation > 0.9:
            base_limit = int(base_limit * 1.2)  # Increase by 20%
        
        # Adjust for time of day (off-peak bonus)
        if self.is_off_peak():
            base_limit = int(base_limit * 1.5)  # Increase by 50%
        
        return f"{base_limit}/hour"
```

#### Burst Allowance
```python
class BurstLimiter:
    """
    Allow temporary bursts above normal limits
    """
    
    burst_rules = {
        "free": {"burst_size": 2, "burst_window": "5min"},
        "pro": {"burst_size": 10, "burst_window": "5min"}, 
        "business": {"burst_size": 25, "burst_window": "5min"},
        "enterprise": {"burst_size": 100, "burst_window": "5min"}
    }
```

#### Geographic Rate Limiting
```python
class GeographicLimiter:
    """
    Different limits based on user location
    """
    
    geographic_multipliers = {
        "US": 1.0,
        "EU": 1.0, 
        "Asia": 0.8,  # Higher latency, slightly reduced limits
        "Other": 0.6  # Conservative limits for other regions
    }
```

## 🛠️ Implementation Architecture

### 1. **Enhanced Rate Limiting Service**

```python
# app/services/rate_limiting_service.py

import asyncio
import time
from typing import Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import redis.asyncio as redis
from fastapi import Request, HTTPException, status

class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro" 
    BUSINESS = "business"
    ENTERPRISE = "enterprise"

@dataclass
class RateLimit:
    requests: int
    window: int  # seconds
    burst_size: int = 0
    burst_window: int = 300  # 5 minutes

class AdvancedRateLimitingService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.limits = self._load_rate_limits()
        
    def _load_rate_limits(self) -> Dict[str, Dict[str, RateLimit]]:
        """Load rate limits configuration"""
        return {
            UserTier.FREE: {
                "ai_generation": RateLimit(5, 3600, 2, 300),  # 5/hour, burst 2 in 5min
                "project_validation": RateLimit(50, 3600, 10, 300),
                "file_operations": RateLimit(100, 3600, 20, 300),
                "api_requests": RateLimit(1000, 3600, 50, 300),
                "auth_operations": RateLimit(10, 600),  # 10 per 10min
            },
            UserTier.PRO: {
                "ai_generation": RateLimit(50, 3600, 10, 300),
                "project_validation": RateLimit(500, 3600, 50, 300),
                "file_operations": RateLimit(1000, 3600, 100, 300),
                "api_requests": RateLimit(10000, 3600, 200, 300),
                "auth_operations": RateLimit(30, 600),
            },
            UserTier.BUSINESS: {
                "ai_generation": RateLimit(200, 3600, 25, 300),
                "project_validation": RateLimit(2000, 3600, 100, 300),
                "file_operations": RateLimit(5000, 3600, 200, 300),
                "api_requests": RateLimit(50000, 3600, 500, 300),
                "auth_operations": RateLimit(100, 600),
            },
            UserTier.ENTERPRISE: {
                # Unlimited but tracked
                "ai_generation": RateLimit(999999, 3600, 1000, 300),
                "project_validation": RateLimit(999999, 3600, 1000, 300),
                "file_operations": RateLimit(999999, 3600, 1000, 300),
                "api_requests": RateLimit(999999, 3600, 1000, 300),
                "auth_operations": RateLimit(999999, 600),
            }
        }
    
    async def check_rate_limit(
        self, 
        user_id: str, 
        user_tier: UserTier,
        operation: str,
        request: Request
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is within rate limits
        Returns: (allowed, headers_dict)
        """
        
        # Get rate limit for user tier and operation
        limit = self.limits[user_tier].get(operation)
        if not limit:
            return True, {}
        
        # Apply dynamic adjustments
        adjusted_limit = await self._apply_dynamic_adjustments(
            limit, user_id, operation, request
        )
        
        # Check against Redis
        current_usage = await self._get_current_usage(user_id, operation, adjusted_limit.window)
        
        # Check burst allowance if normal limit exceeded
        if current_usage >= adjusted_limit.requests and adjusted_limit.burst_size > 0:
            burst_usage = await self._get_current_usage(
                user_id, f"{operation}_burst", adjusted_limit.burst_window
            )
            if burst_usage >= adjusted_limit.burst_size:
                return False, self._get_rate_limit_headers(
                    adjusted_limit, current_usage, True
                )
        elif current_usage >= adjusted_limit.requests:
            return False, self._get_rate_limit_headers(
                adjusted_limit, current_usage, False
            )
        
        # Increment usage
        await self._increment_usage(user_id, operation, adjusted_limit.window)
        if current_usage >= adjusted_limit.requests:
            await self._increment_usage(
                user_id, f"{operation}_burst", adjusted_limit.burst_window
            )
        
        return True, self._get_rate_limit_headers(adjusted_limit, current_usage + 1, False)
    
    async def _apply_dynamic_adjustments(
        self, 
        base_limit: RateLimit, 
        user_id: str, 
        operation: str,
        request: Request
    ) -> RateLimit:
        """Apply dynamic adjustments to base rate limit"""
        
        # System load adjustment
        system_load = await self._get_system_load()
        load_multiplier = 1.0
        if system_load > 0.8:
            load_multiplier = 0.7
        elif system_load < 0.3:
            load_multiplier = 1.3
        
        # User reputation adjustment
        reputation = await self._get_user_reputation(user_id)
        reputation_multiplier = 0.5 + (reputation * 0.5)  # 0.5 to 1.0
        
        # Time-based adjustment (off-peak bonus)
        time_multiplier = 1.5 if self._is_off_peak() else 1.0
        
        # Geographic adjustment
        geo_multiplier = await self._get_geographic_multiplier(request)
        
        # Apply all multipliers
        total_multiplier = load_multiplier * reputation_multiplier * time_multiplier * geo_multiplier
        
        return RateLimit(
            requests=max(1, int(base_limit.requests * total_multiplier)),
            window=base_limit.window,
            burst_size=max(1, int(base_limit.burst_size * total_multiplier)),
            burst_window=base_limit.burst_window
        )
    
    async def _get_current_usage(self, user_id: str, operation: str, window: int) -> int:
        """Get current usage from Redis sliding window"""
        key = f"rate_limit:{user_id}:{operation}"
        now = time.time()
        
        # Clean old entries
        await self.redis.zremrangebyscore(key, 0, now - window)
        
        # Count current entries
        count = await self.redis.zcard(key)
        return count
    
    async def _increment_usage(self, user_id: str, operation: str, window: int):
        """Increment usage counter in Redis"""
        key = f"rate_limit:{user_id}:{operation}"
        now = time.time()
        
        # Add current request
        await self.redis.zadd(key, {str(now): now})
        
        # Set expiration
        await self.redis.expire(key, window + 60)  # Extra 60s buffer
    
    def _get_rate_limit_headers(
        self, 
        limit: RateLimit, 
        current_usage: int, 
        is_burst: bool
    ) -> Dict[str, str]:
        """Generate rate limit headers"""
        remaining = max(0, limit.requests - current_usage)
        reset_time = int(time.time() + limit.window)
        
        headers = {
            "X-RateLimit-Limit": str(limit.requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
            "X-RateLimit-Window": str(limit.window),
        }
        
        if is_burst:
            headers["X-RateLimit-Burst-Used"] = "true"
            headers["X-RateLimit-Burst-Limit"] = str(limit.burst_size)
        
        return headers
    
    async def _get_system_load(self) -> float:
        """Get current system load (0.0 to 1.0)"""
        # Implement system load monitoring
        # Could check CPU, memory, active connections, etc.
        return 0.5  # Placeholder
    
    async def _get_user_reputation(self, user_id: str) -> float:
        """Get user reputation score (0.0 to 1.0)"""
        # Factors: account age, payment status, abuse reports, etc.
        key = f"user_reputation:{user_id}"
        reputation = await self.redis.get(key)
        return float(reputation) if reputation else 0.8  # Default good reputation
    
    def _is_off_peak(self) -> bool:
        """Check if current time is off-peak"""
        import datetime
        now = datetime.datetime.utcnow()
        # Off-peak: 10 PM to 6 AM UTC
        return now.hour >= 22 or now.hour <= 6
    
    async def _get_geographic_multiplier(self, request: Request) -> float:
        """Get geographic multiplier based on request origin"""
        # Extract country from IP or headers
        # Implement IP geolocation
        return 1.0  # Placeholder
```

### 2. **Rate Limiting Middleware**

```python
# app/middleware/rate_limiting_middleware.py

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import time
from app.services.rate_limiting_service import AdvancedRateLimitingService, UserTier
from app.auth.dependencies import get_user_from_token

class RateLimitingMiddleware:
    def __init__(self, rate_limiter: AdvancedRateLimitingService):
        self.rate_limiter = rate_limiter
        
        # Map endpoints to operations
        self.endpoint_operations = {
            "/api/v2/generation/generate": "ai_generation",
            "/ai/generate": "ai_generation",
            "/generations/iterate": "ai_generation",
            "/projects/validate": "project_validation",
            "/projects/preview": "project_validation",
            "/generations/*/files": "file_operations",
            "/generations/*/download": "file_operations",
            "/generations/*/export": "file_operations",
            "/auth/login": "auth_operations",
            "/auth/register": "auth_operations",
            "/auth/refresh": "auth_operations",
        }
    
    async def __call__(self, request: Request, call_next):
        # Skip rate limiting for certain endpoints
        if self._should_skip_rate_limiting(request):
            return await call_next(request)
        
        # Get user info
        user_info = await self._get_user_info(request)
        if not user_info:
            # Anonymous users get minimal limits
            user_id = f"anon_{request.client.host}"
            user_tier = UserTier.FREE
        else:
            user_id = user_info["user_id"]
            user_tier = UserTier(user_info.get("tier", "free"))
        
        # Determine operation type
        operation = self._get_operation_type(request)
        
        # Check rate limit
        allowed, headers = await self.rate_limiter.check_rate_limit(
            user_id, user_tier, operation, request
        )
        
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many {operation} requests. Please try again later.",
                    "retry_after": headers.get("X-RateLimit-Reset"),
                    "upgrade_url": "/pricing" if user_tier == UserTier.FREE else None
                },
                headers=headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request"""
        skip_paths = ["/health", "/docs", "/openapi.json", "/metrics"]
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    async def _get_user_info(self, request: Request) -> Optional[Dict]:
        """Extract user information from request"""
        try:
            # Try to get user from authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
                return await get_user_from_token(token)
        except:
            pass
        return None
    
    def _get_operation_type(self, request: Request) -> str:
        """Determine operation type from request path"""
        path = request.url.path
        method = request.method
        
        # Check specific mappings
        for pattern, operation in self.endpoint_operations.items():
            if self._match_pattern(path, pattern):
                return operation
        
        # Default to general API requests
        return "api_requests"
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Match path against pattern with wildcards"""
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")
        
        if len(pattern_parts) != len(path_parts):
            return False
        
        for pattern_part, path_part in zip(pattern_parts, path_parts):
            if pattern_part != "*" and pattern_part != path_part:
                return False
        
        return True
```

### 3. **Rate Limiting Configuration Management**

```python
# app/core/rate_limiting_config.py

from typing import Dict, Any
from pydantic import BaseSettings
import yaml

class RateLimitingConfig(BaseSettings):
    """Rate limiting configuration"""
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_RATE_LIMIT_DB: int = 1
    
    # Rate limiting settings
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_DYNAMIC_LIMITS: bool = True
    ENABLE_BURST_LIMITS: bool = True
    ENABLE_GEOGRAPHIC_LIMITS: bool = False
    
    # Default multipliers
    SYSTEM_LOAD_THRESHOLD: float = 0.8
    OFF_PEAK_BONUS_MULTIPLIER: float = 1.5
    HIGH_REPUTATION_BONUS: float = 1.2
    
    # Custom limits file
    CUSTOM_LIMITS_FILE: str = "configs/rate_limits.yaml"
    
    def load_custom_limits(self) -> Dict[str, Any]:
        """Load custom rate limits from YAML file"""
        try:
            with open(self.CUSTOM_LIMITS_FILE, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {}

# configs/rate_limits.yaml
rate_limits:
  special_users:
    - user_id: "premium_user_123"
      tier_override: "business"
      custom_limits:
        ai_generation: "100/hour"
    
    - user_id: "beta_tester_456"
      tier_override: "enterprise"
      custom_limits:
        ai_generation: "unlimited"
  
  endpoint_overrides:
    - path: "/api/v2/generation/generate"
      limits:
        free: "3/hour"      # Reduced from default 5/hour
        pro: "30/hour"      # Reduced from default 50/hour
    
    - path: "/generations/*/export"
      limits:
        free: "2/hour"      # Reduced from default 5/hour
  
  time_based_limits:
    - time_range: "peak_hours"  # 9 AM - 6 PM UTC
      multiplier: 0.8           # Reduce limits by 20%
    
    - time_range: "off_peak"    # 10 PM - 6 AM UTC  
      multiplier: 1.5           # Increase limits by 50%
  
  geographic_limits:
    - region: "high_load_regions"
      countries: ["US", "GB", "DE"]
      multiplier: 1.0
    
    - region: "standard_regions"
      countries: ["CA", "AU", "FR"]
      multiplier: 0.9
    
    - region: "conservative_regions"
      countries: ["*"]  # All others
      multiplier: 0.7
```

## 📊 Monitoring & Analytics

### 1. **Rate Limiting Metrics**

```python
# app/services/rate_limiting_metrics.py

from prometheus_client import Counter, Histogram, Gauge
import structlog

# Metrics
rate_limit_requests = Counter(
    "rate_limit_requests_total",
    "Total rate limit checks",
    ["user_tier", "operation", "result"]
)

rate_limit_latency = Histogram(
    "rate_limit_check_duration_seconds",
    "Time spent checking rate limits"
)

rate_limit_denials = Counter(
    "rate_limit_denials_total", 
    "Total rate limit denials",
    ["user_tier", "operation", "reason"]
)

active_users_gauge = Gauge(
    "rate_limit_active_users",
    "Number of active users being rate limited",
    ["tier"]
)

class RateLimitingMetrics:
    def __init__(self):
        self.logger = structlog.get_logger()
    
    def record_rate_limit_check(
        self, 
        user_tier: str, 
        operation: str, 
        allowed: bool,
        latency: float
    ):
        """Record rate limit check metrics"""
        result = "allowed" if allowed else "denied"
        
        rate_limit_requests.labels(
            user_tier=user_tier,
            operation=operation, 
            result=result
        ).inc()
        
        rate_limit_latency.observe(latency)
        
        if not allowed:
            rate_limit_denials.labels(
                user_tier=user_tier,
                operation=operation,
                reason="limit_exceeded"
            ).inc()
        
        # Log for debugging
        self.logger.info(
            "rate_limit_check",
            user_tier=user_tier,
            operation=operation,
            allowed=allowed,
            latency=latency
        )
    
    def record_dynamic_adjustment(
        self, 
        adjustment_type: str, 
        original_limit: int,
        adjusted_limit: int,
        multiplier: float
    ):
        """Record dynamic limit adjustments"""
        self.logger.info(
            "dynamic_rate_limit_adjustment",
            adjustment_type=adjustment_type,
            original_limit=original_limit,
            adjusted_limit=adjusted_limit,
            multiplier=multiplier
        )
```

### 2. **Rate Limiting Dashboard**

```python
# app/routers/admin/rate_limiting.py

@router.get("/admin/rate-limits/stats")
async def get_rate_limiting_stats(
    current_user: User = Depends(get_admin_user)
):
    """Get rate limiting statistics for admin dashboard"""
    return {
        "current_usage": await get_current_usage_by_tier(),
        "denial_rates": await get_denial_rates_by_operation(),
        "top_users": await get_top_users_by_usage(),
        "system_load": await get_system_load_metrics(),
        "geographic_distribution": await get_usage_by_geography()
    }

@router.post("/admin/rate-limits/adjust")
async def adjust_rate_limits(
    adjustment: RateLimitAdjustment,
    current_user: User = Depends(get_admin_user)
):
    """Temporarily adjust rate limits"""
    # Implement emergency rate limit adjustments
    pass
```

## 🚨 Error Handling & User Experience

### 1. **Rate Limit Response Format**

```python
# Standard rate limit error response
{
    "error": "rate_limit_exceeded",
    "message": "Too many AI generation requests. You've reached your limit of 5 requests per hour.",
    "details": {
        "operation": "ai_generation",
        "current_usage": 5,
        "limit": 5,
        "reset_time": "2024-08-21T15:30:00Z",
        "retry_after": 3420  # seconds
    },
    "suggestions": {
        "immediate": [
            "Try again in 57 minutes",
            "Use project validation to test your configuration first"
        ],
        "upgrade": {
            "tier": "pro",
            "benefits": ["50 AI generations per hour", "Priority processing"],
            "upgrade_url": "/pricing?upgrade=pro"
        }
    },
    "alternatives": [
        {
            "action": "use_template",
            "description": "Start with a template and customize it",
            "url": "/templates"
        },
        {
            "action": "project_preview", 
            "description": "Preview your configuration without generating",
            "endpoint": "POST /projects/preview"
        }
    ]
}
```

### 2. **Client-Side Rate Limit Handling**

```typescript
// Frontend rate limit handling
class RateLimitHandler {
    private retryTimers = new Map<string, number>();
    
    handleRateLimit(error: RateLimitError) {
        const { operation, retryAfter, suggestions } = error;
        
        // Show user-friendly message
        this.showRateLimitNotification({
            title: "Generation Limit Reached",
            message: error.message,
            retryAfter: retryAfter,
            alternatives: suggestions.alternatives,
            upgradeOption: suggestions.upgrade
        });
        
        // Schedule automatic retry
        if (retryAfter && retryAfter < 3600) { // Less than 1 hour
            this.scheduleRetry(operation, retryAfter);
        }
        
        // Track metrics
        this.trackRateLimitHit(operation, error.currentUsage, error.limit);
    }
    
    private scheduleRetry(operation: string, retryAfter: number) {
        const timerId = setTimeout(() => {
            this.showRetryNotification(operation);
            this.retryTimers.delete(operation);
        }, retryAfter * 1000);
        
        this.retryTimers.set(operation, timerId);
    }
}
```

## 🔧 Deployment & Configuration

### 1. **Environment Configuration**

```yaml
# .env.production
ENABLE_RATE_LIMITING=true
ENABLE_DYNAMIC_LIMITS=true
ENABLE_BURST_LIMITS=true
RATE_LIMIT_REDIS_URL=redis://redis-cluster:6379/1

# System tuning
RATE_LIMIT_SYSTEM_LOAD_THRESHOLD=0.8
RATE_LIMIT_OFF_PEAK_BONUS=1.5
RATE_LIMIT_REPUTATION_BONUS=1.2

# Geographic settings
ENABLE_GEOGRAPHIC_LIMITS=true
DEFAULT_GEOGRAPHIC_MULTIPLIER=1.0
```

### 2. **Redis Configuration**

```redis.conf
# Redis configuration for rate limiting
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence (optional for rate limiting)
save ""
appendonly no

# Performance tuning
tcp-keepalive 60
timeout 300
```

### 3. **Docker Compose Updates**

```yaml
# docker-compose.prod.yml additions
services:
  redis-rate-limit:
    image: redis:7-alpine
    volumes:
      - ./configs/redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    networks:
      - codebegen-network
  
  app:
    environment:
      - RATE_LIMIT_REDIS_URL=redis://redis-rate-limit:6379/1
    depends_on:
      - redis-rate-limit
```

## 📈 Performance Considerations

### 1. **Redis Optimization**

- **Connection Pooling**: Use Redis connection pool for better performance
- **Pipeline Operations**: Batch Redis operations where possible
- **Memory Management**: Configure appropriate TTL and memory policies
- **Monitoring**: Track Redis performance metrics

### 2. **Caching Strategy**

```python
# Cache frequently accessed data
class RateLimitCache:
    def __init__(self):
        self.user_tier_cache = {}  # Cache user tiers
        self.reputation_cache = {}  # Cache user reputation scores
        self.system_load_cache = None  # Cache system load
        
    async def get_user_tier(self, user_id: str) -> UserTier:
        if user_id not in self.user_tier_cache:
            tier = await self._fetch_user_tier(user_id)
            self.user_tier_cache[user_id] = tier
            # Set expiration
            asyncio.create_task(self._expire_cache_entry(user_id, 300))
        return self.user_tier_cache[user_id]
```

### 3. **Async Optimization**

- **Non-blocking Operations**: All rate limit checks are async
- **Background Cleanup**: Clean expired entries in background tasks
- **Batch Processing**: Process multiple rate limit checks together

## 🔄 Migration Plan

### Phase 1: Enhanced Current Implementation (Week 1)
1. Add user tier-based rate limiting
2. Implement endpoint-specific limits
3. Add proper error responses
4. Basic monitoring setup

### Phase 2: Advanced Features (Week 2-3)
1. Dynamic rate limiting
2. Burst allowance
3. Geographic adjustments
4. User reputation system

### Phase 3: Production Optimization (Week 4)
1. Performance optimization
2. Advanced monitoring
3. Admin dashboard
4. Load testing and tuning

## 🎯 Success Metrics

### Technical Metrics
- **Rate Limit Check Latency**: < 5ms p99
- **Redis Memory Usage**: < 100MB for 10,000 active users
- **System Load Impact**: < 1% CPU overhead
- **Error Rate**: < 0.1% false positives

### Business Metrics  
- **Conversion Rate**: 15% of rate-limited users upgrade
- **User Retention**: No negative impact on user retention
- **Support Tickets**: < 5% rate limit related tickets
- **Revenue Protection**: Prevent $10,000/month in AI API overages

## 🔚 Conclusion

This comprehensive rate limiting design provides:

1. **Scalable Architecture**: Handles millions of requests with minimal overhead
2. **User Experience**: Graceful degradation with helpful error messages
3. **Business Value**: Drives upgrades while protecting resources
4. **Operational Excellence**: Full monitoring and administrative controls
5. **Future-Proof**: Extensible design for new features and requirements

The implementation balances technical robustness with business needs, ensuring CodebeGen can scale effectively while maintaining service quality and driving revenue growth.
