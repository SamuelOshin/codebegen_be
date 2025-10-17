# SSE Retry Handling Guide - Stop Infinite Retry Loops

## Problem Overview

**Symptom**: Frontend makes 1000+ requests per second when generation fails  
**Root Cause**: Frontend retries infinitely when SSE stream closes immediately  
**Impact**: Server resource exhaustion, rate limiting triggers, poor UX

## Backend Changes (Completed)

### 1. Rate Limiting on Token Generation
```http
POST /generations/generate/{id}/stream-token
```

**Rate Limit**: 10 requests per minute per generation  
**Status Code**: `429 Too Many Requests`  
**Response**:
```json
{
  "detail": "Too many token requests. Maximum 10 requests per minute. Please wait before retrying."
}
```

### 2. Terminal State Rejection
Token generation now **fails immediately** if generation is in terminal state:

**Rejected States**:
- `failed`: Generation encountered an error
- `cancelled`: User cancelled generation
- `completed`: Generation finished successfully

**Status Code**: `400 Bad Request`  
**Response Examples**:
```json
{
  "detail": "Generation has failed. Error: Invalid prompt format. Cannot stream."
}
```

```json
{
  "detail": "Generation already completed. Streaming not available for completed generations."
}
```

### 3. Enhanced Stream Events
Stream now sends **proper error events** instead of just closing:

```typescript
// Initial connection event
{
  "generation_id": "abc-123",
  "status": "pending",
  "stage": "connected",
  "progress": 0.0,
  "message": "Stream connected",
  "timestamp": 1234567890.123
}

// Terminal error event (generation failed)
{
  "generation_id": "abc-123",
  "status": "failed",
  "stage": "terminal",  // ← Frontend should STOP retrying
  "progress": 0.0,
  "message": "Invalid prompt: missing required fields",
  "timestamp": 1234567890.456
}

// Timeout event (no progress for 60 seconds)
{
  "generation_id": "abc-123",
  "status": "failed",
  "stage": "timeout",  // ← Frontend should STOP retrying
  "progress": 0.0,
  "message": "Generation timed out - no events received",
  "timestamp": 1234567890.789
}
```

---

## Frontend Implementation (Required)

### 1. Stop Retry on Terminal States

**NEVER retry** when you receive these statuses:
- `status === "failed"`
- `status === "cancelled"`
- `status === "completed"`
- `stage === "terminal"`
- `stage === "timeout"`
- `stage === "error"`

**Example React Hook**:
```typescript
function useGenerationStream(generationId: string) {
  const [shouldRetry, setShouldRetry] = useState(true);
  const [retryCount, setRetryCount] = useState(0);
  const MAX_RETRIES = 5;

  const handleEvent = (event: SSEEvent) => {
    const data = JSON.parse(event.data);
    
    // Stop retry on terminal states
    if (
      data.status === 'failed' ||
      data.status === 'cancelled' ||
      data.status === 'completed' ||
      data.stage === 'terminal' ||
      data.stage === 'timeout' ||
      data.stage === 'error'
    ) {
      setShouldRetry(false);
      console.log('Terminal state reached, stopping retries:', data);
      return;
    }
  };

  const connect = async () => {
    if (!shouldRetry || retryCount >= MAX_RETRIES) {
      console.log('Retry stopped:', { shouldRetry, retryCount });
      return;
    }

    try {
      // Get SSE token
      const response = await fetch(
        `/api/generations/generate/${generationId}/stream-token`,
        { headers: { Authorization: `Bearer ${jwt}` } }
      );

      if (response.status === 429) {
        // Rate limited - wait longer
        console.warn('Rate limited, waiting 60 seconds...');
        setTimeout(connect, 60000);
        return;
      }

      if (response.status === 400) {
        // Terminal state - stop retrying
        const error = await response.json();
        console.error('Generation in terminal state:', error.detail);
        setShouldRetry(false);
        return;
      }

      if (!response.ok) throw new Error('Failed to get SSE token');

      const { sse_token } = await response.json();

      // Connect to stream
      const eventSource = new EventSource(
        `/api/generations/generate/${generationId}/stream?token=${sse_token}`
      );

      eventSource.addEventListener('message', handleEvent);

      eventSource.addEventListener('error', (error) => {
        eventSource.close();
        
        if (shouldRetry && retryCount < MAX_RETRIES) {
          setRetryCount(prev => prev + 1);
          // Exponential backoff: 2s, 4s, 8s, 16s, 32s
          const delay = Math.min(2000 * Math.pow(2, retryCount), 32000);
          console.log(`Retrying in ${delay}ms (attempt ${retryCount + 1}/${MAX_RETRIES})`);
          setTimeout(connect, delay);
        } else {
          console.error('Max retries reached or retry disabled');
          setShouldRetry(false);
        }
      });

    } catch (error) {
      console.error('Failed to connect:', error);
      setRetryCount(prev => prev + 1);
    }
  };

  useEffect(() => {
    connect();
    return () => setShouldRetry(false);
  }, [generationId]);
}
```

### 2. Exponential Backoff

**Required**: Implement exponential backoff for retries:

```typescript
const RETRY_DELAYS = [2000, 4000, 8000, 16000, 32000]; // milliseconds

function getRetryDelay(attemptNumber: number): number {
  return RETRY_DELAYS[Math.min(attemptNumber, RETRY_DELAYS.length - 1)];
}
```

**Why**: Prevents thundering herd problem, gives server time to recover

### 3. Handle 429 Rate Limit Errors

```typescript
if (response.status === 429) {
  // Server rate limited us - stop retrying for 60 seconds
  console.warn('Rate limit hit, pausing retries for 60s');
  showUserNotification('Too many retry attempts. Please wait a minute.');
  
  // Optional: Disable retry button for 60 seconds
  setTimeout(() => {
    console.log('Rate limit window expired, can retry now');
  }, 60000);
  
  return; // Don't retry
}
```

### 4. Handle 400 Bad Request (Terminal State)

```typescript
if (response.status === 400) {
  const error = await response.json();
  
  // Parse error message
  if (error.detail.includes('failed')) {
    showError('Generation failed', error.detail);
  } else if (error.detail.includes('completed')) {
    // Redirect to results page
    router.push(`/generations/${generationId}/results`);
  } else if (error.detail.includes('cancelled')) {
    showInfo('Generation was cancelled');
  }
  
  // NEVER retry on 400
  return;
}
```

### 5. Maximum Retry Limit

**Required**: Never retry more than 5 times

```typescript
const MAX_RETRIES = 5;
let retryCount = 0;

function shouldRetry(): boolean {
  if (retryCount >= MAX_RETRIES) {
    console.error('Max retries exceeded');
    showError('Unable to connect to generation stream');
    return false;
  }
  retryCount++;
  return true;
}
```

---

## Complete TypeScript Example

```typescript
interface GenerationEvent {
  generation_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  stage: string;
  progress: number;
  message: string;
  timestamp: number;
}

class GenerationStreamManager {
  private generationId: string;
  private jwtToken: string;
  private eventSource: EventSource | null = null;
  private retryCount = 0;
  private shouldRetry = true;
  
  private readonly MAX_RETRIES = 5;
  private readonly RETRY_DELAYS = [2000, 4000, 8000, 16000, 32000];
  
  constructor(generationId: string, jwtToken: string) {
    this.generationId = generationId;
    this.jwtToken = jwtToken;
  }
  
  async start(): Promise<void> {
    await this.connect();
  }
  
  stop(): void {
    this.shouldRetry = false;
    this.closeStream();
  }
  
  private closeStream(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
  
  private async connect(): Promise<void> {
    // Check retry limits
    if (!this.shouldRetry) {
      console.log('Retry disabled, not connecting');
      return;
    }
    
    if (this.retryCount >= this.MAX_RETRIES) {
      console.error('Max retries exceeded');
      this.onError('Maximum retry attempts reached');
      return;
    }
    
    try {
      // Step 1: Get SSE token
      const tokenResponse = await fetch(
        `/api/generations/generate/${this.generationId}/stream-token`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.jwtToken}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      // Handle rate limiting
      if (tokenResponse.status === 429) {
        console.warn('Rate limited, waiting 60 seconds');
        this.onRateLimited();
        return; // Don't retry
      }
      
      // Handle terminal states
      if (tokenResponse.status === 400) {
        const error = await tokenResponse.json();
        console.error('Generation in terminal state:', error.detail);
        this.shouldRetry = false;
        this.onTerminalState(error.detail);
        return;
      }
      
      if (!tokenResponse.ok) {
        throw new Error(`Token request failed: ${tokenResponse.status}`);
      }
      
      const { sse_token } = await tokenResponse.json();
      
      // Step 2: Connect to stream
      this.eventSource = new EventSource(
        `/api/generations/generate/${this.generationId}/stream?token=${sse_token}`
      );
      
      this.eventSource.addEventListener('message', (event) => {
        const data: GenerationEvent = JSON.parse(event.data);
        this.handleEvent(data);
      });
      
      this.eventSource.addEventListener('error', () => {
        this.closeStream();
        this.handleStreamError();
      });
      
    } catch (error) {
      console.error('Connection error:', error);
      this.handleStreamError();
    }
  }
  
  private handleEvent(event: GenerationEvent): void {
    console.log('Event received:', event);
    
    // Check for terminal states
    const terminalStatuses = ['failed', 'cancelled', 'completed'];
    const terminalStages = ['terminal', 'timeout', 'error'];
    
    if (
      terminalStatuses.includes(event.status) ||
      terminalStages.includes(event.stage)
    ) {
      console.log('Terminal state detected, stopping retries');
      this.shouldRetry = false;
      this.closeStream();
      
      if (event.status === 'completed') {
        this.onComplete(event);
      } else {
        this.onFailed(event);
      }
      return;
    }
    
    // Normal progress event
    this.onProgress(event);
  }
  
  private handleStreamError(): void {
    if (!this.shouldRetry || this.retryCount >= this.MAX_RETRIES) {
      console.error('Not retrying stream connection');
      return;
    }
    
    this.retryCount++;
    const delay = this.RETRY_DELAYS[
      Math.min(this.retryCount - 1, this.RETRY_DELAYS.length - 1)
    ];
    
    console.log(`Retrying in ${delay}ms (attempt ${this.retryCount}/${this.MAX_RETRIES})`);
    
    setTimeout(() => this.connect(), delay);
  }
  
  // Callbacks (implement these in your UI)
  private onProgress(event: GenerationEvent): void {
    console.log('Progress:', event);
    // Update UI with progress
  }
  
  private onComplete(event: GenerationEvent): void {
    console.log('Generation completed:', event);
    // Redirect to results page
  }
  
  private onFailed(event: GenerationEvent): void {
    console.error('Generation failed:', event.message);
    // Show error to user
  }
  
  private onTerminalState(message: string): void {
    console.error('Terminal state:', message);
    // Show error to user
  }
  
  private onRateLimited(): void {
    console.warn('Rate limited');
    // Show rate limit message to user
  }
  
  private onError(message: string): void {
    console.error('Stream error:', message);
    // Show error to user
  }
}

// Usage
const manager = new GenerationStreamManager(generationId, jwtToken);
manager.start();

// Cleanup on component unmount
onUnmount(() => manager.stop());
```

---

## Testing Checklist

### Test Cases for Frontend

- [ ] **Normal flow**: Generation completes successfully
  - Stream should close after `status: 'completed'`
  - Should NOT retry

- [ ] **Failed generation**: Generation fails due to error
  - Stream sends `status: 'failed'` event
  - Frontend should NOT retry
  - Error message displayed to user

- [ ] **Cancelled generation**: User cancels generation
  - Stream sends `status: 'cancelled'` event
  - Frontend should NOT retry

- [ ] **Network interruption**: Connection drops mid-generation
  - Frontend should retry with exponential backoff
  - Max 5 retry attempts

- [ ] **Rate limiting**: Too many token requests
  - Backend returns `429 Too Many Requests`
  - Frontend should wait 60 seconds before allowing retry
  - User sees appropriate message

- [ ] **Already completed**: Token request for completed generation
  - Backend returns `400 Bad Request`
  - Frontend redirects to results page

- [ ] **Timeout**: No events for 60 seconds
  - Backend sends `stage: 'timeout'` event
  - Frontend stops retrying
  - Error shown to user

---

## Debug Commands

### Check if generation is stuck
```bash
# Get generation status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/generations/$GENERATION_ID

# Expected response
{
  "id": "abc-123",
  "status": "failed",  # or "completed", "cancelled"
  "error_message": "The actual error message",
  ...
}
```

### Monitor server logs for retry spam
```bash
# Look for this pattern (BAD - means infinite retry)
grep "Generated SSE token" logs/app.log | wc -l
# If count > 100 in short time = retry loop

# Check rate limiting
grep "Rate limit exceeded" logs/app.log
```

### Test rate limiting manually
```bash
# Send 11 requests in quick succession (should get 429 on 11th)
for i in {1..11}; do
  curl -X POST \
    -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/generations/$GENERATION_ID/stream-token"
  echo "\n---Request $i---"
done
```

---

## Quick Reference

### HTTP Status Codes

| Code | Meaning | Frontend Action |
|------|---------|-----------------|
| `200` | Token generated | Connect to stream |
| `400` | Terminal state (failed/completed/cancelled) | **STOP retrying**, show error or redirect |
| `401` | Unauthorized | Refresh JWT token |
| `403` | Forbidden | Show "access denied" |
| `404` | Generation not found | Show "not found" |
| `429` | Rate limited | **STOP retrying** for 60s, show message |
| `500` | Server error | Retry with backoff (max 5 times) |

### SSE Event Stages That Mean "STOP"

```typescript
const TERMINAL_STAGES = [
  'terminal',   // Explicit terminal state
  'timeout',    // Stream timed out
  'error',      // Stream encountered error
  'complete'    // Generation finished
];

const TERMINAL_STATUSES = [
  'completed',  // Success
  'failed',     // Error occurred
  'cancelled'   // User cancelled
];
```

---

## Migration Checklist

- [ ] Update frontend SSE connection code with retry limits
- [ ] Add exponential backoff logic
- [ ] Handle 429 rate limit responses
- [ ] Handle 400 terminal state responses
- [ ] Stop retry on terminal event stages
- [ ] Add user notifications for errors
- [ ] Test all failure scenarios
- [ ] Monitor production for retry loops

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-16  
**Status**: ✅ Ready for implementation
