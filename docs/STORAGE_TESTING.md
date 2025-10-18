# Supabase Storage Integration - Testing Guide

This guide helps you test the Supabase Storage integration locally.

## Prerequisites

1. Python 3.11+ installed
2. Dependencies installed: `pip install supabase loguru tqdm`
3. (Optional) Supabase account and project

## Testing Without Supabase (Local-Only Mode)

The system works perfectly without Supabase configured. This tests backward compatibility.

### 1. Configure Environment

```bash
# .env
USE_CLOUD_STORAGE=false
FILE_STORAGE_PATH=./storage/projects
CACHE_PATH=./storage/cache
```

### 2. Test Generation Storage

```python
from app.services.storage_manager import storage_manager

# This will save locally only
storage_path, file_count, size = await storage_manager.save_generation(
    project_id="test-project-123",
    generation_id="test-gen-456",
    version=1,
    files={
        "main.py": "print('Hello World')",
        "README.md": "# Test Project"
    }
)

print(f"Saved to: {storage_path}")
print(f"Files: {file_count}, Size: {size} bytes")
```

### 3. Verify Local Storage

```bash
ls -R ./storage/projects/test-project-123/
```

Expected structure:
```
./storage/projects/test-project-123/
└── generations/
    └── v1__test-gen-456/
        ├── manifest.json
        ├── source/
        │   ├── main.py
        │   └── README.md
        └── artifacts/
```

## Testing With Supabase (Hybrid Mode)

### 1. Set Up Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project (free tier is fine)
3. Wait ~2 minutes for provisioning
4. Get credentials from **Settings → API**

### 2. Configure Environment

```bash
# .env
USE_CLOUD_STORAGE=true
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_BUCKET=codebegen-projects
CACHE_PATH=./storage/cache
CACHE_TTL_HOURS=24
```

### 3. Test Storage Service Initialization

```python
from app.services.supabase_storage_service import SupabaseStorageService

service = SupabaseStorageService()

if service.enabled:
    print("✅ Supabase storage initialized successfully")
    print(f"Bucket: {service.bucket_name}")
else:
    print("❌ Supabase storage not enabled")
    print("Check your environment variables")
```

### 4. Test Upload to Cloud

```python
import asyncio
from pathlib import Path
from app.services.storage_manager import storage_manager

async def test_cloud_upload():
    # Save generation (uploads to cloud in background)
    storage_path, file_count, size = await storage_manager.save_generation(
        project_id="test-project-123",
        generation_id="test-gen-456",
        version=1,
        files={
            "main.py": "print('Hello from cloud')",
            "requirements.txt": "fastapi==0.104.1"
        }
    )
    
    print(f"✅ Saved locally: {storage_path}")
    
    # Wait a moment for background upload
    await asyncio.sleep(2)
    
    # Check Supabase dashboard - file should appear!
    print("Check Supabase dashboard → Storage → codebegen-projects")

# Run test
asyncio.run(test_cloud_upload())
```

### 5. Test Download from Cloud

```python
async def test_cloud_download():
    # Get download URL
    url = await storage_manager.get_download_url(
        project_id="test-project-123",
        generation_id="test-gen-456",
        version=1
    )
    
    if url:
        print(f"✅ Download URL: {url[:50]}...")
        print("URL is valid for 1 hour")
    else:
        print("❌ Could not generate download URL")

asyncio.run(test_cloud_download())
```

### 6. Test Cache Retrieval

```python
async def test_cache():
    # Delete local files but keep cloud
    import shutil
    local_path = Path("./storage/projects/test-project-123")
    if local_path.exists():
        shutil.rmtree(local_path)
        print("Deleted local files")
    
    # Try to get generation (should download from cloud)
    gen_path = await storage_manager.get_generation(
        project_id="test-project-123",
        generation_id="test-gen-456",
        version=1
    )
    
    if gen_path:
        print(f"✅ Downloaded from cloud to cache: {gen_path}")
    else:
        print("❌ Could not retrieve generation")

asyncio.run(test_cache())
```

## Testing Migration Script

### 1. Create Test Data

```bash
# Create sample project structure
mkdir -p storage/projects/test-project-1/generations/v1__gen-1/source
echo "print('test 1')" > storage/projects/test-project-1/generations/v1__gen-1/source/main.py

mkdir -p storage/projects/test-project-1/generations/v2__gen-2/source
echo "print('test 2')" > storage/projects/test-project-1/generations/v2__gen-2/source/main.py
```

### 2. Test Dry Run

```bash
python scripts/migrate_to_supabase.py --dry-run
```

Expected output:
```
📂 Scanning storage: ./storage/projects
✅ Found 2 generations in 1 projects
📤 Uploading 2 generations...
[DRY RUN] Would upload: test-project-1/v1__gen-1
[DRY RUN] Would upload: test-project-1/v2__gen-2
```

### 3. Test Actual Migration

```bash
python scripts/migrate_to_supabase.py --verify
```

### 4. Verify in Supabase

1. Go to Supabase dashboard
2. Navigate to **Storage → codebegen-projects**
3. You should see:
   - `test-project-1/generations/v1__gen-1.tar.gz`
   - `test-project-1/generations/v2__gen-2.tar.gz`

## Common Issues & Solutions

### Issue: "Supabase storage not enabled"

**Solution:**
1. Check `USE_CLOUD_STORAGE=true` in `.env`
2. Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set
3. Restart your application

### Issue: "Failed to create bucket"

**Solution:**
1. Create bucket manually in Supabase dashboard
2. Name it exactly as in `SUPABASE_BUCKET` env var
3. Make sure it's **Private** (not public)

### Issue: "Upload fails silently"

**Solution:**
1. Check logs for error messages
2. Verify service_role key (not anon key) is used
3. Check Supabase project is not paused

### Issue: "Download URL returns 403"

**Solution:**
1. Make sure you're using service_role key
2. Verify file exists in Supabase dashboard
3. Check bucket permissions

## Automated Testing

### Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run storage tests
pytest tests/test_services/test_storage_services.py -v
```

### Integration Test Script

```bash
# Create integration test
cat > test_storage_integration.py << 'EOF'
import asyncio
from app.services.storage_manager import storage_manager

async def main():
    print("Testing storage integration...")
    
    # Test save
    result = await storage_manager.save_generation(
        project_id="test-integration",
        generation_id="gen-001",
        version=1,
        files={"test.txt": "integration test"}
    )
    print(f"✅ Save: {result}")
    
    # Test retrieve
    path = await storage_manager.get_generation(
        project_id="test-integration",
        generation_id="gen-001",
        version=1
    )
    print(f"✅ Retrieve: {path}")
    
    # Test download URL
    url = await storage_manager.get_download_url(
        project_id="test-integration",
        generation_id="gen-001",
        version=1
    )
    print(f"✅ Download URL: {url}")
    
    print("\n✅ All integration tests passed!")

asyncio.run(main())
EOF

python test_storage_integration.py
```

## Performance Testing

### Test Upload Speed

```python
import time
import asyncio

async def test_upload_performance():
    # Create 10MB of test data
    large_file = "x" * (10 * 1024 * 1024)
    files = {f"large_{i}.txt": large_file for i in range(5)}
    
    start = time.time()
    
    await storage_manager.save_generation(
        project_id="perf-test",
        generation_id="large-gen",
        version=1,
        files=files
    )
    
    duration = time.time() - start
    print(f"Uploaded 50MB in {duration:.2f} seconds")
    print(f"Speed: {50/duration:.2f} MB/s")

asyncio.run(test_upload_performance())
```

## Monitoring

### Check Storage Status

```python
async def check_storage_status():
    info = await storage_manager.get_storage_info(
        project_id="test-project-123",
        generation_id="test-gen-456",
        version=1
    )
    
    print(f"Cloud enabled: {info['cloud_enabled']}")
    print(f"Local exists: {info['local_exists']}")
    print(f"Cloud exists: {info['cloud_exists']}")

asyncio.run(check_storage_status())
```

### Check Cache Size

```bash
# Check local cache size
du -sh ./storage/cache

# Check local storage size
du -sh ./storage/projects
```

### Cleanup Cache

```python
async def cleanup_cache():
    count = await storage_manager.cleanup_old_cache(
        max_age_hours=24
    )
    print(f"Cleaned up {count} old cache entries")

asyncio.run(cleanup_cache())
```

## Production Readiness Checklist

Before deploying to production:

- [ ] Supabase project created and configured
- [ ] Environment variables set correctly
- [ ] Bucket created and permissions verified
- [ ] Migration script tested on staging data
- [ ] Local-only mode tested (fallback)
- [ ] Download URLs tested and working
- [ ] Cache cleanup tested
- [ ] Monitoring/logging configured
- [ ] Backup strategy in place
- [ ] Documentation updated

## Support

For issues or questions:
- Check [docs/STORAGE_SETUP.md](STORAGE_SETUP.md) for setup guide
- Review [GitHub Issues](https://github.com/SamuelOshin/codebegen_be/issues)
- Check Supabase [documentation](https://supabase.com/docs/guides/storage)
