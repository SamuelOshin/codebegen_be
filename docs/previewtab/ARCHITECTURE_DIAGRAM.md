# 🎨 Preview Tab with SSE - Visual Architecture Guide

**Purpose**: Visual reference for SSE streaming implementation  
**Best For**: Quick understanding of data flow and components

---

## 🏗️ Complete MVP Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────┐         ┌──────────────────────────────┐    │
│  │ Preview Component   │         │  PreviewTerminal Component   │    │
│  ├─────────────────────┤         ├──────────────────────────────┤    │
│  │ • Launch button     │         │ • Terminal UI (dark bg)      │    │
│  │ • Status display    │◄────────┤ • Log display (colored)      │    │
│  │ • Endpoint testing  │         │ • Connection status          │    │
│  └─────────────────────┘         │ • Auto-scroll                │    │
│                                  └──────────────────────────────┘    │
│                                           ▲                          │
│                                           │ data: {...}             │
│                                      text/event-stream               │
│                                           │                          │
└───────────────────────────────────────────┼──────────────────────────┘
                                            │
                                   ┌────────┴────────┐
                                   │  HTTP + SSE     │
                                   │  Keep-alive: 15s│
                                   └────────┬────────┘
                                            │
┌───────────────────────────────────────────┼──────────────────────────┐
│                       BACKEND (FastAPI)   │                          │
├────────────────────────────────────────────┼──────────────────────────┤
│                                            │                          │
│  ┌──────────────────────────────────────────────┐                    │
│  │  Preview Router (/preview/logs/stream)       │                    │
│  ├──────────────────────────────────────────────┤                    │
│  │ GET /generations/{id}/preview/logs/stream    │                    │
│  │ Returns: StreamingResponse(media_type=SSE)   │                    │
│  └──────────────────────────────────────────────┘                    │
│            ▲                                                          │
│            │ Calls stream_logs() generator                           │
│            │                                                          │
│  ┌──────────┴──────────────────────────────────┐                    │
│  │  PreviewLogStreamer Service                 │                    │
│  ├──────────────────────────────────────────────┤                    │
│  │ • stream_logs() - Async SSE generator        │                    │
│  │ • _read_process_output() - Background thread│                    │
│  │ • _save_log_to_db() - Async DB writes       │                    │
│  └──────────────────────────────────────────────┘                    │
│            ▲                                                          │
│            │ Gets logs from queue                                    │
│            │                                                          │
│  ┌──────────┴──────────────────────────────────┐                    │
│  │  asyncio.Queue (maxsize=1000)               │                    │
│  ├──────────────────────────────────────────────┤                    │
│  │ Buffers log entries                         │                    │
│  │ Drops oldest if full                        │                    │
│  └──────────────────────────────────────────────┘                    │
│            ▲                                                          │
│            │ Puts logs in queue                                      │
│            │                                                          │
│  ┌──────────┴──────────────────────────────────┐                    │
│  │  Background Reader Thread                   │                    │
│  ├──────────────────────────────────────────────┤                    │
│  │ • Reads subprocess stdout line-by-line      │                    │
│  │ • Extracts log level (ERROR, WARN, INFO)   │                    │
│  │ • Creates log entry dict                    │                    │
│  │ • Non-blocking (doesn't block event loop)   │                    │
│  └──────────────────────────────────────────────┘                    │
│            ▲                                                          │
│            │ subprocess.stdout (line-buffered)                       │
│            │ PYTHONUNBUFFERED=1                                      │
│            │                                                          │
└────────────┼───────────────────────────────────────────────────────────┘
             │
┌────────────┴─────────────────────────────────────────────────────────┐
│            GENERATED FASTAPI BACKEND (subprocess)                    │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  subprocess.Popen(                                                    │
│    ["uvicorn", "app.main:app", "--port=3001"],                       │
│    stdout=subprocess.PIPE,                                           │
│    stderr=subprocess.STDOUT,                                         │
│    text=True,                                                        │
│    bufsize=1,  # Line buffered                                       │
│    env={"PYTHONUNBUFFERED": "1"}  # ← CRITICAL                       │
│  )                                                                    │
│                                                                       │
│  Outputs:                                                            │
│  - "INFO: Application startup complete"                             │
│  - "INFO: GET /health 200 OK in 15ms"                               │
│  - "ERROR: Connection failed"                                       │
│  - etc.                                                             │
│                                                                       │
│  Database: sqlite:///./preview.db                                    │
│                                                                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow: Step by Step

### 1️⃣ User Clicks "Preview" Button

```
User UI
  │
  ├─ POST /generations/{id}/preview/launch
  │     └─ Backend validates, creates PreviewInstance
  │     └─ Creates PreviewLogStreamer
  │     └─ Starts subprocess
  │
  ├─ GET /generations/{id}/preview/logs/stream
  │     └─ Opens EventSource connection
  │     └─ Connection stays open
  └─ Waits for logs...
```

### 2️⃣ Subprocess Starts and Outputs Logs

```
Generated Backend (uvicorn)
  │
  ├─ Output: "INFO: Starting server..."
  │     └─ Goes to stdout (line-buffered)
  │
  ├─ Output: "INFO: Uvicorn running on 127.0.0.1:3001"
  │     └─ Goes to stdout immediately (PYTHONUNBUFFERED=1)
  │
  └─ Output: "ERROR: Database failed"
      └─ Goes to stdout (we merged stderr there)
```

### 3️⃣ Background Thread Captures Output

```
Background Reader Thread (daemon)
  │
  ├─ Reads line: "INFO: Starting server..."
  │     ├─ Extracts level: "INFO"
  │     ├─ Creates dict: {timestamp, level, message, source}
  │     └─ Puts in queue.put_nowait(log_entry)
  │
  ├─ Reads line: "INFO: Uvicorn running..."
  │     ├─ Extracts level: "INFO"
  │     ├─ Creates dict: {...}
  │     └─ Puts in queue.put_nowait(log_entry)
  │
  └─ Continues reading...
```

### 4️⃣ SSE Endpoint Streams Logs

```
SSE Generator (stream_logs)
  │
  ├─ Gets log from queue.get(timeout=1.0)
  │     ├─ Increments log_id: 1, 2, 3...
  │     ├─ Yields: "id: 1\n"
  │     ├─ Yields: "data: {json}\n\n"
  │     └─ Calls: _save_log_to_db() (async, non-blocking)
  │
  ├─ No log for 1+ seconds
  │     ├─ Keep-alive every 15 seconds
  │     ├─ Yields: ": keep-alive\n\n"
  │     └─ Prevents timeout
  │
  └─ Continues streaming...
```

### 5️⃣ Frontend Receives SSE Stream

```
Browser EventSource
  │
  ├─ onopen: Connection established ✓
  │
  ├─ onmessage: Receives data
  │     ├─ Parses JSON: {timestamp, level, message}
  │     ├─ Updates logs state: setLogs([...prev, log])
  │     └─ React re-renders
  │
  ├─ Terminal Component Updates
  │     ├─ New log div created
  │     ├─ Color based on level (red/yellow/green)
  │     ├─ Auto-scroll to bottom
  │     └─ User sees: "[12:20:05] INFO: Starting server..."
  │
  └─ Connection stays open...
```

---

## ⚙️ Key Components

### Backend Components

```python
┌─────────────────────────────────────────┐
│ app/services/preview_log_streamer.py    │
├─────────────────────────────────────────┤
│                                         │
│  class PreviewLogStreamer:              │
│  ├── start_preview_with_logging()       │
│  │   └─ Starts subprocess               │
│  │   └─ Starts reader thread            │
│  │                                      │
│  ├── _read_process_output()             │
│  │   └─ Background thread (daemon)      │
│  │   └─ Reads subprocess output         │
│  │   └─ Puts in queue                   │
│  │                                      │
│  ├── _extract_log_level()               │
│  │   └─ Parses log level from output    │
│  │                                      │
│  ├── stream_logs()                      │
│  │   └─ Async generator                 │
│  │   └─ Yields SSE format               │
│  │                                      │
│  ├── _save_log_to_db()                  │
│  │   └─ Async database write            │
│  │   └─ Fire-and-forget                 │
│  │                                      │
│  └── stop()                             │
│      └─ Cleanup                         │
│                                         │
│  # Global registry                      │
│  preview_log_streamers = {}             │
│  get_streamer(id)                       │
│  register_streamer(id, streamer)        │
│  unregister_streamer(id)                │
│                                         │
└─────────────────────────────────────────┘
```

### Frontend Components

```typescript
┌─────────────────────────────────────────┐
│ frontend/hooks/usePreviewLogs.ts        │
├─────────────────────────────────────────┤
│                                         │
│  function usePreviewLogs(generationId)  │
│  ├── EventSource connection             │
│  ├── onopen → setIsConnected(true)      │
│  ├── onmessage → parse JSON + setState  │
│  ├── onerror → close connection         │
│  └── cleanup on unmount                 │
│                                         │
│  Returns: { logs, isConnected }         │
│                                         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ frontend/components/PreviewTerminal.tsx │
├─────────────────────────────────────────┤
│                                         │
│  function PreviewTerminal(props)        │
│  ├── usePreviewLogs hook                │
│  ├── Connection status indicator        │
│  ├── Terminal container (dark bg)       │
│  ├── Log entries with coloring:         │
│  │   - ERROR: red                       │
│  │   - WARN: yellow                     │
│  │   - INFO: green                      │
│  │   - DEBUG: gray                      │
│  ├── Auto-scroll to bottom              │
│  └── "Waiting for logs..." placeholder  │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🔑 Critical Implementation Details

### 1. PYTHONUNBUFFERED=1

**Why**: Without it, Python buffers output, logs arrive delayed

```python
# ❌ Without PYTHONUNBUFFERED
process = subprocess.Popen([...], env={})
# Logs arrive in 1-2 second batches

# ✅ With PYTHONUNBUFFERED
process = subprocess.Popen([...], env={"PYTHONUNBUFFERED": "1"})
# Logs arrive immediately, line-by-line
```

### 2. Line Buffering (bufsize=1)

**Why**: Ensures subprocess output is line-buffered, not full buffered

```python
# ✅ Line buffered - immediate per-line output
process = subprocess.Popen([...], bufsize=1, ...)

# ❌ Full buffered - waits for buffer to fill
process = subprocess.Popen([...], bufsize=-1, ...)
```

### 3. Thread-Based Reading

**Why**: Non-blocking, doesn't freeze FastAPI event loop

```python
# ✅ Background thread reads (non-blocking)
reader_thread = threading.Thread(
    target=self._read_process_output,
    daemon=True
)
reader_thread.start()

# ❌ Blocking read in event loop (freezes app)
while True:
    line = process.stdout.readline()  # Blocks!
```

### 4. Queue Buffering

**Why**: Decouples reading speed from streaming speed

```python
# Queue buffers up to 1000 log entries
self.log_queue = Queue(maxsize=1000)

# If queue full, drop oldest
if queue.full():
    queue.get_nowait()
    queue.put_nowait(new_entry)
```

### 5. SSE Format

**Why**: Strict format required by browser EventSource API

```
# ✅ Correct SSE format
id: 1
data: {"timestamp": "...", "message": "..."}

id: 2
data: {"timestamp": "...", "message": "..."}

: keep-alive
(blank line ends each message)

# ❌ Wrong format
{"timestamp": "...", "message": "..."}
```

### 6. Keep-Alive

**Why**: Prevents connection timeout after 60+ seconds of inactivity

```python
# Every 15 seconds of no logs, send keep-alive
if no_data_count % 15 == 0:
    yield ": keep-alive\n\n"
```

---

## 🎯 Event Timeline: Launch to Complete

```
t=0ms: User clicks "Preview" button
       ├─ POST /preview/launch
       └─ EventSource opened

t=50ms: Backend starts subprocess
        ├─ PreviewLogStreamer created
        ├─ Reader thread started
        └─ Queue initialized

t=100ms: Uvicorn startup logs appear
         ├─ Reader thread captures "INFO: Starting..."
         ├─ Puts in queue
         ├─ SSE generator yields
         └─ Frontend receives

t=150ms: Frontend displays first log
         ├─ React state updated
         ├─ PreviewTerminal re-renders
         ├─ User sees: "[12:20:05] INFO: Starting..."
         └─ Connection status: "Live"

t=1000ms: More logs appear
          ├─ "INFO: Uvicorn running on 127.0.0.1:3001"
          ├─ Frontend displays
          └─ User sees startup happening

t=1500ms: Health check passes
          ├─ Backend marks preview as "running"
          ├─ User can now test endpoints
          └─ Terminal shows "Listening..."

...

t=7200000ms: User stops preview
             ├─ DELETE /preview
             ├─ Streamer stops
             ├─ Subprocess killed
             ├─ SSE connection closes
             └─ Terminal shows "Disconnected"
```

---

## 🧪 Testing Checklist

### Backend Tests
- [ ] Subprocess starts and outputs logs
- [ ] Reader thread captures all output
- [ ] Queue handles burst logs
- [ ] SSE generator yields correctly
- [ ] Keep-alive sent every 15s
- [ ] Database saves non-blocking
- [ ] Streamer cleanup works

### Frontend Tests
- [ ] EventSource connects
- [ ] Logs parsed correctly
- [ ] Connection status updates
- [ ] Auto-scroll works
- [ ] Log colors correct
- [ ] Reconnect on disconnect
- [ ] Cleanup on unmount

### Integration Tests
- [ ] Launch → stream → stop
- [ ] Multiple simultaneous previews
- [ ] Connection drop/reconnect
- [ ] Large log volumes
- [ ] Special characters in logs

---

## 🚀 Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Stream Latency** | ~50-100ms | Time from log output to frontend display |
| **Memory per stream** | ~5MB | Queue buffer + connection overhead |
| **CPU overhead** | <1% | One thread per stream |
| **Connection timeout** | 60+ seconds | With keep-alive every 15s |
| **Max concurrent streams** | 100+ | Limited by server resources |
| **Queue size** | 1000 entries | ~5MB buffer |
| **Keep-alive interval** | 15 seconds | Adjustable |

---

## ✅ Deployment Checklist

- [ ] PYTHONUNBUFFERED=1 in env
- [ ] X-Accel-Buffering: no header (Nginx)
- [ ] Cache-Control: no-cache header
- [ ] Connection: keep-alive header
- [ ] SSE content-type correct
- [ ] Reader thread cleanup on stop
- [ ] Queue properly drained
- [ ] Database connection pooling
- [ ] Logging configured
- [ ] Error handling comprehensive

---

**This visual guide complements the code documentation. Use together for complete understanding!**
