# 🚀 Preview Tab - Phase 5 Production Implementation

**Status**: Planned for Phase 5  
**Timeline**: Weeks 3-4 after MVP complete  
**Version**: 2.0 Production-Grade  
**Last Updated**: October 20, 2025

---

## 📋 Executive Summary

Phase 5 transforms the lightweight MVP preview into a **production-grade, scalable preview system** using Docker containerization, advanced resource management, persistent logging, and enterprise features. This phase upgrades the infrastructure while maintaining backward compatibility with Phase 4.

### Phase 5 Goals
- ✅ Docker containerization with resource limits
- ✅ Production database support (PostgreSQL/MongoDB)
- ✅ Advanced logging with WebSocket streaming
- ✅ Multi-user concurrent previews (3-5 per user)
- ✅ Tier-based resource allocation
- ✅ Health monitoring and auto-recovery
- ✅ Performance optimization and caching
- ✅ Enterprise features (audit logs, analytics)

### Migration from MVP
- Backward compatible with Phase 4 API
- Gradual rollout (feature flags)
- Transparent to users
- Zero downtime migration

---

## 🏗️ Architecture - Phase 5 (Docker-Based)

### High-Level Flow

```
User clicks "Preview" in UI
        ↓
POST /api/generations/{generationId}/preview/launch
        ↓
[Backend Service] Validates generation + tier limits
        ↓
Load generated files from storage
        ↓
Generate Dockerfile from generation metadata
        ↓
Build Docker image (or use cached layer)
        ↓
Run container with resource limits (512MB RAM, 1 CPU)
        ↓
Setup production database (PostgreSQL/MongoDB based on generation)
        ↓
Run migrations + seed data (if provided)
        ↓
Perform comprehensive health check
        ↓
Return preview details + WebSocket URL
        ↓
User tests endpoints via HTTP proxy or WebSocket
        ↓
Real-time logs streamed via WebSocket
        ↓
GET /api/generations/{generationId}/preview/status (advanced metrics)
        ↓
DELETE /api/generations/{generationId}/preview
        ↓
Stop container + cleanup volumes + archive logs
```

### Technology Stack - Phase 5

| Component | Technology | Why |
|-----------|-----------|-----|
| **Runtime** | Docker containers | True isolation, production-representative |
| **Orchestration** | Docker Daemon (local) / Docker Compose | Simple local, scalable to Kubernetes |
| **Database** | PostgreSQL/MongoDB | Match generated tech stack exactly |
| **Resource Limits** | cgroups/Docker limits | 512MB RAM, 1 CPU per instance |
| **Networking** | Docker bridge + port mapping | Isolated networks per container |
| **Logging** | ELK stack or CloudWatch | Centralized, searchable logs |
| **WebSocket** | Python-Websockets | Real-time bidirectional streaming |
| **Caching** | Redis | Cache generated Dockerfiles, dependencies |
| **Monitoring** | Prometheus + Grafana | Advanced metrics and dashboards |

---

## 📊 Enhanced Data Models - Phase 5

### PreviewInstance Model (Updated)

```python
# app/models/preview.py - PHASE 5 UPDATES

class PreviewInstance(Base):
    """Production-grade preview instance with Docker support."""
    
    __tablename__ = "preview_instances"
    
    # === MVP Fields (preserved) ===
    id = Column(String(50), primary_key=True)
    generation_id = Column(String(50), ForeignKey("generations.id"))
    project_id = Column(String(50), ForeignKey("projects.id"))
    user_id = Column(String(50), ForeignKey("users.id"))
    
    status = Column(String(20))  # launching, running, healthy, degraded, unhealthy, failed, stopped
    base_url = Column(String(255))
    preview_token = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime)
    
    # === NEW: Docker Runtime ===
    container_id = Column(String(100), nullable=True)  # Docker container ID
    image_id = Column(String(100), nullable=True)  # Docker image ID
    container_status = Column(String(20))  # created, running, paused, restarting, exited
    
    # === NEW: Resource Management ===
    resource_limits = Column(JSON, default={
        "memory_mb": 512,
        "cpu_cores": 1,
        "storage_gb": 1
    })
    resource_usage = Column(JSON, default={})  # Current: memory%, cpu%, storage%
    last_resource_check = Column(DateTime, nullable=True)
    
    # === NEW: Database Configuration ===
    db_type = Column(String(20))  # sqlite, postgresql, mongodb (from generation)
    db_url = Column(String(500), nullable=True)  # Connection string
    db_ready = Column(Boolean, default=False)  # Ready after migrations
    
    # === NEW: Logging ===
    log_level = Column(String(10), default="INFO")
    max_log_lines = Column(Integer, default=10000)
    log_storage_location = Column(String(500))  # Path to log file or CloudWatch stream
    
    # === NEW: Health Monitoring ===
    health_status = Column(String(20), default="unknown")  # healthy, unhealthy, degraded
    last_health_check = Column(DateTime, nullable=True)
    health_check_interval = Column(Integer, default=30)  # seconds
    consecutive_failures = Column(Integer, default=0)  # For auto-recovery
    
    # === NEW: Performance Metrics ===
    request_count = Column(Integer, default=0)  # Total requests proxied
    error_count = Column(Integer, default=0)  # Failed requests
    avg_response_time = Column(Float)  # milliseconds
    
    # === NEW: Advanced Configuration ===
    environment_vars = Column(JSON, default={})  # Custom env vars
    volume_mounts = Column(JSON, default={})  # Docker volumes
    network_mode = Column(String(20), default="bridge")  # bridge, host, etc.
    
    # === NEW: Tier & Quotas ===
    user_tier = Column(String(20))  # free, pro, enterprise
    session_extensions_used = Column(Integer, default=0)
    session_extensions_allowed = Column(Integer)  # Based on tier
    
    # === NEW: Relationships ===
    logs = relationship("PreviewLog", back_populates="preview", cascade="all, delete-orphan")
    metrics = relationship("PreviewMetric", back_populates="preview", cascade="all, delete-orphan")
    events = relationship("PreviewEvent", back_populates="preview", cascade="all, delete-orphan")


class PreviewLog(Base):
    """Enhanced logging with structured format and real-time streaming."""
    
    __tablename__ = "preview_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    preview_instance_id = Column(String(50), ForeignKey("preview_instances.id"))
    
    # Timestamp and level
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(10), index=True)  # DEBUG, INFO, WARN, ERROR
    
    # Log content
    source = Column(String(50))  # request, database, startup, error, system
    message = Column(String(2000))
    
    # Structured metadata
    metadata = Column(JSON, default={})  # {statusCode, duration, userId, endpoint, etc.}
    
    # Trace information
    trace_id = Column(String(50), nullable=True)  # For distributed tracing
    
    preview = relationship("PreviewInstance", back_populates="logs")


class PreviewMetric(Base):
    """Time-series metrics for performance monitoring."""
    
    __tablename__ = "preview_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    preview_instance_id = Column(String(50), ForeignKey("preview_instances.id"))
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Container metrics
    memory_usage_mb = Column(Integer)
    cpu_usage_percent = Column(Float)
    disk_usage_mb = Column(Integer)
    
    # Request metrics
    requests_per_minute = Column(Integer)
    avg_response_time_ms = Column(Float)
    p95_response_time_ms = Column(Float)
    p99_response_time_ms = Column(Float)
    error_rate_percent = Column(Float)
    
    # Network metrics
    bytes_in = Column(Integer)
    bytes_out = Column(Integer)
    
    preview = relationship("PreviewInstance", back_populates="metrics")


class PreviewEvent(Base):
    """Audit trail of preview lifecycle events."""
    
    __tablename__ = "preview_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    preview_instance_id = Column(String(50), ForeignKey("preview_instances.id"))
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(50))  # launched, stopped, failed, degraded, recovered, extended
    event_data = Column(JSON)  # Details specific to event type
    
    preview = relationship("PreviewInstance", back_populates="events")
```

### Generation Model (Updated)

```python
# app/models/generation.py - ADD NEW FIELDS FOR PREVIEW

class Generation(Base):
    # ... existing fields ...
    
    # NEW: Preview metadata extracted during generation
    generated_dockerfile = Column(Text, nullable=True)  # Generated Dockerfile
    docker_image_name = Column(String(255), nullable=True)  # Suggested image name
    entry_point = Column(String(100), default="uvicorn app.main:app")
    
    # Tech stack details
    db_type = Column(String(20))  # sqlite, postgresql, mongodb
    db_version = Column(String(20))  # e.g., "14.0" for PostgreSQL
    python_version = Column(String(20), default="3.11")
    
    # Preview requirements
    requires_migrations = Column(Boolean, default=True)
    seed_data_included = Column(Boolean, default=False)
    
    # Health check endpoint
    health_check_endpoint = Column(String(255), default="/health")
    health_check_interval = Column(Integer, default=30)  # seconds
    
    preview_instances = relationship("PreviewInstance", back_populates="generation")
```

---

## 🔌 Enhanced API Endpoints - Phase 5

All MVP endpoints work exactly the same, with these enhancements:

### 1. Launch Preview (Enhanced)

**Request** (same as MVP, with optional fields):
```json
{
  "generationId": "gen_abc123",
  "projectId": "proj_xyz789",
  "databaseType": "postgresql",  // Optional override
  "resourceTier": "standard",    // "minimal", "standard", "pro"
  "autoMigrateDatabase": true    // Run migrations automatically
}
```

**Response** (enhanced):
```json
{
  "status": "launched",
  "previewInstanceId": "preview_789abc",
  "baseUrl": "http://localhost:3001",
  "wsUrl": "ws://localhost:8000/api/generations/{id}/preview/logs",
  "previewToken": "preview_abc123xyz_token",
  "resourceAllocated": {
    "memory": "512MB",
    "cpu": "1 core",
    "storage": "1GB"
  },
  "database": {
    "type": "postgresql",
    "ready": true,
    "migrationStatus": "completed"
  },
  "expiresAt": "2025-10-20T13:30:00Z",
  "canExtend": true,
  "extensionsRemaining": 2
}
```

---

### 2. Get Preview Status (Enhanced)

**Response** (enhanced with detailed metrics):
```json
{
  "previewInstanceId": "preview_789abc",
  "status": "running",
  "containerStatus": "running",
  "baseUrl": "http://localhost:3001",
  "uptime": 3600,
  
  "health": {
    "status": "healthy",
    "checks": [
      { "name": "http", "status": "passing", "lastCheck": "2025-10-20T12:20:15Z" },
      { "name": "database", "status": "passing", "lastCheck": "2025-10-20T12:20:15Z" },
      { "name": "memory", "status": "passing", "usage": "45%" }
    ]
  },
  
  "resources": {
    "memory": {
      "allocated": "512MB",
      "used": "230MB",
      "percent": 45
    },
    "cpu": {
      "allocated": "1 core",
      "used": 0.35,
      "percent": 35
    },
    "storage": {
      "allocated": "1GB",
      "used": "350MB",
      "percent": 35
    }
  },
  
  "performance": {
    "requestCount": 1250,
    "errorCount": 3,
    "errorRate": "0.24%",
    "avgResponseTime": "125ms",
    "p95ResponseTime": "450ms"
  },
  
  "database": {
    "type": "postgresql",
    "status": "connected",
    "migrationStatus": "completed",
    "tables": 12,
    "records": 1523
  },
  
  "expiresAt": "2025-10-20T13:30:00Z",
  "timeRemaining": 3600,
  "canExtend": true,
  "extensionsRemaining": 2,
  
  "generatedEndpoints": [
    {
      "method": "GET",
      "path": "/api/users",
      "description": "List all users",
      "responseTime": "50ms",
      "status": "200"
    }
  ]
}
```

---

### 3. WebSocket: Stream Preview Logs (NEW)

**WebSocket Endpoint**: `WS /api/generations/{generationId}/preview/logs`

**Connection Query Params**:
```
?token={previewToken}&level=INFO&buffer=100
```

**Subscribe Message** (client → server):
```json
{
  "action": "subscribe",
  "filters": {
    "level": "INFO",  // INFO, WARN, ERROR, DEBUG
    "source": ["request", "database"],  // Optional filtering
    "search": "error"  // Optional text search
  }
}
```

**Log Stream** (server → client):
```json
{
  "type": "log",
  "timestamp": "2025-10-20T12:20:15Z",
  "level": "INFO",
  "source": "request",
  "message": "GET /api/users completed in 45ms",
  "metadata": {
    "method": "GET",
    "path": "/api/users",
    "statusCode": 200,
    "duration": 45,
    "userId": "user_123"
  }
}
```

**Metrics Stream** (server → client):
```json
{
  "type": "metric",
  "timestamp": "2025-10-20T12:20:30Z",
  "metric": "resource_usage",
  "data": {
    "memory": 245,
    "cpu": 0.42,
    "requests_per_minute": 120,
    "error_rate": 0.24
  }
}
```

**Health Status Stream** (server → client):
```json
{
  "type": "health",
  "timestamp": "2025-10-20T12:20:30Z",
  "status": "healthy",
  "changes": [
    { "name": "database", "status": "healthy", "message": "Connected" }
  ]
}
```

---

### 4. Extend Preview Session (NEW)

**Endpoint**: `POST /api/generations/{generationId}/preview/extend`

**Request**:
```json
{
  "duration": 1800  // Extend by 30 minutes
}
```

**Response**:
```json
{
  "status": "extended",
  "newExpiresAt": "2025-10-20T14:00:00Z",
  "extensionsRemaining": 1,
  "maxExtensions": 3
}
```

---

### 5. Get Performance Metrics (NEW)

**Endpoint**: `GET /api/generations/{generationId}/preview/metrics?start=2025-10-20T12:00:00Z&end=2025-10-20T12:30:00Z`

**Response**:
```json
{
  "metrics": {
    "memory": [
      { "timestamp": "2025-10-20T12:00:00Z", "value": 200 },
      { "timestamp": "2025-10-20T12:01:00Z", "value": 215 }
    ],
    "cpu": [
      { "timestamp": "2025-10-20T12:00:00Z", "value": 0.30 }
    ],
    "responseTime": [
      { "timestamp": "2025-10-20T12:00:00Z", "value": 120, "p95": 450, "p99": 890 }
    ],
    "errors": [
      { "timestamp": "2025-10-20T12:05:00Z", "count": 2, "type": "timeout" }
    ]
  }
}
```

---

### 6. Download Preview Logs (NEW)

**Endpoint**: `GET /api/generations/{generationId}/preview/logs/export?format=json&level=ERROR`

**Response**: JSON, CSV, or GZIP file with all logs

---

### 7. Compare Preview with Version (NEW)

**Endpoint**: `GET /api/generations/{generationId}/preview/compare/{otherVersionId}`

**Response**:
```json
{
  "comparison": {
    "endpoints": {
      "added": [
        { "method": "DELETE", "path": "/api/users/{id}" }
      ],
      "removed": [],
      "modified": []
    },
    "performance": {
      "avgResponseTimeChange": "-15%",
      "errorRateChange": "-50%"
    },
    "models": {
      "added": [],
      "modified": ["User"]
    }
  }
}
```

---

## 🐳 Docker Integration - Phase 5

### Generated Dockerfile (Phase 5)

During generation, extract and store:

```dockerfile
# Generated and stored in generation metadata
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Service - Phase 5

```python
# app/services/docker_preview_service.py - NEW FILE

class DockerPreviewService:
    """Manages Docker containers for preview instances."""
    
    async def build_preview_image(
        self,
        generation_id: str,
        dockerfile_content: str,
        generation_files: Dict[str, str]
    ) -> str:
        """Build Docker image from generation files."""
        # 1. Check cache (if image exists, return)
        cached_image = await self.get_cached_image(generation_id)
        if cached_image:
            return cached_image
        
        # 2. Create build context
        build_context = self.create_build_context(
            dockerfile_content,
            generation_files
        )
        
        # 3. Build image
        image_tag = f"codebegen-preview:{generation_id}"
        image = await docker_client.images.build(
            path=build_context,
            tag=image_tag,
            buildargs={"GENERATION_ID": generation_id},
            rm=True
        )
        
        # 4. Cache image ID
        await cache_store.set(f"docker_image:{generation_id}", image.id)
        
        return image.id
    
    async def run_preview_container(
        self,
        image_id: str,
        preview_instance: PreviewInstance,
        generation: Generation
    ) -> str:
        """Run Docker container with resource limits."""
        # 1. Setup volumes
        volumes = {
            f"preview_{preview_instance.id}_db": {
                "bind": "/app/data",
                "mode": "rw"
            }
        }
        
        # 2. Setup environment
        environment = {
            "DATABASE_URL": generation.db_url,
            "LOG_LEVEL": preview_instance.log_level,
            "PYTHONUNBUFFERED": "1"
        }
        
        # 3. Run container with resource limits
        container = await docker_client.containers.run(
            image_id,
            detach=True,
            ports={"8000/tcp": ("127.0.0.1", preview_instance.port)},
            volumes=volumes,
            environment=environment,
            mem_limit=preview_instance.resource_limits["memory_mb"] * 1024 * 1024,
            cpu_period=100000,
            cpu_quota=int(preview_instance.resource_limits["cpu_cores"] * 100000),
            restart_policy={"Name": "on-failure", "MaximumRetryCount": 3}
        )
        
        return container.id
    
    async def monitor_container(
        self,
        container_id: str,
        preview_instance_id: str
    ):
        """Monitor container health and metrics continuously."""
        container = docker_client.containers.get(container_id)
        
        while True:
            # Check status
            container.reload()
            status = container.status
            
            # Get stats
            stats = container.stats(stream=False)
            
            # Update preview instance
            memory_usage = stats["memory_stats"]["usage"] / (1024 * 1024)
            cpu_usage = self.calculate_cpu_percent(stats)
            
            await db.update_preview_metrics(
                preview_instance_id,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage
            )
            
            # Check for unhealthy status
            if status != "running":
                await handle_container_failure(preview_instance_id, status)
                break
            
            await asyncio.sleep(30)  # Check every 30 seconds
```

---

## 📁 File Structure - Phase 5

```
app/
├── models/
│   ├── preview.py  # UPDATED: Enhanced with Docker fields
│   ├── generation.py  # UPDATED: Add generated_dockerfile, db_type
│   └── preview_metrics.py  # NEW: Metrics and events
│
├── routers/
│   └── preview.py  # UPDATED: New endpoints (extend, metrics, etc.)
│
├── services/
│   ├── docker_preview_service.py  # NEW: Docker orchestration
│   ├── preview_database_service.py  # NEW: DB setup per generation
│   ├── preview_logging_service.py  # NEW: Structured logging
│   ├── preview_metrics_service.py  # NEW: Performance metrics
│   ├── preview_health_service.py  # NEW: Health checks & monitoring
│   └── preview_cache_service.py  # NEW: Docker image caching
│
├── websockets/
│   └── preview_logs_ws.py  # NEW: WebSocket log streaming
│
├── schemas/
│   └── preview.py  # UPDATED: New request/response models
│
└── tasks/
    ├── preview_cleanup_task.py  # UPDATED: Enhanced cleanup
    └── preview_monitoring_task.py  # NEW: Continuous monitoring

infra/
├── docker/
│   ├── Dockerfile.preview  # Base image for preview instances
│   └── docker-compose.preview.yml  # Local Docker Compose setup
│
└── monitoring/
    ├── prometheus-config.yml  # Prometheus scrape config
    └── grafana-dashboard.json  # Grafana dashboard

alembic/
└── versions/
    ├── XXXX_add_preview_metrics.py  # NEW: Metrics tables
    └── XXXX_add_preview_docker_fields.py  # NEW: Docker fields
```

---

## 🔧 Environment Variables - Phase 5

Add to `.env`:

```bash
# === Docker Configuration ===
DOCKER_HOST=unix:///var/run/docker.sock
DOCKER_IMAGE_REGISTRY=localhost  # Or Docker Hub for production

# === Resource Allocation (by tier) ===
PREVIEW_RESOURCE_TIER_FREE={"memory": 256, "cpu": 0.5}
PREVIEW_RESOURCE_TIER_PRO={"memory": 1024, "cpu": 2}
PREVIEW_RESOURCE_TIER_ENTERPRISE={"memory": 2048, "cpu": 4}

# === Session Management ===
PREVIEW_SESSION_TIMEOUT_HOURS=2  # Default session duration
PREVIEW_SESSION_EXTENSION_MINUTES=30  # Per extension
PREVIEW_MAX_EXTENSIONS=3  # Free tier
PREVIEW_MAX_INSTANCES_PER_USER=3  # Pro tier

# === Database Support ===
PREVIEW_SUPPORT_POSTGRESQL=true
PREVIEW_SUPPORT_MONGODB=true
PREVIEW_SUPPORT_SQLITE=true

PREVIEW_POSTGRESQL_POOL_SIZE=10
PREVIEW_POSTGRESQL_POOL_TIMEOUT=30

# === Logging ===
PREVIEW_LOG_BACKEND=cloudwatch  # or elasticsearch, syslog, file
PREVIEW_LOG_RETENTION_DAYS=7
PREVIEW_LOG_STREAM_BUFFER_SIZE=1000

# === Monitoring ===
PREVIEW_METRICS_RETENTION_DAYS=30
PREVIEW_HEALTH_CHECK_INTERVAL=30
PREVIEW_HEALTH_CHECK_TIMEOUT=10

# === Caching ===
PREVIEW_DOCKER_IMAGE_CACHE_TTL=86400  # 24 hours
PREVIEW_DOCKERFILE_CACHE=true

# === Performance ===
PREVIEW_REQUEST_TIMEOUT=60
PREVIEW_DATABASE_INITIALIZATION_TIMEOUT=120
```

---

## 🚀 Implementation Tasks - Phase 5

### Week 3: Docker Infrastructure

**Task 3.1**: Docker integration layer
- [ ] Create `DockerPreviewService`
- [ ] Implement image building from Dockerfile
- [ ] Implement container orchestration
- [ ] Handle resource limits (CPU, memory)
- [ ] Implement container health checks

**Task 3.2**: Database setup per generation
- [ ] Create `PreviewDatabaseService`
- [ ] Auto-detect DB type from generation
- [ ] Setup PostgreSQL test instance (if needed)
- [ ] Run migrations automatically
- [ ] Seed sample data (if provided)

**Task 3.3**: Enhanced models & migrations
- [ ] Update `PreviewInstance` model
- [ ] Create `PreviewMetric` model
- [ ] Create `PreviewEvent` model
- [ ] Write Alembic migrations
- [ ] Test migrations locally

**Task 3.4**: New endpoints (part 1)
- [ ] `POST /preview/extend` endpoint
- [ ] `GET /preview/metrics` endpoint
- [ ] Update all existing endpoints to support Docker

### Week 4: Monitoring & Polish

**Task 4.1**: Logging infrastructure
- [ ] Create `PreviewLoggingService`
- [ ] Structured JSON logging
- [ ] Log aggregation (CloudWatch/ELK)
- [ ] Log retention policies
- [ ] Log export functionality

**Task 4.2**: WebSocket streaming
- [ ] Implement WebSocket endpoint for logs
- [ ] Real-time log streaming
- [ ] Real-time metrics streaming
- [ ] Health status updates
- [ ] Error/warning alerts

**Task 4.3**: Health monitoring
- [ ] Create `PreviewHealthService`
- [ ] Continuous health checks
- [ ] Auto-recovery on failure
- [ ] Degraded mode handling
- [ ] Alerting

**Task 4.4**: Performance optimization
- [ ] Docker image caching
- [ ] Layer optimization
- [ ] Build time reduction
- [ ] Memory/CPU optimization
- [ ] Startup time profiling

**Task 4.5**: Testing & documentation
- [ ] Unit tests for Docker service
- [ ] Integration tests with containers
- [ ] Performance benchmarks
- [ ] Upgrade guide from Phase 4
- [ ] Troubleshooting documentation
- [ ] Operations runbook

---

## 📋 New Endpoints - Phase 5 Summary

| # | Endpoint | Method | MVP | Phase 5 |
|---|----------|--------|-----|---------|
| 1 | `/preview/launch` | POST | ✅ | ✅ Enhanced |
| 2 | `/preview/status` | GET | ✅ | ✅ Enhanced |
| 3 | `/preview` | DELETE | ✅ | ✅ Same |
| 4 | `/endpoints` | GET | ✅ | ✅ Same |
| 5 | `/preview/request` | POST | ✅ | ✅ Same |
| 6 | `/preview/config` | GET | ✅ | ✅ Enhanced |
| 7 | `/preview/logs` | GET | ✅ | ✅ Enhanced |
| 8 | `/preview/logs` | WS | ❌ | ✅ **NEW** |
| 9 | `/preview/extend` | POST | ❌ | ✅ **NEW** |
| 10 | `/preview/metrics` | GET | ❌ | ✅ **NEW** |
| 11 | `/preview/logs/export` | GET | ❌ | ✅ **NEW** |
| 12 | `/preview/compare/{versionId}` | GET | ❌ | ✅ **NEW** |

---

## 🔐 Security Enhancements - Phase 5

### Container Isolation
- ✅ Containers run in separate process namespaces
- ✅ Network isolation via Docker bridge network
- ✅ Volume isolation (no cross-container access)
- ✅ Resource limits prevent DOS attacks
- ✅ Read-only filesystems where possible

### Enhanced Authentication
- ✅ Preview tokens with expiration
- ✅ Token rotation on container restart
- ✅ Rate limiting per user/token
- ✅ Audit trail of all preview access

### Network Security
- ✅ Containers accessible only via proxy
- ✅ No direct port exposure
- ✅ HTTPS support for WebSocket (WSS)
- ✅ CORS headers properly configured

### Data Protection
- ✅ Secrets management (env vars)
- ✅ Database credentials encrypted
- ✅ Log sanitization (remove sensitive data)
- ✅ Audit logging of sensitive operations

---

## 📊 Performance Targets - Phase 5

### Launch Performance
- Container startup: < 10 seconds (cached: < 3 seconds)
- Database initialization: < 5 seconds (existing DB: instant)
- Health check: < 2 seconds
- **Total launch time**: < 20 seconds

### Runtime Performance
- Proxy request latency: < 200ms (p95)
- WebSocket log delivery: < 100ms
- Metrics collection: < 50ms
- **Memory usage**: 512MB per instance
- **CPU usage**: < 0.5 cores average

### Scalability
- Support 100+ concurrent previews (with load balancer)
- Database pools shared efficiently
- Image caching reduces rebuild time by 80%
- Container reuse across generations

---

## 🧪 Testing Strategy - Phase 5

### Docker Integration Tests
```python
@pytest.mark.asyncio
async def test_build_docker_image(docker_service, generation):
    image_id = await docker_service.build_preview_image(
        generation.id,
        generation.generated_dockerfile,
        generation.files
    )
    assert image_id is not None
    assert await docker_service.image_exists(image_id)

@pytest.mark.asyncio
async def test_run_container_with_resource_limits(docker_service):
    container_id = await docker_service.run_preview_container(
        image_id="test_image",
        preview_instance=preview,
        generation=generation
    )
    stats = await docker_service.get_container_stats(container_id)
    assert stats["memory_usage_mb"] <= 512
```

### WebSocket Tests
```python
@pytest.mark.asyncio
async def test_websocket_log_streaming(client, preview):
    async with client.websocket_connect(
        f"/api/generations/{preview.generation_id}/preview/logs"
    ) as ws:
        await ws.send_json({"action": "subscribe", "filters": {"level": "INFO"}})
        
        data = await ws.receive_json()
        assert data["type"] in ["log", "metric", "health"]
```

---

## 🔄 Migration Path: MVP → Phase 5

### Zero-Downtime Migration Strategy

```
Week 1-2: Deploy Phase 5 code behind feature flag
Week 3: Canary deployment (5% of users)
Week 4: Monitor metrics, fix issues
Week 5: Gradual rollout (25% → 50% → 100%)
Week 6: Cleanup (remove MVP code, optimize)
```

### Backward Compatibility
- All MVP endpoints continue to work
- Feature flags control Docker vs in-process
- Configuration options for hybrid mode
- Fallback to MVP if Docker fails

---

## 📈 Metrics & Monitoring - Phase 5

### Key Metrics

```python
# Prometheus metrics
- preview_instances_total (gauge)
- preview_launches_total (counter)
- preview_errors_total (counter)
- preview_launch_duration_seconds (histogram)
- preview_request_duration_seconds (histogram)
- preview_memory_usage_bytes (gauge)
- preview_cpu_usage_percent (gauge)
- docker_image_build_duration_seconds (histogram)
- docker_container_startup_duration_seconds (histogram)
```

### Dashboards
- Preview launch success rate
- Average session duration
- Resource utilization trends
- Error rate by error type
- User tier distribution

---

## 🎯 Success Criteria - Phase 5

### Technical Success
- [ ] All Docker operations < 20 seconds
- [ ] WebSocket streaming <100ms latency
- [ ] 99.9% uptime (SLA)
- [ ] Zero critical bugs in production
- [ ] Proper resource cleanup on all code paths

### User Success
- [ ] Users report faster/more reliable previews
- [ ] WebSocket logs useful for debugging
- [ ] Metrics help understand performance
- [ ] Tier-based features work as expected
- [ ] NPS score improves by 10+ points

### Operational Success
- [ ] Runbooks complete and tested
- [ ] On-call team trained
- [ ] Monitoring alerts configured
- [ ] Disaster recovery procedures documented
- [ ] Performance baselines established

---

## 🚀 Deployment Checklist - Phase 5

- [ ] All tests passing (unit + integration + load)
- [ ] Docker image base is properly optimized
- [ ] Environment variables documented
- [ ] Database migrations tested
- [ ] Monitoring and alerting configured
- [ ] Incident response procedures ready
- [ ] Performance baselines established
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Stakeholders approved for rollout

---

## 📚 Phase 5 Documentation

- [Docker Integration Guide](./DOCKER_INTEGRATION.md) - _Create after phase 4_
- [WebSocket API Reference](./WEBSOCKET_REFERENCE.md) - _Create after phase 4_
- [Performance Tuning Guide](./PERFORMANCE_TUNING.md) - _Create after phase 4_
- [Operational Runbook](./RUNBOOK.md) - _Create before phase 5 launch_
- [Upgrade Guide from MVP](./MVP_TO_PHASE5_UPGRADE.md) - _Create before phase 5 launch_

---

## 🔄 Comparison: MVP vs Phase 5

| Feature | MVP | Phase 5 |
|---------|-----|---------|
| **Runtime** | Python subprocess | Docker container |
| **Startup Time** | 1-3 sec | 10-20 sec (cold), <3 sec (cached) |
| **Database** | SQLite only | PostgreSQL, MongoDB, SQLite |
| **Resource Limits** | Soft (no enforcement) | Hard (CPU, memory, disk) |
| **Isolation** | Shared OS | Container namespace |
| **Logging** | File-based | Centralized (CloudWatch/ELK) |
| **Metrics** | None | Real-time (memory, CPU, requests) |
| **Monitoring** | Manual | Automated health checks |
| **Scalability** | 1 per user | 3-5 per user |
| **Price** | Included | Based on tier |
| **Production-Ready** | No | Yes |

---

**Phase 5 represents a production-grade upgrade while maintaining MVP compatibility. Start Phase 5 planning 2 weeks before Phase 4 ships!**
