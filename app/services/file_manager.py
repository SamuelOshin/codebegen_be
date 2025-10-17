"""
File management service for handling generated project files.
Manages file creation, storage, compression, and delivery.

Enhanced with hierarchical storage structure:
- New: ./storage/projects/{project_id}/generations/v{version}__{generation_id}/
- Old: ./storage/projects/{generation_id}/ (backward compatible)
"""

import os
import sys
import shutil
import zipfile
import tempfile
import asyncio
import logging
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from app.core.config import settings
from app.schemas.generation import GenerationStatus

logger = logging.getLogger(__name__)


class FileManager:
    """Manages generated project files and storage with hierarchical structure."""
    
    def __init__(self):
        self.storage_path = Path(settings.FILE_STORAGE_PATH)
        self.temp_path = Path(settings.TEMP_STORAGE_PATH)
        self.max_file_age_days = 30
        
        # Ensure directories exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
    
    # ==================== NEW: Hierarchical Storage Methods ====================
    
    async def save_generation_files_hierarchical(
        self,
        project_id: str,
        generation_id: str,
        version: int,
        files: Dict[str, str],
        metadata: Optional[Dict] = None
    ) -> Tuple[str, int, int]:
        """
        Save generation files with hierarchical project/version structure.
        
        New structure: ./storage/projects/{project_id}/generations/v{version}__{generation_id}/
        
        Hierarchical storage design:
        - Project-level isolation: Each project gets its own directory
        - Version tracking: Clear version numbers (v1, v2, v3...) in directory names
        - Generation identification: UUID suffix ensures uniqueness within versions
        - Symlink support: 'active' symlink points to current version directory
        - Metadata persistence: manifest.json stores generation statistics and context
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Version number (1, 2, 3...)
            files: Dictionary mapping file paths to content
            metadata: Optional metadata to include in manifest
            
        Returns:
            Tuple of (storage_path, file_count, total_size_bytes)
        """
        try:
            # Create hierarchical path
            generation_dir = self.storage_path / project_id / "generations" / f"v{version}__{generation_id}"
            source_dir = generation_dir / "source"
            artifacts_dir = generation_dir / "artifacts"
            
            # Create directories
            source_dir.mkdir(parents=True, exist_ok=True)
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Calculate file stats
            file_count = len(files)
            total_size_bytes = sum(len(content.encode('utf-8')) for content in files.values())
            
            # Create manifest.json
            manifest = {
                "generation_id": generation_id,
                "project_id": project_id,
                "version": version,
                "created_at": datetime.utcnow().isoformat(),
                "file_count": file_count,
                "total_size_bytes": total_size_bytes,
                "files": list(files.keys()),
                "metadata": metadata or {}
            }
            manifest_path = generation_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            
            # Save source files
            for file_path, content in files.items():
                full_path = source_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding='utf-8')
            
            logger.info(f"✅ Saved generation v{version} for project {project_id} ({file_count} files, {total_size_bytes:,} bytes)")
            return str(generation_dir), file_count, total_size_bytes
            
        except Exception as e:
            logger.error(f"❌ Error saving hierarchical generation files: {e}")
            raise
    
    async def create_generation_diff(
        self,
        project_id: str,
        from_version: int,
        to_version: int
    ) -> Optional[str]:
        """
        Create diff between two generation versions.
        
        Args:
            project_id: Project UUID
            from_version: Source version number
            to_version: Target version number
            
        Returns:
            Path to diff file or None if error
        """
        try:
            # Find generation directories
            generations_dir = self.storage_path / project_id / "generations"
            if not generations_dir.exists():
                logger.warning(f"Generations directory not found for project {project_id}")
                return None
            
            from_dirs = list(generations_dir.glob(f"v{from_version}__*"))
            to_dirs = list(generations_dir.glob(f"v{to_version}__*"))
            
            if not from_dirs or not to_dirs:
                logger.warning(f"Could not find versions {from_version} or {to_version} for project {project_id}")
                return None
            
            from_dir = from_dirs[0] / "source"
            to_dir = to_dirs[0] / "source"
            
            # Check if diff command is available
            diff_available = shutil.which("diff") is not None
            
            if diff_available:
                # Use system diff command (Unix/Linux/Git Bash)
                result = subprocess.run(
                    ["diff", "-ru", str(from_dir), str(to_dir)],
                    capture_output=True,
                    text=True
                )
                diff_content = result.stdout
            else:
                # Fallback: Simple file-by-file comparison
                diff_content = await self._create_simple_diff(from_dir, to_dir)
            
            # Save diff file
            diff_path = to_dirs[0] / f"diff_from_v{from_version}.patch"
            diff_path.write_text(diff_content, encoding='utf-8')
            
            logger.info(f"✅ Created diff from v{from_version} to v{to_version} for project {project_id}")
            return str(diff_path)
            
        except Exception as e:
            logger.error(f"❌ Error creating diff: {e}")
            return None
    
    async def _create_simple_diff(self, from_dir: Path, to_dir: Path) -> str:
        """Create a simple diff when system diff is not available."""
        diff_lines = []
        diff_lines.append(f"=== Diff from {from_dir.name} to {to_dir.name} ===\n")
        
        # Get all files from both directories
        from_files = {f.relative_to(from_dir): f for f in from_dir.rglob('*') if f.is_file()}
        to_files = {f.relative_to(to_dir): f for f in to_dir.rglob('*') if f.is_file()}
        
        # Added files
        added = set(to_files.keys()) - set(from_files.keys())
        if added:
            diff_lines.append(f"\n📄 Added files ({len(added)}):\n")
            for file in sorted(added):
                diff_lines.append(f"  + {file}\n")
        
        # Removed files
        removed = set(from_files.keys()) - set(to_files.keys())
        if removed:
            diff_lines.append(f"\n📄 Removed files ({len(removed)}):\n")
            for file in sorted(removed):
                diff_lines.append(f"  - {file}\n")
        
        # Modified files (simple content comparison)
        common = set(from_files.keys()) & set(to_files.keys())
        modified = []
        for file in common:
            try:
                from_content = from_files[file].read_text(encoding='utf-8')
                to_content = to_files[file].read_text(encoding='utf-8')
                if from_content != to_content:
                    modified.append(file)
            except:
                pass  # Skip binary files
        
        if modified:
            diff_lines.append(f"\n📝 Modified files ({len(modified)}):\n")
            for file in sorted(modified):
                diff_lines.append(f"  ~ {file}\n")
        
        return ''.join(diff_lines)
    
    async def set_active_generation_symlink(
        self,
        project_id: str,
        generation_version: int
    ) -> bool:
        """
        Update symlink to point to active generation.
        
        Note: On Windows, this creates a directory junction instead of a symlink.
        
        Args:
            project_id: Project UUID
            generation_version: Version number to set as active
            
        Returns:
            True if successful, False otherwise
        """
        try:
            generations_dir = self.storage_path / project_id / "generations"
            if not generations_dir.exists():
                logger.warning(f"Generations directory not found for project {project_id}")
                return False
            
            active_link = generations_dir / "active"
            
            # Find target generation directory
            target_dirs = list(generations_dir.glob(f"v{generation_version}__*"))
            if not target_dirs:
                logger.warning(f"Generation v{generation_version} not found for project {project_id}")
                return False
            
            target_dir = target_dirs[0]
            
            # Remove old symlink/junction
            if active_link.exists() or active_link.is_symlink():
                try:
                    if sys.platform == "win32":
                        # Windows: remove junction
                        subprocess.run(["rmdir", str(active_link)], shell=True, check=False)
                    else:
                        active_link.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove old active link: {e}")
            
            # Create new symlink/junction
            try:
                if sys.platform == "win32":
                    # Windows: create junction (doesn't require admin)
                    subprocess.run(
                        ["mklink", "/J", str(active_link), str(target_dir)],
                        shell=True,
                        check=True,
                        capture_output=True
                    )
                else:
                    # Unix: create symbolic link
                    active_link.symlink_to(target_dir.name)
                
                logger.info(f"✅ Set active generation to v{generation_version} for project {project_id}")
                return True
            except Exception as e:
                logger.warning(f"Could not create symlink (this is optional): {e}")
                # Symlink creation is optional, don't fail
                return True
                
        except Exception as e:
            logger.error(f"❌ Error setting active generation symlink: {e}")
            return False
    
    async def cleanup_old_generations(
        self,
        project_id: str,
        keep_latest: int = 5,
        archive_age_days: int = 30
    ) -> int:
        """
        Archive old generations, keep recent ones.
        
        Args:
            project_id: Project UUID
            keep_latest: Number of latest versions to keep
            archive_age_days: Archive generations older than this
            
        Returns:
            Number of archived generations
        """
        try:
            project_dir = self.storage_path / project_id
            generations_dir = project_dir / "generations"
            archive_dir = project_dir / "archive"
            
            if not generations_dir.exists():
                return 0
            
            # Get all generation directories sorted by version
            gen_dirs = sorted(
                [d for d in generations_dir.iterdir() if d.is_dir() and d.name.startswith("v") and "__" in d.name],
                key=lambda p: int(p.name.split("__")[0][1:])
            )
            
            archived_count = 0
            cutoff_date = datetime.now() - timedelta(days=archive_age_days)
            
            # Keep latest N, archive the rest if old enough
            for gen_dir in gen_dirs[:-keep_latest] if len(gen_dirs) > keep_latest else []:
                age_days = (datetime.now() - datetime.fromtimestamp(gen_dir.stat().st_mtime)).days
                
                if age_days > archive_age_days:
                    archive_dir.mkdir(exist_ok=True)
                    archive_target = archive_dir / gen_dir.name
                    
                    shutil.move(str(gen_dir), str(archive_target))
                    archived_count += 1
                    logger.info(f"📦 Archived old generation: {gen_dir.name}")
            
            return archived_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old generations: {e}")
            return 0
    
    def _get_generation_dir(self, project_id: str, version: Optional[int] = None, generation_id: Optional[str] = None) -> Optional[Path]:
        """
        Get generation directory path (supports both old and new structures).
        
        Args:
            project_id: Project UUID
            version: Version number (for new structure)
            generation_id: Generation UUID (for old structure or exact match)
            
        Returns:
            Path to generation directory or None
        """
        try:
            # Try new hierarchical structure first
            if version is not None:
                generations_dir = self.storage_path / project_id / "generations"
                if generations_dir.exists():
                    matching_dirs = list(generations_dir.glob(f"v{version}__*"))
                    if matching_dirs:
                        return matching_dirs[0]
            
            # Try old flat structure
            if generation_id is not None:
                old_path = self.storage_path / generation_id
                if old_path.exists() and old_path.is_dir():
                    return old_path
            
            # Try searching in new structure by generation_id
            if generation_id is not None and project_id is not None:
                generations_dir = self.storage_path / project_id / "generations"
                if generations_dir.exists():
                    matching_dirs = list(generations_dir.glob(f"*__{generation_id}"))
                    if matching_dirs:
                        return matching_dirs[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting generation directory: {e}")
            return None
    
    # ==================== END: New Hierarchical Methods ====================
    
    async def create_project_structure(
        self, 
        generation_id: str, 
        files: Dict[str, str],
        template_name: str = "fastapi_basic"
    ) -> Path:
        """
        Create a project directory structure with generated files.
        
        Args:
            generation_id: Unique identifier for the generation
            files: Dictionary mapping file paths to content
            template_name: Name of the template used
            
        Returns:
            Path to the created project directory
        """
        try:
            project_dir = self.storage_path / generation_id
            
            # Remove existing directory if it exists
            if project_dir.exists():
                shutil.rmtree(project_dir)
                
            project_dir.mkdir(parents=True)
            
            # Create all files
            for file_path, content in files.items():
                full_path = project_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file content
                full_path.write_text(content, encoding='utf-8')
                
            logger.info(f"Created project structure for generation {generation_id}")
            return project_dir
            
        except Exception as e:
            logger.error(f"Error creating project structure: {e}")
            raise

    async def save_generation_files(
        self, 
        generation_id: str, 
        files: Dict[str, str],
        project_id: Optional[str] = None,
        version: Optional[int] = None
    ) -> bool:
        """
        Save generated files to storage.
        
        Supports both old (flat) and new (hierarchical) storage structures:
        - If project_id and version provided: use new hierarchical structure
        - Otherwise: use old flat structure for backward compatibility
        
        Args:
            generation_id: Unique identifier for the generation
            files: Dictionary mapping file paths to content
            project_id: Optional project UUID (for hierarchical storage)
            version: Optional version number (for hierarchical storage)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use new hierarchical structure if project_id and version provided
            if project_id and version is not None:
                await self.save_generation_files_hierarchical(
                    project_id=project_id,
                    generation_id=generation_id,
                    version=version,
                    files=files
                )
            else:
                # Fall back to old flat structure
                await self.create_project_structure(generation_id, files)
            
            logger.info(f"Successfully saved {len(files)} files for generation {generation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save generation files for {generation_id}: {e}")
            return False
    
    async def create_zip_archive(self, generation_id: str) -> Optional[Path]:
        """
        Create a ZIP archive of the generated project.
        
        Args:
            generation_id: Unique identifier for the generation
            
        Returns:
            Path to the created ZIP file or None if error
        """
        try:
            project_dir = self.storage_path / generation_id
            if not project_dir.exists():
                logger.error(f"Project directory not found: {project_dir}")
                return None
                
            zip_path = self.storage_path / f"{generation_id}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in project_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(project_dir)
                        zipf.write(file_path, arcname)
                        
            logger.info(f"Created ZIP archive: {zip_path}")
            return zip_path
            
        except Exception as e:
            logger.error(f"Error creating ZIP archive: {e}")
            return None
    
    async def get_project_files(self, generation_id: str) -> Dict[str, str]:
        """
        Get all files from a generated project.
        
        Args:
            generation_id: Unique identifier for the generation
            
        Returns:
            Dictionary mapping file paths to content
        """
        try:
            project_dir = self.storage_path / generation_id
            if not project_dir.exists():
                return {}
                
            files = {}
            for file_path in project_dir.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(project_dir)
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        files[str(relative_path)] = content
                    except UnicodeDecodeError:
                        # Skip binary files
                        continue
                        
            return files
            
        except Exception as e:
            logger.error(f"Error reading project files: {e}")
            return {}
    
    async def get_file_content(self, generation_id: str, file_path: str) -> Optional[str]:
        """
        Get content of a specific file.
        
        Args:
            generation_id: Unique identifier for the generation
            file_path: Relative path to the file
            
        Returns:
            File content or None if not found
        """
        try:
            full_path = self.storage_path / generation_id / file_path
            if full_path.exists() and full_path.is_file():
                return full_path.read_text(encoding='utf-8')
            return None
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    async def update_file_content(
        self, 
        generation_id: str, 
        file_path: str, 
        content: str
    ) -> bool:
        """
        Update content of a specific file.
        
        Args:
            generation_id: Unique identifier for the generation
            file_path: Relative path to the file
            content: New file content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = self.storage_path / generation_id / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
            
            logger.info(f"Updated file {file_path} for generation {generation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating file {file_path}: {e}")
            return False
    
    async def delete_project(self, generation_id: str) -> bool:
        """
        Delete a generated project and its ZIP archive.
        
        Args:
            generation_id: Unique identifier for the generation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            project_dir = self.storage_path / generation_id
            zip_path = self.storage_path / f"{generation_id}.zip"
            
            success = True
            
            if project_dir.exists():
                shutil.rmtree(project_dir)
                logger.info(f"Deleted project directory: {project_dir}")
            
            if zip_path.exists():
                zip_path.unlink()
                logger.info(f"Deleted ZIP archive: {zip_path}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error deleting project {generation_id}: {e}")
            return False
    
    async def cleanup_old_files(self) -> int:
        """
        Clean up old project files and archives.
        
        Returns:
            Number of cleaned up projects
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_file_age_days)
            cleaned_count = 0
            
            for item in self.storage_path.iterdir():
                if item.stat().st_mtime < cutoff_date.timestamp():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    cleaned_count += 1
                    
            logger.info(f"Cleaned up {cleaned_count} old files/directories")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    async def get_project_stats(self, generation_id: str) -> Dict[str, any]:
        """
        Get statistics about a generated project.
        
        Args:
            generation_id: Unique identifier for the generation
            
        Returns:
            Dictionary with project statistics
        """
        try:
            project_dir = self.storage_path / generation_id
            if not project_dir.exists():
                return {}
                
            stats = {
                "total_files": 0,
                "total_lines": 0,
                "total_size": 0,
                "file_types": {},
                "largest_file": None,
                "largest_file_size": 0
            }
            
            for file_path in project_dir.rglob('*'):
                if file_path.is_file():
                    stats["total_files"] += 1
                    file_size = file_path.stat().st_size
                    stats["total_size"] += file_size
                    
                    # Track largest file
                    if file_size > stats["largest_file_size"]:
                        stats["largest_file_size"] = file_size
                        stats["largest_file"] = str(file_path.relative_to(project_dir))
                    
                    # Count file types
                    extension = file_path.suffix or "no_extension"
                    stats["file_types"][extension] = stats["file_types"].get(extension, 0) + 1
                    
                    # Count lines for text files
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        stats["total_lines"] += len(content.splitlines())
                    except UnicodeDecodeError:
                        # Skip binary files
                        continue
                        
            return stats
            
        except Exception as e:
            logger.error(f"Error getting project stats: {e}")
            return {}
    
    def get_download_url(self, generation_id: str) -> str:
        """
        Get download URL for a generated project.
        
        Args:
            generation_id: Unique identifier for the generation
            
        Returns:
            Download URL
        """
        return f"{settings.API_BASE_URL}/generations/{generation_id}/download"
    
    async def validate_project_structure(self, generation_id: str) -> Tuple[bool, List[str]]:
        """
        Validate the structure of a generated project.
        
        Args:
            generation_id: Unique identifier for the generation
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        try:
            project_dir = self.storage_path / generation_id
            if not project_dir.exists():
                return False, ["Project directory does not exist"]
                
            issues = []
            required_files = ["main.py", "requirements.txt", "README.md"]
            
            # Check for required files
            for required_file in required_files:
                if not (project_dir / required_file).exists():
                    issues.append(f"Missing required file: {required_file}")
            
            # Check Python syntax in .py files
            for py_file in project_dir.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    compile(content, str(py_file), 'exec')
                except SyntaxError as e:
                    issues.append(f"Syntax error in {py_file.relative_to(project_dir)}: {e}")
                except Exception as e:
                    issues.append(f"Error checking {py_file.relative_to(project_dir)}: {e}")
            
            is_valid = len(issues) == 0
            return is_valid, issues
            
        except Exception as e:
            logger.error(f"Error validating project structure: {e}")
            return False, [f"Validation error: {e}"]
    
    async def get_generation_directory(
        self, 
        generation_id: str,
        project_id: Optional[str] = None,
        version: Optional[int] = None
    ) -> Optional[Path]:
        """
        Get the directory path for a generation.
        
        Supports both old and new storage structures.
        
        Args:
            generation_id: Unique identifier for the generation
            project_id: Optional project UUID (for new structure)
            version: Optional version number (for new structure)
            
        Returns:
            Path to generation directory or None if not found
        """
        try:
            # Try using helper method which checks both structures
            gen_dir = self._get_generation_dir(project_id, version, generation_id)
            
            if gen_dir and gen_dir.exists() and gen_dir.is_dir():
                # For new structure, return the source directory
                source_dir = gen_dir / "source"
                if source_dir.exists():
                    return source_dir
                return gen_dir
            
            return None
        except Exception as e:
            logger.error(f"Error getting generation directory: {e}")
            return None


# Global instance
file_manager = FileManager()
