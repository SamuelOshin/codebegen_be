# Iteration Fix - Testing Guide 🧪

**Date:** October 17, 2025  
**Purpose:** Verify iteration now preserves files and uses context awareness

---

## Quick Test

### 1. Start Server
```bash
python main.py
```

### 2. Create V1 Generation (Parent Project)

**POST** `/generations`
```json
{
  "prompt": "Create a FastAPI user management system with posts and comments",
  "tech_stack": "fastapi_postgres",
  "domain": "social_media",
  "generation_mode": "classic"
}
```

**Expected:**
- V1 with ~15 files
- Save the `generation_id`

### 3. Test Iteration (Add Files)

**POST** `/generations/iterate`
```json
{
  "parent_generation_id": "<generation_id_from_v1>",
  "prompt": "Add missing Pydantic schema files for all models",
  "tech_stack": "fastapi_postgres",
  "is_iteration": true
}
```

**Expected Logs:**
```
INFO: [Classic] Fetched 15 parent files for iteration
INFO: [Iteration] Routing to iterate_project() with 15 parent files
INFO: [Iteration] Detected intent: add
INFO: 🔄 STRATEGY: Iteration Mode
INFO: [Iteration] Generated 19 files (parent: 15, new/modified: 4)
INFO: ✅ Saved 19 files
```

**Expected Result:**
- ✅ V2 has 19+ files (NOT 4)
- ✅ All 15 original files preserved
- ✅ 4+ new schema files added

---

## Detailed Test Cases

### Test 1: Add Files ✅
```json
{
  "parent_generation_id": "...",
  "prompt": "Add missing schema files",
  "is_iteration": true
}
```

**Verify:**
- `len(V2_files) > len(V1_files)`
- All V1 files present in V2
- New schema files added

---

### Test 2: Modify Files ✅
```json
{
  "parent_generation_id": "...",
  "prompt": "Fix the authentication bug in app/routers/users.py",
  "is_iteration": true
}
```

**Verify:**
- `len(V2_files) == len(V1_files)`
- Only `users.py` modified
- Other files unchanged

---

### Test 3: Remove Files ✅
```json
{
  "parent_generation_id": "...",
  "prompt": "Remove all test files",
  "is_iteration": true
}
```

**Verify:**
- `len(V2_files) < len(V1_files)`
- Test files removed
- Other files preserved

---

## Log Verification

### Success Indicators ✅
Look for these in server logs:

```
✅ [Iteration] Routing to iterate_project() with X parent files
✅ [Iteration] Detected intent: add|modify|remove
✅ 🔄 STRATEGY: Iteration Mode
✅ [Iteration] Merge complete: X existing + Y changes = Z total files
✅ ✅ Saved Z files
```

### Failure Indicators ❌
If you see these, iteration isn't using new code:

```
❌ Using phased generation for 1 entities  (should not appear for iterations)
❌ ⚡ STRATEGY: Simple Generation  (should be "Iteration Mode")
❌ Direct generation failed  (should use iterate_project)
```

---

## Manual Verification

### Check Database
```python
# Use check_generation_status.py
python check_generation_status.py <generation_id>
```

**Verify:**
- `output_files` count matches expected
- All parent files present
- New files added

### Check Files
```python
# Get generation files
import json
from app.repositories.generations import GenerationRepository

# Check V1
v1_files = generation_repo.get_by_id(parent_id).output_files
print(f"V1: {len(v1_files)} files")

# Check V2
v2_files = generation_repo.get_by_id(iteration_id).output_files
print(f"V2: {len(v2_files)} files")

# Verify preservation
preserved = set(v1_files.keys()) & set(v2_files.keys())
print(f"Preserved: {len(preserved)}/{len(v1_files)} files")

# Check new files
new_files = set(v2_files.keys()) - set(v1_files.keys())
print(f"New files: {list(new_files)}")
```

---

## Expected vs Actual

### Before Fix ❌
```
V1: 15 files
Request: "Add schema files"
V2: 4 files  ← Lost 11 files!
```

### After Fix ✅
```
V1: 15 files
Request: "Add schema files"
V2: 19 files  ← Preserved all + added 4!
```

---

## Troubleshooting

### Issue: Still getting 4 files

**Check:**
1. Is `is_iteration: true` in request?
2. Is `parent_generation_id` valid?
3. Are parent files fetched? Check logs for "Fetched X parent files"
4. Is routing correct? Should see "Routing to iterate_project()"

**Fix:**
- Ensure request has both fields
- Verify parent generation exists in DB
- Check server logs for error messages

### Issue: Logs show "Using phased generation"

**Problem:** Iteration not detected, using normal generation

**Check:**
1. `context.get('is_iteration')` should be True
2. Should see "🔄 STRATEGY: Iteration Mode"

**Fix:**
- Verify context passed to `iterate_project()`
- Check gemini_provider.py iteration detection

### Issue: Files not preserved

**Problem:** Merge logic not working

**Check:**
1. Logs should show "Merge complete"
2. Verify `merged.update(modified_files)` is called

**Fix:**
- Check iterate_project() merge section
- Verify no exceptions during merge

---

## Success Criteria

All must be ✅:

- [ ] Server starts without errors
- [ ] V1 generation creates 15+ files
- [ ] Iteration request accepted (201 Created)
- [ ] Logs show "Routing to iterate_project()"
- [ ] Logs show "Detected intent: add"
- [ ] Logs show "Iteration Mode"
- [ ] V2 has 19+ files (V1 count + new)
- [ ] All V1 files present in V2
- [ ] New schema files added
- [ ] No "Lost files" errors

---

## Performance Expectations

### Iteration Time
- **Parent File Loading:** <500ms
- **Context Building:** <100ms
- **LLM Generation:** 10-30 seconds
- **File Merging:** <100ms
- **Total:** 10-35 seconds

### Memory Usage
- **Parent Files:** ~1-2 MB for 15 files
- **Context Prompt:** ~5-10 KB
- **LLM Response:** ~50-200 KB
- **Merged Files:** ~2-4 MB total

---

## Quick Validation Script

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Create V1
response = requests.post(f"{BASE_URL}/generations", json={
    "prompt": "Create FastAPI user management system",
    "tech_stack": "fastapi_postgres"
})
v1_id = response.json()["generation_id"]
print(f"V1 Created: {v1_id}")

# Wait for completion...
import time
time.sleep(30)

# 2. Get V1 files
v1_response = requests.get(f"{BASE_URL}/generations/{v1_id}")
v1_files = v1_response.json()["output_files"]
print(f"V1 Files: {len(v1_files)}")

# 3. Create V2 (iteration)
response = requests.post(f"{BASE_URL}/generations/iterate", json={
    "parent_generation_id": v1_id,
    "prompt": "Add missing schema files",
    "is_iteration": True
})
v2_id = response.json()["generation_id"]
print(f"V2 Created: {v2_id}")

# Wait for completion...
time.sleep(30)

# 4. Get V2 files
v2_response = requests.get(f"{BASE_URL}/generations/{v2_id}")
v2_files = v2_response.json()["output_files"]
print(f"V2 Files: {len(v2_files)}")

# 5. Verify
preserved = len(set(v1_files.keys()) & set(v2_files.keys()))
new = len(set(v2_files.keys()) - set(v1_files.keys()))

print(f"\n✅ TEST RESULTS:")
print(f"   V1: {len(v1_files)} files")
print(f"   V2: {len(v2_files)} files")
print(f"   Preserved: {preserved}/{len(v1_files)}")
print(f"   New: {new}")

if preserved == len(v1_files) and new > 0:
    print("\n🎉 SUCCESS! Iteration working correctly!")
else:
    print("\n❌ FAILURE! Files not preserved correctly")
```

---

**Ready to Test!** 🚀
