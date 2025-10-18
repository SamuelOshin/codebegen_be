# Supabase Storage Setup Guide

This guide will help you configure Supabase Storage for CodebeGen project file storage.

## 🎯 Overview

CodebeGen uses a hybrid storage approach:
- **Local Storage**: Fast access, immediate availability
- **Cloud Storage (Supabase)**: Scalable, persistent, accessible from anywhere
- **Smart Caching**: Downloads from cloud only when needed

## 📋 Prerequisites

- Supabase account (free tier works great)
- Python 3.11+
- CodebeGen backend installed

## 🚀 Quick Start

### 1. Create a Supabase Project

1. Go to [Supabase](https://app.supabase.com)
2. Click **"New Project"**
3. Choose your organization
4. Set project name (e.g., "codebegen-storage")
5. Set a strong database password
6. Choose your region (closest to your users)
7. Click **"Create new project"**

Wait 1-2 minutes for the project to be provisioned.

### 2. Get Your Credentials

1. Go to **Project Settings** (gear icon in sidebar)
2. Click **API** in the settings menu
3. Copy these values:
   - **Project URL** (e.g., `https://abcdefghij.supabase.co`)
   - **service_role key** (⚠️ Keep this secret!)

### 3. Configure CodebeGen

Add these to your `.env` file:

```env
# Supabase Storage Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
SUPABASE_BUCKET=codebegen-projects

# Enable cloud storage
USE_CLOUD_STORAGE=true

# Optional: Configure cache
CACHE_PATH=./storage/cache
CACHE_TTL_HOURS=24
```

### 4. Bucket Creation

The bucket will be created automatically when you start the backend. But you can also create it manually:

1. Go to **Storage** in the Supabase dashboard
2. Click **"New bucket"**
3. Set name: `codebegen-projects`
4. Make it **Private** (important for security!)
5. Click **"Create bucket"**

## 🔒 Security Setup

### Row Level Security (RLS)

For maximum security, you should set up RLS policies:

1. Go to **Storage** → **Policies**
2. Click **"New policy"**
3. Select your bucket: `codebegen-projects`

#### Policy 1: Read Access (authenticated users)
```sql
-- Name: "Users can read their own project files"
-- Operation: SELECT
-- Target roles: authenticated

-- Policy definition:
bucket_id = 'codebegen-projects'
AND (storage.foldername(name))[1] IN (
  SELECT project_id::text FROM projects WHERE user_id = auth.uid()
)
```

#### Policy 2: Write Access (authenticated users)
```sql
-- Name: "Users can upload to their own projects"
-- Operation: INSERT
-- Target roles: authenticated

-- Policy definition:
bucket_id = 'codebegen-projects'
AND (storage.foldername(name))[1] IN (
  SELECT project_id::text FROM projects WHERE user_id = auth.uid()
)
```

#### Policy 3: Delete Access (authenticated users)
```sql
-- Name: "Users can delete their own project files"
-- Operation: DELETE
-- Target roles: authenticated

-- Policy definition:
bucket_id = 'codebegen-projects'
AND (storage.foldername(name))[1] IN (
  SELECT project_id::text FROM projects WHERE user_id = auth.uid()
)
```

**Note**: These policies assume you're using Supabase Auth. If you're using a different auth system, adjust the policies accordingly or use the service_role key (which bypasses RLS).

## 🧪 Testing Your Setup

### Test 1: Backend Startup
```bash
python -m uvicorn app.main:app --reload
```

Check logs for:
```
✅ Supabase storage initialized (bucket: codebegen-projects)
✅ Hybrid storage initialized (local + cloud)
```

### Test 2: Generate a Project
```bash
curl -X POST http://localhost:8000/api/v1/generations/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "prompt": "Create a simple FastAPI todo API",
    "project_id": "test-project-123"
  }'
```

### Test 3: Check Supabase Dashboard
1. Go to **Storage** in Supabase dashboard
2. Open `codebegen-projects` bucket
3. You should see: `{project_id}/generations/v1__{generation_id}.tar.gz`

## 📊 Storage Structure

```
codebegen-projects/
└── {project_id}/
    └── generations/
        ├── v1__{generation_id}.tar.gz
        ├── v2__{generation_id}.tar.gz
        └── v3__{generation_id}.tar.gz
```

Each `.tar.gz` file contains:
- `source/` - All generated source files
- `artifacts/` - Build artifacts, logs, etc.
- `manifest.json` - Generation metadata

## 🔄 Migrating Existing Projects

If you have existing local projects, use the migration script:

### Dry Run (preview only)
```bash
python scripts/migrate_to_supabase.py --dry-run
```

### Actual Migration
```bash
python scripts/migrate_to_supabase.py
```

### Migrate Specific Project
```bash
python scripts/migrate_to_supabase.py --project-id abc-123
```

The script will:
- ✅ Scan local storage
- ✅ Compress projects to tar.gz
- ✅ Upload to Supabase
- ✅ Verify uploads
- ✅ Generate report
- ✅ Keep local copies (non-destructive)

## 🎛️ Configuration Options

### Disable Cloud Storage
```env
USE_CLOUD_STORAGE=false
```
System reverts to local-only mode (backward compatible).

### Adjust Cache TTL
```env
CACHE_TTL_HOURS=48  # Keep cached files for 48 hours
```

### Enable Auto-Cleanup
```env
AUTO_CLEANUP_ENABLED=true
CLEANUP_INTERVAL_HOURS=6
MAX_CACHE_AGE_HOURS=72
```

## 🐛 Troubleshooting

### Error: "Failed to initialize Supabase storage"

**Possible causes:**
1. Invalid credentials
2. Project URL incorrect
3. Network issues

**Solutions:**
- Double-check `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
- Test connection: `curl https://your-project.supabase.co`
- Check firewall/proxy settings

### Error: "Bucket creation failed"

**Possible causes:**
1. Bucket already exists
2. Insufficient permissions

**Solutions:**
- Create bucket manually in dashboard
- Verify you're using `service_role` key (not `anon` key)

### Upload Failures

**Possible causes:**
1. File too large
2. Network timeout
3. Supabase quota exceeded

**Solutions:**
- Check Supabase dashboard for usage/limits
- Increase timeout settings
- Upgrade Supabase plan if needed

### Downloads Not Working

**Possible causes:**
1. File not uploaded yet (async upload in progress)
2. Cache expired and cloud file missing
3. Signed URL expired

**Solutions:**
- Wait for upload to complete (check logs)
- Check Supabase dashboard for file existence
- Generate new signed URL

## 📈 Monitoring

### Check Upload Status
```bash
# View backend logs
tail -f logs/app.log | grep -i "upload\|supabase"
```

### Storage Usage
Go to **Settings** → **Usage** in Supabase dashboard to monitor:
- Storage size
- Bandwidth
- API requests

### Cache Status
```bash
# Check cache directory size
du -sh ./storage/cache

# List cached projects
ls -lh ./storage/cache/
```

## 🔧 Advanced Configuration

### Custom Bucket Name
```env
SUPABASE_BUCKET=my-custom-bucket-name
```

### Multiple Environments
```env
# Development
SUPABASE_URL=https://dev-project.supabase.co
SUPABASE_SERVICE_KEY=dev-key

# Production
SUPABASE_URL=https://prod-project.supabase.co
SUPABASE_SERVICE_KEY=prod-key
```

### Performance Tuning
```env
# Aggressive caching for frequently accessed projects
CACHE_TTL_HOURS=168  # 1 week

# Conservative cleanup (keep more in cache)
MAX_CACHE_AGE_HOURS=336  # 2 weeks
```

## 🆘 Support

### Documentation
- [Supabase Storage Docs](https://supabase.com/docs/guides/storage)
- [CodebeGen Backend README](../README.md)

### Common Issues
- [GitHub Issues](https://github.com/SamuelOshin/codebegen_be/issues)

### Contact
- Open an issue on GitHub
- Join our Discord community
- Email: support@codebegen.com

## ✅ Checklist

After setup, verify:
- [ ] Supabase project created
- [ ] Credentials added to `.env`
- [ ] Backend starts without errors
- [ ] Bucket appears in Supabase dashboard
- [ ] Test generation uploads successfully
- [ ] Download URLs work
- [ ] RLS policies configured (if using Supabase Auth)
- [ ] Existing projects migrated (if applicable)

---

**Last Updated**: October 2025  
**Version**: 1.0.0
