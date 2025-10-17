# Frontend SSE 422 Error Fix - Missing Token Parameter

## Problem Summary

**Error**: 422 Unprocessable Entity when connecting to SSE stream
```
GET http://localhost:8000/generations/generate/.../stream 422 (Unprocessable Entity)
```

**Root Cause**: The SSE endpoint requires a `token` query parameter, but the frontend EventSource is being created **without the token**, even though the token is successfully obtained from the `/stream-token` endpoint.

**Location**: `codebegen_fe/hooks/use-generation-stream.ts` line ~247

## Backend Expectation

The backend SSE endpoint signature (from `app/routers/generations.py:335`):

```python
@router.get("/generate/{generation_id}/stream")
async def stream_generation_progress(
    generation_id: str,
    token: str = Query(..., description="Short-lived SSE token"),  # ← REQUIRED!
    db: AsyncSession = Depends(get_async_db)
):
```

The backend returns the token in the response from `/stream-token`:

```json
{
  "sse_token": "abc123...",           // ← This is the token!
  "expires_in": 60,
  "stream_url": "/generations/generate/.../stream",
  "generation_id": "..."
}
```

## The Fix

### Current Code (WRONG ❌):
```typescript
// Around line 236-248 in use-generation-stream.ts
const tokenResponse = await generationService.getSSEToken(generationId);

console.log('[useGenerationStream] Got SSE token:', {
  stream_url: tokenResponse.stream_url,
  expires_in: tokenResponse.expires_in
});

// ❌ Missing the token query parameter!
const fullStreamUrl = `${API_BASE_URL}${tokenResponse.stream_url}`;

const eventSource = new EventSource(fullStreamUrl);
```

### Fixed Code (CORRECT ✅):
```typescript
// Around line 236-248 in use-generation-stream.ts
const tokenResponse = await generationService.getSSEToken(generationId);

console.log('[useGenerationStream] Got SSE token:', {
  sse_token: tokenResponse.sse_token,  // Log the token too
  stream_url: tokenResponse.stream_url,
  expires_in: tokenResponse.expires_in
});

// ✅ Append the token as a query parameter
const fullStreamUrl = `${API_BASE_URL}${tokenResponse.stream_url}?token=${tokenResponse.sse_token}`;

console.log('[useGenerationStream] Connecting to full URL with token');

const eventSource = new EventSource(fullStreamUrl);
```

## Complete Fixed Function

Here's the complete `connectToSSE` function with the fix:

```typescript
/**
 * Connect to SSE stream
 */
const connectToSSE = useCallback(async (generationId: string, projectId: string | null) => {
  // Clean up existing connection
  if (eventSourceRef.current) {
    eventSourceRef.current.close();
    eventSourceRef.current = null;
  }
  
  try {
    setState(prev => ({ ...prev, status: 'connecting' }));
    
    // Get SSE token from backend
    const tokenResponse = await generationService.getSSEToken(generationId);
    
    console.log('[useGenerationStream] Got SSE token:', {
      sse_token: tokenResponse.sse_token?.substring(0, 20) + '...', // Log partial token
      stream_url: tokenResponse.stream_url,
      expires_in: tokenResponse.expires_in
    });
    
    // ✅ FIX: Create full URL with backend base URL AND token query parameter
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const fullStreamUrl = `${API_BASE_URL}${tokenResponse.stream_url}?token=${tokenResponse.sse_token}`;
    
    console.log('[useGenerationStream] Connecting to SSE with authenticated token');
    
    // Create EventSource with full URL including token
    const eventSource = new EventSource(fullStreamUrl);
    eventSourceRef.current = eventSource;

    // Set up event listeners
    eventSource.addEventListener('progress', handleEvent);
    eventSource.addEventListener('error', handleError);

    eventSource.onopen = () => {
      console.log('[useGenerationStream] SSE connection established');
      reconnectAttemptsRef.current = 0; // Reset reconnect counter
      setState(prev => ({
        ...prev,
        isConnected: true,
        status: 'generating',
        error: null,
      }));
    };

  } catch (error) {
    console.error('[useGenerationStream] Failed to connect to SSE:', error);
    setState(prev => ({
      ...prev,
      status: 'error',
      error: error instanceof Error ? error.message : 'Failed to connect',
    }));
  }
}, [handleEvent, handleError]);
```

## Exact Changes Required

**File**: `codebegen_fe/hooks/use-generation-stream.ts`

**Line ~237-240**: Change from:
```typescript
console.log('[useGenerationStream] Got SSE token:', {
  stream_url: tokenResponse.stream_url,
  expires_in: tokenResponse.expires_in
});
```

To:
```typescript
console.log('[useGenerationStream] Got SSE token:', {
  sse_token: tokenResponse.sse_token?.substring(0, 20) + '...',
  stream_url: tokenResponse.stream_url,
  expires_in: tokenResponse.expires_in
});
```

**Line ~244**: Change from:
```typescript
const fullStreamUrl = `${API_BASE_URL}${tokenResponse.stream_url}`;
```

To:
```typescript
const fullStreamUrl = `${API_BASE_URL}${tokenResponse.stream_url}?token=${tokenResponse.sse_token}`;
```

## Expected Result

After applying the fix:

### Before (422 Error):
```
GET http://localhost:8000/generations/generate/8960ded9-5b90-4459-8525-19a524c55691/stream
→ 422 Unprocessable Entity
```

### After (Success):
```
GET http://localhost:8000/generations/generate/8960ded9-5b90-4459-8525-19a524c55691/stream?token=abc123...
→ 200 OK
→ SSE events streaming
```

## Verification Steps

1. **Check browser console** - Should see:
   ```
   [useGenerationStream] Got SSE token: {sse_token: "abc123...", stream_url: "...", expires_in: 60}
   [useGenerationStream] Connecting to SSE with authenticated token
   [useGenerationStream] SSE connection established
   ```

2. **Check Network tab** - The SSE request should now include the token:
   ```
   http://localhost:8000/generations/generate/.../stream?token=abc123...
   Status: 200 OK
   ```

3. **Check backend logs** - Should see:
   ```
   INFO: SSE stream started for user ..., generation ...
   ```

4. **Verify SSE events** - Progress events should start streaming:
   ```
   data: {"generation_id":"...","status":"processing","progress":0.1,...}
   ```

## Security Note

The token approach is correct:
- ✅ Short-lived (60 seconds)
- ✅ Single-use
- ✅ User-specific
- ✅ Generation-specific
- ✅ Validated on backend

The token in the URL is acceptable for SSE because:
- EventSource doesn't support custom headers
- Token is short-lived and single-use
- Token expires after 60 seconds
- Token is invalidated after use

## Common Issues

### Issue: Token expired error
**Solution**: The token is valid for 60 seconds. If you see "Invalid or expired SSE token", request a new token.

### Issue: Still getting 422
**Check**:
1. The token is being appended to the URL
2. The token field name is `sse_token` not `token` in the response
3. The backend is returning the `sse_token` field

### Issue: CORS error
**Solution**: Ensure backend CORS allows the frontend origin:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Summary

**Change this line** (~244):
```typescript
const fullStreamUrl = `${API_BASE_URL}${tokenResponse.stream_url}`;
```

**To this**:
```typescript
const fullStreamUrl = `${API_BASE_URL}${tokenResponse.stream_url}?token=${tokenResponse.sse_token}`;
```

This appends the SSE token as a query parameter, which the backend requires for authentication.

## TypeScript Type Safety (Optional)

If your TypeScript types don't include `sse_token`, update them:

```typescript
// In lib/api/types-v2.ts or wherever SSE types are defined
export interface SSETokenResponse {
  sse_token: string;      // ← Add this
  expires_in: number;
  stream_url: string;
  generation_id: string;
}
```
