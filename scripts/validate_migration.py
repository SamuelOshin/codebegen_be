"""
Migration Validation Script

This script validates the database migration for generation versioning.
Run this AFTER applying the migration to ensure everything worked correctly.

Usage:
    python scripts/validate_migration.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, text
from app.core.database import async_session_maker
from app.models.generation import Generation
from app.models.project import Project


async def validate_migration():
    """Validate that the migration was applied correctly."""
    
    print("🔍 Validating Migration: Generation Versioning & Active Tracking\n")
    
    async with async_session_maker() as session:
        try:
            # 1. Check if new columns exist
            print("1️⃣ Checking if new columns exist...")
            
            # Check generations table columns
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'generations' 
                AND column_name IN ('version', 'version_name', 'is_active', 'storage_path', 
                                   'file_count', 'total_size_bytes', 'diff_from_previous', 'changes_summary')
            """))
            gen_columns = [row[0] for row in result.fetchall()]
            
            expected_gen_cols = ['version', 'version_name', 'is_active', 'storage_path', 
                                'file_count', 'total_size_bytes', 'diff_from_previous', 'changes_summary']
            
            if set(gen_columns) == set(expected_gen_cols):
                print("   ✅ All generation columns added successfully")
            else:
                missing = set(expected_gen_cols) - set(gen_columns)
                print(f"   ❌ Missing columns in generations: {missing}")
                return False
            
            # Check projects table columns
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'projects' 
                AND column_name IN ('active_generation_id', 'latest_version')
            """))
            proj_columns = [row[0] for row in result.fetchall()]
            
            expected_proj_cols = ['active_generation_id', 'latest_version']
            
            if set(proj_columns) == set(expected_proj_cols):
                print("   ✅ All project columns added successfully")
            else:
                missing = set(expected_proj_cols) - set(proj_columns)
                print(f"   ❌ Missing columns in projects: {missing}")
                return False
            
            # 2. Check foreign key constraint
            print("\n2️⃣ Checking foreign key constraint...")
            result = await session.execute(text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'projects' 
                AND constraint_name = 'fk_projects_active_generation'
            """))
            
            if result.fetchone():
                print("   ✅ Foreign key constraint created successfully")
            else:
                print("   ❌ Foreign key constraint missing")
                return False
            
            # 3. Check version numbers assigned
            print("\n3️⃣ Checking version numbers for existing generations...")
            result = await session.execute(
                select(func.count(Generation.id)).where(Generation.version.isnot(None))
            )
            versioned_count = result.scalar()
            
            result = await session.execute(select(func.count(Generation.id)))
            total_count = result.scalar()
            
            if versioned_count == total_count and total_count > 0:
                print(f"   ✅ All {total_count} generations have version numbers assigned")
            elif total_count == 0:
                print("   ℹ️  No existing generations to version (empty database)")
            else:
                print(f"   ❌ Only {versioned_count}/{total_count} generations have version numbers")
                return False
            
            # 4. Check storage_path populated
            print("\n4️⃣ Checking storage paths...")
            result = await session.execute(
                select(func.count(Generation.id)).where(Generation.storage_path.isnot(None))
            )
            path_count = result.scalar()
            
            if path_count == total_count and total_count > 0:
                print(f"   ✅ All {total_count} generations have storage paths")
            elif total_count == 0:
                print("   ℹ️  No existing generations to check")
            else:
                print(f"   ⚠️  Only {path_count}/{total_count} generations have storage paths")
            
            # 5. Check version sequencing per project
            print("\n5️⃣ Checking version sequences are correct...")
            result = await session.execute(text("""
                SELECT project_id, COUNT(*) as gen_count, MAX(version) as max_version
                FROM generations
                GROUP BY project_id
                HAVING COUNT(*) != MAX(version)
            """))
            
            issues = result.fetchall()
            if not issues:
                print("   ✅ All projects have correct version sequences")
            else:
                print(f"   ⚠️  {len(issues)} projects have version sequence issues")
                for project_id, gen_count, max_version in issues:
                    print(f"      Project {project_id}: {gen_count} generations, max version {max_version}")
            
            # 6. Check latest_version on projects
            print("\n6️⃣ Checking project latest_version values...")
            result = await session.execute(
                select(func.count(Project.id)).where(Project.latest_version > 0)
            )
            projects_with_versions = result.scalar()
            
            result = await session.execute(
                select(func.count(Project.id))
            )
            total_projects = result.scalar()
            
            if total_projects == 0:
                print("   ℹ️  No projects in database")
            else:
                print(f"   ✅ {projects_with_versions}/{total_projects} projects have latest_version set")
            
            # 7. Check active_generation_id
            print("\n7️⃣ Checking active generation assignments...")
            result = await session.execute(
                select(func.count(Project.id)).where(Project.active_generation_id.isnot(None))
            )
            active_count = result.scalar()
            
            if total_projects == 0:
                print("   ℹ️  No projects to check")
            else:
                print(f"   ✅ {active_count}/{total_projects} projects have active generation set")
            
            # 8. Check is_active flag consistency
            print("\n8️⃣ Checking is_active flag consistency...")
            result = await session.execute(text("""
                SELECT COUNT(*) 
                FROM generations g
                JOIN projects p ON p.active_generation_id = g.id
                WHERE g.is_active = false
            """))
            inconsistent = result.scalar()
            
            if inconsistent == 0:
                print("   ✅ All active generations have is_active=true")
            else:
                print(f"   ⚠️  {inconsistent} active generations have is_active=false")
            
            print("\n" + "="*60)
            print("✅ Migration validation completed successfully!")
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Validation failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run validation."""
    success = await validate_migration()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
