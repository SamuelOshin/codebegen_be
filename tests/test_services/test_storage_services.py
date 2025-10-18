"""
Tests for Supabase Storage Service and Hybrid Storage Manager.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import shutil

from app.services.supabase_storage_service import SupabaseStorageService
from app.services.storage_manager import HybridStorageManager
from app.services.file_manager import FileManager


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_supabase_client():
    """Create mock Supabase client."""
    client = MagicMock()
    client.storage.list_buckets.return_value = []
    client.storage.create_bucket.return_value = True
    client.storage.from_.return_value.upload.return_value = {"path": "test/path"}
    client.storage.from_.return_value.download.return_value = b"test data"
    client.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "https://test.url"}
    client.storage.from_.return_value.remove.return_value = True
    client.storage.from_.return_value.list.return_value = []
    return client


@pytest.fixture
def sample_files():
    """Sample files for testing."""
    return {
        "main.py": "print('Hello, World!')",
        "requirements.txt": "fastapi==0.104.1\nuvicorn==0.24.0",
        "README.md": "# Test Project\n\nThis is a test."
    }


class TestSupabaseStorageService:
    """Tests for SupabaseStorageService."""
    
    @patch('app.services.supabase_storage_service.settings')
    @patch('app.services.supabase_storage_service.create_client')
    def test_initialization_disabled(self, mock_create_client, mock_settings, temp_cache_dir):
        """Test initialization when cloud storage is disabled."""
        mock_settings.USE_CLOUD_STORAGE = False
        mock_settings.SUPABASE_URL = None
        mock_settings.SUPABASE_SERVICE_KEY = None
        mock_settings.CACHE_PATH = str(temp_cache_dir)
        
        service = SupabaseStorageService()
        
        assert service.enabled is False
        mock_create_client.assert_not_called()
    
    @patch('app.services.supabase_storage_service.settings')
    @patch('app.services.supabase_storage_service.create_client')
    def test_initialization_enabled(self, mock_create_client, mock_settings, mock_supabase_client, temp_cache_dir):
        """Test initialization when cloud storage is enabled."""
        mock_settings.USE_CLOUD_STORAGE = True
        mock_settings.SUPABASE_URL = "https://test.supabase.co"
        mock_settings.SUPABASE_SERVICE_KEY = "test-key"
        mock_settings.SUPABASE_BUCKET = "test-bucket"
        mock_settings.CACHE_PATH = str(temp_cache_dir)
        mock_settings.CACHE_TTL_HOURS = 24
        mock_create_client.return_value = mock_supabase_client
        
        service = SupabaseStorageService()
        
        assert service.enabled is True
        assert service.bucket_name == "test-bucket"
        mock_create_client.assert_called_once_with(
            "https://test.supabase.co",
            "test-key"
        )
    
    @pytest.mark.asyncio
    @patch('app.services.supabase_storage_service.settings')
    async def test_compress_generation(self, mock_settings, temp_storage_dir):
        """Test generation compression."""
        mock_settings.USE_CLOUD_STORAGE = False
        
        # Create test generation directory
        gen_dir = temp_storage_dir / "test_gen"
        gen_dir.mkdir()
        (gen_dir / "test.txt").write_text("test content")
        
        service = SupabaseStorageService()
        
        # Compress
        tar_path = await service.compress_generation(
            generation_dir=gen_dir,
            project_id="test-project",
            generation_id="test-gen",
            version=1
        )
        
        assert tar_path.exists()
        assert tar_path.suffix == ".gz"
        
        # Cleanup
        tar_path.unlink()
    
    @pytest.mark.asyncio
    @patch('app.services.supabase_storage_service.settings')
    @patch('app.services.supabase_storage_service.create_client')
    async def test_upload_generation_disabled(self, mock_create_client, mock_settings, temp_storage_dir):
        """Test upload when cloud storage is disabled."""
        mock_settings.USE_CLOUD_STORAGE = False
        
        gen_dir = temp_storage_dir / "test_gen"
        gen_dir.mkdir()
        (gen_dir / "test.txt").write_text("test content")
        
        service = SupabaseStorageService()
        
        result = await service.upload_generation(
            generation_dir=gen_dir,
            project_id="test-project",
            generation_id="test-gen",
            version=1
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('app.services.supabase_storage_service.settings')
    async def test_get_signed_download_url_disabled(self, mock_settings):
        """Test signed URL generation when cloud storage is disabled."""
        mock_settings.USE_CLOUD_STORAGE = False
        
        service = SupabaseStorageService()
        
        url = await service.get_signed_download_url(
            project_id="test-project",
            generation_id="test-gen",
            version=1
        )
        
        assert url is None


class TestHybridStorageManager:
    """Tests for HybridStorageManager."""
    
    @pytest.fixture
    def mock_file_manager(self):
        """Create mock FileManager."""
        mock = AsyncMock(spec=FileManager)
        mock.save_generation_files_hierarchical = AsyncMock(return_value=("/path/to/gen", 3, 1024))
        mock.get_generation_directory = AsyncMock(return_value=Path("/path/to/gen"))
        mock.get_download_url = Mock(return_value="http://localhost/download/test")
        mock.delete_project = AsyncMock(return_value=True)
        return mock
    
    @pytest.fixture
    def mock_supabase_service(self):
        """Create mock SupabaseStorageService."""
        mock = AsyncMock(spec=SupabaseStorageService)
        mock.enabled = True
        mock.upload_generation = AsyncMock(return_value="project/gen.tar.gz")
        mock.download_generation = AsyncMock(return_value=Path("/cache/gen"))
        mock.get_signed_download_url = AsyncMock(return_value="https://signed.url")
        mock.delete_generation = AsyncMock(return_value=True)
        mock.cleanup_old_cache = AsyncMock(return_value=5)
        return mock
    
    @patch('app.services.storage_manager.settings')
    def test_initialization(self, mock_settings, mock_file_manager, mock_supabase_service):
        """Test HybridStorageManager initialization."""
        mock_settings.USE_CLOUD_STORAGE = True
        
        manager = HybridStorageManager(
            file_manager=mock_file_manager,
            supabase_service=mock_supabase_service
        )
        
        assert manager.file_manager == mock_file_manager
        assert manager.supabase_service == mock_supabase_service
        assert manager.cloud_enabled is True
    
    @pytest.mark.asyncio
    @patch('app.services.storage_manager.settings')
    async def test_save_generation(self, mock_settings, mock_file_manager, mock_supabase_service, sample_files):
        """Test saving generation with hybrid storage."""
        mock_settings.USE_CLOUD_STORAGE = True
        
        manager = HybridStorageManager(
            file_manager=mock_file_manager,
            supabase_service=mock_supabase_service
        )
        
        storage_path, file_count, total_size = await manager.save_generation(
            project_id="test-project",
            generation_id="test-gen",
            version=1,
            files=sample_files
        )
        
        # Local save should be called
        mock_file_manager.save_generation_files_hierarchical.assert_called_once()
        
        # Should return local storage info
        assert storage_path == "/path/to/gen"
        assert file_count == 3
        assert total_size == 1024
        
        # Give background task time to start
        await asyncio.sleep(0.1)
    
    @pytest.mark.asyncio
    @patch('app.services.storage_manager.settings')
    async def test_get_generation_local_exists(self, mock_settings, mock_file_manager, mock_supabase_service):
        """Test getting generation when it exists locally."""
        mock_settings.USE_CLOUD_STORAGE = True
        
        manager = HybridStorageManager(
            file_manager=mock_file_manager,
            supabase_service=mock_supabase_service
        )
        
        result = await manager.get_generation(
            project_id="test-project",
            generation_id="test-gen",
            version=1
        )
        
        # Should check local first
        mock_file_manager.get_generation_directory.assert_called_once()
        
        # Should NOT try cloud download
        mock_supabase_service.download_generation.assert_not_called()
        
        assert result == Path("/path/to/gen")
    
    @pytest.mark.asyncio
    @patch('app.services.storage_manager.settings')
    async def test_get_generation_cloud_fallback(self, mock_settings, mock_file_manager, mock_supabase_service):
        """Test getting generation from cloud when not local."""
        mock_settings.USE_CLOUD_STORAGE = True
        
        # Mock local not found
        mock_file_manager.get_generation_directory = AsyncMock(return_value=None)
        
        manager = HybridStorageManager(
            file_manager=mock_file_manager,
            supabase_service=mock_supabase_service
        )
        
        result = await manager.get_generation(
            project_id="test-project",
            generation_id="test-gen",
            version=1
        )
        
        # Should try local first
        mock_file_manager.get_generation_directory.assert_called_once()
        
        # Should fall back to cloud
        mock_supabase_service.download_generation.assert_called_once()
        
        assert result == Path("/cache/gen")
    
    @pytest.mark.asyncio
    @patch('app.services.storage_manager.settings')
    async def test_get_download_url_cloud_preferred(self, mock_settings, mock_file_manager, mock_supabase_service):
        """Test download URL generation prefers cloud URL."""
        mock_settings.USE_CLOUD_STORAGE = True
        
        manager = HybridStorageManager(
            file_manager=mock_file_manager,
            supabase_service=mock_supabase_service
        )
        
        url = await manager.get_download_url(
            project_id="test-project",
            generation_id="test-gen",
            version=1
        )
        
        # Should try cloud first
        mock_supabase_service.get_signed_download_url.assert_called_once()
        
        # Should return cloud URL
        assert url == "https://signed.url"
    
    @pytest.mark.asyncio
    @patch('app.services.storage_manager.settings')
    async def test_get_download_url_local_fallback(self, mock_settings, mock_file_manager, mock_supabase_service):
        """Test download URL falls back to local when cloud fails."""
        mock_settings.USE_CLOUD_STORAGE = True
        
        # Mock cloud URL generation failure
        mock_supabase_service.get_signed_download_url = AsyncMock(return_value=None)
        
        manager = HybridStorageManager(
            file_manager=mock_file_manager,
            supabase_service=mock_supabase_service
        )
        
        url = await manager.get_download_url(
            project_id="test-project",
            generation_id="test-gen",
            version=1
        )
        
        # Should try cloud first
        mock_supabase_service.get_signed_download_url.assert_called_once()
        
        # Should fall back to local URL
        mock_file_manager.get_download_url.assert_called_once()
        assert url == "http://localhost/download/test"
    
    @pytest.mark.asyncio
    @patch('app.services.storage_manager.settings')
    async def test_delete_generation(self, mock_settings, mock_file_manager, mock_supabase_service):
        """Test deleting generation from both local and cloud."""
        mock_settings.USE_CLOUD_STORAGE = True
        
        manager = HybridStorageManager(
            file_manager=mock_file_manager,
            supabase_service=mock_supabase_service
        )
        
        result = await manager.delete_generation(
            project_id="test-project",
            generation_id="test-gen",
            version=1,
            delete_local=True,
            delete_cloud=True
        )
        
        # Should delete from both
        mock_file_manager.delete_project.assert_called_once()
        mock_supabase_service.delete_generation.assert_called_once()
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch('app.services.storage_manager.settings')
    async def test_cleanup_old_cache(self, mock_settings, mock_file_manager, mock_supabase_service):
        """Test cache cleanup."""
        mock_settings.USE_CLOUD_STORAGE = True
        
        manager = HybridStorageManager(
            file_manager=mock_file_manager,
            supabase_service=mock_supabase_service
        )
        
        count = await manager.cleanup_old_cache()
        
        mock_supabase_service.cleanup_old_cache.assert_called_once()
        assert count == 5
    
    @pytest.mark.asyncio
    @patch('app.services.storage_manager.settings')
    async def test_get_storage_info(self, mock_settings, mock_file_manager, mock_supabase_service):
        """Test getting storage information."""
        mock_settings.USE_CLOUD_STORAGE = True
        
        manager = HybridStorageManager(
            file_manager=mock_file_manager,
            supabase_service=mock_supabase_service
        )
        
        info = await manager.get_storage_info(
            project_id="test-project",
            generation_id="test-gen",
            version=1
        )
        
        assert "cloud_enabled" in info
        assert "local_exists" in info
        assert "cloud_exists" in info
        assert info["cloud_enabled"] is True


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with local-only mode."""
    
    @pytest.mark.asyncio
    @patch('app.services.storage_manager.settings')
    async def test_local_only_mode(self, mock_settings, sample_files):
        """Test that system works in local-only mode."""
        mock_settings.USE_CLOUD_STORAGE = False
        
        # Mock file manager
        mock_file_manager = AsyncMock(spec=FileManager)
        mock_file_manager.save_generation_files_hierarchical = AsyncMock(
            return_value=("/path/to/gen", 3, 1024)
        )
        
        # Mock disabled supabase service
        mock_supabase = AsyncMock(spec=SupabaseStorageService)
        mock_supabase.enabled = False
        
        manager = HybridStorageManager(
            file_manager=mock_file_manager,
            supabase_service=mock_supabase
        )
        
        # Should work without cloud
        storage_path, file_count, total_size = await manager.save_generation(
            project_id="test-project",
            generation_id="test-gen",
            version=1,
            files=sample_files
        )
        
        assert storage_path == "/path/to/gen"
        assert file_count == 3
        
        # Cloud upload should not be attempted
        mock_supabase.upload_generation.assert_not_called()
