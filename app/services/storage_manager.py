"""
Hybrid Storage Manager for coordinating local and cloud storage.
Provides seamless integration between FileManager and SupabaseStorageService.
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Tuple
from loguru import logger

from app.core.config import settings
from app.services.file_manager import FileManager
from app.services.supabase_storage_service import SupabaseStorageService


class HybridStorageManager:
    """
    Manages hybrid storage strategy: local + cloud with intelligent caching.
    
    Features:
    - Local-first storage (fast access)
    - Background cloud upload (non-blocking)
    - Automatic cache management
    - Backward compatibility with local-only mode
    - Graceful degradation on cloud failures
    """
    
    def __init__(
        self,
        file_manager: Optional[FileManager] = None,
        supabase_service: Optional[SupabaseStorageService] = None
    ):
        """
        Initialize hybrid storage manager.
        
        Args:
            file_manager: Local file manager (creates if None)
            supabase_service: Cloud storage service (creates if None)
        """
        self.file_manager = file_manager or FileManager()
        self.supabase_service = supabase_service or SupabaseStorageService()
        self.cloud_enabled = settings.USE_CLOUD_STORAGE and self.supabase_service.enabled
        
        if self.cloud_enabled:
            logger.info("✅ Hybrid storage initialized (local + cloud)")
        else:
            logger.info("ℹ️ Hybrid storage initialized (local only)")
    
    async def save_generation(
        self,
        project_id: str,
        generation_id: str,
        version: int,
        files: Dict[str, str],
        metadata: Optional[Dict] = None,
        upload_to_cloud: bool = True
    ) -> Tuple[str, int, int]:
        """
        Save generation with hybrid storage strategy.
        
        Strategy:
        1. Save to local storage first (fast, synchronous)
        2. Upload to cloud in background (async, non-blocking)
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Version number
            files: Dictionary mapping file paths to content
            metadata: Optional metadata to include
            upload_to_cloud: Whether to upload to cloud (default: True)
            
        Returns:
            Tuple of (storage_path, file_count, total_size_bytes)
        """
        try:
            # Step 1: Save locally (always, for immediate access)
            storage_path, file_count, total_size = await self.file_manager.save_generation_files_hierarchical(
                project_id=project_id,
                generation_id=generation_id,
                version=version,
                files=files,
                metadata=metadata
            )
            
            logger.info(f"✅ Saved generation locally: {storage_path}")
            
            # Step 2: Upload to cloud in background (if enabled)
            if self.cloud_enabled and upload_to_cloud:
                asyncio.create_task(
                    self._background_upload(
                        Path(storage_path),
                        project_id,
                        generation_id,
                        version
                    )
                )
            
            return storage_path, file_count, total_size
            
        except Exception as e:
            logger.error(f"❌ Error saving generation: {e}")
            raise
    
    async def _background_upload(
        self,
        generation_dir: Path,
        project_id: str,
        generation_id: str,
        version: int
    ):
        """
        Background task to upload generation to cloud.
        Logs errors but doesn't raise exceptions.
        """
        try:
            cloud_path = await self.supabase_service.upload_generation(
                generation_dir=generation_dir,
                project_id=project_id,
                generation_id=generation_id,
                version=version
            )
            
            if cloud_path:
                logger.info(f"✅ Background upload completed: {cloud_path}")
            else:
                logger.warning(f"⚠️ Background upload failed for generation {generation_id}")
                
        except Exception as e:
            logger.error(f"❌ Background upload error: {e}")
    
    async def get_generation(
        self,
        project_id: str,
        generation_id: str,
        version: Optional[int] = None
    ) -> Optional[Path]:
        """
        Get generation directory with cache-first strategy.
        
        Strategy:
        1. Check local storage first
        2. If not found and cloud enabled, download from cloud
        3. Return path to generation directory
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Optional version number
            
        Returns:
            Path to generation directory or None if not found
        """
        try:
            # Step 1: Try local storage first
            local_path = await self.file_manager.get_generation_directory(
                generation_id=generation_id,
                project_id=project_id,
                version=version
            )
            
            if local_path and local_path.exists():
                logger.debug(f"Found generation in local storage: {local_path}")
                return local_path
            
            # Step 2: Try cloud storage if enabled and version is known
            if self.cloud_enabled and version is not None:
                logger.info(f"Generation not found locally, trying cloud download...")
                cloud_path = await self.supabase_service.download_generation(
                    project_id=project_id,
                    generation_id=generation_id,
                    version=version
                )
                
                if cloud_path and cloud_path.exists():
                    logger.info(f"✅ Downloaded generation from cloud: {cloud_path}")
                    return cloud_path
            
            logger.warning(f"Generation not found: {generation_id} (project: {project_id}, version: {version})")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting generation: {e}")
            return None
    
    async def get_download_url(
        self,
        project_id: str,
        generation_id: str,
        version: int,
        expires_in: int = 3600
    ) -> Optional[str]:
        """
        Get download URL for a generation.
        
        Returns cloud signed URL if available, otherwise generates local URL.
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Version number
            expires_in: URL expiry time in seconds (for cloud URLs)
            
        Returns:
            Download URL (cloud or local)
        """
        try:
            # Try cloud signed URL first (if enabled)
            if self.cloud_enabled:
                cloud_url = await self.supabase_service.get_signed_download_url(
                    project_id=project_id,
                    generation_id=generation_id,
                    version=version,
                    expires_in=expires_in
                )
                
                if cloud_url:
                    logger.debug(f"Generated cloud download URL: {cloud_url[:50]}...")
                    return cloud_url
            
            # Fallback to local URL
            local_url = self.file_manager.get_download_url(generation_id)
            logger.debug(f"Using local download URL: {local_url}")
            return local_url
            
        except Exception as e:
            logger.error(f"❌ Error getting download URL: {e}")
            # Fallback to local URL on error
            return self.file_manager.get_download_url(generation_id)
    
    async def delete_generation(
        self,
        project_id: str,
        generation_id: str,
        version: Optional[int] = None,
        delete_local: bool = True,
        delete_cloud: bool = True
    ) -> bool:
        """
        Delete generation from storage.
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Optional version number (required for cloud deletion)
            delete_local: Whether to delete from local storage
            delete_cloud: Whether to delete from cloud storage
            
        Returns:
            True if at least one deletion succeeded
        """
        success = False
        
        try:
            # Delete from local storage
            if delete_local:
                local_success = await self.file_manager.delete_project(generation_id)
                if local_success:
                    logger.info(f"✅ Deleted generation from local storage: {generation_id}")
                    success = True
            
            # Delete from cloud storage (if enabled and version known)
            if delete_cloud and self.cloud_enabled and version is not None:
                cloud_success = await self.supabase_service.delete_generation(
                    project_id=project_id,
                    generation_id=generation_id,
                    version=version,
                    delete_cache=True
                )
                if cloud_success:
                    logger.info(f"✅ Deleted generation from cloud storage: {generation_id}")
                    success = True
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error deleting generation: {e}")
            return success
    
    async def cleanup_old_cache(self, max_age_hours: Optional[int] = None) -> int:
        """
        Clean up old cached generations.
        
        Args:
            max_age_hours: Maximum cache age in hours (uses config default if None)
            
        Returns:
            Number of cleaned up cache entries
        """
        if not self.cloud_enabled:
            return 0
        
        return await self.supabase_service.cleanup_old_cache(max_age_hours)
    
    async def get_storage_info(
        self,
        project_id: str,
        generation_id: str,
        version: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Get storage information for a generation.
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Optional version number
            
        Returns:
            Dictionary with storage information
        """
        info = {
            "cloud_enabled": self.cloud_enabled,
            "local_exists": False,
            "cloud_exists": False,
            "local_path": None,
            "cloud_url": None
        }
        
        try:
            # Check local storage
            local_path = await self.file_manager.get_generation_directory(
                generation_id=generation_id,
                project_id=project_id,
                version=version
            )
            if local_path and local_path.exists():
                info["local_exists"] = True
                info["local_path"] = str(local_path)
            
            # Check cloud storage (if enabled and version known)
            if self.cloud_enabled and version is not None:
                cloud_url = await self.supabase_service.get_signed_download_url(
                    project_id=project_id,
                    generation_id=generation_id,
                    version=version,
                    expires_in=60  # Short expiry for check only
                )
                if cloud_url:
                    info["cloud_exists"] = True
                    info["cloud_url"] = cloud_url
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Error getting storage info: {e}")
            return info


# Global instance
storage_manager = HybridStorageManager()
