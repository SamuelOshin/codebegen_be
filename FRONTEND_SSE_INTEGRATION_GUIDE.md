# Frontend SSE Integration Guide for Iteration

**Date:** October 17, 2025
**Version:** 1.0
**Applies to:** Iteration feature with live progress updates

---

## Overview

The backend now supports **Server-Sent Events (SSE)** for real-time progress updates during iteration generation. This replaces the previous behavior where the frontend would show immediate failure and lose all progress data.

### Key Improvements

- ✅ **Live Progress Updates**: Frontend receives real-time updates during 2-minute generation
- ✅ **Incremental File Saving**: Files are saved phase-by-phase, preventing data loss
- ✅ **Better UX**: Users see actual progress instead of "failed" status
- ✅ **Error Recovery**: Partial results available even if generation fails

---

## SSE Endpoint

### URL
```
GET /generations/{generation_id}/stream
```

### Authentication
- **Header**: `Authorization: Bearer {token}`
- **Token**: Must be a valid SSE token obtained from generation start

### Response Format
- **Content-Type**: `text/event-stream`
- **Format**: Server-Sent Events with JSON data
- **Connection**: Keep-alive with no caching

---

## Event Flow for Iteration

### 1. Start Iteration Request
```javascript
// POST /generations/iterate
const response = await fetch('/generations/iterate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    parent_generation_id: "e96b74bc-aba8-4837-bb43-237fd687d18b",
    modification_prompt: "Add user authentication and improve error handling"
  })
});

const { generation_id } = await response.json();
```

### 2. Immediately Connect to SSE Stream
```javascript
// Connect to SSE stream immediately after getting generation_id
const eventSource = new EventSource(
  `/generations/${generation_id}/stream?token=${sseToken}`,
  {
    withCredentials: true
  }
);
```

### 3. Handle SSE Events
```javascript
eventSource.onmessage = (event) => {
  try {
    const data = JSON.parse(event.data);
    handleIterationEvent(data);
  } catch (error) {
    console.error('Failed to parse SSE event:', error);
  }
};

eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);
  // Handle connection errors gracefully
};
```

---

## Event Types and Data Structure

All events follow the `StreamingProgressEvent` schema:

```typescript
interface StreamingProgressEvent {
  generation_id: string;
  status: string;           // "processing" | "completed" | "failed"
  stage: string;            // Current phase/stage
  progress: number;         // 0.0 to 1.0 (percentage)
  message: string;          // Human-readable message

  // Optional fields
  ab_group?: string;
  enhanced_features?: Record<string, boolean>;
  generation_mode?: "classic" | "enhanced";
  estimated_time_remaining?: number;
  current_file?: string;
  partial_output?: Record<string, any>;
  phase_info?: PhaseInfo;   // For phased generation

  timestamp: number;
}

interface PhaseInfo {
  total_phases: number;
  current_phase: number;
  entities_count: number;
  phase?: number;           // Current phase number
  name?: string;            // Phase name
  files_generated?: number; // Files in this phase
  total_files?: number;     // Total files so far
}
```

---

## Iteration Event Sequence

### Phase 1: Initialization (0-5%)
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "processing",
  "stage": "initializing",
  "progress": 0.1,
  "message": "Starting classic generation...",
  "generation_mode": "classic",
  "timestamp": 1760660674.205
}
```

### Phase 2: Code Generation Started (5-10%)
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "processing",
  "stage": "code_generation",
  "progress": 0.3,
  "message": "Generating code using classic AI pipeline...",
  "generation_mode": "classic",
  "timestamp": 1760660674.305
}
```

### Phase 3: Phased Generation Started (5%)
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "processing",
  "stage": "phased_generation_started",
  "progress": 0.05,
  "message": "Starting phased generation for 1 entities",
  "generation_mode": "classic",
  "phase_info": {
    "total_phases": 6,
    "current_phase": 0,
    "entities_count": 1
  },
  "timestamp": 1760660674.500
}
```

### Phase 4: Core Infrastructure Complete (20%)
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "processing",
  "stage": "phase_1_complete",
  "progress": 0.2,
  "message": "Phase 1 complete: Generated 5 core infrastructure files",
  "generation_mode": "classic",
  "phase_info": {
    "phase": 1,
    "name": "Core Infrastructure",
    "files_generated": 5,
    "total_files": 5
  },
  "timestamp": 1760660674.800
}
```

### Phase 5: Entity Processing (20-80%)
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "processing",
  "stage": "phase_2_complete",
  "progress": 0.4,
  "message": "Phase 2 complete: Generated 4 User entity files",
  "generation_mode": "classic",
  "phase_info": {
    "phase": 2,
    "name": "User Entity",
    "files_generated": 4,
    "total_files": 9
  },
  "timestamp": 1760660675.200
}
```

### Phase 6: Support Files (80-90%)
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "processing",
  "stage": "phase_5_complete",
  "progress": 0.85,
  "message": "Phase 5 complete: Generated 5 support files",
  "generation_mode": "classic",
  "phase_info": {
    "phase": 5,
    "name": "Support Files",
    "files_generated": 5,
    "total_files": 14
  },
  "timestamp": 1760660675.800
}
```

### Phase 7: Main Application (90-95%)
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "processing",
  "stage": "phase_6_complete",
  "progress": 0.95,
  "message": "Phase 6 complete: Generated 2 main application files",
  "generation_mode": "classic",
  "phase_info": {
    "phase": 6,
    "name": "Main Application",
    "files_generated": 2,
    "total_files": 16
  },
  "timestamp": 1760660676.000
}
```

### Phase 8: File Management (95-98%)
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "processing",
  "stage": "file_management",
  "progress": 0.97,
  "message": "Organizing and saving files...",
  "generation_mode": "classic",
  "timestamp": 1760660676.100
}
```

### Phase 9: Quality Assessment (98-100%)
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "processing",
  "stage": "quality_assessment",
  "progress": 0.99,
  "message": "Running quality assessment...",
  "generation_mode": "classic",
  "timestamp": 1760660676.200
}
```

### Phase 10: Completion (100%)
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "completed",
  "stage": "completed",
  "progress": 1.0,
  "message": "Iteration completed successfully with 16 files",
  "generation_mode": "classic",
  "timestamp": 1760660676.300
}
```

---

## Error Handling Events

### Validation Warning
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "processing",
  "stage": "validation",
  "progress": 0.97,
  "message": "⚠️ Warning: Expected ~14 files, got 12. Some parent files may be missing.",
  "generation_mode": "classic",
  "warning_type": "data_loss_detection",
  "parent_file_count": 14,
  "new_file_count": 12,
  "timestamp": 1760660676.250
}
```

### Generation Failed
```json
{
  "generation_id": "e96b74bc-aba8-4837-bb43-237fd687d18b",
  "status": "failed",
  "stage": "error",
  "progress": 0.0,
  "message": "Classic generation failed: 'FileManager' object has no attribute 'create_generation_zip'",
  "generation_mode": "classic",
  "error": "'FileManager' object has no attribute 'create_generation_zip'",
  "timestamp": 1760660676.400
}
```

---

## Frontend Implementation

### React Hook Example
```javascript
import { useState, useEffect, useRef } from 'react';

function useIterationProgress(generationId, sseToken) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('pending');
  const [message, setMessage] = useState('');
  const [phaseInfo, setPhaseInfo] = useState(null);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    if (!generationId || !sseToken) return;

    // Connect to SSE stream
    const eventSource = new EventSource(
      `/generations/${generationId}/stream?token=${sseToken}`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        setProgress(data.progress * 100); // Convert to percentage
        setStatus(data.status);
        setMessage(data.message);

        if (data.phase_info) {
          setPhaseInfo(data.phase_info);
        }

        // Handle completion
        if (data.status === 'completed') {
          eventSource.close();
          // Redirect to results page or show success
        }

        // Handle errors
        if (data.status === 'failed') {
          eventSource.close();
          // Show error message
        }

      } catch (error) {
        console.error('SSE parsing error:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      setStatus('error');
      setMessage('Connection lost');
    };

    eventSourceRef.current = eventSource;

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [generationId, sseToken]);

  return { progress, status, message, phaseInfo };
}
```

### Vue.js Composition API Example
```javascript
import { ref, onMounted, onUnmounted } from 'vue';

export function useIterationProgress(generationId, sseToken) {
  const progress = ref(0);
  const status = ref('pending');
  const message = ref('');
  const phaseInfo = ref(null);
  let eventSource = null;

  const connect = () => {
    if (!generationId || !sseToken) return;

    eventSource = new EventSource(
      `/generations/${generationId}/stream?token=${sseToken}`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        progress.value = data.progress * 100;
        status.value = data.status;
        message.value = data.message;

        if (data.phase_info) {
          phaseInfo.value = data.phase_info;
        }

      } catch (error) {
        console.error('SSE parsing error:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      status.value = 'error';
      message.value = 'Connection lost';
    };
  };

  const disconnect = () => {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  };

  onMounted(() => connect());
  onUnmounted(() => disconnect());

  return {
    progress: readonly(progress),
    status: readonly(status),
    message: readonly(message),
    phaseInfo: readonly(phaseInfo),
    disconnect
  };
}
```

### UI Progress Bar Component
```jsx
function IterationProgress({ generationId, sseToken }) {
  const { progress, status, message, phaseInfo } = useIterationProgress(generationId, sseToken);

  return (
    <div className="iteration-progress">
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="progress-info">
        <div className="status">
          {status === 'processing' && <Spinner />}
          {status === 'completed' && <CheckIcon />}
          {status === 'failed' && <ErrorIcon />}
          <span>{message}</span>
        </div>

        {phaseInfo && (
          <div className="phase-details">
            <span>Phase {phaseInfo.phase}/{phaseInfo.total_phases}</span>
            <span>{phaseInfo.name}</span>
            <span>{phaseInfo.total_files} files generated</span>
          </div>
        )}

        <div className="progress-text">
          {Math.round(progress)}% complete
        </div>
      </div>
    </div>
  );
}
```

---

## Error Handling

### Connection Errors
```javascript
eventSource.onerror = (error) => {
  console.error('SSE connection failed:', error);

  // Try to reconnect with exponential backoff
  setTimeout(() => {
    console.log('Attempting to reconnect...');
    connectToSSE();
  }, 2000);
};
```

### Timeout Handling
- SSE stream automatically times out after 5 minutes of no events
- Frontend should handle timeout gracefully
- Show appropriate error message to user

### Event Parsing Errors
```javascript
try {
  const data = JSON.parse(event.data);
  // Process event
} catch (error) {
  console.warn('Invalid SSE event data:', event.data);
  // Continue listening for valid events
}
```

---

## Best Practices

### 1. Immediate Connection
```javascript
// Connect to SSE immediately after starting iteration
const startIteration = async () => {
  const response = await fetch('/generations/iterate', {/*...*/});
  const { generation_id, sse_token } = await response.json();

  // Connect immediately - don't wait for user navigation
  connectToProgressStream(generation_id, sse_token);

  // Navigate to progress page
  navigate(`/generation/${generation_id}/progress`);
};
```

### 2. Connection Management
```javascript
// Clean up connections when component unmounts
useEffect(() => {
  return () => {
    if (eventSource) {
      eventSource.close();
    }
  };
}, []);
```

### 3. Progress State Management
```javascript
// Store progress in component state
const [iterationState, setIterationState] = useState({
  status: 'pending',     // 'pending' | 'processing' | 'completed' | 'failed'
  progress: 0,           // 0-100
  message: '',
  phaseInfo: null,
  error: null
});
```

### 4. User Feedback
- Show progress bar with percentage
- Display current phase information
- Provide estimated time remaining (if available)
- Show file counts as they increase
- Handle errors gracefully with retry options

---

## Migration from Old Behavior

### Before (Broken)
```javascript
// Old behavior - immediate failure
const startIteration = async () => {
  try {
    const response = await fetch('/generations/iterate', {/*...*/});
    // User sees "success" but actually failed
    navigate('/success');
  } catch (error) {
    // Show error immediately
    showError('Iteration failed');
  }
};
```

### After (Working)
```javascript
// New behavior - real-time progress
const startIteration = async () => {
  const response = await fetch('/generations/iterate', {/*...*/});
  const { generation_id, sse_token } = await response.json();

  // Connect to live progress updates
  connectToSSE(generation_id, sse_token);

  // Show progress page immediately
  navigate(`/iteration/${generation_id}/progress`);
};
```

---

## Testing

### Manual Testing Steps
1. Start iteration on existing generation
2. Verify SSE connection established
3. Monitor progress events in browser dev tools
4. Verify progress bar updates correctly
5. Check that files are saved incrementally
6. Test error scenarios (network disconnect, server errors)

### Automated Testing
```javascript
// Mock SSE events for testing
const mockEvents = [
  { status: 'processing', stage: 'phased_generation_started', progress: 0.05 },
  { status: 'processing', stage: 'phase_1_complete', progress: 0.2 },
  // ... more events
];

mockEvents.forEach(event => {
  eventSource.onmessage({ data: JSON.stringify(event) });
});
```

---

## Troubleshooting

### Common Issues

**SSE Connection Fails**
- Check `sse_token` is valid and not expired
- Verify CORS settings allow EventSource
- Check network connectivity

**Events Not Received**
- Verify `generation_id` matches the iteration request
- Check server logs for event emission
- Ensure frontend is listening on correct endpoint

**Progress Bar Not Updating**
- Verify event parsing logic
- Check that `progress` field is converted correctly (0.0-1.0 → 0-100)
- Ensure component re-renders on state changes

**Connection Drops**
- Implement reconnection logic with backoff
- Handle network interruptions gracefully
- Show appropriate loading states

---

## API Reference

### SSE Token
- **Endpoint**: `POST /generations/iterate`
- **Response**: Includes `sse_token` for stream authentication
- **Validity**: Token expires when stream closes or after timeout

### Stream Format
```
data: {"generation_id":"...","status":"processing",...}\n\n
data: {"generation_id":"...","status":"completed",...}\n\n
```

### Event Fields
- `generation_id`: UUID of the generation
- `status`: Current status (`processing`, `completed`, `failed`)
- `stage`: Current processing stage
- `progress`: Progress percentage (0.0 to 1.0)
- `message`: Human-readable status message
- `timestamp`: Unix timestamp

---

**Status:** ✅ Production Ready  
**Compatibility:** Backward compatible with existing iterations  
**Performance:** Minimal overhead, real-time updates  
**Reliability:** Automatic reconnection, error recovery