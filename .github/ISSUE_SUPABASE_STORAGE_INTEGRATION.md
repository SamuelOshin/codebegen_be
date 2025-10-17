# Integrate Supabase Storage for CodebeGen Project Files

## 🎯 Objective

Migrate CodebeGen's project storage system from local-only file storage to a hybrid approach using Supabase Storage (cloud) with local caching. This will enable scalable, production-ready storage of generated FastAPI projects.

## 📊 Priority

**Priority:** High  
**Type:** Feature Enhancement  
**Estimated Effort:** 3-5 days  
**Skills Required:** Python, FastAPI, Supabase, Async Programming

---

## 📋 Task Instructions

### Phase 1: Analysis & Planning (CRITICAL - DO THIS FIRST)

**Before writing any code, you MUST:**

#### 1. Analyze the existing codebase structure:
- [ ] Locate and examine `app/services/file_manager.py`
- [ ] Identify all places where `FileManager` is currently being used
- [ ] Find all API endpoints that save or retrieve generated projects
- [ ] Map out the current file storage flow (generation → saving → retrieval)
- [ ] Check if there's already a database schema for projects/generations
- [ ] Identify the current project directory structure

#### 2. Review existing implementations:
- [ ] Examine the `save_generation_files()` method
- [ ] Examine the `save_generation_files_hierarchical()` method
- [ ] Check how generation directories are currently accessed
- [ ] Look for any existing storage configuration (environment variables, config files)
- [ ] Identify any existing cleanup or archival logic

#### 3. Create a detailed implementation plan that includes:
- [ ] Which files need to be created (new services)
- [ ] Which files need to be modified (existing services, routes)
- [ ] Database migrations needed (if any)
- [ ] Environment variables to add
- [ ] Integration points with existing code
- [ ] Backward compatibility considerations
- [ ] Testing strategy
- [ ] Rollback plan if something goes wrong

#### 4. Present your analysis and plan in this format:

```markdown
## ANALYSIS REPORT

### Current State
- FileManager location: [path]
- Current storage method: [local/hierarchical/flat]
- Storage path: [current path]
- Usage locations: [list all files using FileManager]

### Dependencies Found
- Database ORM: [SQLAlchemy/Prisma/etc]
- Async framework: [FastAPI confirmed]
- Current environment setup: [.env structure]

### Proposed Changes

#### New Files to Create:
1. `app/services/supabase_storage_service.py` - Core Supabase integration
2. `app/services/storage_manager.py` - Hybrid storage orchestration
3. `app/core/config.py` (or modify existing) - Storage configuration
4. `scripts/migrate_to_supabase.py` - Migration script

#### Files to Modify:
1. `[filename]` - Reason: [why]
2. `[filename]` - Reason: [why]

#### Database Changes:
- [List any schema changes needed]
- [Migration files required]

#### Environment Variables:
```env
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
SUPABASE_BUCKET=codebegen-projects
USE_CLOUD_STORAGE=true
CACHE_PATH=/tmp/codebegen-cache
CACHE_TTL_HOURS=2
```

### Integration Points:
1. [Endpoint/Service] → [What changes needed]
2. [Endpoint/Service] → [What changes needed]

### Risks & Mitigation:
- Risk: [potential issue]
  - Mitigation: [how to handle]
```

**⚠️ STOP HERE AND WAIT FOR APPROVAL BEFORE PROCEEDING TO PHASE 2**

---

### Phase 2: Implementation (Only after Phase 1 approval)

Once the plan is approved, implement the following components:

#### 2.1 Create Supabase Storage Service

**File:** `app/services/supabase_storage_service.py`

**Requirements:**
- Class: `SupabaseStorageService`
- Initialize with Supabase credentials from environment
- Auto-create bucket `codebegen-projects` if it doesn't exist
- Implement methods:
  - `upload_generation()` - Compress and upload project to Supabase
  - `download_generation()` - Download and extract to local cache
  - `get_signed_download_url()` - Generate temporary download link (1 hour expiry)
  - `delete_generation()` - Remove from Supabase and cache
  - `list_project_generations()` - List all versions of a project
  - `cleanup_old_cache()` - Remove cache older than X hours
- Use tar.gz compression for uploads
- Handle errors gracefully with proper logging
- Support async/await throughout

**Technical Requirements:**
- Use `supabase-py` library
- Use `loguru` for logging
- Compress directories using `tarfile`
- Store with path format: `{project_id}/generations/v{version}__{generation_id}.tar.gz`
- Include metadata in compression (manifest.json compatibility)

#### 2.2 Create Hybrid Storage Manager

**File:** `app/services/storage_manager.py` (or integrate into existing service)

**Requirements:**
- Class: `HybridStorageManager`
- Accept `FileManager` and `SupabaseStorageService` as dependencies
- Implement hybrid flow:
  1. Save locally first (for immediate access)
  2. Upload to Supabase in background (fire-and-forget task)
  3. On retrieval: check local cache first, download from Supabase if needed
- Methods:
  - `save_generation()` - Save to both local and cloud
  - `get_generation()` - Retrieve from cache or cloud
  - `get_download_url()` - Get URL for user downloads
- Make cloud storage optional (controlled by `USE_CLOUD_STORAGE` env var)
- Preserve all existing FileManager functionality

#### 2.3 Update Existing FileManager Integration

**Modify existing code to use the new hybrid storage:**

- **DO NOT break existing functionality**
- Add optional cloud upload after local save
- Ensure backward compatibility (local-only mode still works)
- Update any generation endpoints to use `HybridStorageManager`
- Add download URL to API responses

**Changes should be minimal and non-breaking:**
```python
# Before
result = await file_manager.save_generation_files_hierarchical(...)

# After
result = await storage_manager.save_generation(...)
# ^ Should have same signature + additional cloud benefits
```

#### 2.4 Configuration Setup

**File:** `.env.example` and configuration docs

**Add:**
```env
# Supabase Storage Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_BUCKET=codebegen-projects

# Storage Options
USE_CLOUD_STORAGE=true  # Set false to disable cloud storage
CACHE_PATH=/tmp/codebegen-cache
CACHE_TTL_HOURS=2

# Optional: Auto-cleanup
AUTO_CLEANUP_ENABLED=true
CLEANUP_INTERVAL_HOURS=6
MAX_CACHE_AGE_HOURS=24
```

**Create:** `docs/STORAGE_SETUP.md` with:
- How to get Supabase credentials
- How to create the storage bucket
- RLS policies to set up
- Migration instructions
- Troubleshooting guide

#### 2.5 Migration Script

**File:** `scripts/migrate_to_supabase.py`

**Requirements:**
- Scan existing local project storage
- Upload all existing projects to Supabase
- Preserve directory structure and metadata
- Show progress (use tqdm or similar)
- Dry-run mode (preview without uploading)
- Verify uploads (check file exists in Supabase)
- Handle errors gracefully (skip and log, don't crash)
- Generate migration report

**Usage:**
```bash
# Dry run (preview)
python scripts/migrate_to_supabase.py --dry-run

# Actual migration
python scripts/migrate_to_supabase.py

# Migrate specific project
python scripts/migrate_to_supabase.py --project-id abc-123
```

#### 2.6 Background Cleanup Task (Optional)

**File:** `app/tasks/storage_cleanup.py`

**Requirements:**
- Scheduled task (using APScheduler or similar)
- Runs every 6 hours
- Cleans cache older than 24 hours
- Logs cleanup activity
- Can be disabled via env var

#### 2.7 Update API Responses

**Modify generation endpoints to include:**
```json
{
  "generation_id": "uuid",
  "download_url": "https://...", // Signed Supabase URL
  "expires_in": 3600, // 1 hour
  "storage": {
    "local_path": "/path/to/local",
    "cloud_enabled": true,
    "uploaded": true
  }
}
```

---

## 🛡️ Critical Requirements

### Backward Compatibility
- ✅ Existing local-only storage MUST continue to work
- ✅ Setting `USE_CLOUD_STORAGE=false` reverts to old behavior
- ✅ All existing API contracts preserved
- ✅ No breaking changes to database schema
- ✅ Existing projects accessible without migration

### Error Handling
- ✅ Supabase upload failures don't crash generation
- ✅ Local save always succeeds even if cloud fails
- ✅ Graceful degradation (work without cloud if needed)
- ✅ Clear error messages in logs
- ✅ Retry logic for transient failures

### Security
- ✅ Use service_role key (not anon key) in backend
- ✅ Never expose Supabase keys in frontend
- ✅ Signed URLs for downloads (auto-expire in 1 hour)
- ✅ Validate user ownership before allowing downloads
- ✅ Private bucket (public: false)

### Performance
- ✅ Local save must be fast (don't wait for upload)
- ✅ Background upload using async tasks
- ✅ Cache frequently accessed projects locally
- ✅ Compress files before upload (reduce bandwidth)
- ✅ Don't block API responses waiting for uploads

### Testing
- ✅ Test with cloud storage enabled
- ✅ Test with cloud storage disabled (backward compat)
- ✅ Test upload failure scenarios
- ✅ Test cache expiration and re-download
- ✅ Test signed URL generation and expiry
- ✅ Test migration script with sample data

---

## 📦 Dependencies to Install

Add to `requirements.txt`:
```txt
supabase>=2.0.0  # Supabase Python client
loguru>=0.7.0    # Logging (if not already installed)
tqdm>=4.66.0     # Progress bars for migration script
```

Or install directly:
```bash
pip install supabase loguru tqdm
```

---

## 🧪 Testing Checklist

After implementation, verify:

- [ ] Can save new generation with cloud storage
- [ ] Local files created correctly
- [ ] Files uploaded to Supabase automatically
- [ ] Can download generation from cache
- [ ] Can download generation from Supabase (cache miss)
- [ ] Signed URLs work and expire correctly
- [ ] Works with `USE_CLOUD_STORAGE=false` (local only)
- [ ] Existing local projects still accessible
- [ ] Migration script uploads existing projects
- [ ] Cleanup task removes old cache
- [ ] API returns download URLs
- [ ] Upload failures don't break generation
- [ ] User can only download their own projects

---

## 📝 Documentation to Create/Update

1. **README.md** - Add Supabase setup section
2. **docs/STORAGE_SETUP.md** - Detailed Supabase configuration guide
3. **docs/MIGRATION.md** - How to migrate existing projects
4. **.env.example** - Add new environment variables
5. **API documentation** - Update responses with download_url

---

## 🚨 Important Notes

### What NOT to Do:
- ❌ Don't delete or modify existing FileManager methods
- ❌ Don't break existing API endpoints
- ❌ Don't make cloud storage mandatory
- ❌ Don't expose Supabase credentials
- ❌ Don't wait for uploads in API responses
- ❌ Don't delete local files immediately after upload

### What TO Do:
- ✅ Keep backward compatibility at all times
- ✅ Make cloud storage optional (feature flag)
- ✅ Upload in background (non-blocking)
- ✅ Log all operations (success and failures)
- ✅ Test both local-only and hybrid modes
- ✅ Document everything clearly

---

## 🎯 Success Criteria

Implementation is complete when:

1. ✅ New generations save to both local and Supabase
2. ✅ Users can download via signed URLs
3. ✅ Cache works (no redundant downloads)
4. ✅ Old projects still accessible
5. ✅ Works with cloud storage disabled
6. ✅ Migration script successfully uploads existing projects
7. ✅ No breaking changes to existing code
8. ✅ All tests pass
9. ✅ Documentation complete
10. ✅ Environment variables configured

---

## 🔄 Rollback Plan

If something goes wrong:

1. Set `USE_CLOUD_STORAGE=false` in environment
2. System reverts to local-only storage
3. No data loss (local files preserved)
4. All functionality continues working

---

## ❓ Questions to Answer Before Starting

1. What ORM are you using? (SQLAlchemy, Prisma, etc.)
2. Do you have a config.py file for centralized configuration?
3. How are dependencies injected in your routes? (FastAPI Depends?)
4. What's your current project/generation database schema?
5. Do you have background task infrastructure? (Celery, APScheduler, etc.)
6. What's your testing framework? (pytest?)
7. How do you handle migrations? (Alembic, raw SQL, etc.)

---

## 🔗 Related Issues

- N/A (Initial implementation)

## 🏷️ Labels

`enhancement` `storage` `supabase` `high-priority` `backend` `infrastructure`

---

## 👥 Assignees

To be assigned

---

## 📅 Timeline

- **Phase 1 (Analysis):** 1 day
- **Phase 2 (Implementation):** 2-3 days
- **Testing & Documentation:** 1 day
- **Total Estimated Time:** 3-5 days

---

**Note:** This is a critical infrastructure change. Take time with the analysis phase to ensure a smooth implementation that maintains backward compatibility.
