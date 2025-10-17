# Error Analysis - Generation Failure (2025-10-16)

**Generation ID**: `0c9055c8-b6fa-4b5e-bf5e-ed96a7391ccc`  
**User ID**: `47533dd7-4ebc-4f3e-8aa3-a46094a7174f`  
**Status**: ❌ FAILED

---

## Executive Summary

**Critical Error**: Generation failed due to SQLAlchemy inspection error  
**Root Cause**: Passing class instead of instance to inspection system  
**Impact**: 100% generation failure rate  
**Severity**: 🔴 **CRITICAL** - Blocks all code generation

---

## Error Breakdown

### 1. 🔴 CRITICAL: SQLAlchemy Inspection Error

**Log Entry**:
```
ERROR - ❌ Error processing generation 0c9055c8-b6fa-4b5e-bf5e-ed96a7391ccc: 
No inspection system is available for object of type <class 'type'>
```

**Location**: `app.services.ai_orchestrator`  
**Severity**: 🔴 **CRITICAL**  
**Status**: Backend bug

#### Analysis

This error occurs when SQLAlchemy's `inspect()` function receives a **class** instead of an **instance**:

```python
# ❌ WRONG - Passing class
from sqlalchemy import inspect
inspect(Generation)  # <class 'type'> - FAILS

# ✅ CORRECT - Passing instance
generation = await generation_repo.get_by_id(id)
inspect(generation)  # Works!
```

#### Impact
- Generation processing fails immediately
- Status updated to `"failed"`
- No code generated
- Frontend receives error
- User sees failure message

#### Root Cause

Likely in `ai_orchestrator.py` when trying to inspect generation object:

**Possible code locations**:
```python
# Bad pattern - somewhere in ai_orchestrator
def process_generation(generation_class):  # ← Receiving class, not instance
    # ...
    inspection = inspect(generation_class)  # ← FAILS HERE
```

**Where to look**:
1. `app/services/ai_orchestrator.py` - Check all `inspect()` calls
2. Generation object passing between services
3. Background task that processes generation

#### Solution

**Need to investigate**: Read `ai_orchestrator.py` to find the exact line

**Fix will be**:
```python
# Ensure we're passing instance, not class
async def process_generation(generation_id: str):
    generation = await generation_repo.get_by_id(generation_id)  # Get instance
    # Use generation instance, not Generation class
```

---

### 2. ⚠️ MEDIUM: DateTime Timezone Mismatch

**Log Entry**:
```
WARNING - Error finding similar project: 
can't subtract offset-naive and offset-aware datetimes
```

**Location**: `app.services.auto_project_service`  
**Severity**: ⚠️ **MEDIUM**  
**Status**: Backend bug

#### Analysis

Comparing two datetime objects with different timezone awareness:

```python
# Example of the problem
from datetime import datetime

dt_naive = datetime.utcnow()  # No timezone info
dt_aware = datetime.now(timezone.utc)  # Has timezone info

time_diff = dt_aware - dt_naive  # ❌ FAILS!
```

#### Impact
- Similar project detection fails
- Falls back to creating new project (works fine)
- Minor: Creates duplicate projects unnecessarily

#### Location

In `auto_project_service._find_similar_project()`:

```python
# Likely comparing project.created_at with current time
one_hour_ago = datetime.utcnow() - timedelta(hours=1)  # Naive
if project.created_at > one_hour_ago:  # If created_at is aware, FAILS
    ...
```

#### Solution

**Fix**: Make all datetime comparisons use timezone-aware datetimes

```python
from datetime import datetime, timezone, timedelta

# ✅ CORRECT - Both timezone-aware
def _find_similar_project(self, ...):
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    
    # Compare with database timestamps
    if project.created_at > one_hour_ago:  # Works if created_at is aware
        ...
```

**Also check**: Database column definition
```python
# In models/project.py
created_at = Column(DateTime(timezone=True), ...)  # Should have timezone=True
```

---

### 3. 🔵 INFO: 422 Unprocessable Entity (Frontend Issue)

**Log Entry**:
```
"GET /generations/generate/{id}/stream HTTP/1.1" 422 Unprocessable Entity
```

**Severity**: 🔵 **INFO**  
**Status**: ✅ Expected behavior (frontend not updated yet)

#### Analysis

Frontend is calling the **OLD stream endpoint** without SSE token:

**What frontend is doing** (WRONG):
```typescript
// ❌ OLD WAY (no longer supported)
const eventSource = new EventSource(
  `/api/generations/generate/${id}/stream`
  // Missing: ?token=sse-token-here
);
```

**What frontend SHOULD do** (CORRECT):
```typescript
// ✅ NEW WAY (secure)
// Step 1: Get SSE token
const response = await fetch(
  `/api/generations/generate/${id}/stream-token`,
  { headers: { Authorization: `Bearer ${jwt}` } }
);
const { sse_token } = await response.json();

// Step 2: Connect with SSE token
const eventSource = new EventSource(
  `/api/generations/generate/${id}/stream?token=${sse_token}`
);
```

#### Impact
- Frontend cannot connect to stream
- User doesn't see real-time progress
- Frontend falls back to polling (if implemented)

#### Solution

**Frontend Team Action Required**: Update SSE connection code

**Expected Query Parameter**:
```
GET /generations/generate/{id}/stream?token={sse_token}
```

**Parameter Details**:
- **Name**: `token` (required)
- **Type**: String
- **Source**: From POST `/generate/{id}/stream-token` endpoint
- **Lifetime**: 60 seconds, single-use
- **Format**: URL-safe base64 string (e.g., `"7Lia1fam8VNuvPDYK2RKg0e9m3iJrkf4Dr5vEsY7uVM"`)

**Reference Documentation**: `SSE_RETRY_HANDLING_GUIDE.md` and `FRONTEND_SECURE_SSE_MIGRATION.md`

---

### 4. 🟡 LOW: Frontend Retry Loop (Frontend Issue)

**Log Entries**:
```
WARNING - Attempted to stream failed generation (×10)
INFO - "POST /stream-token HTTP/1.1" 400 Bad Request (×10)
WARNING - Rate limit exceeded
INFO - "POST /stream-token HTTP/1.1" 429 Too Many Requests
```

**Severity**: 🟡 **LOW**  
**Status**: ✅ Rate limiting working as designed

#### Analysis

Frontend is retrying despite receiving `400 Bad Request`:

**Timeline**:
1. Generation fails at 16:44:10
2. Frontend tries to get SSE token at 16:44:13 → `400 Bad Request`
3. Frontend retries every 1-2 seconds (×10 times)
4. Rate limiting triggers at 16:44:30 → `429 Too Many Requests`

**Why 400 is returned**:
```http
POST /generate/{id}/stream-token
Response: 400 Bad Request
{
  "detail": "Generation has failed. Error: No inspection system is available for object of type <class 'type'>. Cannot stream."
}
```

This is **correct backend behavior** - the generation failed, so streaming is not available.

#### Impact
- Wastes server resources (but rate limiting protects)
- User sees multiple failed connection attempts
- Eventually triggers rate limit (429)

#### Solution

**Frontend Team Action Required**: Implement proper error handling

**Required Logic**:
```typescript
const response = await fetch('/stream-token', ...);

if (response.status === 400) {
  // Generation in terminal state - DO NOT RETRY
  const error = await response.json();
  
  if (error.detail.includes('failed')) {
    showError('Generation failed', error.detail);
    stopRetrying();  // ← CRITICAL: Stop retry loop
  }
  
  return; // Don't retry
}

if (response.status === 429) {
  // Rate limited - wait 60 seconds
  showError('Too many requests. Please wait a minute.');
  stopRetrying();  // ← CRITICAL: Stop retry loop
  return;
}
```

**Reference**: `SSE_RETRY_HANDLING_GUIDE.md` section "Stop Retry on Terminal States"

---

## Error Priority Matrix

| # | Error | Severity | Impact | Owner | Fix ETA |
|---|-------|----------|--------|-------|---------|
| 1 | SQLAlchemy inspection error | 🔴 CRITICAL | 100% failure | Backend | Immediate |
| 2 | DateTime timezone mismatch | ⚠️ MEDIUM | Duplicate projects | Backend | 1-2 hours |
| 3 | 422 missing token | 🔵 INFO | No streaming | Frontend | Pending |
| 4 | Retry loop | 🟡 LOW | Resource waste | Frontend | Pending |

---

## Immediate Actions Required

### Backend Team (You) 🔴 URGENT

#### 1. Fix SQLAlchemy Inspection Error (TOP PRIORITY)

**Action**: Investigate `app/services/ai_orchestrator.py`

**Look for**:
- Any `inspect()` calls
- Any place passing `Generation` class instead of instance
- Background task that processes generation

**Steps**:
1. Read `ai_orchestrator.py` 
2. Find the `inspect()` call that's failing
3. Ensure it receives an **instance** not a **class**
4. Test with a generation

**Test command**:
```bash
# After fixing, test generation
curl -X POST http://localhost:8000/api/generations/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a FastAPI REST API", "project_id": null}'
```

#### 2. Fix DateTime Timezone Issue

**Action**: Update `app/services/auto_project_service.py`

**Changes needed**:
```python
from datetime import datetime, timezone, timedelta

# In _find_similar_project method
one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)  # Make timezone-aware
```

### Frontend Team 🟡 MODERATE

#### 1. Update SSE Connection Code

**Required changes**:
- Use two-step token flow (documented in `SSE_RETRY_HANDLING_GUIDE.md`)
- Add query parameter `?token={sse_token}` to stream endpoint
- Stop retrying on 400 and 429 responses

**Files to update**:
- SSE connection logic
- Generation streaming component
- Error handling

#### 2. Implement Retry Stopping Logic

**Required changes**:
- Detect 400 Bad Request → stop retrying
- Detect 429 Rate Limit → stop retrying
- Maximum 5 retry attempts
- Exponential backoff

---

## Expected Request/Response Structures

### Frontend → Backend: Generate Code

**Endpoint**: `POST /generations/generate`

**Request Headers**:
```http
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request Body** (Expected Structure):
```json
{
  "prompt": "Create a REST API with authentication",
  "project_id": "uuid-or-null",
  "context": {
    "additional_requirements": ["Optional", "array", "of", "strings"]
  },
  "generation_mode": "phased",
  "is_iteration": false,
  "parent_generation_id": null
}
```

**Field Requirements**:
- `prompt` (required): string, min 10 characters
- `project_id` (optional): UUID string or null (will auto-create project)
- `context` (optional): object with additional info
- `generation_mode` (optional): "phased" | "unified" (default: "phased")
- `is_iteration` (optional): boolean (default: false)
- `parent_generation_id` (optional): UUID string or null

**Response** (Success - 201 Created):
```json
{
  "id": "0c9055c8-b6fa-4b5e-bf5e-ed96a7391ccc",
  "status": "pending",
  "user_id": "47533dd7-4ebc-4f3e-8aa3-a46094a7174f",
  "project_id": "3b3537f2-2364-4a6a-9e56-19524751430d",
  "project_name": "Rest Api",
  "project_domain": "general",
  "auto_created_project": true,
  "prompt": "Create a REST API...",
  "created_at": "2025-10-16T16:44:09.123456Z"
}
```

### Frontend → Backend: Get SSE Token

**Endpoint**: `POST /generations/generate/{generation_id}/stream-token`

**Request Headers**:
```http
Authorization: Bearer {jwt_token}
```

**Request Body**: None

**Response** (Success - 200 OK):
```json
{
  "sse_token": "7Lia1fam8VNuvPDYK2RKg0e9m3iJrkf4Dr5vEsY7uVM",
  "expires_in": 60,
  "stream_url": "/generations/generate/{id}/stream",
  "generation_id": "0c9055c8-b6fa-4b5e-bf5e-ed96a7391ccc"
}
```

**Response** (Failed Generation - 400 Bad Request):
```json
{
  "detail": "Generation has failed. Error: No inspection system is available for object of type <class 'type'>. Cannot stream."
}
```

**Response** (Rate Limited - 429 Too Many Requests):
```json
{
  "detail": "Too many token requests. Maximum 10 requests per minute. Please wait before retrying."
}
```

### Frontend → Backend: Stream Progress

**Endpoint**: `GET /generations/generate/{generation_id}/stream?token={sse_token}`

**Query Parameters** (REQUIRED):
- `token`: SSE token from stream-token endpoint

**Request Headers**:
```http
Accept: text/event-stream
```

**Response** (Success - 200 OK):
```http
Content-Type: text/event-stream

data: {"generation_id":"...","status":"processing","stage":"connected","progress":0.0,"message":"Stream connected","timestamp":1234567890.123}

data: {"generation_id":"...","status":"processing","stage":"planning","progress":0.2,"message":"Planning architecture...","timestamp":1234567890.456}

data: {"generation_id":"...","status":"completed","stage":"complete","progress":1.0,"message":"Generation complete","timestamp":1234567890.789}
```

**Response** (Missing Token - 422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["query", "token"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

---

## Verification Checklist

### After Backend Fix

- [ ] Run generation with simple prompt
- [ ] Check logs for SQLAlchemy error (should be gone)
- [ ] Verify generation completes successfully
- [ ] Check similar project detection works
- [ ] No datetime warnings in logs

### After Frontend Fix

- [ ] SSE connection includes `?token=` parameter
- [ ] Failed generation shows error (doesn't retry)
- [ ] Completed generation doesn't retry streaming
- [ ] Rate limit (429) stops retry attempts
- [ ] Max 5 retries on network errors

---

## Debug Commands

### Check generation status
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/generations/0c9055c8-b6fa-4b5e-bf5e-ed96a7391ccc
```

### Check generation error message
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/generations/0c9055c8-b6fa-4b5e-bf5e-ed96a7391ccc \
  | jq '.error_message'
```

### Test token generation for failed generation
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/generations/0c9055c8-b6fa-4b5e-bf5e-ed96a7391ccc/stream-token"
# Should return 400 Bad Request
```

---

**Document Version**: 1.0  
**Date**: 2025-10-16 16:44  
**Status**: 🔴 Critical errors identified - awaiting fixes
