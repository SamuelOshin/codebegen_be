"""
Storage integration helper for adding cloud storage to existing endpoints.
Provides backward-compatible wrapper functions for seamless integration.
"""

from pathlib import Path
from typing import Optional, Dict, Tuple
from loguru import logger

from app.core.config import settings
from app.services.file_manager import file_manager
from app.services.storage_manager import storage_manager


class StorageIntegrationHelper:
    """
    Helper class to provide easy integration of hybrid storage into existing endpoints.
    
    This class provides drop-in replacements for file_manager methods that add
    cloud storage support while maintaining backward compatibility.
    """
    
    def __init__(self):
        self.file_manager = file_manager
        self.storage_manager = storage_manager
        self.cloud_enabled = settings.USE_CLOUD_STORAGE
    
    async def save_generation_with_cloud(
        self,
        project_id: str,
        generation_id: str,
        version: int,
        files: Dict[str, str],
        metadata: Optional[Dict] = None
    ) -> Tuple[str, int, int]:
        """
        Save generation with automatic cloud upload.
        
        This is a drop-in replacement for file_manager.save_generation_files_hierarchical
        that adds cloud storage support.
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Version number
            files: Dictionary mapping file paths to content
            metadata: Optional metadata
            
        Returns:
            Tuple of (storage_path, file_count, total_size_bytes)
        """
        return await self.storage_manager.save_generation(
            project_id=project_id,
            generation_id=generation_id,
            version=version,
            files=files,
            metadata=metadata,
            upload_to_cloud=self.cloud_enabled
        )
    
    async def get_download_url_for_generation(
        self,
        project_id: str,
        generation_id: str,
        version: int
    ) -> Optional[str]:
        """
        Get download URL for a generation (cloud or local).
        
        Args:
            project_id: Project UUID
            generation_id: Generation UUID
            version: Version number
            
        Returns:
            Download URL (cloud signed URL if available, otherwise local URL)
        """
        return await self.storage_manager.get_download_url(
            project_id=project_id,
            generation_id=generation_id,
            version=version
        )
    
    async def enrich_generation_response(
        self,
        generation_dict: Dict,
        include_download_url: bool = True
    ) -> Dict:
        """
        Enrich generation response with cloud storage information.
        
        Args:
            generation_dict: Generation response dictionary
            include_download_url: Whether to include download URL
            
        Returns:
            Enriched generation dictionary
        """
        if not include_download_url or not self.cloud_enabled:
            return generation_dict
        
        project_id = generation_dict.get("project_id")
        generation_id = generation_dict.get("id")
        version = generation_dict.get("version")
        
        if project_id and generation_id and version:
            download_url = await self.get_download_url_for_generation(
                project_id=project_id,
                generation_id=generation_id,
                version=version
            )
            
            if download_url:
                generation_dict["download_url"] = download_url
                generation_dict["cloud_storage_enabled"] = True
        
        return generation_dict
    
    def get_storage_info(self) -> Dict:
        """
        Get current storage configuration info.
        
        Returns:
            Dictionary with storage configuration
        """
        return {
            "cloud_enabled": self.cloud_enabled,
            "bucket": settings.SUPABASE_BUCKET if self.cloud_enabled else None,
            "cache_path": settings.CACHE_PATH,
            "cache_ttl_hours": settings.CACHE_TTL_HOURS,
        }


# Global instance
storage_helper = StorageIntegrationHelper()
