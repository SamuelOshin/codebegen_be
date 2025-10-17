# SSE Connection Established But No Events Received - Debug Plan

## Problem

- ✅ Frontend successfully connects to SSE (sees "SSE connection established")
- ✅ Backend accepts the connection (no 422/404 errors)
- ❌ NO progress events are received by frontend during entire generation
- ❌ Generation completes on backend but frontend never sees updates

## Backend Logs Show

```
INFO: SSE stream started for user ..., generation ...
INFO: Starting phased generation for 3 entities
INFO: Phase 1: Core infrastructure
INFO: Saved 2 files from Phase 1
... (generation happens successfully)
```

But NO logs of SSE events being sent!

## Root Cause Analysis

The SSE endpoint reads from `generation_events[generation_id]`:

```python
# In stream_generation_progress()
async def event_stream():
    while True:
        if generation_id in generation_events:
            events = generation_events[generation_id]
            for event in events[last_event_index:]:
                # Send event to frontend
                yield f"data: {event.json()}\\n\\n"
```

But the `_emit_event` function just appends to the list:

```python
async def _emit_event(generation_id: str, event_data: Dict[str, Any]):
    if generation_id not in generation_events:
        generation_events[generation_id] = []
    generation_events[generation_id].append(event_data)
```

##  The Problem

**The generation happens in a BACKGROUND TASK**, but the SSE stream is polling the `generation_events` dictionary.

Events are being added to `generation_events[generation_id]` by:
1. `_process_classic_generation()` (background task)
2. Which calls `ai_orchestrator.process_generation()` 
3. Which calls `provider.generate_code()` with `event_callback=_emit_event`
4. Which creates `GeminiPhasedGenerator(event_callback=_emit_event)`
5. Which calls `await self._emit_event({...})`

**BUT**: The phased generator's `_emit_event` method might not be calling the router's `_emit_event` properly!

## Verification Steps

### Step 1: Check if router _emit_event is being called

Add logging to `app/routers/generations.py`:

```python
async def _emit_event(generation_id: str, event_data: Dict[str, Any]):
    """Emit an event for streaming"""
    logger.info(f"🔔 [_emit_event] generation_id={generation_id}, stage={event_data.get('stage')}, progress={event_data.get('progress')}")  # ADD THIS
    
    if generation_id not in generation_events:
        generation_events[generation_id] = []
        logger.info(f"📝 [_emit_event] Created new event list for {generation_id}")  # ADD THIS
    
    event_data["timestamp"] = time.time()
    generation_events[generation_id].append(event_data)
    
    logger.info(f"📊 [_emit_event] Total events for {generation_id}: {len(generation_events[generation_id])}")  # ADD THIS
```

### Step 2: Check if SSE loop is reading events

Add logging to the SSE event_stream function in `app/routers/generations.py`:

```python
async def event_stream():
    last_event_index = 0
    max_empty_polls = 120
    empty_poll_count = 0
    
    logger.info(f"📡 [SSE] Stream started for generation {generation_id}")  # ADD THIS
    
    try:
        # ... initial event sending ...
        
        while True:
            try:
                # Check if there are new events
                if generation_id in generation_events:
                    events = generation_events[generation_id]
                    
                    logger.info(f"📊 [SSE] Found {len(events)} total events, last_index={last_event_index}")  # ADD THIS
                    
                    # Reset empty poll counter when events exist
                    empty_poll_count = 0
                    
                    # Send new events
                    for event in events[last_event_index:]:
                        logger.info(f"📤 [SSE] Sending event: stage={event.get('stage')}, progress={event.get('progress')}")  # ADD THIS
                        
                        unified_event = StreamingProgressEvent(...)
                        yield f"data: {unified_event.json()}\\n\\n"
                        last_event_index += 1
                else:
                    logger.warning(f"⚠️  [SSE] No events found for {generation_id} (poll #{empty_poll_count})")  # ADD THIS
                    empty_poll_count += 1
```

### Step 3: Verify GeminiPhasedGenerator is calling callback

Check `app/services/llm_providers/gemini_phased_generator.py`:

```python
async def _emit_event(self, event_data: Dict[str, Any]) -> None:
    """Emit event to frontend if callback is available"""
    logger.info(f"🎯 [PhasedGen] Attempting to emit event: stage={event_data.get('stage')}")  # ADD THIS
    
    if self.event_callback and self.generation_id:
        try:
            logger.info(f"✅ [PhasedGen] Calling event_callback for {self.generation_id}")  # ADD THIS
            await self.event_callback(self.generation_id, event_data)
            logger.info(f"✅ [PhasedGen] Event callback completed")  # ADD THIS
        except Exception as e:
            logger.warning(f"Failed to emit event: {e}")
    else:
        logger.warning(f"⚠️  [PhasedGen] No callback or generation_id! callback={self.event_callback is not None}, gen_id={self.generation_id}")  # ADD THIS
```

## Expected vs Actual

### Expected Flow:
1. Frontend connects to SSE → Backend accepts connection
2. Background task starts generation → Calls `_emit_event()`
3. Events added to `generation_events[gen_id]` → SSE loop reads and sends events
4. Frontend receives events → Updates UI with progress

### Actual Flow (Suspected):
1. Frontend connects to SSE → ✅ Backend accepts connection
2. Background task starts generation → ❓ Calls `_emit_event()`?
3. Events added to `generation_events[gen_id]`? → ❌ SSE loop finds no events
4. Frontend receives NO events → ❌ UI stuck on "connecting"

## Most Likely Issues

### Issue #1: event_callback is None
The callback might not be passed properly through the chain:
- `_process_classic_generation(...)` calls `ai_orchestrator.process_generation(..., event_callback=_emit_event)`
- But maybe `ai_orchestrator` doesn't pass it to the provider?

### Issue #2: generation_id mismatch
The `generation_id` used to emit events might be different from the one used in SSE connection.

### Issue #3: Background task not awaited
The background task might be running but not actually calling the callback.

### Issue #4: Events emitted BEFORE SSE connection
If events are emitted very quickly (before SSE connects), they might be missed.

## Quick Fix to Test

Add this temporary fix to see if events are being stored:

In `app/routers/generations.py`, after the SSE connection is established, add a test event:

```python
async def event_stream():
    last_event_index = 0
    
    # Send initial connection event
    initial_event = StreamingProgressEvent(...)
    yield f"data: {initial_event.json()}\\n\\n"
    
    # 🧪 TEST: Send a manual test event
    test_event = StreamingProgressEvent(
        generation_id=generation_id,
        status="processing",
        stage="test",
        progress=0.5,
        message="TEST EVENT - SSE is working!",
        timestamp=time.time()
    )
    yield f"data: {test_event.json()}\\n\\n"
    
    # Now check for real events
    while True:
        ...
```

If the frontend receives the TEST EVENT, then SSE is working and the issue is that `generation_events[generation_id]` is empty.

If the frontend DOESN'T receive the TEST EVENT, then there's an issue with the SSE response format or frontend parsing.

## Action Items

1. **Add logging** to `_emit_event`, SSE loop, and `GeminiPhasedGenerator._emit_event`
2. **Add test event** to verify SSE is working at all
3. **Check generation_events dict** - add logging to see if events are being added
4. **Verify event_callback** - ensure it's not None in the phased generator
5. **Check timing** - ensure SSE connects before generation completes

## Next Steps

Run the generation again with the added logging and share:
1. Backend console output (with the new log messages)
2. Frontend console output
3. Network tab showing the SSE connection details

This will tell us exactly where the breakdown is happening.
