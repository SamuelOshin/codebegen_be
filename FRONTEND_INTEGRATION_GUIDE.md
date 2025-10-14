# Frontend Integration Guide: Live Code Generation Monitoring

## Overview

The CodeBegen API provides a comprehensive live communication system for monitoring code generation progress. This system offers two complementary approaches:

1. **Server-Sent Events (SSE) Streaming** - Real-time updates via persistent HTTP connections
2. **HTTP Polling Fallback** - Lightweight status checks for environments where streaming isn't available

Both approaches provide detailed progress information, error handling, and user-friendly status updates with emojis and statistics.

## API Endpoints

### Base URL
```
https://your-api-domain.com/api/v2/generation
```

### Authentication
All endpoints require JWT authentication via Bearer token:
```
Authorization: Bearer <your-jwt-token>
```

### Available Endpoints

#### 1. Start Generation
```http
POST /api/v2/generation/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "prompt": "Create a user management API with FastAPI",
  "project_id": "optional-project-id",
  "generation_mode": "auto",
  "tech_stack": "fastapi_postgres",
  "constraints": ["dockerized", "tested", "authenticated"]
}
```

**Response:**
```json
{
  "generation_id": "gen_1234567890",
  "status": "processing",
  "message": "Generation started successfully",
  "user_id": "user_123",
  "project_id": "proj_456",
  "prompt": "Create a user management API with FastAPI",
  "generation_mode": "enhanced",
  "created_at": "2025-09-23T10:30:00Z",
  "updated_at": "2025-09-23T10:30:00Z"
}
```

#### 2. Stream Progress (Real-time)
```http
GET /api/v2/generation/{generation_id}/stream
Accept: text/event-stream
Authorization: Bearer <token>
```

#### 3. Poll Status (Fallback)
```http
GET /api/v2/generation/{generation_id}/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "generation_id": "gen_1234567890",
  "status": "processing",
  "created_at": "2025-09-23T10:30:00Z",
  "updated_at": "2025-09-23T10:30:05Z",
  "progress": 0.3,
  "stage": "code_generation",
  "message": "📝 Generating API endpoints... (3/10 files)",
  "current_event": {
    "status": "processing",
    "stage": "code_generation",
    "progress": 0.3,
    "message": "📝 Generating API endpoints... (3/10 files)",
    "timestamp": 1727087405.123,
    "estimated_time_remaining": 45.2,
    "current_file": "app/routers/users.py"
  },
  "estimated_time_remaining": 45.2,
  "has_events": true
}
```

## Event Data Structures

### StreamingProgressEvent

All streaming events follow this structure:

```typescript
interface StreamingProgressEvent {
  generation_id: string;
  status: string;           // "connected" | "processing" | "completed" | "failed" | "error" | "timeout" | "disconnected"
  stage: string;            // Current processing stage
  progress: number;         // 0.0 to 1.0 progress percentage
  message: string;          // User-friendly message with emojis

  // Optional enhanced fields
  ab_group?: string;
  enhanced_features?: Record<string, boolean>;
  generation_mode?: "classic" | "enhanced" | "auto";

  // Metadata
  estimated_time_remaining?: number;  // seconds
  current_file?: string;              // Currently processing file
  partial_output?: Record<string, any>; // Partial results

  timestamp: number;  // Unix timestamp
}
```

### Status Response

The polling endpoint returns:

```typescript
interface GenerationStatusResponse {
  generation_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;    // ISO 8601 timestamp
  updated_at: string;    // ISO 8601 timestamp
  progress: number;      // 0.0 to 1.0
  stage: string;
  message: string;
  current_event?: StreamingProgressEvent;
  estimated_time_remaining?: number;
  has_events: boolean;

  // Only present for completed/failed generations
  completed_at?: string;
  error?: string;
}
```

## Progress Stages

The system reports progress through these stages:

1. **connected** - Stream connection established
2. **initializing** - Setting up generation environment
3. **schema_extraction** - 📋 Analyzing requirements and extracting schema
4. **code_generation** - 📝 Generating code files
5. **code_review** - 🔍 Reviewing and improving code quality
6. **documentation** - 📚 Generating documentation
7. **finalizing** - ✨ Finalizing and packaging results
8. **completed** - ✅ Generation finished successfully
9. **failed** - ❌ Generation failed with error

## JavaScript/TypeScript Implementation

### 1. Server-Sent Events (SSE) Streaming

```typescript
class GenerationMonitor {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectDelay = 1000; // ms

  constructor(
    private generationId: string,
    private token: string,
    private onProgress: (event: StreamingProgressEvent) => void,
    private onError: (error: string) => void,
    private onComplete: (event: StreamingProgressEvent) => void
  ) {}

  startStreaming(): void {
    const url = `/api/v2/generation/${this.generationId}/stream`;
    const headers = {
      'Authorization': `Bearer ${this.token}`
    };

    // Note: EventSource doesn't support custom headers in browsers
    // You'll need to proxy the request or use a different approach
    this.eventSource = new EventSource(url);

    this.eventSource.onmessage = (event) => {
      try {
        const progressEvent: StreamingProgressEvent = JSON.parse(event.data);
        this.onProgress(progressEvent);

        if (progressEvent.status === 'completed' || progressEvent.status === 'failed') {
          this.onComplete(progressEvent);
          this.stopStreaming();
        }
      } catch (error) {
        this.onError(`Failed to parse progress event: ${error}`);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      this.handleReconnect();
    };

    this.eventSource.onopen = () => {
      console.log('SSE connection opened');
      this.reconnectAttempts = 0;
    };
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

      setTimeout(() => {
        this.stopStreaming();
        this.startStreaming();
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      this.onError('Failed to reconnect after maximum attempts. Switching to polling...');
      this.fallbackToPolling();
    }
  }

  stopStreaming(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  private fallbackToPolling(): void {
    // Implement polling fallback (see next section)
    this.startPolling();
  }
}
```

### 2. HTTP Polling Fallback

```typescript
class GenerationPoller {
  private pollInterval: number = 2000; // 2 seconds
  private maxPolls: number = 300; // 10 minutes max
  private pollCount: number = 0;
  private timeoutId: number | null = null;

  constructor(
    private generationId: string,
    private token: string,
    private onProgress: (status: GenerationStatusResponse) => void,
    private onError: (error: string) => void,
    private onComplete: (status: GenerationStatusResponse) => void
  ) {}

  startPolling(): void {
    this.pollCount = 0;
    this.poll();
  }

  private async poll(): Promise<void> {
    if (this.pollCount >= this.maxPolls) {
      this.onError('Polling timeout - generation may still be running');
      return;
    }

    try {
      const response = await fetch(`/api/v2/generation/${this.generationId}/status`, {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        if (response.status === 404) {
          this.onError('Generation not found');
          return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const status: GenerationStatusResponse = await response.json();
      this.onProgress(status);

      if (status.status === 'completed' || status.status === 'failed') {
        this.onComplete(status);
        this.stopPolling();
        return;
      }

      this.pollCount++;
      this.timeoutId = window.setTimeout(() => this.poll(), this.pollInterval);

    } catch (error) {
      this.onError(`Polling failed: ${error}`);
      // Continue polling despite errors
      this.pollCount++;
      this.timeoutId = window.setTimeout(() => this.poll(), this.pollInterval);
    }
  }

  stopPolling(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
  }
}
```

### 3. Unified Monitor (Streaming + Polling)

```typescript
class UnifiedGenerationMonitor {
  private streamer: GenerationMonitor | null = null;
  private poller: GenerationPoller | null = null;
  private useStreaming: boolean = true;

  constructor(
    private generationId: string,
    private token: string,
    private onProgress: (event: StreamingProgressEvent | GenerationStatusResponse) => void,
    private onError: (error: string) => void,
    private onComplete: (event: StreamingProgressEvent | GenerationStatusResponse) => void
  ) {}

  start(): void {
    if (this.useStreaming && this.supportsEventSource()) {
      this.startStreaming();
    } else {
      this.startPolling();
    }
  }

  private supportsEventSource(): boolean {
    return typeof EventSource !== 'undefined';
  }

  private startStreaming(): void {
    this.streamer = new GenerationMonitor(
      this.generationId,
      this.token,
      this.onProgress,
      (error) => {
        console.warn('Streaming failed, falling back to polling:', error);
        this.useStreaming = false;
        this.startPolling();
      },
      this.onComplete
    );
    this.streamer.startStreaming();
  }

  private startPolling(): void {
    this.poller = new GenerationPoller(
      this.generationId,
      this.token,
      this.onProgress,
      this.onError,
      this.onComplete
    );
    this.poller.startPolling();
  }

  stop(): void {
    if (this.streamer) {
      this.streamer.stopStreaming();
      this.streamer = null;
    }
    if (this.poller) {
      this.poller.stopPolling();
      this.poller = null;
    }
  }
}
```

### 4. React Hook Example

```typescript
import { useState, useEffect, useRef } from 'react';

interface UseGenerationMonitorOptions {
  generationId: string | null;
  token: string;
  onComplete?: (result: GenerationStatusResponse) => void;
  onError?: (error: string) => void;
}

interface GenerationProgress {
  progress: number;
  stage: string;
  message: string;
  status: string;
  estimatedTimeRemaining?: number;
  currentFile?: string;
}

export function useGenerationMonitor({
  generationId,
  token,
  onComplete,
  onError
}: UseGenerationMonitorOptions) {
  const [progress, setProgress] = useState<GenerationProgress | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const monitorRef = useRef<UnifiedGenerationMonitor | null>(null);

  useEffect(() => {
    if (!generationId || !token) return;

    setIsLoading(true);
    setError(null);

    monitorRef.current = new UnifiedGenerationMonitor(
      generationId,
      token,
      (event) => {
        const progressData: GenerationProgress = {
          progress: event.progress,
          stage: event.stage,
          message: event.message,
          status: event.status,
          estimatedTimeRemaining: event.estimated_time_remaining || event.estimatedTimeRemaining,
          currentFile: event.current_file || event.currentFile
        };
        setProgress(progressData);
      },
      (errorMsg) => {
        setError(errorMsg);
        onError?.(errorMsg);
      },
      (result) => {
        setIsLoading(false);
        onComplete?.(result);
      }
    );

    monitorRef.current.start();

    return () => {
      monitorRef.current?.stop();
    };
  }, [generationId, token, onComplete, onError]);

  return { progress, isLoading, error };
}
```

## Error Handling

### Common Error Scenarios

1. **Authentication Errors**
   ```json
   {
     "detail": "Could not validate credentials",
     "status_code": 401
   }
   ```

2. **Generation Not Found**
   ```json
   {
     "detail": "Generation not found",
     "status_code": 404
   }
   ```

3. **Access Denied**
   ```json
   {
     "detail": "You don't have permission to view this generation",
     "status_code": 403
   }
   ```

4. **Stream Errors**
   ```json
   {
     "generation_id": "gen_123",
     "status": "error",
     "stage": "stream_error",
     "progress": 0.0,
     "message": "Stream processing error: Connection lost",
     "timestamp": 1727087405.123
   }
   ```

### Recovery Strategies

1. **Automatic Reconnection**: For streaming failures, automatically retry with exponential backoff
2. **Fallback to Polling**: When streaming fails completely, switch to HTTP polling
3. **Graceful Degradation**: Continue showing last known progress during connection issues
4. **User Notifications**: Inform users of connection issues and automatic recovery attempts

## Best Practices

### 1. Connection Management
- Always clean up EventSource connections when components unmount
- Implement proper timeout handling (30-minute limit on server)
- Use connection pooling for polling to avoid overwhelming the server

### 2. User Experience
- Show progress bars with smooth animations
- Display user-friendly messages with emojis
- Provide estimated time remaining when available
- Show current file being processed for transparency

### 3. Error Recovery
- Implement automatic fallback from streaming to polling
- Show helpful error messages with recovery suggestions
- Allow manual retry for failed operations

### 4. Performance
- Poll at reasonable intervals (2-5 seconds)
- Limit concurrent monitoring sessions
- Cache progress state locally to handle reconnections

### 5. Security
- Never expose JWT tokens in client-side logs
- Validate all event data before processing
- Use HTTPS for all API communications

## Browser Compatibility

### Server-Sent Events Support
- Chrome: Full support
- Firefox: Full support
- Safari: Full support (iOS 10+)
- Edge: Full support

### Fallback Strategy
For browsers without SSE support, automatically use HTTP polling.

## Testing

### Mock Data for Development

```typescript
const mockProgressEvents: StreamingProgressEvent[] = [
  {
    generation_id: "gen_test",
    status: "processing",
    stage: "schema_extraction",
    progress: 0.1,
    message: "📋 Analyzing requirements...",
    timestamp: Date.now() / 1000
  },
  {
    generation_id: "gen_test",
    status: "processing",
    stage: "code_generation",
    progress: 0.6,
    message: "📝 Generating API endpoints... (5/8 files)",
    timestamp: Date.now() / 1000,
    current_file: "app/models/user.py",
    estimated_time_remaining: 30
  },
  {
    generation_id: "gen_test",
    status: "completed",
    stage: "finished",
    progress: 1.0,
    message: "✅ Generation completed successfully!",
    timestamp: Date.now() / 1000
  }
];
```

This comprehensive system ensures your frontend can reliably monitor code generation progress with excellent user experience, automatic error recovery, and graceful fallbacks.</content>
<parameter name="filePath">c:\Users\PC\Documents\CODEBEGEN(NEW)\codebegen_be\FRONTEND_INTEGRATION_GUIDE.md