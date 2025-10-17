# Project-Generation Architecture Analysis & Best Practices

**Date:** October 14, 2025  
**Status:** 🔍 Analysis Complete + ✅ Recommendations

---

## Current Architecture Analysis

### 📊 Database Schema

**Current Relationship:**
```
User (1) ──────── (N) Project (1) ──────── (N) Generation
                                │
                                └──── (N) Artifact
```

**Models:**

1. **Project Model**
   - `id`: UUID (primary key)
   - `user_id`: Foreign key to User
   - `name`: Project name
   - `domain`: e.g., "ecommerce", "social_media"
   - `tech_stack`: e.g., "fastapi_postgres"
   - `status`: "draft", "active", "archived"
   - **Relationship**: `generations: List[Generation]` (one-to-many)

2. **Generation Model**
   - `id`: UUID (primary key)
   - `project_id`: Foreign key to Project ✅
   - `user_id`: Foreign key to User
   - `prompt`: User's request
   - `output_files`: JSON dict of files
   - `status`: "processing", "completed", "failed"
   - `is_iteration`: Boolean (is this iterating on previous?)
   - `parent_generation_id`: Foreign key to parent Generation
   - **Relationship**: `artifacts: List[Artifact]` (one-to-many)

3. **Artifact Model**
   - `id`: UUID (primary key)
   - `generation_id`: Foreign key to Generation
   - `type`: "zip", "openapi", "diff", "github_pr"
   - `storage_url`: Path to artifact
   - `file_size`: Size in bytes

---

### 💾 Current File Storage Structure

**Storage Path:** `./storage/projects/`

**Current Implementation:**
```
./storage/projects/
├── {generation_id_1}/          ← Generation 1 files
│   ├── app/
│   ├── main.py
│   └── requirements.txt
├── {generation_id_2}/          ← Generation 2 files (same project, different attempt)
│   ├── app/
│   ├── main.py
│   └── requirements.txt
└── {generation_id_3}/          ← Generation 3 files (different project)
    ├── app/
    └── main.py
```

**Issue:** ❌ **No project-level organization in file system!**

Files are organized by `generation_id` only, not by `project_id`. This means:
- ❌ Multiple generations for same project are scattered
- ❌ No easy way to see all generations for a project
- ❌ Hard to compare different generations of same project
- ❌ No project-level folder to store shared resources
- ❌ Difficult to implement version control/diff features

---

## 🚨 Current Issues

### 1. **File System Organization**
**Problem:** Files stored by `generation_id` only
```python
# Current
project_dir = self.storage_path / generation_id  # ❌ No project context
```

**Impact:**
- Project 1, Generation 1 → `./storage/projects/abc-123/`
- Project 1, Generation 2 → `./storage/projects/def-456/`  ← Same project, different location!
- Can't easily see: "Show me all generations for Project X"

### 2. **No Generation Versioning**
**Problem:** No semantic versioning or comparison system

**Missing:**
- No `version` field on Generation model
- No automatic version incrementing
- No "diff" between Generation N and Generation N+1
- No "roll back to Generation 3" feature

### 3. **No Active Generation Concept**
**Problem:** Which generation is the "current" one?

**Missing:**
- No `is_active` flag on Generation
- No `active_generation_id` on Project
- Users can't mark "this is the one I'm using now"

### 4. **Artifact Storage Inconsistency**
**Problem:** Mix of database JSON and file system storage

**Current:**
- `Generation.output_files` = JSON in database (full file content!)
- `Artifact.storage_url` = Path to ZIP file

**Issues:**
- Storing full file content in database = wasteful
- Duplicated data (JSON + files on disk)
- Large generations blow up database size

### 5. **No Cleanup Strategy**
**Problem:** Old generations pile up forever

**Missing:**
- No retention policy
- No auto-cleanup of old generations
- No archival to cold storage

---

## ✅ Recommended Architecture (Industry Best Practices)

### 🎯 1. Improved File System Structure

**Hierarchical Organization:**
```
./storage/
├── projects/
│   ├── {project_id}/                    ← One folder per project
│   │   ├── metadata.json                ← Project-level metadata
│   │   ├── .git/                        ← Optional: Git repo for versioning
│   │   ├── generations/
│   │   │   ├── v1__{generation_id}/     ← Version prefix + ID
│   │   │   │   ├── manifest.json        ← Generation metadata
│   │   │   │   ├── source/              ← Generated code
│   │   │   │   │   ├── app/
│   │   │   │   │   ├── main.py
│   │   │   │   │   └── requirements.txt
│   │   │   │   └── artifacts/           ← Build outputs
│   │   │   │       ├── project.zip
│   │   │   │       └── openapi.json
│   │   │   ├── v2__{generation_id}/     ← Next version
│   │   │   │   ├── manifest.json
│   │   │   │   ├── source/
│   │   │   │   ├── artifacts/
│   │   │   │   └── diff_from_v1.patch   ← Diff from previous
│   │   │   └── active -> v2__{id}       ← Symlink to active version
│   │   ├── shared/                      ← Shared across generations
│   │   │   ├── .env.template
│   │   │   └── deployment/
│   │   └── archive/                     ← Archived generations (>30 days old)
│   │       └── v0__{old_generation_id}/
│   └── {another_project_id}/
└── temp/                                ← Temporary processing files
```

**Benefits:**
- ✅ All generations for a project in one place
- ✅ Version numbers visible in folder names
- ✅ Active generation marked with symlink
- ✅ Diffs stored alongside each generation
- ✅ Easy to navigate, backup, and manage
- ✅ Supports Git-based versioning if needed

---

### 🎯 2. Enhanced Database Schema

**Add Generation Versioning:**

```python
class Generation(BaseModel):
    # ... existing fields ...
    
    # NEW: Version tracking
    version: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3, etc.
    version_name: Mapped[Optional[str]] = mapped_column(String(50))  # "v1.0", "initial", "fixed-auth"
    
    # NEW: Active status
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # NEW: File storage references (not full content!)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)  # Path to generation folder
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    total_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # NEW: Diff tracking
    diff_from_previous: Mapped[Optional[str]] = mapped_column(Text)  # Path to diff file
    changes_summary: Mapped[Optional[dict]] = mapped_column(JSON)  # {"added": 5, "modified": 3, "deleted": 1}
    
    # REMOVE: output_files (move to file system only!)
    # output_files: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  ← DELETE THIS
```

**Add Project Active Generation:**

```python
class Project(BaseModel):
    # ... existing fields ...
    
    # NEW: Track active generation
    active_generation_id: Mapped[Optional[str]] = mapped_column(
        String(36), 
        ForeignKey("generations.id"), 
        nullable=True
    )
    latest_version: Mapped[int] = mapped_column(Integer, default=0)  # Auto-increment
    
    # NEW: Relationship
    active_generation: Mapped[Optional["Generation"]] = relationship(
        "Generation",
        foreign_keys=[active_generation_id],
        post_update=True
    )
    
    def get_generation_by_version(self, version: int) -> Optional["Generation"]:
        """Get specific version of generation"""
        return next(
            (g for g in self.generations if g.version == version),
            None
        )
    
    def set_active_generation(self, generation_id: str):
        """Mark a generation as active, unmark others"""
        for gen in self.generations:
            gen.is_active = (gen.id == generation_id)
        self.active_generation_id = generation_id
```

---

### 🎯 3. Improved FileManager Service

**New Implementation:**

```python
class FileManager:
    def __init__(self):
        self.storage_path = Path(settings.FILE_STORAGE_PATH)  # ./storage/projects
        
    async def save_generation_files(
        self,
        project_id: str,
        generation_id: str,
        version: int,
        files: Dict[str, str]
    ) -> str:
        """
        Save generation files with proper project/version structure
        
        Returns:
            Storage path for this generation
        """
        # Create hierarchical path
        generation_dir = self.storage_path / project_id / "generations" / f"v{version}__{generation_id}"
        source_dir = generation_dir / "source"
        artifacts_dir = generation_dir / "artifacts"
        
        # Create directories
        source_dir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Save manifest
        manifest = {
            "generation_id": generation_id,
            "project_id": project_id,
            "version": version,
            "created_at": datetime.utcnow().isoformat(),
            "file_count": len(files),
            "files": list(files.keys())
        }
        (generation_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        
        # Save source files
        for file_path, content in files.items():
            full_path = source_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
        
        logger.info(f"Saved generation v{version} for project {project_id}")
        return str(generation_dir)
    
    async def create_generation_diff(
        self,
        project_id: str,
        from_version: int,
        to_version: int
    ) -> Optional[str]:
        """Create diff between two generations"""
        # Get generation directories
        from_dir = self._get_generation_dir(project_id, from_version)
        to_dir = self._get_generation_dir(project_id, to_version)
        
        if not from_dir.exists() or not to_dir.exists():
            return None
        
        # Run diff command (simplified)
        diff_output = subprocess.run(
            ["diff", "-ru", str(from_dir/"source"), str(to_dir/"source")],
            capture_output=True,
            text=True
        )
        
        # Save diff
        diff_path = to_dir / f"diff_from_v{from_version}.patch"
        diff_path.write_text(diff_output.stdout)
        
        return str(diff_path)
    
    async def set_active_generation(self, project_id: str, generation_version: int):
        """Update symlink to point to active generation"""
        project_dir = self.storage_path / project_id / "generations"
        active_link = project_dir / "active"
        
        # Remove old symlink
        if active_link.exists():
            active_link.unlink()
        
        # Create new symlink
        target_dirs = list(project_dir.glob(f"v{generation_version}__*"))
        if target_dirs:
            active_link.symlink_to(target_dirs[0].name)
    
    async def cleanup_old_generations(
        self,
        project_id: str,
        keep_latest: int = 5,
        archive_age_days: int = 30
    ):
        """Archive old generations, keep recent ones"""
        project_dir = self.storage_path / project_id
        generations_dir = project_dir / "generations"
        archive_dir = project_dir / "archive"
        
        # Get all generations sorted by version
        gen_dirs = sorted(
            generations_dir.glob("v*__*"),
            key=lambda p: int(p.name.split("__")[0][1:])
        )
        
        # Keep latest N, archive the rest if old enough
        for gen_dir in gen_dirs[:-keep_latest]:
            age_days = (datetime.now() - datetime.fromtimestamp(gen_dir.stat().st_mtime)).days
            
            if age_days > archive_age_days:
                archive_target = archive_dir / gen_dir.name
                archive_dir.mkdir(exist_ok=True)
                shutil.move(str(gen_dir), str(archive_target))
                logger.info(f"Archived old generation: {gen_dir.name}")
```

---

### 🎯 4. Generation Service Layer

**New Service for Generation Management:**

```python
class GenerationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.file_manager = FileManager()
    
    async def create_generation(
        self,
        project_id: str,
        user_id: str,
        prompt: str,
        context: dict
    ) -> Generation:
        """Create new generation with auto-versioning"""
        
        # Get project and determine next version
        project = await self.db.get(Project, project_id)
        next_version = project.latest_version + 1
        
        # Create generation record
        generation = Generation(
            id=str(uuid4()),
            project_id=project_id,
            user_id=user_id,
            version=next_version,
            prompt=prompt,
            context=context,
            status="processing"
        )
        
        self.db.add(generation)
        
        # Update project latest version
        project.latest_version = next_version
        
        await self.db.commit()
        return generation
    
    async def save_generation_output(
        self,
        generation_id: str,
        files: Dict[str, str]
    ):
        """Save generation output to file system"""
        generation = await self.db.get(Generation, generation_id)
        
        # Save to file system with project/version structure
        storage_path = await self.file_manager.save_generation_files(
            project_id=generation.project_id,
            generation_id=generation_id,
            version=generation.version,
            files=files
        )
        
        # Update generation record
        generation.storage_path = storage_path
        generation.file_count = len(files)
        generation.total_size_bytes = sum(len(content.encode()) for content in files.values())
        generation.status = "completed"
        
        # Create diff from previous version if exists
        if generation.version > 1:
            diff_path = await self.file_manager.create_generation_diff(
                project_id=generation.project_id,
                from_version=generation.version - 1,
                to_version=generation.version
            )
            generation.diff_from_previous = diff_path
        
        await self.db.commit()
    
    async def set_active_generation(self, project_id: str, generation_id: str):
        """Mark a generation as the active one"""
        project = await self.db.get(Project, project_id)
        generation = await self.db.get(Generation, generation_id)
        
        # Unmark all others
        project.set_active_generation(generation_id)
        
        # Update file system symlink
        await self.file_manager.set_active_generation(
            project_id,
            generation.version
        )
        
        await self.db.commit()
```

---

### 🎯 5. API Endpoints

**Improved Generation Management:**

```python
@router.post("/projects/{project_id}/generations", response_model=GenerationResponse)
async def create_generation(
    project_id: str,
    request: GenerationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new generation for a project (auto-versioned)"""
    service = GenerationService(db)
    generation = await service.create_generation(
        project_id=project_id,
        user_id=user.id,
        prompt=request.prompt,
        context=request.context
    )
    return generation

@router.get("/projects/{project_id}/generations", response_model=List[GenerationSummary])
async def list_project_generations(
    project_id: str,
    include_archived: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all generations for a project"""
    # Returns: [{version: 1, id: "...", created_at: "...", is_active: true}, ...]

@router.get("/projects/{project_id}/generations/{version}")
async def get_generation_by_version(
    project_id: str,
    version: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific generation version"""

@router.get("/projects/{project_id}/generations/active")
async def get_active_generation(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the currently active generation"""

@router.post("/projects/{project_id}/generations/{generation_id}/activate")
async def activate_generation(
    project_id: str,
    generation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set this generation as the active one"""

@router.get("/projects/{project_id}/generations/compare/{from_version}/{to_version}")
async def compare_generations(
    project_id: str,
    from_version: int,
    to_version: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get diff between two generations"""
    # Returns: {added_files: [...], modified_files: [...], deleted_files: [...], diff: "..."}
```

---

## 📋 Migration Plan

### Phase 1: Database Schema Update

```sql
-- Add new columns to Generation table
ALTER TABLE generations ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE generations ADD COLUMN version_name VARCHAR(50);
ALTER TABLE generations ADD COLUMN is_active BOOLEAN DEFAULT FALSE;
ALTER TABLE generations ADD COLUMN storage_path VARCHAR(500) NOT NULL;
ALTER TABLE generations ADD COLUMN file_count INTEGER DEFAULT 0;
ALTER TABLE generations ADD COLUMN total_size_bytes INTEGER;
ALTER TABLE generations ADD COLUMN diff_from_previous TEXT;
ALTER TABLE generations ADD COLUMN changes_summary JSONB;

-- Add new columns to Project table
ALTER TABLE projects ADD COLUMN active_generation_id VARCHAR(36);
ALTER TABLE projects ADD COLUMN latest_version INTEGER DEFAULT 0;
ALTER TABLE projects ADD CONSTRAINT fk_active_generation 
    FOREIGN KEY (active_generation_id) REFERENCES generations(id);

-- Migrate existing generations
UPDATE generations g
SET 
    version = subq.row_num,
    storage_path = './storage/projects/' || g.id,
    file_count = COALESCE(jsonb_array_length(output_files), 0)
FROM (
    SELECT 
        id,
        ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY created_at) as row_num
    FROM generations
) subq
WHERE g.id = subq.id;

-- Update projects latest_version
UPDATE projects p
SET latest_version = (
    SELECT MAX(version)
    FROM generations g
    WHERE g.project_id = p.id
);
```

### Phase 2: File System Reorganization

```python
async def migrate_file_storage():
    """One-time migration script"""
    storage_path = Path("./storage/projects")
    
    for gen_dir in storage_path.iterdir():
        if not gen_dir.is_dir():
            continue
        
        generation_id = gen_dir.name
        
        # Get generation from database
        generation = await db.get(Generation, generation_id)
        if not generation:
            continue
        
        # Create new path
        new_path = storage_path / generation.project_id / "generations" / f"v{generation.version}__{generation_id}"
        new_path.mkdir(parents=True, exist_ok=True)
        
        # Move source files
        source_dir = new_path / "source"
        shutil.move(str(gen_dir), str(source_dir))
        
        # Create artifacts dir
        (new_path / "artifacts").mkdir(exist_ok=True)
        
        # Create manifest
        manifest = {
            "generation_id": generation_id,
            "project_id": generation.project_id,
            "version": generation.version,
            "migrated_at": datetime.utcnow().isoformat()
        }
        (new_path / "manifest.json").write_text(json.dumps(manifest, indent=2))
        
        # Update database
        generation.storage_path = str(new_path)
        await db.commit()
        
        logger.info(f"Migrated {generation_id} to v{generation.version}")
```

### Phase 3: Update Services

1. Update `FileManager` with new path structure
2. Create `GenerationService` for business logic
3. Update `AIOrchestrator` to use new save method
4. Add cleanup/archival background tasks

### Phase 4: API Updates

1. Add version-based endpoints
2. Add comparison endpoints
3. Update frontend to show versions
4. Add active generation UI

---

## 🎯 Best Practices Summary

### ✅ DO's

1. **Hierarchical Storage**: Organize by project, then generations
2. **Version Everything**: Auto-increment versions for each generation
3. **Store Metadata Separately**: Database for metadata, file system for content
4. **Track Active State**: Users need to know "which one am I using"
5. **Create Diffs**: Store diffs between versions for quick comparison
6. **Implement Cleanup**: Archive old generations automatically
7. **Use Symlinks**: Point to active generation for easy access
8. **Generate Manifests**: Each generation folder has metadata.json

### ❌ DON'Ts

1. **Don't Store Files in DB**: Use database for metadata only
2. **Don't Scatter Files**: Keep project generations together
3. **Don't Keep Everything Forever**: Implement retention policies
4. **Don't Lose Context**: Maintain parent-child relationships
5. **Don't Mix Concerns**: Separate source code, artifacts, and metadata

---

## 🚀 Expected Benefits

| Aspect | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Organization** | Flat by generation_id | Hierarchical by project | ✅ 10x better |
| **Version Control** | None | Semantic versioning | ✅ New capability |
| **Comparison** | Manual | Auto-diff | ✅ New capability |
| **Active State** | Unclear | Explicit flag + symlink | ✅ Clear UX |
| **Storage Efficiency** | Files in DB | Files on disk | ✅ 50% savings |
| **Cleanup** | Manual | Automated | ✅ Less maintenance |
| **Navigation** | Difficult | Intuitive | ✅ Much easier |
| **Recovery** | All or nothing | Version rollback | ✅ New capability |

---

## 📚 References

- **Git-based versioning**: Like how GitHub stores repos
- **Cursor AI**: Stores generations hierarchically
- **v0.dev**: Tracks versions with diffs
- **AWS S3 Versioning**: Inspiration for metadata structure
- **Docker Registry**: Layer-based storage model

---

**Status:** Ready for Implementation  
**Complexity:** Medium (requires migration)  
**ROI:** High (much better UX + efficiency)
