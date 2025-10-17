# Critical Iteration Bug: Missing Merge Logic

## The Problem

When calling iteration with a V1 generation that has missing files:

```
POST /api/generations/iterate
{
    "parent_generation_id": "v1_with_14_files",
    "modification_prompt": "Add missing schema file"
}
```

**Expected Result**: V2 with 15 files (14 from V1 + 1 new schema)
**Actual Result**: V2 with 1 file (only the AI-generated schema) ❌

---

## Root Cause

### Issue #1: is_iteration Flag Lost
**File**: `app/routers/unified_generation.py`

```python
# Line 120-128: Classic generation processing
async def _process_classic_generation(generation_id, request, ...):
    orchestrator_request = GenerationRequest(
        prompt=request.prompt,
        context={
            **request.context,
            "tech_stack": request.tech_stack or "fastapi_postgres",
            "domain": request.domain,
            # ❌ request.is_iteration NOT passed!
            # ❌ request.parent_generation_id NOT passed!
        }
    )
```

**Same issue in enhanced generation** (line 760-775)

### Issue #2: Parent Files Not Fetched
**Missing code**: Before calling orchestrator, should:
```python
if request.is_iteration:
    parent_gen = await generation_repo.get_by_id(request.parent_generation_id)
    parent_files = parent_gen.output_files
```

### Issue #3: No Merge Logic in iterate_project()
**File**: `app/services/ai_orchestrator.py:1357`

```python
async def iterate_project(self, existing_files, modification_prompt):
    """Handle iterative modifications to existing projects"""
    
    schema = self._extract_schema_from_files(existing_files)
    modified_files = await code_provider.generate_code(...)
    
    return modified_files  # ❌ Returns ONLY new files, doesn't merge!
```

**Should be**:
```python
async def iterate_project(self, existing_files, modification_prompt):
    schema = self._extract_schema_from_files(existing_files)
    modified_files = await code_provider.generate_code(...)
    
    # ✅ Merge existing + modified
    merged = existing_files.copy()
    merged.update(modified_files)
    return merged
```

---

## Fix Plan

### Fix 1: Propagate is_iteration Flag to Orchestrator
**File**: `app/routers/unified_generation.py`

**Line 1007-1010 (Classic generation)**:
```python
# BEFORE
orchestrator_request = GenerationRequest(
    prompt=request.prompt,
    context={
        **request.context,
        "tech_stack": request.tech_stack or "fastapi_postgres",
        "domain": request.domain,
        "constraints": request.constraints,
        "generation_mode": "classic"
    },
    user_id=user_id,
    use_enhanced_prompts=False
)

# AFTER
orchestrator_request = GenerationRequest(
    prompt=request.prompt,
    context={
        **request.context,
        "tech_stack": request.tech_stack or "fastapi_postgres",
        "domain": request.domain,
        "constraints": request.constraints,
        "generation_mode": "classic",
        "is_iteration": request.is_iteration,  # ← ADD
        "parent_generation_id": request.parent_generation_id,  # ← ADD
    },
    user_id=user_id,
    use_enhanced_prompts=False
)
```

**Line 760-775 (Enhanced generation)**: Same fix

### Fix 2: Fetch Parent Files for Iteration
**File**: `app/routers/unified_generation.py`

**Add before generating**:
```python
async def _process_classic_generation(generation_id, request, user_id, generation_config, db):
    # ... existing code ...
    
    # ← ADD THIS BLOCK
    parent_files = None
    if request.is_iteration and request.parent_generation_id:
        try:
            parent_gen = await generation_repo.get_by_id(request.parent_generation_id)
            if parent_gen:
                parent_files = parent_gen.output_files or {}
                logger.info(f"Fetched {len(parent_files)} parent files for iteration")
        except Exception as e:
            logger.warning(f"Could not fetch parent files: {e}")
    # ← END ADD
    
    # Pass parent files to orchestrator if iteration
    if parent_files:
        orchestrator_request.context["parent_files"] = parent_files
```

### Fix 3: Implement Merge Logic
**File**: `app/services/ai_orchestrator.py`

**Lines 1357-1386**:
```python
async def iterate_project(self, existing_files: Dict[str, str], modification_prompt: str) -> Dict[str, str]:
    """Handle iterative modifications to existing projects"""
    try:
        # Get code generation provider
        code_provider = await self.provider_factory.get_provider(LLMTask.CODE_GENERATION)
        
        # For now, use the code generation with context about existing files
        context = {
            "existing_files": list(existing_files.keys()),
            "is_iteration": True,
            "tech_stack": "fastapi_postgres"
        }
        
        # Create a schema from existing files
        schema = self._extract_schema_from_files(existing_files)
        
        # Generate modified version
        modified_files = await code_provider.generate_code(
            prompt=modification_prompt,
            schema=schema,
            context=context
        )
        
        # ✅ ADD MERGE LOGIC HERE
        if modified_files:
            # Start with existing files
            merged = existing_files.copy()
            # Override/add with new modifications
            merged.update(modified_files)
            return merged
        else:
            # If generation fails, return existing
            return existing_files
        # ✅ END MERGE LOGIC
        
    except Exception as e:
        print(f"Iteration failed: {e}")
        # Return original files if iteration fails
        return existing_files
```

### Fix 4: Handle Iteration in process_generation Flow
**File**: `app/services/ai_orchestrator.py`

**In `_process_with_generation_service()` method (around line 300)**:

```python
# Add before schema extraction
parent_files = None
if generation_data.get("is_iteration"):
    parent_generation_id = generation_data.get("parent_generation_id")
    if parent_generation_id:
        try:
            parent_gen = await db.get(Generation, parent_generation_id)
            if parent_gen:
                parent_files = parent_gen.output_files or {}
                logger.info(f"Loading {len(parent_files)} parent files for iteration")
        except Exception as e:
            logger.warning(f"Could not load parent files: {e}")

# Then use parent files in schema extraction
if parent_files and generation_data.get("is_iteration"):
    schema = self._extract_schema_from_files(parent_files)
else:
    schema = await self._extract_schema(generation_data, enhanced_prompts if enhanced else None)
```

### Fix 5: Validate Result Before Saving
**File**: `app/routers/unified_generation.py`

**Before calling `file_manager.save_generation_files()`**:

```python
# Validate iteration results
if request.is_iteration and request.parent_generation_id:
    parent_gen = await generation_repo.get_by_id(request.parent_generation_id)
    parent_file_count = len(parent_gen.output_files or {})
    new_file_count = len(result_dict.get("files", {}))
    
    # Warn if we lost files
    if new_file_count < parent_file_count * 0.8:  # 80% threshold
        logger.warning(
            f"Iteration result has {new_file_count} files but parent had {parent_file_count}. "
            f"Possible data loss detected!"
        )
        # Could raise error or emit warning event
```

---

## Implementation Order

1. **First**: Fix merge logic in `iterate_project()` (prevents immediate data loss)
2. **Second**: Propagate is_iteration flag through orchestrator
3. **Third**: Fetch parent files when iterating
4. **Fourth**: Handle iteration in process_generation flow
5. **Fifth**: Add validation before saving

---

## Testing Criteria

After implementing fixes, iteration should:

✅ When V1 has 14 files and iteration adds 1 file → V2 should have 15 files
✅ When V1 has 14 files and iteration modifies 2 files → V2 should have 14 files with 2 updated
✅ When V1 has missing schema file → User can iterate to add it → V2 complete
✅ File count in response should be >= parent file count
✅ All parent files accessible in V2 directory

---

## Code Review Checklist

- [ ] is_iteration propagated to GenerationRequest
- [ ] parent_generation_id propagated to GenerationRequest
- [ ] Parent files fetched before orchestrator call
- [ ] Merge logic added to iterate_project()
- [ ] Process_generation handles iteration path
- [ ] File validation before storage
- [ ] Unit tests cover iteration scenarios
- [ ] Integration tests verify file preservation
- [ ] Logging captures all iteration steps

