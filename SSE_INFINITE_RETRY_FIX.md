# SSE Infinite Retry Loop - Fix Complete

## Problem Summary

**Issue**: Frontend making 1000+ requests/second in infinite retry loop  
**Generation ID**: `a4e2d98e-d4f3-4475-a0e4-6ecaa86ee881`  
**Root Cause**: Generation failed, but stream closed immediately without proper error signaling, causing frontend to retry infinitely

### Log Evidence
```
16:15:17 - SSE stream started
16:15:17 - SSE stream closed  (< 5ms later)
16:15:17 - New token requested (212ms later)
16:15:17 - SSE stream started
16:15:17 - SSE stream closed  (IMMEDIATE)
... repeats 1000+ times
```

---

## Backend Fixes Applied

### 1. ✅ Rate Limiting on Token Generation

**File**: `app/routers/generations.py`

Added rate limiting to prevent abuse:
- **Limit**: 10 token requests per minute per generation
- **Response**: `429 Too Many Requests`
- **Message**: "Too many token requests. Maximum 10 requests per minute. Please wait before retrying."

```python
# Rate limiting check
rate_limit_key = f"{current_user.id}:{generation_id}"
if len(_token_generation_attempts[rate_limit_key]) >= 10:
    raise HTTPException(status_code=429, ...)
```

**Benefit**: Stops retry spam from overwhelming server

---

### 2. ✅ Terminal State Detection in Token Endpoint

**File**: `app/routers/generations.py`

Token generation now **rejects** requests for failed/completed generations:

```python
# Check if generation is in a terminal state
if generation.status in ["failed", "cancelled"]:
    raise HTTPException(
        status_code=400,
        detail=f"Generation has {generation.status}. Error: {generation.error_message}. Cannot stream."
    )

if generation.status == "completed":
    raise HTTPException(
        status_code=400,
        detail="Generation already completed. Streaming not available."
    )
```

**HTTP Status**: `400 Bad Request`

**Benefit**: Frontend immediately knows not to retry

---

### 3. ✅ Enhanced Stream Events with Error Signaling

**File**: `app/routers/generations.py`

Stream now sends **proper events** instead of just closing:

#### Initial Connection Event
```json
{
  "generation_id": "abc-123",
  "status": "pending",
  "stage": "connected",
  "progress": 0.0,
  "message": "Stream connected",
  "timestamp": 1234567890.123
}
```

#### Terminal State Event (Failed Generation)
```json
{
  "generation_id": "abc-123",
  "status": "failed",
  "stage": "terminal",
  "progress": 0.0,
  "message": "Generation error message here",
  "timestamp": 1234567890.456
}
```

#### Timeout Event (No Events for 60s)
```json
{
  "generation_id": "abc-123",
  "status": "failed",
  "stage": "timeout",
  "progress": 0.0,
  "message": "Generation timed out - no events received",
  "timestamp": 1234567890.789
}
```

**Benefit**: Frontend receives explicit "stop retrying" signal

---

### 4. ✅ Database Status Refresh

Stream now refreshes generation status from database:

```python
# Refresh generation status from database
await db.refresh(generation)

# Check if generation entered error state
if generation.status in ["failed", "cancelled"]:
    error_event = StreamingProgressEvent(
        status=generation.status,
        stage="error",
        message=generation.error_message or f"Generation {generation.status}"
    )
    yield f"data: {error_event.json()}\\n\\n"
    break
```

**Benefit**: Detects failures even if no events were generated

---

### 5. ✅ Stream Timeout Protection

Added 60-second timeout if no events received:

```python
max_empty_polls = 120  # 120 * 0.5s = 60 seconds
empty_poll_count = 0

if empty_poll_count >= max_empty_polls:
    timeout_event = StreamingProgressEvent(
        status="failed",
        stage="timeout",
        message="Generation timed out - no events received"
    )
    yield f"data: {timeout_event.json()}\\n\\n"
    break
```

**Benefit**: Prevents infinite waiting on stuck generations

---

## Frontend Requirements

### Critical Changes Needed

The frontend **MUST** be updated to handle these changes:

#### 1. Stop Retry on Terminal States

**NEVER retry** when receiving:
- `status === "failed"`
- `status === "cancelled"`  
- `status === "completed"`
- `stage === "terminal"`
- `stage === "timeout"`
- `stage === "error"`

```typescript
const handleEvent = (event: SSEEvent) => {
  const data = JSON.parse(event.data);
  
  if (
    data.status === 'failed' ||
    data.status === 'cancelled' ||
    data.status === 'completed' ||
    data.stage === 'terminal' ||
    data.stage === 'timeout' ||
    data.stage === 'error'
  ) {
    // STOP RETRYING!
    stopRetry();
    return;
  }
};
```

#### 2. Handle HTTP 429 (Rate Limit)

```typescript
const response = await fetch('/stream-token', ...);

if (response.status === 429) {
  // Rate limited - DO NOT RETRY for 60 seconds
  showError('Too many requests. Please wait.');
  return;
}
```

#### 3. Handle HTTP 400 (Terminal State)

```typescript
if (response.status === 400) {
  const error = await response.json();
  
  if (error.detail.includes('failed')) {
    showError('Generation failed', error.detail);
  } else if (error.detail.includes('completed')) {
    router.push(`/generations/${id}/results`);
  }
  
  // NEVER retry on 400
  return;
}
```

#### 4. Implement Retry Limits

```typescript
const MAX_RETRIES = 5;
const RETRY_DELAYS = [2000, 4000, 8000, 16000, 32000]; // Exponential backoff

function shouldRetry(retryCount: number): boolean {
  return retryCount < MAX_RETRIES;
}

function getRetryDelay(retryCount: number): number {
  return RETRY_DELAYS[Math.min(retryCount, RETRY_DELAYS.length - 1)];
}
```

---

## Testing Your Frontend

### Test Case 1: Failed Generation

1. Create a generation that will fail (e.g., invalid prompt)
2. Connect to stream
3. **Expected behavior**:
   - Receive event with `status: "failed"` or `stage: "terminal"`
   - Frontend stops retrying
   - Error message shown to user
   - Token generation endpoint returns `400` on subsequent requests

### Test Case 2: Rate Limiting

1. Manually trigger rapid retries (e.g., spam refresh)
2. **Expected behavior**:
   - After 10 requests in 1 minute, receive `429` response
   - Frontend shows rate limit message
   - No more requests for 60 seconds

### Test Case 3: Already Completed Generation

1. Try to stream a completed generation
2. **Expected behavior**:
   - Token endpoint returns `400 Bad Request`
   - Frontend redirects to results page
   - No streaming attempted

### Test Case 4: Network Interruption

1. Start streaming active generation
2. Disconnect network mid-stream
3. **Expected behavior**:
   - Frontend retries with exponential backoff (2s, 4s, 8s, 16s, 32s)
   - Max 5 retry attempts
   - Clear error message after max retries

---

## Immediate Actions Required

### For Backend (You)
✅ **DONE** - All backend changes implemented
- Rate limiting active
- Terminal state detection working
- Enhanced events being sent
- Timeout protection enabled

### For Frontend Team
🔴 **URGENT** - Frontend must be updated immediately:

1. **Stop infinite retry loop** (CRITICAL)
   - Add terminal state detection
   - Implement retry limits
   - Handle HTTP 400 and 429 responses

2. **Update SSE connection logic** (HIGH)
   - Check event.stage for "terminal", "timeout", "error"
   - Implement exponential backoff
   - Add max retry counter

3. **Update UI** (MEDIUM)
   - Show rate limit messages
   - Display terminal state errors clearly
   - Add retry count indicator

**Documentation**: See `SSE_RETRY_HANDLING_GUIDE.md` for complete implementation guide

---

## Monitoring & Verification

### Check if fix is working

```bash
# Backend logs should show:
grep "Rate limit exceeded" logs/app.log
# Should see entries if frontend is still spamming

# Count SSE token generations in last minute
grep "Generated SSE token" logs/app.log | tail -20
# Should see at most 10 per generation per minute

# Check for terminal state rejections
grep "Attempted to stream failed generation" logs/app.log
# Should see entries if fix is working
```

### Metrics to track

- **Token requests per minute**: Should be < 10 per generation
- **Stream duration**: Failed generations should close in < 1 second
- **Retry attempts**: Should see max 5 retries for network issues
- **429 responses**: Should increase if frontend hasn't updated yet

---

## Files Changed

### Backend Files
1. `app/routers/generations.py` - Rate limiting + terminal state detection + enhanced events
2. `SSE_RETRY_HANDLING_GUIDE.md` - **NEW** - Frontend implementation guide
3. `SSE_INFINITE_RETRY_FIX.md` - **NEW** - This document

### Frontend Files (Needs Update)
- Your SSE connection/retry logic
- Generation status handling
- Error display components
- Rate limit handling

---

## Rollback Plan

If issues occur:

```bash
# Revert changes to generations.py
git diff HEAD^ app/routers/generations.py
git checkout HEAD^ app/routers/generations.py

# Restart server
pkill -f uvicorn
python -m uvicorn main:app --reload --port 8000
```

**Note**: Old behavior will return (no rate limiting, immediate stream close on errors)

---

## Next Steps

1. ✅ **Backend deployed** - Changes are live
2. 🔴 **Frontend team notified** - Share `SSE_RETRY_HANDLING_GUIDE.md`
3. ⏳ **Frontend implements fixes** - Critical for production
4. ⏳ **Testing** - Verify all scenarios work
5. ⏳ **Monitor production** - Watch for retry loops

---

## Support

**Questions?** Check the comprehensive guide:
- `SSE_RETRY_HANDLING_GUIDE.md` - Complete frontend implementation
- `FRONTEND_SECURE_SSE_MIGRATION.md` - Original SSE security migration

**Debugging?**
```bash
# Check generation status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/generations/$GENERATION_ID

# Test rate limiting
for i in {1..11}; do
  curl -X POST -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/generations/$GENERATION_ID/stream-token"
done
```

---

**Fix Version**: 1.0  
**Date**: 2025-10-16  
**Status**: ✅ Backend complete, 🔴 Frontend update required
