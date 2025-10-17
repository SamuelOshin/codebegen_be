# 🚀 Version Tracking Migration Guide

## Overview

This guide provides step-by-step instructions for migrating the CodebeGen backend from flat file storage to hierarchical version-tracked storage with enhanced generation management capabilities.

## Migration Summary

### What Changed
- **Database Schema**: Added version tracking fields to `generations` and `projects` tables
- **File Storage**: Migrated from flat structure to hierarchical `./storage/projects/{project_id}/generations/v{version}__{generation_id}/`
- **API Endpoints**: Added 5 new version management endpoints
- **Service Layer**: Introduced `GenerationService` for business logic encapsulation
- **Architecture**: Enhanced with proper service layer pattern and version tracking

### Key Benefits
- **Version Control**: Track multiple generations per project with automatic versioning
- **Active Generation Management**: Set and switch between different versions
- **Diff Generation**: Compare changes between versions
- **Hierarchical Storage**: Organized file structure with metadata tracking
- **Backward Compatibility**: Existing generations continue to work

## Prerequisites

### Environment Requirements
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Alembic 1.12+
- Access to production database backups

### Pre-Migration Checklist
- [ ] Create full database backup
- [ ] Create full file system backup of `./storage/` directory
- [ ] Verify current database schema matches expected state
- [ ] Test migration on staging environment first
- [ ] Schedule maintenance window (estimated: 30-60 minutes)
- [ ] Notify stakeholders of planned downtime

## Step-by-Step Migration

### Phase 1: Database Migration

#### 1.1 Backup Current State
```bash
# Create database backup
pg_dump -h localhost -U username -d codebegen > codebegen_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# Create file system backup
tar -czf storage_backup_$(date +%Y%m%d_%H%M%S).tar.gz ./storage/
```

#### 1.2 Run Database Migration
```bash
# Activate virtual environment
source .venv/bin/activate  # or appropriate activation command

# Generate SQL preview (optional, for review)
alembic upgrade 39e7f45c72f1 --sql > migration_preview.sql

# Apply the migration
alembic upgrade 39e7f45c72f1

# Verify migration success
alembic current
```

#### 1.3 Validate Database Changes
```bash
# Check that new columns were added
python -c "
from app.core.database import get_db
from sqlalchemy import text

with get_db() as db:
    # Verify generations table
    result = db.execute(text('SELECT version, is_active, storage_path FROM generations LIMIT 1'))
    print('Generations table columns:', result.keys())

    # Verify projects table
    result = db.execute(text('SELECT active_generation_id, latest_version FROM projects LIMIT 1'))
    print('Projects table columns:', result.keys())

    # Check version assignment
    result = db.execute(text('SELECT COUNT(*) as total, COUNT(version) as with_version FROM generations'))
    row = result.fetchone()
    print(f'Total generations: {row.total}, With versions: {row.with_version}')
"
```

### Phase 2: File System Migration

#### 2.1 Verify Storage Directory
```bash
# Check current storage structure
ls -la ./storage/

# Should show empty or flat structure
# New generations will automatically use hierarchical structure
```

#### 2.2 Test New Storage Creation
```bash
# Run a test generation to verify hierarchical storage works
python -c "
from app.services.generation_service import GenerationService
from app.services.file_manager import FileManager
import asyncio

async def test_storage():
    service = GenerationService()
    # This will create the hierarchical structure when saving

asyncio.run(test_storage())
"
```

### Phase 3: Application Deployment

#### 3.1 Update Application Code
```bash
# Pull latest changes (if using version control)
git pull origin main

# Install any new dependencies
pip install -r requirements.txt
```

#### 3.2 Restart Application Services
```bash
# Stop current services
docker-compose down  # or systemctl stop codebegen

# Start with new code
docker-compose up -d  # or systemctl start codebegen

# Verify application starts successfully
curl -f http://localhost:8000/health || echo "Health check failed"
```

### Phase 4: Post-Migration Validation

#### 4.1 API Endpoint Testing
```bash
# Test new version management endpoints
PROJECT_ID=your-test-project-id

# List all versions
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/projects/${PROJECT_ID}/generations

# Get active generation
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/projects/${PROJECT_ID}/generations/active

# Test version comparison (if multiple versions exist)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/projects/${PROJECT_ID}/generations/compare/1/2
```

#### 4.2 Database Validation
```bash
# Verify all generations have versions
python -c "
from app.core.database import get_db
from sqlalchemy import text

with get_db() as db:
    result = db.execute(text('''
        SELECT
            COUNT(*) as total_generations,
            COUNT(version) as with_versions,
            COUNT(CASE WHEN is_active = true THEN 1 END) as active_generations,
            MAX(version) as max_version
        FROM generations
    '''))
    row = result.fetchone()
    print(f'Validation Results:')
    print(f'  Total generations: {row.total_generations}')
    print(f'  With versions: {row.with_versions}')
    print(f'  Active generations: {row.active_generations}')
    print(f'  Max version: {row.max_version}')
"
```

#### 4.3 File System Validation
```bash
# Check hierarchical structure creation
find ./storage/projects/ -type d -name "v*__*" | head -5

# Verify manifest.json files exist
find ./storage/projects/ -name "manifest.json" | wc -l

# Check for active generation symlinks
find ./storage/projects/ -type l -name "active" | head -5
```

## Rollback Procedures

### Emergency Rollback
If critical issues occur during migration:

#### 1. Immediate Application Rollback
```bash
# Revert to previous deployment
git checkout PREVIOUS_COMMIT_HASH
docker-compose down && docker-compose up -d
```

#### 2. Database Rollback
```bash
# Rollback migration (if needed)
alembic downgrade -1

# Or restore from backup
psql -h localhost -U username -d codebegen < codebegen_pre_migration_DATE.sql
```

#### 3. File System Rollback
```bash
# Restore file backup
rm -rf ./storage/
tar -xzf storage_backup_DATE.tar.gz
```

### Partial Rollback Scenarios

#### Database Only Rollback
If only database issues occur:
```bash
alembic downgrade 39e7f45c72f1
# Application will fall back to old behavior
```

#### File System Only Rollback
If file system issues occur:
```bash
# Remove new hierarchical directories
find ./storage/projects/ -type d -name "generations" -exec rm -rf {} +

# Restore flat structure from backup
tar -xzf storage_backup_DATE.tar.gz
```

## Monitoring and Alerts

### Key Metrics to Monitor
- **API Response Times**: New endpoints should perform within 200ms
- **Database Query Performance**: Version queries should not exceed 100ms
- **Storage Usage**: Monitor disk space for hierarchical structure
- **Error Rates**: Watch for 5xx errors on new endpoints

### Alert Conditions
- Migration completion rate < 100%
- New endpoint error rate > 5%
- Database connection timeouts
- File system permission errors

## Troubleshooting

### Common Issues

#### Issue: Migration Fails with Foreign Key Errors
```
ERROR: insert or update on table "projects" violates foreign key constraint
```
**Solution**: Ensure all referenced generations exist before migration
```sql
-- Check for orphaned references
SELECT p.id, p.active_generation_id
FROM projects p
LEFT JOIN generations g ON p.active_generation_id = g.id
WHERE p.active_generation_id IS NOT NULL AND g.id IS NULL;
```

#### Issue: Version Numbers Not Sequential
**Solution**: Version numbers are assigned based on creation order, not sequentially. This is expected behavior.

#### Issue: File System Permissions
```
ERROR: Permission denied when creating directories
```
**Solution**: Ensure application has write permissions to `./storage/`
```bash
chown -R appuser:appuser ./storage/
chmod -R 755 ./storage/
```

#### Issue: Active Generation Not Set
**Solution**: Run post-migration script to set active generations
```python
# scripts/set_active_generations.py
from app.core.database import get_db
from sqlalchemy import text

with get_db() as db:
    # Set latest generation as active for each project
    db.execute(text('''
        UPDATE projects
        SET active_generation_id = latest_gen.generation_id
        FROM (
            SELECT DISTINCT ON (project_id)
                project_id,
                id as generation_id
            FROM generations
            WHERE project_id IS NOT NULL
            ORDER BY project_id, version DESC
        ) latest_gen
        WHERE projects.id = latest_gen.project_id
        AND projects.active_generation_id IS NULL
    '''))
    db.commit()
```

### Performance Considerations

#### Database Indexes
After migration, consider adding these indexes for better performance:
```sql
CREATE INDEX idx_generations_project_version ON generations(project_id, version);
CREATE INDEX idx_generations_is_active ON generations(is_active) WHERE is_active = true;
CREATE INDEX idx_projects_active_generation ON projects(active_generation_id);
```

#### File System Optimization
- Monitor inode usage (hierarchical structure creates more directories)
- Consider filesystem type (ext4 recommended for many small files)
- Implement cleanup policies for old generations

## Testing Checklist

### Pre-Production Testing
- [ ] All existing API endpoints work
- [ ] New version management endpoints return correct data
- [ ] File downloads work from both old and new storage
- [ ] Generation creation uses hierarchical storage
- [ ] Version comparison shows correct diffs
- [ ] Active generation switching updates symlinks
- [ ] Database queries perform within acceptable limits

### Load Testing
- [ ] Test with 100+ concurrent generations
- [ ] Verify version listing performance with 50+ versions per project
- [ ] Test file system performance with large generation outputs

## Support and Contacts

### Emergency Contacts
- **Database Issues**: DBA Team - dba@company.com
- **Application Issues**: DevOps Team - devops@company.com
- **AI Pipeline Issues**: ML Team - ml@company.com

### Documentation Links
- [Architecture Overview](docs/architecture.md)
- [API Documentation](docs/openapi.yaml)
- [Deployment Guide](docs/deployment.md)

---

## Migration Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Preparation | 1-2 hours | Backups, staging tests, stakeholder notification |
| Database Migration | 5-10 minutes | Schema changes and data migration |
| File System Migration | 10-15 minutes | Storage restructuring (if needed) |
| Application Deployment | 5-10 minutes | Code deployment and service restart |
| Validation | 15-30 minutes | Testing and monitoring |
| **Total Estimated Time** | **30-60 minutes** | End-to-end migration |

**Last Updated**: October 15, 2025
**Migration Version**: 39e7f45c72f1
