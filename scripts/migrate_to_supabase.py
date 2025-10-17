#!/usr/bin/env python3
"""
Migration script to upload existing local projects to Supabase Storage.

Usage:
    python scripts/migrate_to_supabase.py [options]

Options:
    --dry-run           Preview migration without uploading
    --project-id ID     Migrate only a specific project
    --verify            Verify uploads after migration
    --no-progress       Disable progress bars
"""

import sys
import argparse
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from tqdm import tqdm

from app.core.config import settings
from app.services.supabase_storage_service import SupabaseStorageService


class MigrationReport:
    """Track migration progress and results."""
    
    def __init__(self):
        self.total_projects = 0
        self.total_generations = 0
        self.uploaded_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.total_size_bytes = 0
        self.errors: List[Dict] = []
        self.start_time = datetime.now()
    
    def add_success(self, size: int):
        self.uploaded_count += 1
        self.total_size_bytes += size
    
    def add_failure(self, error: str):
        self.failed_count += 1
        self.errors.append({
            "timestamp": datetime.now().isoformat(),
            "error": error
        })
    
    def add_skip(self):
        self.skipped_count += 1
    
    def get_summary(self) -> str:
        duration = datetime.now() - self.start_time
        size_mb = self.total_size_bytes / (1024 * 1024)
        
        summary = f"""
╔═══════════════════════════════════════════════════════════╗
║           SUPABASE MIGRATION REPORT                       ║
╠═══════════════════════════════════════════════════════════╣
║ Projects found:        {self.total_projects:>6}                         ║
║ Generations found:     {self.total_generations:>6}                         ║
║ Successfully uploaded: {self.uploaded_count:>6}                         ║
║ Failed:                {self.failed_count:>6}                         ║
║ Skipped:               {self.skipped_count:>6}                         ║
║ Total size:            {size_mb:>6.2f} MB                     ║
║ Duration:              {str(duration).split('.')[0]:>10}                  ║
╚═══════════════════════════════════════════════════════════╝
"""
        
        if self.errors:
            summary += "\n❌ ERRORS:\n"
            for i, error in enumerate(self.errors[:10], 1):  # Show first 10 errors
                summary += f"  {i}. {error['error']}\n"
            if len(self.errors) > 10:
                summary += f"  ... and {len(self.errors) - 10} more errors\n"
        
        return summary


class SupabaseMigration:
    """Handles migration of local projects to Supabase Storage."""
    
    def __init__(self, dry_run: bool = False, show_progress: bool = True):
        self.dry_run = dry_run
        self.show_progress = show_progress
        self.storage_path = Path(settings.FILE_STORAGE_PATH)
        self.supabase_service = SupabaseStorageService()
        self.report = MigrationReport()
        
        if not self.supabase_service.enabled:
            logger.error("❌ Supabase storage not enabled or configured")
            logger.error("Set USE_CLOUD_STORAGE=true and configure SUPABASE_URL and SUPABASE_SERVICE_KEY")
            sys.exit(1)
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No files will be uploaded")
    
    def scan_projects(self, project_id: Optional[str] = None) -> List[Dict]:
        """
        Scan local storage for projects and generations.
        
        Args:
            project_id: Optional project ID to scan (None = scan all)
            
        Returns:
            List of generation metadata dicts
        """
        generations = []
        
        if not self.storage_path.exists():
            logger.warning(f"Storage path not found: {self.storage_path}")
            return generations
        
        logger.info(f"📂 Scanning storage: {self.storage_path}")
        
        # Scan for new hierarchical structure: {project_id}/generations/v{version}__{generation_id}/
        for project_dir in self.storage_path.iterdir():
            if not project_dir.is_dir():
                continue
            
            # Skip if filtering by project_id
            if project_id and project_dir.name != project_id:
                continue
            
            self.report.total_projects += 1
            
            generations_dir = project_dir / "generations"
            if not generations_dir.exists():
                continue
            
            # Scan generation directories
            for gen_dir in generations_dir.iterdir():
                if not gen_dir.is_dir() or gen_dir.name == "active":
                    continue
                
                # Parse directory name: v{version}__{generation_id}
                try:
                    name_parts = gen_dir.name.split("__")
                    if len(name_parts) != 2:
                        continue
                    
                    version_str = name_parts[0].replace("v", "")
                    generation_id = name_parts[1]
                    version = int(version_str)
                    
                    # Check if manifest exists
                    manifest_path = gen_dir / "manifest.json"
                    metadata = {}
                    if manifest_path.exists():
                        with open(manifest_path) as f:
                            metadata = json.load(f)
                    
                    generations.append({
                        "project_id": project_dir.name,
                        "generation_id": generation_id,
                        "version": version,
                        "path": gen_dir,
                        "metadata": metadata
                    })
                    
                    self.report.total_generations += 1
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"Skipping invalid directory: {gen_dir.name}")
                    continue
        
        logger.info(f"✅ Found {len(generations)} generations in {self.report.total_projects} projects")
        return generations
    
    async def upload_generation(self, gen_info: Dict) -> bool:
        """
        Upload a single generation to Supabase.
        
        Args:
            gen_info: Generation metadata dict
            
        Returns:
            True on success, False on failure
        """
        project_id = gen_info["project_id"]
        generation_id = gen_info["generation_id"]
        version = gen_info["version"]
        gen_path = gen_info["path"]
        
        try:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would upload: {project_id}/v{version}__{generation_id}")
                self.report.add_skip()
                return True
            
            # Upload to Supabase
            cloud_path = await self.supabase_service.upload_generation(
                generation_dir=gen_path,
                project_id=project_id,
                generation_id=generation_id,
                version=version
            )
            
            if cloud_path:
                # Calculate size
                size = sum(f.stat().st_size for f in gen_path.rglob('*') if f.is_file())
                self.report.add_success(size)
                logger.info(f"✅ Uploaded: {project_id}/v{version}__{generation_id} ({size / 1024:.1f} KB)")
                return True
            else:
                self.report.add_failure(f"Upload failed: {project_id}/v{version}__{generation_id}")
                logger.error(f"❌ Upload failed: {project_id}/v{version}__{generation_id}")
                return False
                
        except Exception as e:
            error_msg = f"Error uploading {project_id}/v{version}__{generation_id}: {e}"
            self.report.add_failure(error_msg)
            logger.error(f"❌ {error_msg}")
            return False
    
    async def verify_upload(self, gen_info: Dict) -> bool:
        """
        Verify that a generation was successfully uploaded.
        
        Args:
            gen_info: Generation metadata dict
            
        Returns:
            True if verified, False otherwise
        """
        project_id = gen_info["project_id"]
        generation_id = gen_info["generation_id"]
        version = gen_info["version"]
        
        try:
            # Try to get signed URL (verifies file exists)
            signed_url = await self.supabase_service.get_signed_download_url(
                project_id=project_id,
                generation_id=generation_id,
                version=version,
                expires_in=60
            )
            
            return signed_url is not None
            
        except Exception as e:
            logger.warning(f"Verification failed for {project_id}/v{version}__{generation_id}: {e}")
            return False
    
    async def run(self, project_id: Optional[str] = None, verify: bool = False):
        """
        Run the migration.
        
        Args:
            project_id: Optional project ID to migrate (None = migrate all)
            verify: Whether to verify uploads
        """
        logger.info("🚀 Starting Supabase migration")
        
        # Scan for projects
        generations = self.scan_projects(project_id)
        
        if not generations:
            logger.warning("No generations found to migrate")
            return
        
        # Upload generations
        logger.info(f"📤 Uploading {len(generations)} generations...")
        
        if self.show_progress:
            progress = tqdm(generations, desc="Uploading", unit="gen")
        else:
            progress = generations
        
        for gen_info in progress:
            success = await self.upload_generation(gen_info)
            
            # Verify if requested and upload succeeded
            if verify and success and not self.dry_run:
                verified = await self.verify_upload(gen_info)
                if not verified:
                    logger.warning(f"⚠️ Verification failed: {gen_info['project_id']}/v{gen_info['version']}__{gen_info['generation_id']}")
        
        # Print report
        print(self.report.get_summary())
        
        # Save detailed report
        if not self.dry_run:
            report_path = Path("migration_report.json")
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_projects": self.report.total_projects,
                    "total_generations": self.report.total_generations,
                    "uploaded": self.report.uploaded_count,
                    "failed": self.report.failed_count,
                    "skipped": self.report.skipped_count,
                    "total_size_mb": self.report.total_size_bytes / (1024 * 1024)
                },
                "errors": self.report.errors
            }
            
            with open(report_path, "w") as f:
                json.dump(report_data, f, indent=2)
            
            logger.info(f"📄 Detailed report saved to: {report_path}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate CodebeGen projects to Supabase Storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview migration (dry run)
  python scripts/migrate_to_supabase.py --dry-run

  # Migrate all projects
  python scripts/migrate_to_supabase.py

  # Migrate specific project
  python scripts/migrate_to_supabase.py --project-id abc-123

  # Migrate with verification
  python scripts/migrate_to_supabase.py --verify
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without uploading"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        help="Migrate only a specific project"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify uploads after migration"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bars"
    )
    
    args = parser.parse_args()
    
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Run migration
    migration = SupabaseMigration(
        dry_run=args.dry_run,
        show_progress=not args.no_progress
    )
    
    try:
        await migration.run(
            project_id=args.project_id,
            verify=args.verify
        )
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
