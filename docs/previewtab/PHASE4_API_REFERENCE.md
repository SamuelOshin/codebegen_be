# Phase 4: Preview Tab MVP - API Reference

**Version**: 1.0.0  
**Last Updated**: October 16, 2025  
**Base URL**: `http://localhost:8000/api/v1`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Request/Response Examples](#request-response-examples)
5. [Error Codes](#error-codes)
6. [Rate Limiting](#rate-limiting)
7. [Webhooks](#webhooks)

---

## Overview

The Preview Tab API enables real-time execution and testing of generated code. Key capabilities:

- **Launch Preview Instances**: Start generated applications in isolated containers
- **Monitor Status**: Track instance health and lifecycle
- **Stream Logs**: Real-time subprocess output via SSE
- **Proxy Requests**: Forward HTTP requests to running instances
- **Discover Endpoints**: Auto-detect API routes
- **Manage Sessions**: Secure token-based access

### Request/Response Format

All requests should include:
- `Content-Type: application/json` header
- Authorization token in `Authorization: Bearer {token}` header
- Valid JSON in request body (where applicable)

All responses use:
- JSON format (unless streaming)
- Consistent HTTP status codes
- Descriptive error messages

---

## Authentication

### Token Requirements

All endpoints (except public docs) require authentication:

```http
Authorization: Bearer {access_token}
```

**Token Format**: JWT tokens issued by auth service

**Obtaining Token**:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com", "password":"***"}'

# Response
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Session Token (Preview-Specific)

In addition to auth token, preview endpoints use `X-Preview-Token`:

```http
X-Preview-Token: {session_token}
```

**When Required**: Proxy request endpoint only  
**Format**: UUID v4 generated on preview launch  
**Lifetime**: Follows `PREVIEW_SESSION_TIMEOUT` setting (default: 30 minutes)

---

## Endpoints

### 1. Launch Preview

**Endpoint**: `POST /generations/{generation_id}/preview/launch`

**Description**: Create and launch a new preview instance

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `generation_id` | UUID | Yes | ID of generation to preview |

**Request Body**:
```json
{
  "project_id": "string",
  "timeout": 30
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `project_id` | string | Yes | - | Project ID for context |
| `timeout` | integer | No | 30 | Startup timeout in seconds |

**Request Example**:
```bash
curl -X POST http://localhost:8000/api/v1/generations/gen_abc123/preview/launch \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_xyz789",
    "timeout": 30
  }'
```

**Response (201 Created)**:
```json
{
  "id": "preview_550e8400-e29b-41d4-a716-446655440000",
  "generation_id": "gen_abc123",
  "user_id": "user_def456",
  "project_id": "proj_xyz789",
  "status": "starting",
  "port": 3001,
  "base_url": "http://localhost:3001",
  "session_token": "sess_550e8400-e29b-41d4-a716-446655440001",
  "created_at": "2025-10-16T14:30:00Z",
  "token_expiry": "2025-10-16T15:00:00Z"
}
```

**Error Responses**:

`400 Bad Request` - Invalid request:
```json
{
  "detail": "project_id is required"
}
```

`401 Unauthorized` - Missing/invalid token:
```json
{
  "detail": "Not authenticated"
}
```

`403 Forbidden` - Not owner:
```json
{
  "detail": "User does not own this generation"
}
```

`404 Not Found` - Generation doesn't exist:
```json
{
  "detail": "Generation not found"
}
```

`503 Service Unavailable` - No ports available:
```json
{
  "detail": "No ports available for preview (max 100 concurrent)"
}
```

---

### 2. Get Preview Status

**Endpoint**: `GET /generations/{generation_id}/preview/status`

**Description**: Get current status of preview instance

**Path Parameters**:
| Name | Type | Required |
|------|------|----------|
| `generation_id` | UUID | Yes |

**Request Example**:
```bash
curl -X GET http://localhost:8000/api/v1/generations/gen_abc123/preview/status \
  -H "Authorization: Bearer {token}"
```

**Response (200 OK)**:
```json
{
  "id": "preview_550e8400-e29b-41d4-a716-446655440000",
  "generation_id": "gen_abc123",
  "user_id": "user_def456",
  "status": "running",
  "port": 3001,
  "base_url": "http://localhost:3001",
  "uptime_seconds": 125,
  "memory_usage_mb": 256,
  "cpu_usage_percent": 2.5,
  "health": "healthy",
  "started_at": "2025-10-16T14:30:00Z",
  "endpoints_count": 5
}
```

**Status Field Values**:
- `starting` - Initializing, not yet healthy
- `running` - Healthy and accepting requests
- `stopping` - Shutting down
- `stopped` - Successfully terminated
- `failed` - Failed to start or crashed

**Error Responses**:

`404 Not Found` - No preview running:
```json
{
  "detail": "No preview found for this generation"
}
```

---

### 3. Stop Preview

**Endpoint**: `DELETE /generations/{generation_id}/preview`

**Description**: Stop running preview instance and cleanup

**Path Parameters**:
| Name | Type | Required |
|------|------|----------|
| `generation_id` | UUID | Yes |

**Request Example**:
```bash
curl -X DELETE http://localhost:8000/api/v1/generations/gen_abc123/preview \
  -H "Authorization: Bearer {token}"
```

**Response (204 No Content)**:
(No response body)

**Error Responses**:

`404 Not Found` - No preview running:
```json
{
  "detail": "No preview found for this generation"
}
```

`500 Internal Server Error` - Cleanup failed:
```json
{
  "detail": "Failed to stop preview: {error}"
}
```

---

### 4. List Discovered Endpoints

**Endpoint**: `GET /generations/{generation_id}/preview/endpoints`

**Description**: Get list of discovered API endpoints

**Path Parameters**:
| Name | Type | Required |
|------|------|----------|
| `generation_id` | UUID | Yes |

**Query Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `tag` | string | - | Filter by tag |
| `method` | string | - | Filter by HTTP method (GET, POST, etc) |

**Request Example**:
```bash
curl "http://localhost:8000/api/v1/generations/gen_abc123/preview/endpoints?tag=users" \
  -H "Authorization: Bearer {token}"
```

**Response (200 OK)**:
```json
{
  "endpoints": [
    {
      "path": "/api/users",
      "method": "GET",
      "summary": "List all users",
      "description": "Retrieve paginated list of users with filtering options",
      "tags": ["users"]
    },
    {
      "path": "/api/users",
      "method": "POST",
      "summary": "Create user",
      "description": "Create a new user account",
      "tags": ["users"]
    },
    {
      "path": "/api/users/{id}",
      "method": "GET",
      "summary": "Get user by ID",
      "description": "Retrieve specific user details",
      "tags": ["users"]
    },
    {
      "path": "/api/users/{id}",
      "method": "PUT",
      "summary": "Update user",
      "description": "Update user information",
      "tags": ["users"]
    },
    {
      "path": "/api/users/{id}",
      "method": "DELETE",
      "summary": "Delete user",
      "description": "Remove user permanently",
      "tags": ["users"]
    }
  ],
  "count": 5
}
```

**Endpoint Object Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | URL path (may include `{param}` placeholders) |
| `method` | string | HTTP method (GET, POST, PUT, DELETE, PATCH) |
| `summary` | string | Short description from docstring |
| `description` | string | Detailed description |
| `tags` | array | Categorization tags |

**Error Responses**:

`404 Not Found` - Preview not running:
```json
{
  "detail": "No preview found for this generation"
}
```

---

### 5. Proxy HTTP Request

**Endpoint**: `POST /generations/{generation_id}/preview/request`

**Description**: Forward HTTP request to running preview instance

**Path Parameters**:
| Name | Type | Required |
|------|------|----------|
| `generation_id` | UUID | Yes |

**Headers**:
| Name | Required | Description |
|------|----------|-------------|
| `X-Preview-Token` | Yes | Session token from launch |
| `Content-Type` | No | Request content type |

**Request Body**:
```json
{
  "method": "GET",
  "path": "/api/users",
  "query": {
    "limit": "10",
    "offset": "0"
  },
  "body": null,
  "headers": {
    "Content-Type": "application/json"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `method` | string | Yes | HTTP method (GET, POST, etc) |
| `path` | string | Yes | Request path |
| `query` | object | No | Query parameters |
| `body` | any | No | Request body (JSON or string) |
| `headers` | object | No | Custom headers to include |

**Request Example**:
```bash
curl -X POST http://localhost:8000/api/v1/generations/gen_abc123/preview/request \
  -H "Authorization: Bearer {token}" \
  -H "X-Preview-Token: sess_550e8400-e29b-41d4-a716-446655440001" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "path": "/api/users",
    "query": {
      "limit": "10",
      "offset": "0"
    },
    "body": null,
    "headers": {}
  }'
```

**Response (200 OK)**:
```json
{
  "status_code": 200,
  "headers": {
    "content-type": "application/json",
    "server": "uvicorn"
  },
  "body": "{\"users\":[{\"id\":1,\"name\":\"Alice\",\"email\":\"alice@example.com\"},{\"id\":2,\"name\":\"Bob\",\"email\":\"bob@example.com\"}],\"total\":2}",
  "elapsed_ms": 45
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `status_code` | integer | HTTP status code from preview |
| `headers` | object | Response headers |
| `body` | string | Response body (raw string) |
| `elapsed_ms` | integer | Request duration in milliseconds |

**Error Responses**:

`400 Bad Request` - Invalid request:
```json
{
  "detail": "method is required"
}
```

`401 Unauthorized` - Invalid token:
```json
{
  "detail": "Invalid preview token"
}
```

`404 Not Found` - Preview not running:
```json
{
  "detail": "No preview found for this generation"
}
```

`504 Gateway Timeout` - Preview took too long:
```json
{
  "detail": "Request timeout after 10 seconds"
}
```

---

### 6. Get Preview Config

**Endpoint**: `GET /generations/{generation_id}/preview/config`

**Description**: Get configuration for preview instance

**Path Parameters**:
| Name | Type | Required |
|------|------|----------|
| `generation_id` | UUID | Yes |

**Request Example**:
```bash
curl http://localhost:8000/api/v1/generations/gen_abc123/preview/config \
  -H "Authorization: Bearer {token}"
```

**Response (200 OK)**:
```json
{
  "port": 3001,
  "base_url": "http://localhost:3001",
  "session_timeout_seconds": 1800,
  "max_uptime_seconds": 3600,
  "memory_limit_mb": 512,
  "startup_timeout_seconds": 30,
  "health_check_retries": 3,
  "health_check_interval_seconds": 1
}
```

**Configuration Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `port` | integer | Allocated port for preview |
| `base_url` | string | Full URL for accessing preview |
| `session_timeout_seconds` | integer | How long session token is valid |
| `max_uptime_seconds` | integer | Maximum time preview can run |
| `memory_limit_mb` | integer | Memory limit per preview |
| `startup_timeout_seconds` | integer | Max time to wait for startup |
| `health_check_retries` | integer | Number of health check attempts |
| `health_check_interval_seconds` | integer | Delay between health checks |

---

### 7. Stream Logs (SSE)

**Endpoint**: `GET /generations/{generation_id}/preview/logs/stream`

**Description**: Stream real-time subprocess output via Server-Sent Events

**Path Parameters**:
| Name | Type | Required |
|------|------|----------|
| `generation_id` | UUID | Yes |

**Headers**:
```
Accept: text/event-stream
Authorization: Bearer {token}
```

**Request Example**:
```bash
curl -N http://localhost:8000/api/v1/generations/gen_abc123/preview/logs/stream \
  -H "Authorization: Bearer {token}"
```

**Response Headers**:
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
Transfer-Encoding: chunked
```

**Response Stream**:
```
data: {"timestamp":"2025-10-16T14:30:00Z","level":"INFO","message":"Starting uvicorn server","source":"subprocess"}

data: {"timestamp":"2025-10-16T14:30:01Z","level":"INFO","message":"Uvicorn running on http://0.0.0.0:3001","source":"subprocess"}

data: {"timestamp":"2025-10-16T14:30:02Z","level":"INFO","message":"Application startup complete","source":"subprocess"}

data: {"timestamp":"2025-10-16T14:30:05Z","level":"INFO","message":"GET /api/users - 200","source":"subprocess"}

data: {"timestamp":"2025-10-16T14:30:10Z","level":"ERROR","message":"ValueError: Invalid input","source":"subprocess"}

: heartbeat
```

**Event Format**:
```json
{
  "timestamp": "2025-10-16T14:30:00Z",
  "level": "INFO|WARNING|ERROR|DEBUG",
  "message": "Log message text",
  "source": "subprocess|system"
}
```

**Log Levels**:
- `DEBUG` - Detailed diagnostic information
- `INFO` - General informational messages
- `WARNING` - Warning conditions
- `ERROR` - Error conditions

**Special Events**:
- Empty line (heartbeat) - Connection alive check
- `:` prefix - Comment (server ping)

**Client Implementation (JavaScript)**:
```javascript
const eventSource = new EventSource(
  '/api/v1/generations/gen_abc123/preview/logs/stream',
  { headers: { 'Authorization': `Bearer ${token}` } }
);

eventSource.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(`[${log.level}] ${log.message}`);
};

eventSource.onerror = () => {
  console.error('Stream connection lost');
  eventSource.close();
};
```

**Error Response (Outside Stream)**:

`404 Not Found`:
```json
{
  "detail": "No preview found for this generation"
}
```

---

## Request/Response Examples

### Example 1: Full Preview Lifecycle

**Step 1: Launch**
```bash
curl -X POST http://localhost:8000/api/v1/generations/gen_abc123/preview/launch \
  -H "Authorization: Bearer eyJ0eXAi..." \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj_xyz789", "timeout": 30}'

# Response:
# {
#   "id": "preview_550e8400...",
#   "status": "starting",
#   "port": 3001,
#   "session_token": "sess_550e8400...",
#   ...
# }
```

**Step 2: Monitor Status**
```bash
curl http://localhost:8000/api/v1/generations/gen_abc123/preview/status \
  -H "Authorization: Bearer eyJ0eXAi..."

# Poll until status = "running" (typically 2-3 seconds)
```

**Step 3: Get Endpoints**
```bash
curl http://localhost:8000/api/v1/generations/gen_abc123/preview/endpoints \
  -H "Authorization: Bearer eyJ0eXAi..."

# Returns list of discovered endpoints
```

**Step 4: Make Requests**
```bash
curl -X POST http://localhost:8000/api/v1/generations/gen_abc123/preview/request \
  -H "Authorization: Bearer eyJ0eXAi..." \
  -H "X-Preview-Token: sess_550e8400..." \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "path": "/api/users",
    "query": {"limit": "10"}
  }'

# Test multiple endpoints
```

**Step 5: Stream Logs**
```bash
curl -N http://localhost:8000/api/v1/generations/gen_abc123/preview/logs/stream \
  -H "Authorization: Bearer eyJ0eXAi..."

# Observe real-time output
```

**Step 6: Cleanup**
```bash
curl -X DELETE http://localhost:8000/api/v1/generations/gen_abc123/preview \
  -H "Authorization: Bearer eyJ0eXAi..."

# Response: 204 No Content
```

### Example 2: Error Handling

```bash
# Missing token
curl http://localhost:8000/api/v1/generations/gen_abc123/preview/status
# Response: 401 Not authenticated

# Invalid generation
curl http://localhost:8000/api/v1/generations/invalid_id/preview/status \
  -H "Authorization: Bearer eyJ0eXAi..."
# Response: 404 Not found

# No ports available
curl -X POST http://localhost:8000/api/v1/generations/gen_abc123/preview/launch \
  -H "Authorization: Bearer eyJ0eXAi..." \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj_xyz789"}'
# Response: 503 Service unavailable (when 100 previews active)

# Wrong session token
curl -X POST http://localhost:8000/api/v1/generations/gen_abc123/preview/request \
  -H "Authorization: Bearer eyJ0eXAi..." \
  -H "X-Preview-Token: wrong_token" \
  -d '{"method": "GET", "path": "/"}'
# Response: 401 Invalid preview token
```

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | When | Action |
|------|---------|------|--------|
| 200 | OK | Request succeeded | Use response |
| 201 | Created | Resource created | Use response |
| 204 | No Content | Success, no body | Done |
| 400 | Bad Request | Invalid input | Fix request |
| 401 | Unauthorized | Auth failed | Provide token |
| 403 | Forbidden | Not permitted | Check permissions |
| 404 | Not Found | Resource missing | Check ID |
| 408 | Request Timeout | Too slow | Retry |
| 409 | Conflict | Resource exists | Use existing |
| 429 | Too Many Requests | Rate limit | Wait & retry |
| 500 | Server Error | Server issue | Retry later |
| 503 | Unavailable | Service down | Retry later |
| 504 | Gateway Timeout | Too slow | Retry |

### Error Response Format

```json
{
  "detail": "Descriptive error message",
  "error_code": "SPECIFIC_ERROR",
  "timestamp": "2025-10-16T14:30:00Z",
  "request_id": "req_550e8400..."
}
```

### Common Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `PREVIEW_NOT_FOUND` | 404 | No preview for generation |
| `GENERATION_NOT_FOUND` | 404 | Generation doesn't exist |
| `INVALID_TOKEN` | 401 | Auth token invalid/expired |
| `INVALID_SESSION_TOKEN` | 401 | Preview session token invalid |
| `PERMISSION_DENIED` | 403 | User doesn't own generation |
| `NO_PORTS_AVAILABLE` | 503 | All ports allocated |
| `STARTUP_TIMEOUT` | 504 | Preview didn't start in time |
| `HEALTH_CHECK_FAILED` | 500 | Preview health check failed |
| `REQUEST_TIMEOUT` | 504 | Proxied request timed out |
| `INVALID_REQUEST` | 400 | Malformed request |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

---

## Rate Limiting

### Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Launch Preview | 10/hour | Per user |
| Status Check | 100/minute | Per user |
| Proxy Request | 1000/hour | Per preview |
| Stream Logs | 1/preview | Active connection |
| List Endpoints | 100/minute | Per user |

### Headers

Responses include rate limit info:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1634125200
```

### Rate Limit Response (429)

```json
{
  "detail": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 300,
  "reset_time": "2025-10-16T15:30:00Z"
}
```

---

## Webhooks

### Preview Lifecycle Events

The system can send webhooks for important events:

**Webhook Payload**:
```json
{
  "event": "preview.launched|preview.started|preview.stopped|preview.failed",
  "timestamp": "2025-10-16T14:30:00Z",
  "preview_id": "preview_550e8400...",
  "generation_id": "gen_abc123",
  "user_id": "user_def456",
  "data": {
    "status": "running",
    "port": 3001,
    "error": null
  }
}
```

**Events**:
- `preview.launched` - Instance created, starting
- `preview.started` - Health check passed
- `preview.stopped` - Stopped successfully
- `preview.failed` - Failed to start/crashed

---

## Best Practices

### Polling vs Streaming

**Use Polling For**:
- Occasional status checks
- Infrequent updates
- Simple implementations

```javascript
async function waitForPreview(generationId, maxAttempts = 30) {
  for (let i = 0; i < maxAttempts; i++) {
    const response = await fetch(`/api/v1/generations/${generationId}/preview/status`);
    const data = await response.json();
    if (data.status === 'running') return data;
    await new Promise(r => setTimeout(r, 1000));
  }
  throw new Error('Preview startup timeout');
}
```

**Use Streaming For**:
- Real-time monitoring
- Complete log capture
- Better UX

```javascript
function streamLogs(generationId) {
  const eventSource = new EventSource(`/api/v1/generations/${generationId}/preview/logs/stream`);
  
  eventSource.onmessage = (event) => {
    const log = JSON.parse(event.data);
    displayLog(log);
  };
}
```

### Error Handling

Always implement retry logic:

```javascript
async function launchWithRetry(generationId, maxRetries = 3) {
  let lastError;
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fetch(`/api/v1/generations/${generationId}/preview/launch`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      }).then(r => r.json());
    } catch (error) {
      lastError = error;
      await new Promise(r => setTimeout(r, 1000 * (i + 1))); // Exponential backoff
    }
  }
  
  throw lastError;
}
```

### Resource Cleanup

Always stop previews when done:

```javascript
try {
  await launchPreview(generationId);
  // ... do work ...
} finally {
  await stopPreview(generationId); // Always cleanup
}
```

---

## Changelog

### v1.0.0 (2025-10-16)

- Initial release
- 7 API endpoints
- Real-time SSE streaming
- Endpoint auto-discovery
- Full 45-unit test coverage

---

**API Version**: 1.0.0  
**Last Updated**: 2025-10-16  
**Status**: Stable ✅
