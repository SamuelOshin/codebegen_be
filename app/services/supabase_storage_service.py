"""
Supabase Storage Service for cloud-based project file storage.
Handles upload, download, and management of generated projects in Supabase Storage.
"""

import os
import tarfile
import tempfile
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from loguru import logger
from supabase import create_client, Client, StorageException

from app.core.config import settings


class SupabaseStorageService:
    """
    Manages cloud storage operations using Supabase Storage.
    
    Features:
    - Automatic bucket creation and management
    - Project compression (tar.gz) for efficient uploads
    - Signed URL generation for secure downloads
    - Cache management with TTL
    - Error handling with graceful degradation
    """
    
    def __init__(self):
        """Initialize Supabase client and bucket."""
        self.enabled = settings.USE_CLOUD_STORAGE and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY
        
        if not self.enabled:
            logger.info("Cloud storage disabled or not configured")
            return
        
        try:
            self.client: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
            self.bucket_name = settings.SUPABASE_BUCKET
            self.cache_path = Path(settings.CACHE_PATH)
            self.cache_ttl_hours = settings.CACHE_TTL_HOURS
            
            # Ensure cache directory exists
            self.cache_path.mkdir(parents=True, exist_ok=True)
            
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
            logger.info(f"✅ Supabase storage initialized (bucket: {self.bucket_name})")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase storage: {e}")
            self.enabled = False
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            # Try to get bucket info
            buckets = self.client.storage.list_buckets()
            bucket_exists = any(b['name'] == self.bucket_name for b in buckets)
            
            if not bucket_exists:
                # Create private bucket
                self.client.storage.create_bucket(
                    self.bucket_name,
                    options={"public": False}
                )
                logger.info(f"✅ Created Supabase bucket: {self.bucket_name}")
            else:
                logger.debug(f"Bucket {self.bucket_name} already exists")
                
        except Exception as e:
            logger.warning(f"Could not verify/create bucket (may already exist): {e}")
    
    def _get_storage_path(self, project_id: str, generation_id: str, version: int) -> str:
        """
        Generate storage path for a generation.
        Format: {project_id}/generations/v{version}__{generation_id}.tar.gz
        """
        return f"{project_id}/generations/v{version}__{generation_id}.tar.gz"
    
    def _get_cache_path(self, project_id: str, generation_id: str, version: int) -> Path:
        """Get local cache path for a generation."""
        return self.cache_path / project_id / f"v{version}__{generation_id}"
    
    async def compress_generation(
        self,
        generation_dir: Path,
        project_id: str,
        generation_id: str,
        version: int
    ) -> Path:
        """
        Compress a generation directory to tar.gz.
        
        Args:
            generation_dir: Path to generation directory
            project_id: Project UUID
            generation_id: Generation UUID
            version: Version number
            
        Returns:
            Path to compressed tar.gz file
        """
        try:
            # Create temp file for compression
            temp_dir = Path(tempfile.gettempdir())
            tar_path = temp_dir / f"{generation_id}.tar.gz"
            
            # Compress directory
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(generation_dir, arcname=generation_dir.name)
            
            logger.debug(f"Compressed generation to {tar_path} ({tar_path.stat().st_size} bytes)")
            return tar_path
            
        except Exception as e:
            logger.error(f"❌ Error compressing generation: {e}")
            raise
    
    async def upload_generation(
        self,
        generation_dir: Path,
        project_id: str,
        generation_id: str,
        version: int
    ) -> Optional[str]:
        """
        Upload a generation directory to Supabase Storage.
        
        Args:
            generation_dir: Path to generation directory
            project_id: Project UUID
            generation_id: Generation UUID
            version: Version number
            
        Returns:
            Storage path on success, None on failure
        """
        if not self.enabled:
            logger.debug("Cloud storage not enabled, skipping upload")
            return None
        
        try:
            # Compress generation
            tar_path = await self.compress_generation(
                generation_dir, project_id, generation_id, version
            )
            
            # Generate storage path
            storage_path = self._get_storage_path(project_id, generation_id, version)
            
            # Upload to Supabase
            with open(tar_path, "rb") as f:
                file_data = f.read()
                
            self.client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": "application/gzip", "upsert": "true"}
            )
            
            # Cleanup temp file
            tar_path.unlink()
            
            logger.info(f"✅ Uploaded generation to cloud: {storage_path}")
            return storage_path
            
        except StorageException as e:
            logger.error(f"❌ Supabase storage error uploading generation: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error uploading generation: {e}")
            return None
    
    async def download_generation(
        self,
        project_id: str,
        generation_id: str,
        version: int
    ) -> Optional[Path]:
        """
        Download and extract a generation from Supabase Storage.
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Version number
            
        Returns:
            Path to extracted generation directory, or None on failure
        """
        if not self.enabled:
            logger.debug("Cloud storage not enabled, skipping download")
            return None
        
        try:
            # Check cache first
            cache_dir = self._get_cache_path(project_id, generation_id, version)
            if cache_dir.exists():
                # Check if cache is still fresh
                cache_age = datetime.now() - datetime.fromtimestamp(cache_dir.stat().st_mtime)
                if cache_age < timedelta(hours=self.cache_ttl_hours):
                    logger.debug(f"Using cached generation: {cache_dir}")
                    return cache_dir / "source"  # Return source directory
            
            # Download from Supabase
            storage_path = self._get_storage_path(project_id, generation_id, version)
            
            file_data = self.client.storage.from_(self.bucket_name).download(storage_path)
            
            # Save to temp file
            temp_dir = Path(tempfile.gettempdir())
            tar_path = temp_dir / f"{generation_id}.tar.gz"
            
            with open(tar_path, "wb") as f:
                f.write(file_data)
            
            # Extract to cache
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=cache_dir)
            
            # Cleanup temp file
            tar_path.unlink()
            
            logger.info(f"✅ Downloaded and extracted generation to cache: {cache_dir}")
            return cache_dir / "source"  # Return source directory
            
        except StorageException as e:
            logger.error(f"❌ Supabase storage error downloading generation: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error downloading generation: {e}")
            return None
    
    async def get_signed_download_url(
        self,
        project_id: str,
        generation_id: str,
        version: int,
        expires_in: int = 3600
    ) -> Optional[str]:
        """
        Generate a signed URL for downloading a generation.
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Version number
            expires_in: URL expiry time in seconds (default: 1 hour)
            
        Returns:
            Signed URL or None on failure
        """
        if not self.enabled:
            logger.debug("Cloud storage not enabled, skipping signed URL generation")
            return None
        
        try:
            storage_path = self._get_storage_path(project_id, generation_id, version)
            
            response = self.client.storage.from_(self.bucket_name).create_signed_url(
                path=storage_path,
                expires_in=expires_in
            )
            
            signed_url = response.get("signedURL")
            
            if signed_url:
                logger.debug(f"Generated signed URL for {storage_path} (expires in {expires_in}s)")
                return signed_url
            else:
                logger.warning(f"No signed URL in response: {response}")
                return None
            
        except StorageException as e:
            logger.error(f"❌ Supabase storage error generating signed URL: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error generating signed URL: {e}")
            return None
    
    async def delete_generation(
        self,
        project_id: str,
        generation_id: str,
        version: int,
        delete_cache: bool = True
    ) -> bool:
        """
        Delete a generation from Supabase Storage and optionally from cache.
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Version number
            delete_cache: Whether to delete from cache as well
            
        Returns:
            True on success, False on failure
        """
        if not self.enabled:
            logger.debug("Cloud storage not enabled, skipping delete")
            return False
        
        try:
            storage_path = self._get_storage_path(project_id, generation_id, version)
            
            # Delete from Supabase
            self.client.storage.from_(self.bucket_name).remove([storage_path])
            logger.info(f"✅ Deleted generation from cloud: {storage_path}")
            
            # Delete from cache if requested
            if delete_cache:
                cache_dir = self._get_cache_path(project_id, generation_id, version)
                if cache_dir.exists():
                    import shutil
                    shutil.rmtree(cache_dir)
                    logger.debug(f"Deleted cached generation: {cache_dir}")
            
            return True
            
        except StorageException as e:
            logger.error(f"❌ Supabase storage error deleting generation: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error deleting generation: {e}")
            return False
    
    async def list_project_generations(
        self,
        project_id: str
    ) -> List[Dict[str, any]]:
        """
        List all generations for a project in Supabase Storage.
        
        Args:
            project_id: Project UUID
            
        Returns:
            List of generation metadata dicts
        """
        if not self.enabled:
            logger.debug("Cloud storage not enabled, skipping list")
            return []
        
        try:
            # List files in project generations folder
            files = self.client.storage.from_(self.bucket_name).list(
                path=f"{project_id}/generations",
                options={"sortBy": {"column": "created_at", "order": "desc"}}
            )
            
            generations = []
            for file in files:
                if file['name'].endswith('.tar.gz'):
                    # Parse filename: v{version}__{generation_id}.tar.gz
                    name = file['name'].replace('.tar.gz', '')
                    parts = name.split('__')
                    if len(parts) == 2:
                        version_str = parts[0].replace('v', '')
                        generation_id = parts[1]
                        
                        generations.append({
                            "generation_id": generation_id,
                            "version": int(version_str),
                            "size": file.get('metadata', {}).get('size', 0),
                            "created_at": file.get('created_at'),
                            "updated_at": file.get('updated_at'),
                        })
            
            return generations
            
        except StorageException as e:
            logger.error(f"❌ Supabase storage error listing generations: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Error listing generations: {e}")
            return []
    
    async def cleanup_old_cache(
        self,
        max_age_hours: Optional[int] = None
    ) -> int:
        """
        Remove cached generations older than specified age.
        
        Args:
            max_age_hours: Maximum cache age in hours (uses config default if None)
            
        Returns:
            Number of cleaned up cache entries
        """
        try:
            max_age = max_age_hours or settings.MAX_CACHE_AGE_HOURS
            cutoff_time = datetime.now() - timedelta(hours=max_age)
            cleaned_count = 0
            
            if not self.cache_path.exists():
                return 0
            
            # Walk through cache directory
            for project_dir in self.cache_path.iterdir():
                if not project_dir.is_dir():
                    continue
                
                for gen_dir in project_dir.iterdir():
                    if not gen_dir.is_dir():
                        continue
                    
                    # Check age
                    mod_time = datetime.fromtimestamp(gen_dir.stat().st_mtime)
                    if mod_time < cutoff_time:
                        import shutil
                        shutil.rmtree(gen_dir)
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old cache: {gen_dir}")
            
            if cleaned_count > 0:
                logger.info(f"✅ Cleaned up {cleaned_count} old cached generations")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up cache: {e}")
            return 0


# Global instance
supabase_storage_service = SupabaseStorageService()
