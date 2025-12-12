# 🚀 Preview Tab - MVP Implementation (Phase 4)

**Status**: In Planning  
**Timeline**: Weeks 1-2 of Phase 4  
**Version**: 1.0 MVP  
**Last Updated**: October 20, 2025

---

## 📋 Executive Summary

The Preview Tab MVP enables users to test generated FastAPI backends in a **lightweight, fast iteration environment** without complex infrastructure setup. This phase focuses on **core functionality** with **minimal dependencies** to ship quickly and gather user feedback.

### Phase 4 Goals
- ✅ Launch and stop preview instances in <3 seconds
- ✅ Execute generated code with in-process Uvicorn
- ✅ Test generated API endpoints via proxy
- ✅ View instance status and health
- ✅ Display generated endpoints for quick reference
- ✅ **Real-time log streaming via SSE (terminal-style UX)** ← CRITICAL FOR MVP
- ✅ Subprocess output capture and display

### Out of Scope (Phase 5)
- ❌ Docker containerization
- ❌ Production resource limits
- ❌ Advanced logging & WebSocket streaming
- ❌ Multi-project preview management
- ❌ Cloud deployment

---

## 🏗️ Architecture - MVP (In-Process Execution)

### High-Level Flow

```
User clicks "Preview" in UI
        ↓
POST /api/generations/{generationId}/preview/launch
        ↓
[Backend Service] Validates generation + allocates port
        ↓
Load generated files from storage
        ↓
Create temp directory with project structure
        ↓
Start Uvicorn subprocess with SQLite database
        ↓
Run health check (retry 3x with 1sec interval)
        ↓
Return preview details + token
        ↓
User tests endpoints via proxy requests
        ↓
GET /api/generations/{generationId}/preview/status
        ↓
DELETE /api/generations/{generationId}/preview (optional)
        ↓
Stop Uvicorn subprocess + cleanup temp files
```

### Technology Stack - MVP

| Component | Technology | Why |
|-----------|-----------|-----|
| **Runtime** | Subprocess + Uvicorn | Fast startup, no Docker overhead |
| **Database** | SQLite (in-memory/file) | No external dependencies, fast |
| **Port Allocation** | Port pool (3001-3100) | Simple, conflict-free |
| **Authentication** | Bearer token (JWT-like) | Lightweight, session-based |
| **Log Streaming** | SSE (Server-Sent Events) | Real-time logs, simple HTTP, auto-reconnect |
| **Log Capture** | Threading + subprocess pipes | Non-blocking, immediate output capture |
| **Cleanup** | Background task (5min interval) | Simple resource management |

---

## 📊 Data Models - MVP

### PreviewInstance Model

```python
# app/models/preview.py

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime, timedelta

class PreviewInstance(Base):
    """Represents a running preview instance of generated code."""
    
    __tablename__ = "preview_instances"
    
    # Identifiers
    id = Column(String(50), primary_key=True)  # preview_789abc
    generation_id = Column(String(50), ForeignKey("generations.id"))
    project_id = Column(String(50), ForeignKey("projects.id"))
    user_id = Column(String(50), ForeignKey("users.id"))
    
    # Runtime Information
    status = Column(String(20))  # launching, running, failed, stopped
    port = Column(Integer)  # 3001-3100
    base_url = Column(String(255))  # http://localhost:3001
    process_id = Column(Integer, nullable=True)  # OS process ID
    
    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime)  # Auto-stop time
    
    # Authentication
    preview_token = Column(String(100))  # One-time token for this session
    token_expires_at = Column(DateTime)
    
    # Health & Diagnostics
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(20), default="unknown")  # unknown, healthy, unhealthy
    error_message = Column(String(500), nullable=True)
    
    # Configuration (MVP = simple)
    temp_directory = Column(String(500))  # Path to temp project files
    log_level = Column(String(10), default="ERROR")  # ERROR, WARN, INFO
    
    # Relationships
    generation = relationship("Generation", back_populates="preview_instances")
    user = relationship("User")
    project = relationship("Project")
    logs = relationship("PreviewLog", back_populates="preview")


class PreviewLog(Base):
    """Lightweight log entries from preview instances."""
    
    __tablename__ = "preview_logs"
    
    id = Column(Integer, primary_key=True)
    preview_instance_id = Column(String(50), ForeignKey("preview_instances.id"))
    
    # Log Entry
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(10))  # ERROR, WARN (MVP: errors only)
    message = Column(String(1000))
    
    # Relationships
    preview = relationship("PreviewInstance", back_populates="logs")
```

### Update Generation Model

```python
# app/models/generation.py - ADD this relationship

class Generation(Base):
    # ... existing fields ...
    
    # Add this relationship
    preview_instances = relationship(
        "PreviewInstance",
        back_populates="generation",
        cascade="all, delete-orphan"
    )
```

---

## 🔌 API Endpoints - MVP

### 1. Launch Preview Instance

**Endpoint**: `POST /api/generations/{generationId}/preview/launch`

**Headers**:
```
Authorization: Bearer <user_jwt_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "generationId": "gen_abc123",
  "projectId": "proj_xyz789"
}
```

**Success Response** (200 OK):
```json
{
  "status": "launched",
  "previewInstanceId": "preview_789abc",
  "generationId": "gen_abc123",
  "baseUrl": "http://localhost:3001",
  "previewToken": "preview_abc123xyz_token",
  "expiresAt": "2025-10-20T13:30:00Z",
  "healthCheckUrl": "http://localhost:3001/health"
}
```

**Error Response** (400/500):
```json
{
  "status": "failed",
  "error": "launch_failed",
  "message": "Cannot launch: Missing required files (main.py, requirements.txt)",
  "details": {
    "reason": "invalid_generation",
    "missingFiles": ["app/main.py"]
  }
}
```

**Status Codes**:
- `200` - Preview launched successfully
- `400` - Invalid generation or missing files
- `403` - User not authorized
- `409` - Another preview already running for this generation
- `500` - Server error during launch

**Logic**:
```python
async def launch_preview(
    generation_id: str,
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    # 1. Validate generation exists & belongs to user
    generation = await db.get_generation(generation_id)
    if not generation or generation.user_id != current_user.id:
        raise HTTPException(403, "Unauthorized")
    
    # 2. Check if preview already running
    existing = await db.get_active_preview(generation_id)
    if existing and existing.status == "running":
        raise HTTPException(409, "Preview already running")
    
    # 3. Validate generation has required files
    files = await storage.get_generation_files(generation_id)
    required = ["app/main.py", "requirements.txt"]
    if not all(f in files for f in required):
        raise HTTPException(400, "Missing required files")
    
    # 4. Check user's active preview limit (1 for MVP)
    user_active = await db.count_user_active_previews(current_user.id)
    if user_active >= 1:
        raise HTTPException(409, "User preview limit (1) reached")
    
    # 5. Allocate port & create preview record
    port = allocate_port()
    preview = PreviewInstance(
        id=f"preview_{generate_id()}",
        generation_id=generation_id,
        project_id=project_id,
        user_id=current_user.id,
        port=port,
        base_url=f"http://localhost:{port}",
        status="launching",
        preview_token=generate_secure_token(),
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    await db.save(preview)
    
    # 6. Start async launch task
    asyncio.create_task(launch_preview_instance(preview, generation, files))
    
    return {
        "status": "launched",
        "previewInstanceId": preview.id,
        "baseUrl": preview.base_url,
        "previewToken": preview.preview_token,
        "expiresAt": preview.expires_at.isoformat()
    }
```

---

### 2. Get Preview Status

**Endpoint**: `GET /api/generations/{generationId}/preview/status`

**Headers**:
```
Authorization: Bearer <user_jwt_token>
```

**Success Response** (200 OK):
```json
{
  "previewInstanceId": "preview_789abc",
  "status": "running",
  "baseUrl": "http://localhost:3001",
  "uptime": 3600,
  "lastHealthCheck": "2025-10-20T12:20:00Z",
  "healthStatus": "healthy",
  "createdAt": "2025-10-20T12:20:00Z",
  "expiresAt": "2025-10-20T13:30:00Z",
  "generatedEndpoints": [
    {
      "method": "GET",
      "path": "/api/users",
      "description": "List all users"
    },
    {
      "method": "POST",
      "path": "/api/users",
      "description": "Create new user"
    }
  ]
}
```

**Error Response** (404):
```json
{
  "status": "not_found",
  "error": "no_active_preview",
  "message": "No active preview for this generation"
}
```

**Logic**:
```python
async def get_preview_status(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    preview = await db.get_active_preview(generation_id)
    if not preview:
        raise HTTPException(404, "No active preview")
    
    # Check if expired
    if datetime.utcnow() > preview.expires_at:
        await stop_preview_instance(preview)
        raise HTTPException(404, "Preview expired")
    
    # Extract endpoints from generation metadata
    generation = await db.get_generation(generation_id)
    endpoints = parse_endpoints_from_generation(generation)
    
    return {
        "previewInstanceId": preview.id,
        "status": preview.status,
        "baseUrl": preview.base_url,
        "uptime": (datetime.utcnow() - preview.started_at).total_seconds(),
        "healthStatus": preview.health_status,
        "generatedEndpoints": endpoints
    }
```

---

### 3. Stop Preview Instance

**Endpoint**: `DELETE /api/generations/{generationId}/preview`

**Headers**:
```
Authorization: Bearer <user_jwt_token>
```

**Success Response** (200 OK):
```json
{
  "status": "stopped",
  "message": "Preview instance stopped successfully",
  "stoppedAt": "2025-10-20T12:30:00Z"
}
```

**Logic**:
```python
async def stop_preview(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    preview = await db.get_active_preview(generation_id)
    if not preview:
        raise HTTPException(404, "No active preview")
    
    await stop_preview_instance(preview)
    
    return {
        "status": "stopped",
        "message": "Preview instance stopped successfully"
    }
```

---

### 4. Get Generated Endpoints Metadata

**Endpoint**: `GET /api/generations/{generationId}/endpoints`

**Headers**:
```
Authorization: Bearer <user_jwt_token>
```

**Success Response** (200 OK):
```json
{
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/users",
      "description": "List all users",
      "requestSchema": {
        "query": {
          "page": "integer",
          "limit": "integer"
        }
      },
      "responseSchema": {
        "status": "string",
        "data": "array"
      }
    },
    {
      "method": "POST",
      "path": "/api/users",
      "description": "Create new user",
      "requestBody": {
        "name": "string",
        "email": "string"
      }
    }
  ]
}
```

**Logic**:
```python
async def get_endpoints(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    generation = await db.get_generation(generation_id)
    if not generation:
        raise HTTPException(404, "Generation not found")
    
    # Extract from generation metadata or Swagger spec
    endpoints = await extract_endpoints_from_generation(generation)
    
    return {"endpoints": endpoints}
```

---

### 5. Proxy API Calls to Preview Instance

**Endpoint**: `POST /api/generations/{generationId}/preview/request`

**Headers**:
```
Authorization: Bearer <user_jwt_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "method": "GET",
  "path": "/api/users",
  "query": {
    "page": 1,
    "limit": 10
  },
  "body": null,
  "headers": {
    "Accept": "application/json"
  }
}
```

**Success Response** (Proxied):
```json
{
  "statusCode": 200,
  "data": {
    "users": [
      { "id": "1", "name": "John", "email": "john@example.com" },
      { "id": "2", "name": "Jane", "email": "jane@example.com" }
    ]
  },
  "headers": {
    "content-type": "application/json"
  }
}
```

**Error Response** (Service unavailable):
```json
{
  "statusCode": 503,
  "error": "preview_unavailable",
  "message": "Preview instance not running or timed out"
}
```

**Logic**:
```python
async def proxy_request(
    generation_id: str,
    request_data: ProxyRequestSchema,
    current_user: User = Depends(get_current_user)
):
    # Get active preview
    preview = await db.get_active_preview(generation_id)
    if not preview or preview.status != "running":
        raise HTTPException(503, "Preview not available")
    
    # Validate token in headers
    token = request_data.headers.get("X-Preview-Token")
    if token != preview.preview_token:
        raise HTTPException(403, "Invalid preview token")
    
    # Forward request to preview instance
    try:
        response = await forward_http_request(
            base_url=preview.base_url,
            method=request_data.method,
            path=request_data.path,
            query=request_data.query,
            body=request_data.body,
            timeout=30
        )
        
        return {
            "statusCode": response.status_code,
            "data": response.json() if response.headers.get("content-type") == "application/json" else response.text,
            "headers": dict(response.headers)
        }
    except asyncio.TimeoutError:
        raise HTTPException(504, "Preview request timed out")
    except Exception as e:
        raise HTTPException(503, f"Preview error: {str(e)}")
```

---

### 6. Get Preview Configuration

**Endpoint**: `GET /api/generations/{generationId}/preview/config`

**Headers**:
```
Authorization: Bearer <user_jwt_token>
```

**Response** (200 OK):
```json
{
  "previewTimeout": 3600,
  "maxInstances": 1,
  "sessionExpiry": 3600,
  "autoStopInactiveAfter": 1800,
  "environment": {
    "NODE_ENV": "development",
    "LOG_LEVEL": "ERROR"
  },
  "limitations": {
    "tier": "free",
    "maxConcurrentPreviews": 1,
    "maxSessionDuration": 3600,
    "features": {
      "websocketLogs": false,
      "advancedMetrics": false
    }
  }
}
```

**Logic**:
```python
async def get_preview_config(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    user_tier = current_user.subscription_tier  # "free" or "pro"
    
    return {
        "previewTimeout": 3600,
        "maxInstances": 1 if user_tier == "free" else 3,
        "sessionExpiry": 3600,
        "autoStopInactiveAfter": 1800,
        "environment": {
            "NODE_ENV": "development",
            "LOG_LEVEL": "ERROR"
        },
        "limitations": {
            "tier": user_tier,
            "maxConcurrentPreviews": 1 if user_tier == "free" else 3,
            "maxSessionDuration": 3600,
            "features": {
                "websocketLogs": False,  # Phase 5
                "advancedMetrics": False  # Phase 5
            }
        }
    }
```

---

### 7. Stream Preview Logs (SSE Real-Time)

**Endpoint**: `GET /api/generations/{generationId}/preview/logs/stream` (Server-Sent Events)

**Headers**:
```
Authorization: Bearer <user_jwt_token>
Accept: text/event-stream
```

**Response** (200 OK - SSE Stream):
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

id: 1
data: {"timestamp": "2025-10-20T12:20:05Z", "level": "INFO", "message": "Starting Uvicorn server...", "source": "startup"}

id: 2
data: {"timestamp": "2025-10-20T12:20:06Z", "level": "INFO", "message": "Uvicorn running on http://127.0.0.1:3001", "source": "startup"}

id: 3
data: {"timestamp": "2025-10-20T12:20:07Z", "level": "INFO", "message": "GET /health 200 OK in 15ms", "source": "request"}

id: 4
data: {"timestamp": "2025-10-20T12:20:08Z", "level": "ERROR", "message": "Database connection failed: psycopg2.OperationalError", "source": "startup"}
```

**Why SSE for MVP?**
- ✅ Real-time logs (~100ms latency vs 2s polling)
- ✅ Terminal-like experience for users
- ✅ Simple HTTP (no WebSocket complexity)
- ✅ Auto-reconnect on disconnect
- ✅ Lower server load
- ✅ Easy to upgrade to WebSocket in Phase 5

**Logic**:
```python
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio

@router.get("/generations/{generation_id}/preview/logs/stream")
async def stream_preview_logs(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stream preview logs in real-time via SSE."""
    
    # Get active preview
    preview = await db.get_active_preview(generation_id)
    if not preview:
        raise HTTPException(404, "No active preview")
    
    # Verify user owns this preview
    if preview.user_id != current_user.id:
        raise HTTPException(403, "Unauthorized")
    
    # Get the log streamer for this preview
    streamer = preview_log_streamers.get(preview.id)
    if not streamer:
        raise HTTPException(503, "Preview logs not available")
    
    return StreamingResponse(
        streamer.stream_logs(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Connection": "keep-alive"
        }
    )
```

**Frontend Usage** (JavaScript):
```javascript
const eventSource = new EventSource(
    `/api/generations/${generationId}/preview/logs/stream`
)

eventSource.onmessage = (event) => {
    const log = JSON.parse(event.data)
    console.log(`[${log.level}] ${log.message}`)
    
    // Display in terminal UI
    terminalUI.appendLog(log)
}

eventSource.onerror = () => {
    console.error("SSE connection lost")
    eventSource.close()
}
```

---

## � SSE Implementation Deep Dive - MVP

### Architecture: Real-Time Log Streaming

The MVP uses **Server-Sent Events (SSE)** for real-time terminal-style log display:

```
Generated FastAPI Backend (subprocess)
    ↓ (stdout/stderr)
Thread Reader (captures line-by-line output)
    ↓ (pipe)
Log Queue (asyncio.Queue)
    ↓
SSE Endpoint (streaming to frontend)
    ↓ (async save)
Database (PreviewLog table)
    ↓ (HTTP stream)
Frontend (Terminal UI component)
```

### Backend Service: PreviewLogStreamer

```python
# filepath: app/services/preview_log_streamer.py - NEW FILE

import asyncio
import threading
import subprocess
import json
import logging
from datetime import datetime
from queue import Queue
from typing import AsyncGenerator
from app.models.preview import PreviewLog
from app.core.database import db

logger = logging.getLogger(__name__)

class PreviewLogStreamer:
    """
    Manages real-time log streaming from preview subprocess to frontend.
    Captures subprocess output and streams via SSE.
    """
    
    def __init__(self, preview_id: str, temp_dir: str, port: int):
        self.preview_id = preview_id
        self.temp_dir = temp_dir
        self.port = port
        self.process: subprocess.Popen = None
        self.reader_thread: threading.Thread = None
        self.running = False
        self.log_queue: Queue = Queue(maxsize=1000)
        self.log_count = 0
    
    async def start_preview_with_logging(self) -> subprocess.Popen:
        """
        Start Uvicorn subprocess and set up log streaming.
        Critical: PYTHONUNBUFFERED=1 for immediate output capture.
        """
        self.running = True
        
        # Start Uvicorn with full output capture
        self.process = subprocess.Popen(
            [
                "uvicorn",
                "app.main:app",
                f"--port={self.port}",
                "--log-level=info",
                "--access-log"  # Enable access logging
            ],
            cwd=self.temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr into stdout
            text=True,
            bufsize=1,  # Line buffered for immediate output
            env={
                "DATABASE_URL": "sqlite:///./preview.db",
                "PYTHONUNBUFFERED": "1",  # CRITICAL: No buffering
                "LOG_LEVEL": "INFO"
            }
        )
        
        # Start background thread to read subprocess output
        self.reader_thread = threading.Thread(
            target=self._read_process_output,
            name=f"LogReader-{self.preview_id}",
            daemon=True
        )
        self.reader_thread.start()
        
        logger.info(f"Preview {self.preview_id} started with PID {self.process.pid}")
        
        return self.process
    
    def _read_process_output(self):
        """
        Continuously read subprocess stdout/stderr.
        Runs in background thread to avoid blocking main event loop.
        """
        try:
            while self.running and self.process and self.process.stdout:
                # Read one line (blocks until newline)
                line = self.process.stdout.readline()
                
                if not line:
                    # EOF - process ended
                    break
                
                # Parse log level from Uvicorn output
                level = self._extract_log_level(line)
                
                # Create log entry
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": level,
                    "message": line.strip(),
                    "source": "preview"
                }
                
                # Add to queue for streaming
                try:
                    self.log_queue.put_nowait(log_entry)
                except:
                    # Queue full - drop oldest entry
                    try:
                        self.log_queue.get_nowait()
                        self.log_queue.put_nowait(log_entry)
                    except:
                        pass  # Queue still full, skip this entry
        
        except Exception as e:
            logger.error(f"Error reading process output: {e}", exc_info=True)
        
        finally:
            logger.info(f"Reader thread stopping for {self.preview_id}")
    
    def _extract_log_level(self, line: str) -> str:
        """
        Extract log level from Uvicorn log format.
        Uvicorn formats: INFO, WARNING, ERROR, CRITICAL
        """
        line_upper = line.upper()
        
        if "ERROR" in line_upper or "CRITICAL" in line_upper:
            return "ERROR"
        elif "WARNING" in line_upper or "WARN" in line_upper:
            return "WARN"
        elif "DEBUG" in line_upper:
            return "DEBUG"
        else:
            return "INFO"
    
    async def stream_logs(self) -> AsyncGenerator[str, None]:
        """
        SSE generator - yields log entries as they arrive from subprocess.
        Frontend connects via: GET /preview/logs/stream
        This is called by FastAPI StreamingResponse.
        """
        log_id = 0
        no_data_count = 0
        
        while self.running:
            try:
                # Non-blocking queue get with timeout
                log_entry = self.log_queue.get(timeout=1.0)
                no_data_count = 0  # Reset counter
                log_id += 1
                
                # Format as SSE (Server-Sent Events)
                yield f"id: {log_id}\n"
                yield f"data: {json.dumps(log_entry)}\n\n"
                
                # Save to database asynchronously (fire-and-forget)
                asyncio.create_task(self._save_log_to_db(log_entry))
                
            except:
                # Timeout - no new logs in past second
                no_data_count += 1
                
                # Send keep-alive every 15 seconds
                if no_data_count % 15 == 0:
                    yield ": keep-alive\n\n"
                
                await asyncio.sleep(0.1)
    
    async def _save_log_to_db(self, log_entry: dict):
        """
        Save log entry to database asynchronously.
        Non-blocking - doesn't affect SSE stream.
        """
        try:
            log = PreviewLog(
                preview_instance_id=self.preview_id,
                timestamp=datetime.fromisoformat(
                    log_entry["timestamp"].replace("Z", "+00:00")
                ),
                level=log_entry["level"],
                message=log_entry["message"]
            )
            db.add(log)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save log to DB: {e}")
    
    async def stop(self):
        """Stop streaming and cleanup."""
        self.running = False
        
        # Terminate subprocess gracefully
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Process {self.preview_id} didn't terminate, killing")
                self.process.kill()
        
        # Wait for reader thread
        if self.reader_thread:
            self.reader_thread.join(timeout=2)
        
        logger.info(f"Preview {self.preview_id} stopped")


# Global registry of active streamers
preview_log_streamers: dict[str, PreviewLogStreamer] = {}

def get_streamer(preview_id: str) -> PreviewLogStreamer:
    """Get the streamer for a preview instance."""
    return preview_log_streamers.get(preview_id)

def register_streamer(preview_id: str, streamer: PreviewLogStreamer):
    """Register a new streamer."""
    preview_log_streamers[preview_id] = streamer

def unregister_streamer(preview_id: str):
    """Unregister a streamer."""
    if preview_id in preview_log_streamers:
        del preview_log_streamers[preview_id]
```

### Updated PreviewService to Use SSE

```python
# filepath: app/services/preview_service.py - UPDATE launch_preview_instance

from app.services.preview_log_streamer import (
    PreviewLogStreamer,
    register_streamer,
    unregister_streamer
)

async def launch_preview_instance(preview: PreviewInstance, generation, files):
    """Launch preview with SSE log streaming."""
    
    temp_dir = None
    streamer = None
    
    try:
        # 1. Create temporary directory
        temp_dir = create_temp_project_dir()
        write_files_to_disk(files, temp_dir)
        
        # 2. Create log streamer
        streamer = PreviewLogStreamer(
            preview_id=preview.id,
            temp_dir=temp_dir,
            port=preview.port
        )
        register_streamer(preview.id, streamer)
        
        # 3. Start subprocess with log streaming
        process = await streamer.start_preview_with_logging()
        preview.process_id = process.pid
        
        # 4. Wait for startup with health checks (3 retries, 1 sec each)
        for attempt in range(3):
            await asyncio.sleep(1)
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://localhost:{preview.port}/health",
                        timeout=2
                    )
                    if response.status_code == 200:
                        break
            except:
                if attempt == 2:  # Last retry failed
                    raise HTTPException(500, "Preview failed to start")
        
        # 5. Update status
        preview.started_at = datetime.utcnow()
        preview.status = "running"
        preview.health_status = "healthy"
        preview.temp_directory = temp_dir
        await db.save(preview)
        
        logger.info(f"Preview {preview.id} launched successfully")
        
    except Exception as e:
        logger.error(f"Preview launch failed: {e}", exc_info=True)
        
        # Cleanup on failure
        if streamer:
            await streamer.stop()
            unregister_streamer(preview.id)
        
        if temp_dir:
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        # Update preview status
        preview.status = "failed"
        preview.error_message = str(e)
        preview.health_status = "unhealthy"
        await db.save(preview)
        
        raise

async def stop_preview_instance(preview: PreviewInstance):
    """Stop preview and clean up resources."""
    
    # Stop streamer
    streamer = get_streamer(preview.id)
    if streamer:
        await streamer.stop()
        unregister_streamer(preview.id)
    
    # Clean up temp directory
    if preview.temp_directory:
        import shutil
        try:
            shutil.rmtree(preview.temp_directory)
        except Exception as e:
            logger.warning(f"Failed to clean temp dir {preview.temp_directory}: {e}")
    
    # Update status
    preview.status = "stopped"
    preview.stopped_at = datetime.utcnow()
    await db.save(preview)
    
    logger.info(f"Preview {preview.id} stopped")
```

### Updated Endpoint to Serve SSE Stream

```python
# filepath: app/routers/preview.py - UPDATE logs endpoint

from fastapi.responses import StreamingResponse
from app.services.preview_log_streamer import get_streamer

@router.get("/generations/{generation_id}/preview/logs/stream")
async def stream_preview_logs(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Stream preview logs in real-time via Server-Sent Events (SSE).
    
    Frontend connects:
    ```javascript
    const eventSource = new EventSource(
        `/api/generations/${generationId}/preview/logs/stream`
    )
    
    eventSource.onmessage = (event) => {
        const log = JSON.parse(event.data)
        terminalUI.addLog(log)
    }
    
    eventSource.onerror = () => {
        console.error("Stream disconnected")
        eventSource.close()
    }
    ```
    """
    
    # Get active preview
    preview = await db.get_active_preview(generation_id)
    if not preview:
        raise HTTPException(404, "No active preview")
    
    # Verify ownership
    if preview.user_id != current_user.id:
        raise HTTPException(403, "Unauthorized")
    
    # Get streamer
    streamer = get_streamer(preview.id)
    if not streamer:
        raise HTTPException(503, "Preview logs not available")
    
    # Return SSE stream
    return StreamingResponse(
        streamer.stream_logs(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )
```

### Frontend: React Hook for SSE

```typescript
// filepath: frontend/hooks/usePreviewLogs.ts - NEW FILE

import { useEffect, useRef, useState } from 'react'

export interface PreviewLog {
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR'
  message: string
  source: string
}

export function usePreviewLogs(generationId: string) {
  const [logs, setLogs] = useState<PreviewLog[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!generationId) return

    // Create SSE connection
    const eventSource = new EventSource(
      `/api/generations/${generationId}/preview/logs/stream`
    )

    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      console.log('SSE connection established')
      setIsConnected(true)
    }

    eventSource.onmessage = (event) => {
      try {
        const log = JSON.parse(event.data) as PreviewLog
        setLogs((prev) => [...prev, log])
        
        // Auto-scroll terminal to bottom
        setTimeout(() => {
          const terminal = document.getElementById('preview-terminal')
          if (terminal) {
            terminal.scrollTop = terminal.scrollHeight
          }
        }, 0)
      } catch (error) {
        console.error('Failed to parse log:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error)
      setIsConnected(false)
      eventSource.close()
    }

    return () => {
      eventSource.close()
      setIsConnected(false)
    }
  }, [generationId])

  return { logs, isConnected }
}
```

### Frontend: Terminal UI Component

```typescript
// filepath: frontend/components/PreviewTerminal.tsx - NEW FILE

import { usePreviewLogs, PreviewLog } from '@/hooks/usePreviewLogs'
import { useEffect, useRef } from 'react'

interface PreviewTerminalProps {
  generationId: string
  className?: string
}

export function PreviewTerminal({ generationId, className = '' }: PreviewTerminalProps) {
  const { logs, isConnected } = usePreviewLogs(generationId)
  const terminalRef = useRef<HTMLDivElement>(null)

  // Auto-scroll on new logs
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [logs])

  const getLevelColor = (level: string): string => {
    switch (level) {
      case 'ERROR':
        return 'text-red-400'
      case 'WARN':
        return 'text-yellow-400'
      case 'INFO':
        return 'text-green-400'
      case 'DEBUG':
        return 'text-gray-400'
      default:
        return 'text-white'
    }
  }

  return (
    <div className={`bg-gray-900 rounded-lg font-mono text-sm ${className}`}>
      {/* Header */}
      <div className="bg-gray-800 px-4 py-2 flex justify-between items-center rounded-t-lg">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-400' : 'bg-red-400'
            }`}
          />
          <span className="text-gray-300">
            {isConnected ? 'Live' : 'Disconnected'}
          </span>
        </div>
        <span className="text-gray-500 text-xs">{logs.length} lines</span>
      </div>

      {/* Terminal */}
      <div
        ref={terminalRef}
        className="h-64 p-4 overflow-y-auto bg-gray-950 text-white rounded-b-lg space-y-0"
      >
        {logs.length === 0 && (
          <div className="text-gray-500 italic">Waiting for logs...</div>
        )}

        {logs.map((log, idx) => (
          <div
            key={idx}
            className={`font-mono text-xs leading-tight ${getLevelColor(
              log.level
            )}`}
          >
            <span className="text-gray-600">[{log.timestamp.split('T')[1]}]</span>
            <span className="ml-2">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## �📁 File Structure - MVP

```
app/
├── models/
│   ├── preview.py  # NEW: PreviewInstance & PreviewLog models
│   └── generation.py  # UPDATE: add preview_instances relationship
│
├── routers/
│   └── preview.py  # NEW: All preview endpoints (including SSE)
│
├── services/
│   ├── preview_service.py  # NEW: Preview launch/stop logic
│   ├── preview_log_streamer.py  # NEW: SSE log streaming (core MVP feature)
│   ├── preview_proxy_service.py  # NEW: HTTP proxy logic
│   └── endpoint_extractor.py  # NEW: Extract endpoints from generation
│
├── schemas/
│   └── preview.py  # NEW: Request/response schemas
│
└── utils/
    ├── port_allocator.py  # NEW: Port allocation (3001-3100)
    └── token_generator.py  # NEW: Secure token generation

frontend/
├── hooks/
│   └── usePreviewLogs.ts  # NEW: React hook for SSE streaming
│
└── components/
    └── PreviewTerminal.tsx  # NEW: Terminal UI component

alembic/
└── versions/
    └── XXXX_add_preview_tables.py  # NEW: Migration for preview tables

tests/
└── test_preview/  # NEW: Preview endpoint tests
    ├── test_launch_preview.py
    ├── test_proxy_request.py
    └── test_preview_status.py
```

---

## 🔧 Environment Variables - MVP

Add to `.env`:

```bash
# Preview Configuration
PREVIEW_PORT_MIN=3001
PREVIEW_PORT_MAX=3100
PREVIEW_SESSION_TIMEOUT=3600  # 1 hour
PREVIEW_INACTIVE_TIMEOUT=1800  # 30 minutes auto-cleanup
PREVIEW_MAX_INSTANCES_PER_USER=1  # Free tier

# Database for preview instances
PREVIEW_DB_TYPE=sqlite  # or postgresql for Phase 5
PREVIEW_DB_PATH=./storage/previews  # Local SQLite files

# Logging
PREVIEW_LOG_LEVEL=ERROR  # Only log errors in MVP
PREVIEW_MAX_LOG_LINES=1000
```

---

## 🚀 Implementation Tasks - MVP

### Week 1: Core Infrastructure

**Task 1.1**: Create database models
- [ ] Add `PreviewInstance` model
- [ ] Add `PreviewLog` model
- [ ] Create Alembic migration
- [ ] Run migration locally

**Task 1.2**: Implement port allocator utility
- [ ] Create `PortAllocator` class
- [ ] Track allocated ports in memory
- [ ] Release ports on cleanup
- [ ] Add tests

**Task 1.3**: Build SSE log streaming service (CRITICAL FOR MVP UX)
- [ ] Create `PreviewLogStreamer` class
- [ ] Implement subprocess output capture (thread-based)
- [ ] Implement async SSE generator
- [ ] Handle log queue management
- [ ] Implement database save (async, background)
- [ ] Global streamer registry
- [ ] Add comprehensive logging

**Task 1.4**: Create API endpoints (4/7)
- [ ] `POST /preview/launch` endpoint (with SSE setup)
- [ ] `GET /preview/status` endpoint
- [ ] `DELETE /preview` endpoint (with streamer cleanup)
- [ ] `GET /preview/logs/stream` endpoint (SSE streaming)

### Week 2: Testing & Polish

**Task 2.1**: Implement remaining endpoints (3/7)
- [ ] `GET /endpoints` endpoint
- [ ] `POST /preview/request` (proxy) endpoint
- [ ] `GET /preview/config` endpoint

**Task 2.2**: HTTP proxy service
- [ ] Create `PreviewProxyService`
- [ ] Forward requests to preview instance
- [ ] Handle timeout/error cases
- [ ] Validate preview token

**Task 2.3**: Endpoint extraction
- [ ] Create `EndpointExtractor`
- [ ] Parse generated code for routes
- [ ] Extract OpenAPI schema if available
- [ ] Format for UI consumption

**Task 2.4**: Background cleanup task
- [ ] Cron job every 5 minutes
- [ ] Kill expired previews
- [ ] Clean temp directories
- [ ] Stop streamers
- [ ] Log cleanup events

**Task 2.5**: Frontend SSE integration
- [ ] Create `usePreviewLogs` React hook
- [ ] Create `PreviewTerminal` component
- [ ] Test SSE connection handling
- [ ] Test auto-scroll and formatting
- [ ] Test error/reconnect scenarios

**Task 2.6**: Testing
- [ ] Unit tests for port allocator
- [ ] Unit tests for PreviewLogStreamer
- [ ] Integration tests for all 7 endpoints
- [ ] E2E tests: launch → stream logs → stop
- [ ] Error case testing (invalid generation, permissions, etc.)
- [ ] SSE connection stability tests

**Task 2.7**: Documentation
- [ ] API documentation
- [ ] SSE streaming guide
- [ ] Setup guide for developers
- [ ] Troubleshooting guide

---

## ✅ Acceptance Criteria - MVP

### Functional Requirements

- [ ] **Launch**: Preview launches in <3 seconds
- [ ] **Running**: Instance stays running until stopped or 1hr timeout
- [ ] **Status**: Can check if preview is running
- [ ] **Endpoints**: Can view all generated endpoints
- [ ] **Proxy**: Can call API endpoints through proxy
- [ ] **Stop**: Can manually stop preview instance
- [ ] **Cleanup**: Resources freed after stop/timeout
- [ ] **Token**: Preview token validated for all requests
- [ ] **Errors**: Clear error messages for invalid states
- [ ] **Logs**: Basic error logging captured

### Non-Functional Requirements

- [ ] **Performance**: Endpoint responses <200ms (excluding proxied requests)
- [ ] **Uptime**: No process leaks, ports properly released
- [ ] **Security**: Preview token validated, user permissions checked
- [ ] **Scalability**: Handles 1 preview per user without issues
- [ ] **Database**: All preview data persisted, recoverable after restart

### User Experience

- [ ] **UI Integration**: Frontend can launch/stop/test preview
- [ ] **Feedback**: Clear status messages during launch
- [ ] **Error Recovery**: User can retry after failure
- [ ] **Discovery**: User can easily find "Preview" button
- [ ] **Testing**: User can quickly test generated endpoints

---

## 🧪 Testing Strategy - MVP

### Unit Tests

```python
# tests/test_preview/test_port_allocator.py
def test_allocate_port_returns_available_port():
    allocator = PortAllocator(min_port=3001, max_port=3100)
    port = allocator.allocate()
    assert 3001 <= port <= 3100

def test_allocated_port_not_reused():
    allocator = PortAllocator()
    port1 = allocator.allocate()
    port2 = allocator.allocate()
    assert port1 != port2

def test_release_port_makes_it_available():
    allocator = PortAllocator()
    port = allocator.allocate()
    allocator.release(port)
    port_again = allocator.allocate()
    assert port == port_again
```

### Integration Tests

```python
# tests/test_preview/test_endpoints.py
@pytest.mark.asyncio
async def test_launch_preview_endpoint(client, user, generation):
    response = await client.post(
        f"/api/generations/{generation.id}/preview/launch",
        json={"generationId": generation.id, "projectId": generation.project_id},
        headers={"Authorization": f"Bearer {user.token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "launched"
    assert "previewInstanceId" in response.json()

@pytest.mark.asyncio
async def test_proxy_request_to_preview(client, user, preview):
    response = await client.post(
        f"/api/generations/{preview.generation_id}/preview/request",
        json={
            "method": "GET",
            "path": "/api/users",
            "query": {},
            "body": None,
            "headers": {"X-Preview-Token": preview.preview_token}
        },
        headers={"Authorization": f"Bearer {user.token}"}
    )
    assert response.status_code == 200
```

---

## 🐛 Error Handling - MVP

### Common Error Scenarios

| Error | Status | Message | Solution |
|-------|--------|---------|----------|
| Generation not found | 404 | "Generation not found" | Check generation ID |
| User not authorized | 403 | "Unauthorized access" | Verify permissions |
| Already running | 409 | "Preview already running" | Stop existing or wait |
| Files missing | 400 | "Missing required files: {list}" | Re-generate |
| Port allocation failed | 500 | "Unable to allocate port" | Retry or wait |
| Launch timeout | 504 | "Preview failed to start" | Check logs, retry |
| Request timeout | 504 | "Preview request timed out" | Reduce timeout, check network |
| Proxy error | 503 | "Preview unavailable" | Preview may have crashed |

---

## 📊 Monitoring & Observability - MVP

### Key Metrics to Track

```python
# Simple metrics to log
- Preview launches per day
- Average launch time (seconds)
- Success rate (launched / total attempts)
- Average session duration (minutes)
- Error rate by error type
- Concurrent preview instances (current)
```

### Logging Points

```python
# Key events to log
logging.info(f"Preview launched: {preview_id} (port {port})")
logging.info(f"Preview stopped: {preview_id} (uptime: {uptime}s)")
logging.error(f"Launch failed: {preview_id} - {error}")
logging.warning(f"Preview expired: {preview_id}")
logging.debug(f"Proxy request: {method} {path} -> {status}")
```

---

## 🔐 Security - MVP

### Authentication & Authorization

- ✅ All endpoints require JWT auth
- ✅ Users can only access their own previews
- ✅ Preview token validated for proxy requests
- ✅ Tokens expire when preview stops

### Isolation

- ✅ Each preview runs in separate process
- ✅ SQLite database per preview (isolated)
- ✅ Temp files in separate directory per preview
- ✅ No access to backend code or database

### Input Validation

- ✅ Validate generation exists
- ✅ Validate generation files exist
- ✅ Sanitize proxy request paths (no path traversal)
- ✅ Limit request body size

---

## 🎯 Success Metrics - MVP

### Shipping Success
- [ ] All 5 core endpoints working (launch, status, stop, endpoints, proxy)
- [ ] Zero critical bugs on main branch
- [ ] >90% test coverage for preview code
- [ ] Documentation complete and reviewed

### User Success
- [ ] Users can launch preview in <3 seconds
- [ ] Users can test endpoints without confusion
- [ ] Error messages are clear and actionable
- [ ] First-time user can complete flow without help

### Technical Success
- [ ] No memory leaks (processes properly cleaned up)
- [ ] No port conflicts (allocator working correctly)
- [ ] Database migrations working
- [ ] Works with both generated Python 3.11+ backends

---

## 📝 Notes & Known Limitations - MVP

### Known Limitations
1. **One preview per user** - scaling handled in Phase 5
2. **1 hour timeout** - no manual extension in MVP
3. **SQLite only** - no PostgreSQL in preview yet
4. **SSE for logging** - upgrade to WebSocket in Phase 5 for bidirectional
5. **Error logs prominently shown** - INFO/DEBUG available but less emphasized
6. **In-process execution** - no real resource limits, but fine for MVP

### What MVP Gets Right ✅
1. **Real-time terminal-style UX** - users see startup/errors instantly
2. **Simple implementation** - SSE is HTTP-based, no WebSocket complexity
3. **Frontend-friendly** - EventSource API is built into browsers
4. **Easy to upgrade** - SSE → WebSocket migration straightforward

### Future Improvements (Phase 5)
- Upgrade to WebSocket for bidirectional communication
- Add production resource limits (Docker)
- Support PostgreSQL/MongoDB in preview
- Advanced metrics and performance monitoring
- Archive logs for audit trail

---

## 📚 References

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Uvicorn Server](https://www.uvicorn.org)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Testing FastAPI Apps](https://fastapi.tiangolo.com/advanced/testing-websockets/)

---

**Ready to proceed with Week 1 implementation? Review the tasks and confirm scope with the team!**
