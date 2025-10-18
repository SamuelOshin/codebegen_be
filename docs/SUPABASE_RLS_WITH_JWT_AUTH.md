# Integrating Supabase Storage RLS with Your JWT Auth System

## Overview

Your CodebeGen backend uses **custom JWT authentication** (not Supabase Auth). This means:
- ✅ User IDs are in JWT token claims (`sub`)
- ✅ Stored in your PostgreSQL `users` table
- ✅ Needs custom RLS policies for Supabase Storage

## 🔑 Your Auth System

```python
# From: app/auth/dependencies.py
# JWT Token contains: {"sub": user_id, ...}
# Decoded by: jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

## 🔒 Two Approaches for RLS Policies

### Approach 1: Use Service Role Key (Recommended for Now)

**Simplest approach** - The backend uses `SUPABASE_SERVICE_KEY` which **bypasses RLS entirely**.

**Pros:**
- ✅ No RLS policy setup needed
- ✅ Backend manages all authorization
- ✅ Your JWT auth controls access
- ✅ Fastest implementation
- ✅ Easy to debug

**Cons:**
- Direct Supabase Storage API calls need to validate JWT themselves
- Not suitable if frontend calls Supabase Storage directly

**Current Status:** Your implementation already uses this approach!

```python
# From: app/services/supabase_storage_service.py
supabase = create_client(
    settings.SUPABASE_URL, 
    settings.SUPABASE_SERVICE_KEY  # ← Bypasses RLS
)
```

---

### Approach 2: Custom RLS Policies (Advanced)

For maximum security, implement RLS policies that work with your JWT system.

**Setup Steps:**

#### Step 1: Store User IDs in Supabase Auth

You have two options:

**Option A: Sync Your Users to Supabase Auth**
```python
# Create a Supabase auth user for each CodebeGen user
# Store their CodebeGen user_id in custom claims

{
  "sub": "supabase-auth-id",
  "custom_claims": {
    "codebegen_user_id": "your-user-id"
  }
}
```

**Option B: Use Custom JWT with Supabase (Recommended for you)**
```
Use Supabase's "Custom JWT" feature to trust your JWT tokens
```

#### Step 2: Configure Supabase JWT Settings

1. Go to **Settings** → **API** in Supabase dashboard
2. Find **JWT Settings** section
3. Keep the JWT Secret for now (we'll use Service Role Key instead)

#### Step 3: Create RLS Policies

**For your current system, use this approach:**

Since you control the backend and use Service Role Key, the RLS policies protect against:
- Direct API access without authentication
- Unauthorized access through other means

**Policy 1: Prevent Anonymous Access**
```sql
-- Name: "Prevent anonymous access"
-- Operation: SELECT, INSERT, UPDATE, DELETE
-- Target roles: anon

-- Policy definition:
false  -- Always deny anonymous
```

**Policy 2: Allow Service Role (Backend)**
```sql
-- Name: "Backend service role can manage all"
-- Operation: SELECT, INSERT, UPDATE, DELETE
-- Target roles: service_role

-- Policy definition:
true  -- Always allow service_role
```

#### Step 4: Apply Policies in Supabase

1. Go to **Storage** → **Policies** in Supabase dashboard
2. Select bucket: `codebegen-projects`
3. Add the policies above

---

## 🎯 Best Practice for Your Setup

Your current implementation is **production-ready** because:

✅ **Backend Authorization**
```python
# app/routers/generations.py
async def get_generation(
    generation_id: str,
    current_user: UserResponse = Depends(get_current_user),  # ← JWT validated
    db: AsyncSession = Depends(get_async_db)
):
    # Backend validates user owns this generation
    generation = await generation_repo.get_by_id(generation_id)
    if generation.user_id != current_user.id:
        raise HTTPException(403, "Forbidden")
```

✅ **Service Role Used**
```python
# Backend uses service_role key (bypasses RLS)
# Only authenticated requests reach here
```

✅ **Double Authorization**
```
Request → JWT Validation (FastAPI) → Authorization (Backend Logic) → Supabase
```

---

## 📋 Implementation Checklist

### Current Status (Already Done)
- [x] Service Role Key in `.env`
- [x] Cloud storage initialized
- [x] Backend validates user ownership
- [x] No RLS policies needed yet

### Optional Enhancements
- [ ] Add RLS policies for defense-in-depth
- [ ] Frontend secure URLs for direct downloads
- [ ] Implement signed URLs with expiry

---

## 🔐 Security Comparison

### Your Current Approach (Service Role Key)
```
User Request
    ↓
FastAPI JWT Validation (app/auth/dependencies.py)
    ↓
Business Logic Authorization (e.g., "user owns project?")
    ↓
Service Role API Call to Supabase
    ↓
Success/Error Response

Security: ✅ Strong (multiple validation layers)
Complexity: ✅ Low
```

### Alternative: RLS Policies Only
```
User Request with JWT
    ↓
Supabase Auth JWT Validation
    ↓
RLS Policy Evaluation
    ↓
Success/Error Response

Security: ✅ Strong (RLS enforces all rules)
Complexity: ⚠️ High (requires JWT format compatibility)
```

---

## 💡 Recommendations

### For Production (Current Approach)
**Keep using Service Role Key** because:
1. Your JWT system is custom and robust
2. Backend controls all authorization
3. Simple to implement and debug
4. No RLS policy maintenance needed
5. Works great for backend-driven applications

### Code Example: Current Flow
```python
# User authenticates with JWT
@router.post("/generate")
async def generate(
    request: GenerationRequest,
    current_user: User = Depends(get_current_user),  # JWT validated
):
    # Backend validates ownership
    project = await project_repo.get_by_id(request.project_id)
    if project.user_id != current_user.id:
        raise HTTPException(403)
    
    # Storage helper uses service role (trusted)
    await storage_helper.save_generation_with_cloud(
        project_id=project.id,  # Only accessible user can reach here
        generation_id=generation_id,
        version=version,
        files=files
    )
```

---

## 🚀 If You Want Frontend Direct Access Later

If frontend needs direct Supabase Storage access (e.g., download files without backend):

### Option 1: Signed URLs (Recommended)
```python
# Backend generates time-limited signed URL
download_url = await storage_manager.get_download_url(
    project_id=project_id,
    generation_id=generation_id,
    version=version
)
# Returns: https://...supabase.co/...?token=xyz (1 hour expiry)
# Frontend can download with this URL
```

**Current Status:** ✅ Already implemented!

```python
# From: app/services/storage_integration_helper.py
async def get_download_url_for_generation(
    self,
    project_id: str,
    generation_id: str,
    version: int
) -> Optional[str]:
    """Returns signed cloud URL with local fallback"""
```

### Option 2: Row-Level Security (Advanced)
Would require converting your JWT to Supabase Auth format.

---

## 🎓 Summary

| Aspect | Your System | Status |
|--------|-------------|--------|
| JWT Authentication | ✅ Custom JWT | Working |
| Supabase Access | ✅ Service Role Key | Working |
| RLS Policies | ⏳ Optional | Not needed yet |
| Signed URLs | ✅ Implemented | Download protection |
| Authorization | ✅ Backend validates | Secure |
| Production Ready | ✅ Yes | Go ahead! |

---

## 🔗 Related Files

- **Authentication**: `app/auth/dependencies.py`
- **Storage Helper**: `app/services/storage_integration_helper.py`
- **Generation Endpoints**: `app/routers/generations.py`
- **Config**: `.env` (SUPABASE_SERVICE_KEY)

---

## ✅ Next Steps

1. **No changes needed** - Your system works as-is
2. **Optional**: Add RLS policies for defense-in-depth
3. **Later**: Implement frontend direct downloads if needed

**Status: ✨ READY FOR PRODUCTION**

---

**Last Updated**: October 18, 2025  
**Version**: 1.0.0
