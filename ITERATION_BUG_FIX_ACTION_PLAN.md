# Iteration Bug Fix - Action Plan

**Date:** October 17, 2025  
**Priority:** 🔴 CRITICAL  
**Status:** Analysis Complete - Ready for Implementation

---

## The Bug

**User Has:** 15 files in V1 (complete FastAPI project)  
**User Wants:** "Add the missing schema file"  
**Expected Result:** V2 with 16-19 files (15 original + schema files)  
**Actual Result:** V2 with 4-6 completely new files ❌

**Impact:** Iteration feature is completely broken and unusable.

---

## Root Causes

### 1. **iterate_project() Never Called** ❌
```python
# Current flow:
/generations/iterate 
  → _process_classic_generation()
    → ai_orchestrator.process_generation()  # WRONG!
      → Full generation from scratch

# iterate_project() exists but is orphaned code
```

### 2. **Zero Context to LLM** ❌
```python
# What LLM receives:
Prompt: "Add the missing schema file"
Schema: {entities: []} # Empty or wrong

# What LLM doesn't see:
- Existing 15 files ❌
- Project structure ❌
- Existing code ❌
- That this is an EDIT ❌
```

### 3. **Wrong Generation Strategy** ❌
```python
# System sees: "1 entity" (from modification prompt)
# Triggers: Simple generation for new 1-entity project
# Result: Generates new project instead of editing existing
```

---

## The Fix - 3 Critical Changes

### Fix #1: Route to iterate_project() ✅

**File:** `app/routers/generations.py`  
**Method:** `_process_classic_generation()`  
**Line:** ~990

**Change:**
```python
# BEFORE (BROKEN):
if request.is_iteration and parent_files:
    await ai_orchestrator.process_generation(...)  # Full regen ❌

# AFTER (FIXED):
if request.is_iteration and parent_files:
    result_files = await ai_orchestrator.iterate_project(
        existing_files=parent_files,
        modification_prompt=request.prompt
    )  # Context-aware editing ✅
```

### Fix #2: Context-Aware Prompting ✅

**File:** `app/services/ai_orchestrator.py`  
**Method:** `iterate_project()`  
**Line:** ~1380

**Add These Methods:**
```python
1. _detect_iteration_intent() - Detects add/modify/remove
2. _format_file_tree() - Shows project structure
3. _show_key_files() - Shows relevant code to LLM
```

**Enhance iterate_project():**
```python
async def iterate_project(self, existing_files, modification_prompt):
    # Build context-rich prompt
    intent = self._detect_iteration_intent(modification_prompt, existing_files)
    file_tree = self._format_file_tree(existing_files)
    key_files = self._show_key_files(existing_files, max_files=5)
    
    context_prompt = f"""
EXISTING PROJECT: {len(existing_files)} files
{file_tree}

KEY FILES:
{key_files}

USER REQUEST: {modification_prompt}
INTENT: {intent}

Generate ONLY files that need to be added or modified.
Preserve all other files.
"""
    
    # Now LLM understands it's editing, not creating ✅
    modified_files = await provider.generate_code(context_prompt, ...)
    
    # Merge with existing files
    return {**existing_files, **modified_files}
```

### Fix #3: Skip Phased Generation for Iterations ✅

**File:** `app/services/llm_providers/gemini_provider.py`  
**Method:** `generate_code()`  
**Line:** ~245

**Change:**
```python
async def generate_code(self, prompt, schema, context, ...):
    # Check if iteration
    is_iteration = context.get('is_iteration', False)
    
    if is_iteration:
        # Use simple iteration-focused generation
        return await self._generate_iteration_changes(prompt, schema, context)
    
    # Normal phased/simple generation logic...
```

---

## Implementation Steps

### Step 1: Add Helper Methods to ai_orchestrator.py ✅

```python
def _detect_iteration_intent(self, prompt: str, existing_files: Dict) -> str:
    """Detect add/modify/remove intent"""
    prompt_lower = prompt.lower()
    
    if any(word in prompt_lower for word in ['add', 'create', 'new', 'missing']):
        return 'add'
    elif any(word in prompt_lower for word in ['fix', 'update', 'change', 'modify']):
        return 'modify'
    elif any(word in prompt_lower for word in ['remove', 'delete', 'drop']):
        return 'remove'
    
    return 'unknown'

def _format_file_tree(self, files: Dict[str, str]) -> str:
    """Create visual file tree"""
    # Build tree structure from file paths
    # Return formatted string like:
    # app/
    # ├── models/
    # │   ├── user.py
    # │   └── post.py
    # └── routers/
    #     └── users.py

def _show_key_files(self, files: Dict[str, str], max_files: int = 5) -> str:
    """Show most relevant files to LLM"""
    # Prioritize: main.py, config, models, schemas
    # Return: "=== filepath ===\ncontent\n..."
```

### Step 2: Update iterate_project() in ai_orchestrator.py ✅

Replace entire method with context-aware version (see full code in ITERATION_SYSTEM_REDESIGN.md).

### Step 3: Fix Routing in generations.py ✅

```python
# Line ~975-1010 in _process_classic_generation()

# Add this block BEFORE the current generation logic:
if request.is_iteration and parent_files:
    logger.info(f"[Iteration] Using iterate_project with {len(parent_files)} parent files")
    
    result_files = await ai_orchestrator.iterate_project(
        existing_files=parent_files,
        modification_prompt=request.prompt,
        context={
            "tech_stack": request.tech_stack or "fastapi_postgres",
            "domain": request.domain,
            "constraints": request.constraints
        }
    )
    
    result_dict = {
        "files": result_files,
        "schema": {},
        "review_feedback": [],
        "documentation": {},
        "quality_score": 0.8
    }
    
    # Skip to file saving section...
    
else:
    # Normal generation...
```

### Step 4: Add Iteration Mode to gemini_provider.py ✅

```python
async def generate_code(self, prompt, schema, context, ...):
    is_iteration = context.get('is_iteration', False)
    
    if is_iteration:
        logger.info("Using iteration mode")
        return await self._generate_iteration_changes(prompt, schema, context)
    
    # Existing logic...

async def _generate_iteration_changes(self, prompt, schema, context):
    """Simple generation for iterations"""
    result = await self.model.generate_content_async(
        prompt,
        generation_config={
            "temperature": 0.3,  # Lower for precise edits
            "max_output_tokens": 8000
        }
    )
    return self._parse_json_response(result.text)
```

---

## Testing Plan

### Test 1: Add Missing Files ✅
```python
# Setup
V1 = 15 files (complete FastAPI project, missing schemas)

# Request
POST /generations/iterate
{
  "parent_generation_id": "...",
  "modification_prompt": "Add the missing schema files"
}

# Expected Result
V2 = 19 files
- All 15 original files ✅
- 4 new schema files added ✅
- No files lost ✅

# Verification
assert len(V2_files) >= len(V1_files)
assert all(f in V2_files for f in V1_files)
```

### Test 2: Modify Existing File ✅
```python
# Setup
V1 = 15 files

# Request
"Fix the authentication bug in users.py"

# Expected Result
V2 = 15 files
- 14 files unchanged ✅
- users.py modified ✅

# Verification
assert len(V2_files) == len(V1_files)
assert V2_files['users.py'] != V1_files['users.py']
assert V2_files['post.py'] == V1_files['post.py']  # Unchanged
```

### Test 3: Remove Files ✅
```python
# Setup
V1 = 15 files (includes 3 test files)

# Request
"Remove all test files"

# Expected Result
V2 = 12 files
- 3 test files removed ✅
- 12 files preserved ✅

# Verification
assert len(V2_files) == 12
assert 'test_user.py' not in V2_files
```

---

## Expected Logs After Fix

### Before (Broken) ❌
```
INFO: POST /generations/iterate HTTP/1.1" 201 Created
INFO: Using phased generation for 1 entities  ← WRONG!
INFO: ✅ Saved 4 files  ← Lost 11 files!
```

### After (Fixed) ✅
```
INFO: POST /generations/iterate HTTP/1.1" 201 Created
INFO: [Iteration] Using iterate_project with 15 parent files ✅
INFO: Detected iteration intent: add ✅
INFO: Iteration merge: 15 existing + 4 new = 19 total files ✅
INFO: ✅ Saved 19 files ✅
```

---

## Risk Assessment

### Low Risk Changes ✅
- Adding new methods (_detect_intent, _format_tree, _show_key_files)
- These are pure functions, no side effects
- Can't break existing functionality

### Medium Risk Changes ⚠️
- Updating iterate_project() - existing method is unused anyway
- Routing to iterate_project() - only affects iterations
- Adding iteration mode to provider - fallback exists

### Mitigation
- Keep old code paths for non-iterations
- Add extensive logging
- Test with multiple scenarios
- Gradual rollout with feature flag

---

## Rollout Plan

### Phase 1: Implement Core Fixes (2 hours)
1. Add helper methods to ai_orchestrator.py
2. Update iterate_project() with context awareness
3. Fix routing in generations.py
4. Add iteration mode to gemini_provider.py

### Phase 2: Testing (1 hour)
1. Test Case 1: Add files
2. Test Case 2: Modify files
3. Test Case 3: Remove files
4. Verify logs show correct flow

### Phase 3: Deployment (30 min)
1. Deploy to staging
2. Run integration tests
3. Verify with real user scenarios
4. Deploy to production

---

## Success Criteria

✅ Iteration preserves all parent files  
✅ New files are added to existing files  
✅ Modified files are updated, others unchanged  
✅ Logs show "iterate_project" being used  
✅ File count: V2 >= V1 (for additions)  
✅ No data loss

---

## Documentation Updates

After implementation:
1. ✅ Update API documentation
2. ✅ Update FRONTEND_SSE_INTEGRATION_GUIDE.md
3. ✅ Create user guide for iterations
4. ✅ Add examples to README

---

## Next Actions

**Immediate (Now):**
1. Implement Fix #1: Route to iterate_project() ✅
2. Implement Fix #2: Add context-aware prompting ✅
3. Implement Fix #3: Add iteration mode ✅

**Then (Test):**
4. Run test scenarios
5. Verify logs
6. Check file preservation

**Finally (Deploy):**
7. Deploy to staging
8. Integration tests
9. Production deployment

**Status:** Ready to implement  
**ETA:** 2-3 hours total  
**Priority:** CRITICAL - blocks iteration feature

---

**Full Implementation Details:** See `ITERATION_SYSTEM_REDESIGN.md`
