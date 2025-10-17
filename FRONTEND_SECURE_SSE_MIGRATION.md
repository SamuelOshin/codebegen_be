# 🔐 SECURE SSE STREAMING - FRONTEND MIGRATION GUIDE

**Date:** October 16, 2025  
**Status:** 🚨 SECURITY FIX - Immediate Action Required  
**Change Type:** Breaking Change  
**Priority:** HIGH - Security Vulnerability Fixed  

---

## 📋 EXECUTIVE SUMMARY

We've fixed a **critical security vulnerability** in SSE (Server-Sent Events) authentication. The old method exposed JWT tokens in URLs and server logs. The new method uses short-lived, single-use tokens that are much more secure.

### What Changed?

**OLD (Insecure):**
```typescript
// ❌ JWT token exposed in URL
const url = `/generations/${id}/stream?token=${jwtToken}`
const eventSource = new EventSource(url)
```

**NEW (Secure):**
```typescript
// ✅ Step 1: Get short-lived SSE token
const { sse_token } = await getSSEToken(generationId)

// ✅ Step 2: Use SSE token (expires in 60s, single-use)
const url = `/generations/${id}/stream?token=${sse_token}`
const eventSource = new EventSource(url)
```

---

## 🚨 SECURITY ISSUES FIXED

### Why Was the Old Method Insecure?

1. **Server Logs Exposure** 🔴 CRITICAL
   ```bash
   # JWT tokens logged in access logs
   127.0.0.1 "GET /stream?token=eyJhbGci... HTTP/1.1"
   ```

2. **Browser History** 🔴 HIGH
   - Tokens stored in browser history
   - Autocomplete exposes tokens
   - Shared computers retain history

3. **Referrer Headers** 🟡 MEDIUM
   - Tokens leaked when clicking external links
   - Third-party analytics capture full URLs

4. **Link Sharing** 🔴 CRITICAL
   - Users accidentally share URLs with embedded tokens
   - Slack/Email/Discord expose tokens

### New Security Features

✅ **Short-lived tokens** - Expire in 60 seconds  
✅ **Single-use tokens** - Invalidated after first connection  
✅ **No JWT exposure** - Real JWT never appears in URLs  
✅ **Automatic cleanup** - Tokens deleted after use  
✅ **Access validation** - Verifies user has access to generation  

---

## 🔄 MIGRATION STEPS

### Step 1: Update API Service

Create a new method to fetch SSE tokens:

```typescript
// lib/api/services/generation.ts

export interface SSETokenResponse {
  sse_token: string
  expires_in: number
  stream_url: string
  generation_id: string
}

export class GenerationService {
  /**
   * Get short-lived SSE token for streaming.
   * 
   * Security: Uses standard Bearer authentication.
   * Token expires in 60 seconds and is single-use.
   * 
   * @param generationId - Generation ID to stream
   * @returns SSE token response
   * @throws {APIError} If generation not found or access denied
   */
  async getSSEToken(generationId: string): Promise<SSETokenResponse> {
    const response = await this.client.post<SSETokenResponse>(
      `/generations/generate/${generationId}/stream-token`,
      {},
      {
        headers: {
          'Authorization': `Bearer ${this.getAccessToken()}`  // ✅ JWT in header (secure)
        }
      }
    )
    
    return response.data
  }
  
  /**
   * Get access token from storage.
   * 
   * @returns JWT access token
   */
  private getAccessToken(): string {
    // Get from your auth state management
    return localStorage.getItem('access_token') || ''
  }
}

export const generationService = new GenerationService()
```

### Step 2: Update Generation Monitor

Modify your SSE streaming logic to use the new token flow:

```typescript
// lib/generation-monitor.ts

export interface StreamingProgressEvent {
  generation_id: string
  status: string
  stage: string
  progress: number
  message: string
  timestamp: number
  ab_group?: string
  enhanced_features?: Record<string, boolean>
  generation_mode?: string
}

export class GenerationMonitor {
  private eventSource: EventSource | null = null
  private generationId: string
  private retryCount: number = 0
  private maxRetries: number = 3
  
  constructor(generationId: string) {
    this.generationId = generationId
  }
  
  /**
   * Start streaming generation progress.
   * 
   * NEW: Fetches short-lived SSE token before connecting.
   * 
   * @param onProgress - Callback for progress events
   * @param onError - Optional error callback
   * @param onComplete - Optional completion callback
   */
  async startStreaming(
    onProgress: (event: StreamingProgressEvent) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): Promise<void> {
    try {
      // ✅ STEP 1: Get short-lived SSE token (60 second expiry)
      const { sse_token, stream_url } = await generationService.getSSEToken(
        this.generationId
      )
      
      // ✅ STEP 2: Connect to SSE stream with temporary token
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const url = `${baseUrl}${stream_url}?token=${sse_token}`
      
      this.eventSource = new EventSource(url)
      
      this.eventSource.onmessage = (event) => {
        try {
          const data: StreamingProgressEvent = JSON.parse(event.data)
          
          // Call progress callback
          onProgress(data)
          
          // Check for completion
          if (data.status === 'completed' || data.status === 'failed') {
            this.stopStreaming()
            onComplete?.()
          }
          
          // Reset retry count on successful message
          this.retryCount = 0
          
        } catch (error) {
          console.error('Failed to parse SSE event:', error)
          onError?.(error as Error)
        }
      }
      
      this.eventSource.onerror = (error) => {
        console.error('SSE connection error:', error)
        
        // Call error callback
        onError?.(new Error('SSE connection failed'))
        
        // Retry logic with exponential backoff
        this.stopStreaming()
        
        if (this.retryCount < this.maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, this.retryCount), 10000)
          this.retryCount++
          
          console.log(`Retrying SSE connection in ${delay}ms (attempt ${this.retryCount}/${this.maxRetries})`)
          
          setTimeout(() => {
            this.startStreaming(onProgress, onError, onComplete)
          }, delay)
        } else {
          console.error('Max retries reached, giving up on SSE connection')
          onError?.(new Error('Max retries reached'))
        }
      }
      
      this.eventSource.onopen = () => {
        console.log('SSE connection established for generation:', this.generationId)
        this.retryCount = 0
      }
      
    } catch (error) {
      console.error('Failed to get SSE token:', error)
      onError?.(error as Error)
      throw error
    }
  }
  
  /**
   * Stop streaming and close connection.
   */
  stopStreaming(): void {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
      console.log('SSE connection closed for generation:', this.generationId)
    }
  }
  
  /**
   * Check if currently streaming.
   */
  isStreaming(): boolean {
    return this.eventSource !== null && this.eventSource.readyState === EventSource.OPEN
  }
}
```

### Step 3: Update React Component

Update your generation page to use the new monitor:

```typescript
// app/generations/[id]/page.tsx

'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { GenerationMonitor, type StreamingProgressEvent } from '@/lib/generation-monitor'
import { toast } from 'sonner'

export default function GenerationPage() {
  const params = useParams()
  const router = useRouter()
  const generationId = params.id as string
  
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState<string>('connecting')
  const [message, setMessage] = useState<string>('Initializing...')
  const [monitor, setMonitor] = useState<GenerationMonitor | null>(null)
  
  useEffect(() => {
    // Create monitor instance
    const genMonitor = new GenerationMonitor(generationId)
    setMonitor(genMonitor)
    
    // Start streaming
    genMonitor.startStreaming(
      // onProgress
      (event: StreamingProgressEvent) => {
        setProgress(event.progress * 100)  // Convert 0-1 to 0-100
        setStatus(event.status)
        setMessage(event.message)
        
        console.log('Progress update:', event)
      },
      
      // onError
      (error: Error) => {
        console.error('Streaming error:', error)
        toast.error('Connection error', {
          description: error.message
        })
      },
      
      // onComplete
      () => {
        console.log('Generation complete!')
        toast.success('Generation complete')
        
        // Optionally redirect to results page
        setTimeout(() => {
          router.push(`/generations/${generationId}/results`)
        }, 2000)
      }
    )
    
    // Cleanup on unmount
    return () => {
      genMonitor.stopStreaming()
    }
  }, [generationId, router])
  
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Generation Progress</h1>
      
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Status:</span>
          <span className="text-sm text-muted-foreground">{status}</span>
        </div>
        
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>{message}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          
          <div className="w-full bg-secondary rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
```

### Step 4: Update Types

Add new type definitions:

```typescript
// lib/api/types/generation.ts

export interface SSETokenResponse {
  sse_token: string
  expires_in: number
  stream_url: string
  generation_id: string
}

export interface StreamingProgressEvent {
  generation_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  stage: string
  progress: number  // 0.0 to 1.0
  message: string
  timestamp: number
  ab_group?: string
  enhanced_features?: Record<string, boolean>
  generation_mode?: string
  estimated_time_remaining?: number
  current_file?: string
}
```

---

## 🧪 TESTING CHECKLIST

### Unit Tests

```typescript
// __tests__/lib/generation-monitor.test.ts

import { GenerationMonitor } from '@/lib/generation-monitor'
import { generationService } from '@/lib/api/services/generation'

jest.mock('@/lib/api/services/generation')

describe('GenerationMonitor - Secure SSE', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })
  
  it('should fetch SSE token before connecting', async () => {
    const mockToken = {
      sse_token: 'test-token-123',
      expires_in: 60,
      stream_url: '/generations/gen-123/stream',
      generation_id: 'gen-123'
    }
    
    ;(generationService.getSSEToken as jest.Mock).mockResolvedValue(mockToken)
    
    const monitor = new GenerationMonitor('gen-123')
    
    await monitor.startStreaming(jest.fn())
    
    expect(generationService.getSSEToken).toHaveBeenCalledWith('gen-123')
  })
  
  it('should NOT use JWT token in EventSource URL', async () => {
    const mockToken = {
      sse_token: 'short-lived-token',
      expires_in: 60,
      stream_url: '/generations/gen-123/stream',
      generation_id: 'gen-123'
    }
    
    ;(generationService.getSSEToken as jest.Mock).mockResolvedValue(mockToken)
    
    const EventSourceSpy = jest.spyOn(global, 'EventSource')
    
    const monitor = new GenerationMonitor('gen-123')
    await monitor.startStreaming(jest.fn())
    
    // Verify SSE token is used, not JWT
    expect(EventSourceSpy).toHaveBeenCalledWith(
      expect.stringContaining('token=short-lived-token')
    )
    expect(EventSourceSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('eyJhbGci')  // JWT pattern
    )
  })
  
  it('should handle token fetch errors gracefully', async () => {
    const error = new Error('Failed to fetch SSE token')
    ;(generationService.getSSEToken as jest.Mock).mockRejectedValue(error)
    
    const monitor = new GenerationMonitor('gen-123')
    const onError = jest.fn()
    
    await expect(
      monitor.startStreaming(jest.fn(), onError)
    ).rejects.toThrow('Failed to fetch SSE token')
    
    expect(onError).toHaveBeenCalledWith(error)
  })
})
```

### Integration Tests

```typescript
// __tests__/integration/sse-streaming.test.ts

import { render, waitFor, screen } from '@testing-library/react'
import GenerationPage from '@/app/generations/[id]/page'
import { generationService } from '@/lib/api/services/generation'

jest.mock('@/lib/api/services/generation')

describe('SSE Streaming Integration', () => {
  it('should complete full streaming flow', async () => {
    // Mock SSE token fetch
    ;(generationService.getSSEToken as jest.Mock).mockResolvedValue({
      sse_token: 'test-token',
      expires_in: 60,
      stream_url: '/generations/gen-123/stream'
    })
    
    // Mock EventSource
    const mockEventSource = {
      onmessage: null,
      onerror: null,
      onopen: null,
      close: jest.fn(),
      readyState: EventSource.OPEN
    }
    
    global.EventSource = jest.fn(() => mockEventSource) as any
    
    render(<GenerationPage params={{ id: 'gen-123' }} />)
    
    // Wait for token fetch
    await waitFor(() => {
      expect(generationService.getSSEToken).toHaveBeenCalled()
    })
    
    // Simulate progress event
    mockEventSource.onmessage?.({
      data: JSON.stringify({
        generation_id: 'gen-123',
        status: 'processing',
        stage: 'schema_extraction',
        progress: 0.5,
        message: 'Extracting schema...'
      })
    } as MessageEvent)
    
    // Verify UI updates
    await waitFor(() => {
      expect(screen.getByText(/50%/)).toBeInTheDocument()
      expect(screen.getByText(/Extracting schema/)).toBeInTheDocument()
    })
  })
})
```

---

## 📊 API ENDPOINT CHANGES

### New Endpoint: POST `/generations/generate/{generation_id}/stream-token`

**Purpose:** Generate short-lived SSE token

**Authentication:** Bearer Token (in Authorization header)

**Request:**
```bash
curl -X POST \
  https://api.codebegen.com/generations/generate/abc-123/stream-token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "sse_token": "xB7dK9mN2pQ5rT8vW1yZ4aE6gJ0hL3nM5oS7tU9vX2yA1cD4fG6hK8mP",
  "expires_in": 60,
  "stream_url": "/generations/generate/abc-123/stream",
  "generation_id": "abc-123"
}
```

**Errors:**
- `401 Unauthorized` - Invalid or expired JWT token
- `403 Forbidden` - User doesn't have access to generation
- `404 Not Found` - Generation not found

### Updated Endpoint: GET `/generations/generate/{generation_id}/stream`

**Changes:**
- ✅ Now accepts `token` query parameter (SSE token, not JWT)
- ✅ Token must be obtained from `/stream-token` endpoint
- ❌ No longer accepts JWT token directly

**Request:**
```bash
# Old (insecure)
GET /generations/generate/abc-123/stream?token=eyJhbGci...JWT_TOKEN

# New (secure)
GET /generations/generate/abc-123/stream?token=xB7dK9mN...SSE_TOKEN
```

**Response:** Server-Sent Events stream

---

## 🔒 SECURITY BEST PRACTICES

### Do's ✅

1. **Always fetch SSE token fresh** - Don't reuse tokens
2. **Handle token expiration** - Implement retry logic
3. **Use HTTPS in production** - Prevent token interception
4. **Close connections properly** - Clean up EventSource
5. **Log errors appropriately** - Track connection issues

### Don'ts ❌

1. **Don't store SSE tokens** - They're single-use and short-lived
2. **Don't share stream URLs** - Each user needs their own token
3. **Don't retry with same token** - Fetch new token for retry
4. **Don't expose tokens in logs** - Mask tokens in error messages
5. **Don't use JWT directly** - Always use SSE token endpoint

---

## 🚀 DEPLOYMENT CHECKLIST

- [ ] Update `GenerationService` with `getSSEToken()` method
- [ ] Update `GenerationMonitor` class with new flow
- [ ] Update all components using SSE streaming
- [ ] Add error handling for token fetch failures
- [ ] Implement retry logic with new token fetch
- [ ] Update type definitions
- [ ] Write unit tests for token flow
- [ ] Write integration tests for streaming
- [ ] Test on staging environment
- [ ] Monitor for 401 errors in production
- [ ] Update documentation
- [ ] Train team on new flow

---

## 📈 MONITORING

### Metrics to Track

```typescript
// Example: Track SSE metrics

analytics.track('sse_token_requested', {
  generation_id: generationId,
  timestamp: Date.now()
})

analytics.track('sse_connection_established', {
  generation_id: generationId,
  retry_count: retryCount,
  timestamp: Date.now()
})

analytics.track('sse_connection_error', {
  generation_id: generationId,
  error: error.message,
  retry_count: retryCount,
  timestamp: Date.now()
})
```

### Key Metrics

- **Token Request Rate** - Requests to `/stream-token` endpoint
- **Token Validation Success Rate** - % of valid tokens
- **Connection Error Rate** - SSE connection failures
- **Average Connection Duration** - How long streams last
- **Retry Rate** - How often retries are needed

---

## ❓ FAQ

### Q: Why the change?

**A:** The old method exposed JWT tokens in URLs, which appeared in server logs, browser history, and could be accidentally shared. This was a security vulnerability.

### Q: How long are SSE tokens valid?

**A:** 60 seconds from generation. They're designed for immediate use only.

### Q: Can I reuse an SSE token?

**A:** No. SSE tokens are single-use and are automatically invalidated after the first connection.

### Q: What if the token expires before I connect?

**A:** You'll get a 401 error. Simply fetch a new token and try again.

### Q: Do I need to change my JWT authentication?

**A:** No. JWT authentication for regular API calls remains the same. Only SSE streaming has changed.

### Q: What if my connection drops mid-stream?

**A:** Implement retry logic that fetches a new SSE token before reconnecting. See the `GenerationMonitor` example above.

### Q: Is this backward compatible?

**A:** No, this is a breaking change. Old clients using JWT tokens directly will receive 401 errors.

### Q: When does this go into effect?

**A:** The backend change is live now. Frontend must be updated ASAP to avoid 401 errors.

---

## 🆘 TROUBLESHOOTING

### Issue: Getting 401 Unauthorized errors

**Solution:**
1. Verify you're calling `/stream-token` endpoint first
2. Check JWT token in Authorization header is valid
3. Ensure SSE token is being used (not JWT token)
4. Check token hasn't expired (60 second window)

### Issue: Connection drops immediately

**Solution:**
1. Check network connectivity
2. Verify generation_id is correct
3. Ensure CORS is configured properly
4. Check browser console for detailed errors

### Issue: Token fetch fails

**Solution:**
1. Verify JWT token is valid and not expired
2. Check user has access to the generation
3. Ensure generation exists
4. Check API endpoint URL is correct

---

## 📞 SUPPORT

**Backend Team Contact:**
- Slack: #backend-team
- Email: backend@codebegen.com

**Questions?**
- Check backend docs: `docs/SECURE_SSE_IMPLEMENTATION.md`
- Review security analysis: Above in this document
- Test with example code provided

---

**Document Version:** 1.0  
**Last Updated:** October 16, 2025  
**Effective Date:** Immediate  
**Priority:** HIGH - Security Fix  
**Estimated Implementation Time:** 2-4 hours
