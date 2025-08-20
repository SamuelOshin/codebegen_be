"""
File management service for handling generated project files.
Manages file creation, storage, compression, and delivery.
"""

import os
import shutil
import zipfile
import tempfile
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from app.core.config import settings
from app.schemas.generation import GenerationStatus

logger = logging.getLogger(__name__)


class FileManager:
    """Manages generated project files and storage."""
    
    def __init__(self):
        self.storage_path = Path(settings.FILE_STORAGE_PATH)
        self.temp_path = Path(settings.TEMP_STORAGE_PATH)
        self.max_file_age_days = 30
        
        # Ensure directories exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
    
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

    async def save_generation_files(self, generation_id: str, files: Dict[str, str]) -> bool:
        """
        Save generated files to storage.
        
        Args:
            generation_id: Unique identifier for the generation
            files: Dictionary mapping file paths to content
            
        Returns:
            True if successful, False otherwise
        """
        try:
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


# Global instance
file_manager = FileManager()
