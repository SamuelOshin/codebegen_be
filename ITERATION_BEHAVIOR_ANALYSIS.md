# Iteration Behavior Analysis: Expected Flow with Missing Schema File

## Current Scenario
- **V1 Generation Status**: Completed but missing `app/schemas/project.py` file
- **Iteration Request**: User calls `/generations/iterate` with `parent_generation_id=v1` and `modification_prompt="Add missing schema file"`
- **Question**: What happens when this iteration goes through the AI Orchestrator?

---

## Expected Behavior Flow

### Phase 1: Iteration Request Validation ✅
**Endpoint**: `POST /api/generations/iterate` (unified_generation.py:429)

```python
# 1. Validate parent generation exists
parent_generation = await generation_repo.get_by_id(request.parent_generation_id)
# ✅ PASS: V1 generation found with id, project_id, context, output_files

# 2. Validate user ownership
if parent_generation.user_id != current_user.id:
    # ✅ PASS: User owns the generation
    pass

# 3. Get parent generation files
# ✅ SUCCESS: Files retrieved from v1 (15 files minus the missing schema file)
# Files include: main.py, requirements.txt, config.py, etc. (14 files)
# Missing: app/schemas/project.py
```

**Result**: V2 generation record created with:
- `is_iteration=True`
- `parent_generation_id=v1_id`
- `version=2`
- Context includes parent tech stack and user preferences

---

### Phase 2: AI Orchestrator Processes Iteration 🔄
**Method**: `ai_orchestrator.iterate_project()` (ai_orchestrator.py:1357)

#### Step 2a: Extract Schema from Existing V1 Files
```python
existing_files = {
    "main.py": "...",
    "requirements.txt": "...",
    "config.py": "...",
    "app/routers/users.py": "...",
    # ... 14 files total (NO app/schemas/project.py)
}

schema = self._extract_schema_from_files(existing_files)
# Returns:
{
    "entities": ["User", "Config", ...],  # From existing models
    "endpoints": ["GET /users", "POST /users", ...],  # From existing routers
    "relationships": [],
    "constraints": []
}
```

**Key Issue**: Schema extraction is based on **existing files only**. Missing `app/schemas/project.py` means:
- ❌ No schema entities extracted from that file (because it doesn't exist)
- ❌ AI provider doesn't know what Project entity should look like
- ✅ But knows about User, Config entities from other files

#### Step 2b: Generate Modified Code via LLM
```python
modified_files = await code_provider.generate_code(
    prompt=modification_prompt,  # "Add missing schema file"
    schema=schema,  # ⚠️ Incomplete schema (no Project entity)
    context={
        "existing_files": [list of 14 files],
        "is_iteration": True,
        "tech_stack": "fastapi_postgres"
    }
)
```

**What Happens**:
1. **Gemini 2.5 Pro receives**:
   - Modification prompt: "Add missing schema file"
   - Extracted schema with 14 files' entities/endpoints
   - Context indicating this is an iteration
   
2. **Possible Outcomes**:

   **Scenario A: Successful Regeneration** ✅
   - AI generates NEW complete modified_files dict
   - Includes all original 14 files + newly generated `app/schemas/project.py`
   - Returns dict with 15+ files
   
   **Scenario B: Partial Files** ⚠️
   - AI only generates the missing file
   - Returns: `{"app/schemas/project.py": "..."}`
   - **Problem**: Only 1 file returned, original 14 are lost!
   
   **Scenario C: Generation Failure** ❌
   - AI cannot generate valid code
   - `modified_files = {}` or raises exception
   - Falls back to `return existing_files` (line 1386)
   - Returns original 14 files unchanged

---

### Phase 3: Merge Logic (CRITICAL) 🚨
**Currently in ai_orchestrator.py:1357-1376**

```python
# CURRENT CODE - NO MERGE LOGIC
async def iterate_project(self, existing_files, modification_prompt):
    schema = self._extract_schema_from_files(existing_files)
    modified_files = await code_provider.generate_code(...)
    return modified_files  # ⚠️ RETURNS ONLY NEW FILES!
```

**Expected Behavior**: 
- Should return **merged result**: existing files + new/modified files
- But currently returns **only** what code_provider generates

**Actual Behavior**:
```python
# If Scenario A (full regeneration):
return {all 15 files including new schema}  ✅ Works!

# If Scenario B (only new file):
return {"app/schemas/project.py": "..."}  ❌ LOSES 14 FILES!

# If Scenario C (failure):
return existing_files  ✅ Works (fallback)
```

---

### Phase 4: File Storage
**Method**: `file_manager.save_generation_files()` (unified_generation.py flow)

```python
# Files passed to file manager
files_to_save = modified_files  # What iterate_project returned

# Result directories created:
storage/
├── project_id/
│   ├── generations/
│   │   ├── v1__<timestamp>/
│   │   │   ├── main.py
│   │   │   ├── requirements.txt
│   │   │   ├── app/routers/users.py
│   │   │   └── [13 more files]
│   │   └── v2__<new_timestamp>/
│   │       ├── app/schemas/project.py  [IF SCENARIO B]
│   │       └── [ONLY 1 FILE if Scenario B!]
```

**Outcome**:
- V2 gets saved with **only what was generated**
- If AI only returned 1 file → V2 has 1 file
- If AI returned all 15 → V2 has 15 files

---

### Phase 5: Generation Status Update ✅
**After file storage**: Status marked as `"completed"`

```python
# Database record updated
generation_v2 = {
    "id": v2_id,
    "version": 2,
    "parent_generation_id": v1_id,
    "status": "completed",
    "file_count": len(saved_files),  # Could be 1, 15, or more
    "total_size_bytes": sum(file_sizes),
    "output_files": saved_files,
    "created_at": now
}
```

---

## ACTUAL EXPECTED BEHAVIOR (Current Code)

Based on trace through ai_orchestrator.py:

### 🎯 Most Likely Outcome: **Data Loss** ❌

**Why**:
1. Schema extraction from 14 files produces incomplete schema
2. AI provider likely generates a **complete replacement set** OR just the new file
3. `iterate_project()` returns **exactly what AI generated** (no merge)
4. If AI only returns new file → V2 becomes **single-file project**

**Specific Flow**:
```
User: "Add missing schema file"
     ↓
V1 files (14) → extract_schema() → incomplete schema
     ↓
AI generates: {"app/schemas/project.py": "..."}  [just the new file]
     ↓
iterate_project() returns: {"app/schemas/project.py": "..."}
     ↓
file_manager saves: V2 = [ONLY 1 FILE]
     ↓
User sees: V2 with 1 file instead of 15 files ❌
```

---

## Required Fixes

### Fix 1: Add Merge Logic to `iterate_project()`
**Location**: app/services/ai_orchestrator.py:1357

```python
async def iterate_project(
    self, 
    existing_files: Dict[str, str], 
    modification_prompt: str
) -> Dict[str, str]:
    """Handle iterative modifications to existing projects"""
    try:
        schema = self._extract_schema_from_files(existing_files)
        context = {
            "existing_files": list(existing_files.keys()),
            "is_iteration": True,
            "tech_stack": "fastapi_postgres"
        }
        
        modified_files = await code_provider.generate_code(
            prompt=modification_prompt,
            schema=schema,
            context=context
        )
        
        # 🔥 ADD THIS: Merge logic
        if modified_files:
            # Start with existing files
            merged = existing_files.copy()
            # Override/add with new modifications
            merged.update(modified_files)
            return merged
        else:
            # If generation fails, return existing
            return existing_files
            
    except Exception as e:
        print(f"Iteration failed: {e}")
        # Return original files if iteration fails
        return existing_files
```

### Fix 2: Enhance Schema Extraction for Iterations
**Add context indicating iteration**:

```python
# Before generation
context = {
    "existing_files": list(existing_files.keys()),
    "is_iteration": True,
    "iteration_context": {
        "total_existing_files": len(existing_files),
        "expected_modification": "Add missing schema file"  # From prompt
    },
    "tech_stack": "fastapi_postgres"
}

# AI knows:
# - This is an iteration
# - How many files already exist
# - Should preserve existing structure
```

### Fix 3: Add File Comparison Before Saving
**Add validation that iteration result includes minimum expected files**:

```python
async def save_generation_files(self, generation_id, files):
    # If this is an iteration and files < parent file count
    parent_gen = await generation_repo.get_by_id(parent_id)
    if parent_gen and len(files) < len(parent_gen.output_files) * 0.8:
        raise ValueError(
            f"Iteration result has {len(files)} files but parent had "
            f"{len(parent_gen.output_files)}. Possible data loss detected."
        )
    # Save files
    return await self._save_files(generation_id, files)
```

---

## Expected Behavior After Fixes

### ✅ Correct Iteration Flow

```
V1 (15 files: main.py, requirements.txt, ..., app/schemas/project.py ❌ MISSING)
     ↓
Iteration request: "Add missing schema file"
     ↓
extract_schema(14 files) → finds User, Config entities, endpoints
     ↓
AI generates: {"app/schemas/project.py": "class Project(BaseModel): ..."}
     ↓
✅ MERGE: existing_files.update(modified_files)
     ↓
Result dict: {main.py, requirements.txt, ..., app/schemas/project.py ✅ NEW}
     ↓
V2 = 15 files (all original + newly generated schema file)
     ↓
User sees: V2 COMPLETED with 15 files ✅
```

---

## Summary Table

| Aspect | Current Behavior | Expected Behavior | Status |
|--------|-----------------|-------------------|--------|
| **Schema Extraction** | From existing 14 files only | From existing + context-aware | ⚠️ Works but incomplete |
| **File Generation** | AI generates new files | AI generates modifications | ✅ Works |
| **Merge Logic** | **MISSING** - returns only new | Merge existing + new | ❌ Bug |
| **Data Preservation** | Files could be lost | All existing files preserved | ❌ Risk |
| **V2 Result** | Could have 1-15 files | Should have 15+ files | ⚠️ Variable |
| **User Experience** | Confusing/data loss | Clear versioning | ❌ Broken |

---

## Recommendation

**Immediate Action Required**: Add merge logic to `iterate_project()` method before accepting iteration requests with missing files. Otherwise, users risk losing files during iteration.

