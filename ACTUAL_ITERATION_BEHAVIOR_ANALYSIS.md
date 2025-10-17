# Iteration Behavior: ACTUAL Current Implementation

## Executive Summary

**When a V1 generation with missing schema file goes through iteration, here's EXACTLY what happens:**

---

## Complete Trace: V1 (14 files, missing schema) → Iterate → V2

### Entry Point
```python
# Frontend calls:
POST /api/generations/iterate
{
    "parent_generation_id": "v1_uuid",
    "modification_prompt": "Add missing schema file"
}
```

### Step 1: Iteration Request Handler
**Location**: `app/routers/unified_generation.py:429`

```python
@router.post("/iterate", ...)
async def create_iteration(request: IterationRequest, ...):
    # 1. Validate parent exists
    parent_generation = await generation_repo.get_by_id(request.parent_generation_id)
    # ✅ FOUND: V1 generation
    
    # 2. Create UnifiedGenerationRequest
    unified_request = UnifiedGenerationRequest(
        prompt=request.modification_prompt,  # "Add missing schema file"
        project_id=parent_generation.project_id,
        context=request.context,
        is_iteration=True,  # ⭐ KEY FLAG
        parent_generation_id=request.parent_generation_id,  # Links to V1
        generation_mode=request.generation_mode
    )
    
    # 3. Call generate_project with is_iteration=True
    return await generate_project(unified_request, ...)
```

### Step 2: Route Goes to Classic or Enhanced Processing
**Location**: `app/routers/unified_generation.py:80-128`

```python
# Feature flag determines mode
generation_config = generation_feature_flag.get_generation_config(
    user_id=current_user.id,
    requested_mode=request.generation_mode,  # Typically AUTO
    is_iteration=True,  # ⭐ FLAG PASSED
    project_id=request.project_id
)

# Select processing based on mode
if generation_config.mode == GenerationMode.ENHANCED:
    background_tasks.add_task(
        _process_enhanced_generation,  # Enhanced route
        generation_id, request, ...
    )
else:
    background_tasks.add_task(
        _process_classic_generation,  # Classic route
        generation_id, request, ...
    )
```

### Step 3A: Classic Generation Route (Most Common)
**Location**: `app/routers/unified_generation.py:976`

```python
async def _process_classic_generation(
    generation_id: str,
    request: UnifiedGenerationRequest,  # ✅ is_iteration=True
    ...
):
    # NO special iteration handling here!
    # Treats iteration EXACTLY like regular generation
    
    # Calls AI orchestrator
    orchestrator_request = GenerationRequest(
        prompt=request.prompt,  # "Add missing schema file"
        context={
            "tech_stack": "fastapi_postgres",
            "domain": request.domain,
            ...
            "generation_mode": "classic"
            # ❌ NOTE: is_iteration flag NOT passed to orchestrator!
        },
        user_id=user_id
    )
    
    generation_result = await ai_orchestrator.generate_project(orchestrator_request)
    # ⚠️ PROBLEM: Orchestrator doesn't know this is an iteration!
```

### Step 3B: Enhanced Generation Route
**Location**: `app/routers/unified_generation.py:558`

```python
async def _process_enhanced_generation(
    generation_id: str,
    request: UnifiedGenerationRequest,  # ✅ is_iteration=True
    ...
):
    # Same problem: is_iteration flag lost!
    
    enhanced_prompt = await enhanced_service.enhance_prompt(
        original_prompt=request.prompt,
        context_analysis=...,
        ...
    )
    
    generation_result = await ai_orchestrator.process_generation(
        generation_id,
        {
            "prompt": enhanced_prompt,
            "context": {
                "tech_stack": "fastapi_postgres",
                ...
                # ❌ is_iteration NOT passed to orchestrator
            },
            ...
        }
    )
```

### Step 4: AI Orchestrator (Where the Bug Happens!)
**Location**: `app/services/ai_orchestrator.py:260`

```python
async def process_generation(
    self,
    generation_id: str,
    generation_data: dict
):
    # The orchestrator doesn't know this is an iteration!
    # It treats it as a FRESH generation
    
    return await self._process_with_generation_service(
        generation_id,
        generation_data,
        file_manager,
        enhanced=(generation_data.get("use_enhanced_prompts", True) and 
                  self.enhanced_prompt_system is not None)
    )
```

**Inside `_process_with_generation_service()`**:
```python
async def _process_with_generation_service(...):
    # Stage 1: Context Analysis
    # Stage 2: Schema Extraction
    
    # BUT WAIT - for iterations, we should:
    # 1. Get parent generation files
    # 2. Extract schema from PARENT files
    # 3. Generate MODIFICATIONS only
    # 4. MERGE with parent files
    
    # WHAT ACTUALLY HAPPENS:
    # Treats it as fresh generation request
    # No parent file context at all!
```

### Step 5: Schema Extraction (The Problem Compounds)
**Location**: `app/services/ai_orchestrator.py:350+`

```python
# Stage 2: Schema extraction
schema = await self._extract_schema(generation_data, enhanced_prompts if enhanced else None)
```

Inside `_extract_schema()`:
```python
async def _extract_schema(self, generation_data, enhanced_prompts):
    # Extracts schema from the PROMPT text only
    # NOT from existing files!
    
    schema = await provider.extract_schema(
        schema_prompt,  # Just the text: "Add missing schema file"
        context={
            "domain": "general",
            "tech_stack": "fastapi_postgres"
        }
    )
    return schema
```

**Schema extracted**: Very minimal schema based on text alone, not from the 14 existing files

### Step 6: Code Generation (Fate is Sealed)
**Location**: `app/services/ai_orchestrator.py:400+`

```python
# Step 3: Code generation
code_start = time.time()

# Generated code based on:
# 1. Prompt: "Add missing schema file"
# 2. Schema: Minimal extraction from prompt text
# 3. Context: Tech stack = fastapi_postgres (that's all!)
#
# AI DOES NOT KNOW:
# - What files already exist (14 files)
# - What entities are already modeled (User, Config, etc.)
# - What the project structure looks like
# - That this should preserve existing code

files = await code_provider.generate_code(
    prompt=prompt,
    schema=schema,
    context=context
)

# Result depends on what LLM generates:
# Scenario A: Full regeneration - Returns 15+ files (unlikely)
# Scenario B: Partial update - Returns only {"app/schemas/project.py": "..."} (likely!)
# Scenario C: Failure - Returns empty dict {}
```

### Step 7: File Storage (Data Loss Occurs Here)
**Location**: `app/routers/unified_generation.py:1073+`

```python
file_metadata = await file_manager.save_generation_files(
    generation_id=generation_id,
    files=files  # ⚠️ What code_provider returned
)
```

Inside `save_generation_files()`:
```python
async def save_generation_files(self, generation_id, files):
    # Save files to v2 directory
    # NO merging with parent (V1) files!
    
    generation_dir = storage_path / project_id / "generations" / f"v2__timestamp"
    
    for file_path, content in files.items():
        full_path = generation_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
    
    return file_metadata
```

**Result**:
- If files contains 1 file → V2 directory has 1 file ❌
- If files contains 15 files → V2 directory has 15 files ✅
- If files is empty → V2 directory is empty ❌

### Step 8: Generation Record Updated
**Location**: Various services

```python
# Database record for V2 generation
generation_v2 = {
    "id": generation_id,
    "version": 2,
    "parent_generation_id": v1_id,
    "is_iteration": True,
    "status": "completed",
    "file_count": len(files),  # ⚠️ Could be 1, 15, or 0
    "output_files": files,  # ⚠️ Could be incomplete
    "created_at": now,
    "updated_at": now
}
```

---

## Key Findings: Why Data Loss Happens

### 1. ❌ is_iteration Flag Dropped
- Set in iteration endpoint ✅
- Passed to generate_project ✅
- **Lost when calling orchestrator** ❌
- Never reaches `process_generation()` ❌

### 2. ❌ No Parent File Context
- V1 generation not fetched
- V1 files not passed to orchestrator
- Schema not extracted from V1
- Orchestrator treats as brand-new generation

### 3. ❌ No Merge Logic
- Files returned by LLM are treated as complete set
- No comparison with parent
- No preservation of parent files
- Stored as-is

### 4. ❌ Current Code Flow
```
Iteration Request
    ↓
unified_generation.py: create_iteration() ✅ has is_iteration=True
    ↓
unified_generation.py: generate_project() ✅ has is_iteration=True
    ↓
unified_generation.py: _process_classic/enhanced() ❌ LOST is_iteration
    ↓
ai_orchestrator.py: process_generation() ❌ Doesn't know it's iteration
    ↓
ai_orchestrator.py: generate_code() ❌ Treats as fresh generation
    ↓
Result files ⚠️ Could be incomplete
    ↓
file_manager.save_files() ❌ No merge, saves as-is
    ↓
V2 generation ❌ May have missing files
```

---

## Actual Behavior Summary

### With V1 = 14 files (missing schema), Iterate with "Add missing schema file"

**Most Likely Outcome**:
```
V1: [main.py, requirements.txt, config.py, app/models/user.py, ...13 more] (14 total)
    ↓ Iterate
AI generates: [app/schemas/project.py]  (just the new file)
    ↓ No merge
V2: [app/schemas/project.py]  (1 file)  ❌ DATA LOSS!
    ↓
User sees: File count: 1/15, Status: ✅ Completed
           But 14 files are missing!
```

**Less Likely Outcomes**:
1. AI regenerates everything → V2 has 15+ files ✅
2. AI fails → V2 empty → Status shows "completed" but no files ❌
3. AI returns full set → V2 has 15+ files ✅

---

## What Should Happen (Proper Iteration Flow)

```python
# In unified_generation.py during iteration:
if request.is_iteration:
    # Fetch parent generation files
    parent_gen = await generation_repo.get_by_id(request.parent_generation_id)
    parent_files = parent_gen.output_files  # 14 files
    
    # Pass to orchestrator WITH parent context
    await ai_orchestrator.iterate_project(
        parent_files=parent_files,  # ← Currently missing!
        modification_prompt=request.modification_prompt,
        parent_generation_id=request.parent_generation_id
    )

# In ai_orchestrator.py:
async def iterate_project(self, parent_files, modification_prompt, parent_generation_id):
    # Extract schema from PARENT files (not prompt)
    schema = self._extract_schema_from_files(parent_files)
    
    # Generate modifications in context of parent
    modified_files = await code_provider.generate_code(
        prompt=modification_prompt,
        schema=schema,
        context={
            "existing_files": list(parent_files.keys()),
            "is_iteration": True,
            "preserve_existing_code": True
        }
    )
    
    # MERGE parent + modifications
    merged = parent_files.copy()
    merged.update(modified_files)
    
    return merged  # ← Returns complete set
```

---

## Current Status in Codebase

| Component | Current | Expected | Gap |
|-----------|---------|----------|-----|
| **Iteration Detection** | ✅ Detected at endpoint | ✅ Same | ✅ OK |
| **is_iteration Flag** | ✅ Set in request | ❌ Lost in orchestrator | ❌ BUG |
| **Parent Fetch** | ❌ Not fetched | ✅ Should fetch | ❌ BUG |
| **Parent Files Context** | ❌ Not passed | ✅ Should pass | ❌ BUG |
| **Schema Extraction** | ❌ From prompt only | ✅ From parent files | ❌ BUG |
| **Merge Logic** | ❌ Missing | ✅ Should exist | ❌ BUG |
| **Result Validation** | ❌ None | ✅ Should validate | ❌ BUG |

---

## Verdict

### ❌ Current Behavior: BROKEN for Iterations with Missing Files

**Symptom**: V1 has 14 files → Iterate → V2 has 1 file → User confused

**Root Cause**: 
1. is_iteration flag not propagated to orchestrator
2. Parent files not fetched or used
3. No merge logic in iterate_project()
4. Orchestrator treats iteration as fresh generation

**Impact**: 
- High risk of data loss
- Version history becomes confusing
- Users lose work between iterations
- Iteration feature is unreliable

**Severity**: 🔴 **CRITICAL** - Breaks core iteration feature

