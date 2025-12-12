# Pre-Implementation Discovery - CodeBEGen Preview Tab MVP

**Date**: October 20, 2025  
**Status**: ✅ Discovery Complete  
**Next**: Database Models Implementation

---

## 📋 Existing Components to Reuse (DRY Principle)

### Database Infrastructure
- **Base Model**: `app.models.base.Base` - Extend this for all new models
- **BaseModel**: `app.models.base.BaseModel` - Use for models with ID/timestamps
- **Async Database**: `app.core.database.get_async_db()` - Use for all DB operations
- **Sync Database**: `app.core.database.get_db()` - For migrations only

### Authentication & Security
- **User Dependency**: `app.auth.dependencies.get_current_user` - Use for all authenticated endpoints
- **Token Service**: `app.services.sse_token_service.SSETokenService` - Reuse token generation/validation patterns
- **JWT Security**: `app.core.security.create_access_token()` - For any new token needs

### File Storage
- **Storage Manager**: `app.services.storage_manager.HybridStorageManager` - Use for accessing generation files
- **File Manager**: `app.services.file_manager.FileManager` - Local file operations

### API Patterns
- **Router Registration**: `app.main:app.include_router()` - Follow existing prefix/tag patterns
- **Streaming Response**: `fastapi.responses.StreamingResponse` - Used in `unified_generation.py`
- **Error Handling**: `app.core.exceptions` - Extend existing exception hierarchy

### Existing Models
- **Generation**: `app.models.generation.Generation` - Add preview relationship to this
- **User**: `app.models.user.User` - Reference for ownership
- **Project**: `app.models.project.Project` - Reference for project context

---

## 🆕 Components to Create (No Duplicates)

### Database Models
- **PreviewInstance**: New model for preview sessions
- **PreviewLog**: New model for log storage

### Utilities
- **PortAllocator**: New utility (no existing port management found)
- **TokenGenerator**: Extend existing SSE token patterns (no generic token util found)

### Services
- **PreviewLogStreamer**: New service for SSE streaming (no existing subprocess/streaming found)
- **PreviewService**: New service for launch/stop logic
- **PreviewProxyService**: New service for HTTP proxying
- **EndpointExtractor**: New utility for parsing FastAPI routes

### API Endpoints
- **Preview Router**: 7 new endpoints following existing patterns
- **Background Cleanup**: New scheduled task

---

## 🔍 Key Findings

### ✅ What Exists (Reuse)
1. **Database sessions**: Use `Depends(get_async_db)` pattern
2. **User authentication**: Use `Depends(get_current_user)` 
3. **File access**: Use `HybridStorageManager` for generation files
4. **Token generation**: Study `SSETokenService` patterns
5. **Router structure**: Follow `unified_generation.py` patterns
6. **Exception handling**: Extend `app.core.exceptions`

### ❌ What Doesn't Exist (Create)
1. **Port allocation**: No existing port management utilities
2. **Subprocess management**: No existing subprocess patterns found
3. **SSE for logs**: Existing streaming is for generation progress, not logs
4. **HTTP proxying**: No existing proxy utilities
5. **Preview models**: No existing preview-related database models

### ⚠️ Potential Breaking Changes (Avoid)
1. **Don't modify existing models** without adding relationships
2. **Don't change existing API endpoints** or response formats
3. **Don't alter existing authentication flow**
4. **Don't modify existing file storage patterns**

---

## 🏗️ Implementation Plan

### Phase 1: Foundation (Non-Breaking)
1. **Models**: Create PreviewInstance + PreviewLog (extend Base)
2. **Migration**: Alembic migration with proper FKs
3. **Utilities**: PortAllocator + token utilities
4. **Services**: PreviewLogStreamer (core SSE functionality)

### Phase 2: API Layer
1. **Services**: PreviewService + PreviewProxyService + EndpointExtractor
2. **Router**: 7 endpoints following existing patterns
3. **Registration**: Add to main.py router list

### Phase 3: Testing & Polish
1. **Tests**: Unit tests (>90% coverage) + Integration tests
2. **Cleanup**: Background task for expired previews
3. **Frontend**: React hook + terminal component

---

## 📊 Success Metrics
- [ ] Zero breaking changes to existing functionality
- [ ] All new code follows existing patterns
- [ ] >90% test coverage for new components
- [ ] Preview launches in <3 seconds
- [ ] Real-time SSE log streaming works
- [ ] All 7 API endpoints functional

---

**Ready to proceed with database models implementation.**