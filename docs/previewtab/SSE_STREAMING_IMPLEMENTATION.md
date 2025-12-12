# 🔌 SSE Streaming Implementation Guide - MVP

**Purpose**: Real-time log streaming from preview subprocess to frontend  
**Status**: Critical MVP feature  
**Implementation Time**: ~3-4 hours  
**Complexity**: Medium

---

## 📚 Table of Contents

1. [Why SSE?](#why-sse)
2. [Architecture Overview](#architecture-overview)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## 🤔 Why SSE?

### The Problem
Without streaming, users see a blank terminal for 1-2 seconds waiting for preview to start. This feels broken.

### The Solution: Server-Sent Events (SSE)
```
Subprocess output (real-time)
        ↓
Backend captures (thread-based)
        ↓
SSE endpoint streams (HTTP)
        ↓
Frontend displays (terminal UI)
        ↓
User sees startup happening in real-time
```

### SSE vs Alternatives

| Feature | Polling | SSE | WebSocket |
|---------|---------|-----|-----------|
| **Latency** | 2000ms | ~100ms | ~50ms |
| **Setup** | Trivial | Medium | Complex |
| **Browser Support** | 100% | 95% (older IE) | 95% (older IE) |
| **HTTP** | Yes | Yes | No (upgrade) |
| **Auto-reconnect** | Manual | Built-in | Manual |
| **MVP Recommended** | ❌ | ✅ | ❌ Phase 5 |

**Decision**: SSE for MVP (fast, simple) → WebSocket in Phase 5 (production-grade)

---

## 🏗️ Architecture Overview

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Generated FastAPI Backend (subprocess)                      │
│ - Uvicorn server running                                    │
│ - Outputs to stdout/stderr                                  │
│ - Example: "INFO: Application startup complete"            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ subprocess stdout/stderr
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Background Thread (read_process_output)                     │
│ - Reads line-by-line from subprocess                        │
│ - Non-blocking (uses threading)                             │
│ - Doesn't block FastAPI event loop                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ log entry dict
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ asyncio.Queue (1000 items max)                              │
│ - Buffers log entries                                       │
│ - Drops oldest if full                                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ stream_logs async generator
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ FastAPI StreamingResponse                                   │
│ - Sends SSE stream to frontend                              │
│ - Content-Type: text/event-stream                           │
│ - Keep-alive every 15 seconds                               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTP SSE stream
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Browser EventSource                                         │
│ - Receives SSE messages                                     │
│ - Parses JSON from data field                               │
│ - Auto-reconnects on disconnect                             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ onmessage event
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ React Component (PreviewTerminal)                           │
│ - Updates log state                                         │
│ - Renders in terminal UI                                    │
│ - Auto-scrolls to bottom                                    │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Thread-based capture** - Subprocess reads happen in background thread
2. **Queue buffering** - Async queue decouples reading from streaming
3. **Async database saves** - Logs saved in background, don't block stream
4. **SSE keep-alive** - 15-second keep-alive prevents connection timeouts

---

## 💻 Backend Implementation

### 1. Create PreviewLogStreamer Service

**File**: `app/services/preview_log_streamer.py`

```python
import asyncio
import threading
import subprocess
import json
import logging
from datetime import datetime
from queue import Queue
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

class PreviewLogStreamer:
    """Manages real-time log streaming from preview subprocess."""
    
    def __init__(self, preview_id: str, temp_dir: str, port: int):
        self.preview_id = preview_id
        self.temp_dir = temp_dir
        self.port = port
        self.process: subprocess.Popen = None
        self.reader_thread: threading.Thread = None
        self.running = False
        self.log_queue: Queue = Queue(maxsize=1000)
    
    async def start_preview_with_logging(self) -> subprocess.Popen:
        """
        Start Uvicorn subprocess with log streaming.
        
        CRITICAL: PYTHONUNBUFFERED=1 ensures immediate output capture.
        Without it, output is buffered and delayed.
        """
        self.running = True
        
        self.process = subprocess.Popen(
            [
                "uvicorn",
                "app.main:app",
                f"--port={self.port}",
                "--log-level=info",
                "--access-log"
            ],
            cwd=self.temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr into stdout
            text=True,
            bufsize=1,  # Line buffered
            env={
                "DATABASE_URL": "sqlite:///./preview.db",
                "PYTHONUNBUFFERED": "1"  # ← CRITICAL
            }
        )
        
        # Start reader thread
        self.reader_thread = threading.Thread(
            target=self._read_process_output,
            daemon=True
        )
        self.reader_thread.start()
        
        return self.process
    
    def _read_process_output(self):
        """Background thread that reads subprocess output."""
        try:
            while self.running and self.process and self.process.stdout:
                line = self.process.stdout.readline()
                
                if not line:
                    break
                
                # Parse log level
                level = self._extract_log_level(line)
                
                # Create log entry
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": level,
                    "message": line.strip(),
                    "source": "preview"
                }
                
                # Add to queue (drop oldest if full)
                try:
                    self.log_queue.put_nowait(log_entry)
                except:
                    try:
                        self.log_queue.get_nowait()
                        self.log_queue.put_nowait(log_entry)
                    except:
                        pass
        
        except Exception as e:
            logger.error(f"Error reading output: {e}")
    
    def _extract_log_level(self, line: str) -> str:
        """Extract log level from Uvicorn format."""
        line_upper = line.upper()
        
        if "ERROR" in line_upper or "CRITICAL" in line_upper:
            return "ERROR"
        elif "WARNING" in line_upper:
            return "WARN"
        elif "DEBUG" in line_upper:
            return "DEBUG"
        else:
            return "INFO"
    
    async def stream_logs(self) -> AsyncGenerator[str, None]:
        """SSE generator - yields log entries as they arrive."""
        log_id = 0
        no_data_count = 0
        
        while self.running:
            try:
                log_entry = self.log_queue.get(timeout=1.0)
                no_data_count = 0
                log_id += 1
                
                # SSE format: id + data
                yield f"id: {log_id}\n"
                yield f"data: {json.dumps(log_entry)}\n\n"
                
                # Save to DB (async, non-blocking)
                asyncio.create_task(self._save_log_to_db(log_entry))
                
            except:
                no_data_count += 1
                
                # Keep-alive every 15 seconds
                if no_data_count % 15 == 0:
                    yield ": keep-alive\n\n"
                
                await asyncio.sleep(0.1)
    
    async def _save_log_to_db(self, log_entry: dict):
        """Save log entry to database asynchronously."""
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
            logger.error(f"Failed to save log: {e}")
    
    async def stop(self):
        """Stop streaming and cleanup."""
        self.running = False
        
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        
        if self.reader_thread:
            self.reader_thread.join(timeout=2)


# Global registry
preview_log_streamers: dict[str, PreviewLogStreamer] = {}

def get_streamer(preview_id: str) -> PreviewLogStreamer:
    return preview_log_streamers.get(preview_id)

def register_streamer(preview_id: str, streamer: PreviewLogStreamer):
    preview_log_streamers[preview_id] = streamer

def unregister_streamer(preview_id: str):
    if preview_id in preview_log_streamers:
        del preview_log_streamers[preview_id]
```

### 2. Update Preview Service

**File**: `app/services/preview_service.py`

```python
from app.services.preview_log_streamer import (
    PreviewLogStreamer,
    register_streamer,
    unregister_streamer,
    get_streamer
)

async def launch_preview_instance(preview: PreviewInstance, generation, files):
    """Launch preview with SSE log streaming."""
    
    temp_dir = None
    streamer = None
    
    try:
        # Create temp directory
        temp_dir = create_temp_project_dir()
        write_files_to_disk(files, temp_dir)
        
        # Create and register streamer
        streamer = PreviewLogStreamer(
            preview_id=preview.id,
            temp_dir=temp_dir,
            port=preview.port
        )
        register_streamer(preview.id, streamer)
        
        # Start subprocess with logging
        process = await streamer.start_preview_with_logging()
        preview.process_id = process.pid
        
        # Health check
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
                if attempt == 2:
                    raise
        
        preview.started_at = datetime.utcnow()
        preview.status = "running"
        preview.temp_directory = temp_dir
        await db.save(preview)
        
    except Exception as e:
        if streamer:
            await streamer.stop()
            unregister_streamer(preview.id)
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise

async def stop_preview_instance(preview: PreviewInstance):
    """Stop preview and cleanup streamer."""
    
    streamer = get_streamer(preview.id)
    if streamer:
        await streamer.stop()
        unregister_streamer(preview.id)
    
    if preview.temp_directory:
        shutil.rmtree(preview.temp_directory, ignore_errors=True)
    
    preview.status = "stopped"
    preview.stopped_at = datetime.utcnow()
    await db.save(preview)
```

### 3. Add SSE Endpoint

**File**: `app/routers/preview.py`

```python
from fastapi.responses import StreamingResponse
from app.services.preview_log_streamer import get_streamer

@router.get("/generations/{generation_id}/preview/logs/stream")
async def stream_preview_logs(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stream preview logs via SSE."""
    
    preview = await db.get_active_preview(generation_id)
    if not preview:
        raise HTTPException(404, "No active preview")
    
    if preview.user_id != current_user.id:
        raise HTTPException(403, "Unauthorized")
    
    streamer = get_streamer(preview.id)
    if not streamer:
        raise HTTPException(503, "Logs not available")
    
    return StreamingResponse(
        streamer.stream_logs(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

---

## 🎨 Frontend Implementation

### 1. React Hook: usePreviewLogs

**File**: `frontend/hooks/usePreviewLogs.ts`

```typescript
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

    const eventSource = new EventSource(
      `/api/generations/${generationId}/preview/logs/stream`
    )
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      console.log('SSE connected')
      setIsConnected(true)
    }

    eventSource.onmessage = (event) => {
      try {
        const log = JSON.parse(event.data) as PreviewLog
        setLogs((prev) => [...prev, log])
      } catch (error) {
        console.error('Failed to parse log:', error)
      }
    }

    eventSource.onerror = () => {
      console.error('SSE error')
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

### 2. Terminal Component

**File**: `frontend/components/PreviewTerminal.tsx`

```typescript
import { usePreviewLogs } from '@/hooks/usePreviewLogs'
import { useEffect, useRef } from 'react'

interface PreviewTerminalProps {
  generationId: string
}

export function PreviewTerminal({ generationId }: PreviewTerminalProps) {
  const { logs, isConnected } = usePreviewLogs(generationId)
  const terminalRef = useRef<HTMLDivElement>(null)

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
    <div className="bg-gray-900 rounded-lg">
      {/* Header */}
      <div className="bg-gray-800 px-4 py-2 flex justify-between">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-400' : 'bg-red-400'
            }`}
          />
          <span>{isConnected ? 'Live' : 'Disconnected'}</span>
        </div>
      </div>

      {/* Terminal */}
      <div
        ref={terminalRef}
        className="h-64 p-4 overflow-y-auto bg-gray-950 font-mono text-sm text-white"
      >
        {logs.length === 0 && (
          <div className="text-gray-500">Waiting for logs...</div>
        )}

        {logs.map((log, idx) => (
          <div key={idx} className={`text-xs ${getLevelColor(log.level)}`}>
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

## 🧪 Testing

### Backend: Unit Test

```python
# tests/test_preview/test_log_streamer.py

@pytest.mark.asyncio
async def test_preview_log_streamer():
    """Test log streaming from subprocess."""
    
    # Create a simple test script
    test_script = '''
import sys
import time
print("Starting...")
sys.stdout.flush()
time.sleep(0.5)
print("Done!")
sys.stdout.flush()
'''
    
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, "test.py")
    with open(script_path, "w") as f:
        f.write(test_script)
    
    # Create streamer
    streamer = PreviewLogStreamer("test_preview", temp_dir, 3001)
    
    # Mock process
    import subprocess
    streamer.process = subprocess.Popen(
        ["python", script_path],
        cwd=temp_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={"PYTHONUNBUFFERED": "1"}
    )
    streamer.running = True
    
    # Start reader thread
    reader_thread = threading.Thread(
        target=streamer._read_process_output,
        daemon=True
    )
    reader_thread.start()
    
    # Give time to read output
    await asyncio.sleep(2)
    
    # Check queue has logs
    assert streamer.log_queue.qsize() > 0
    
    log = streamer.log_queue.get()
    assert log["level"] == "INFO"
    assert "Starting" in log["message"]
    
    # Cleanup
    streamer.running = False
    reader_thread.join()
```

### Frontend: Integration Test

```typescript
// frontend/hooks/__tests__/usePreviewLogs.test.ts

describe('usePreviewLogs', () => {
  it('should connect to SSE stream', async () => {
    const { result } = renderHook(() => usePreviewLogs('gen_123'))
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
  })

  it('should parse and display logs', async () => {
    const { result } = renderHook(() => usePreviewLogs('gen_123'))
    
    // Mock SSE event
    const event = new MessageEvent('message', {
      data: JSON.stringify({
        timestamp: '2025-10-20T12:20:05Z',
        level: 'INFO',
        message: 'Test log'
      })
    })
    
    // Simulate SSE message
    // ... test code
    
    await waitFor(() => {
      expect(result.current.logs.length).toBeGreaterThan(0)
    })
  })
})
```

---

## 🔧 Troubleshooting

### Issue: No logs appearing in terminal

**Checklist**:
- [ ] PYTHONUNBUFFERED=1 set in subprocess env
- [ ] subprocess stdout/stderr redirected correctly
- [ ] Reader thread running
- [ ] SSE connection established (check browser console)

**Debug**:
```python
# Add logging to _read_process_output
logger.debug(f"Read line: {line}")
logger.debug(f"Queue size: {self.log_queue.qsize()}")
```

### Issue: SSE connection drops frequently

**Causes**:
- Nginx buffering (add X-Accel-Buffering: no header)
- Idle timeout (add keep-alive `: \n\n` every 15s)
- Browser closing connection

**Solution**:
```python
# Ensure keep-alive is sent
if no_data_count % 15 == 0:
    yield ": keep-alive\n\n"
```

### Issue: Browser console shows 404 on SSE endpoint

**Check**:
- [ ] Endpoint path matches exactly
- [ ] User is authenticated
- [ ] Preview exists and is running
- [ ] Streamer registered in global dict

---

## ✅ Checklist

- [ ] PreviewLogStreamer class created
- [ ] Subprocess output capture working
- [ ] Queue buffering implemented
- [ ] SSE endpoint created
- [ ] Frontend hook created
- [ ] Terminal component created
- [ ] Tests written and passing
- [ ] Keep-alive working
- [ ] Auto-scroll working on frontend
- [ ] Error handling complete
- [ ] Logging/debugging in place

---

**Total Implementation Time**: ~3-4 hours  
**Complexity**: Medium  
**Impact on MVP**: Critical (makes preview feel professional)
