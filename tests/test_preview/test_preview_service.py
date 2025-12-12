# Unit tests for PreviewService
"""
Unit tests for PreviewService class.
Tests preview lifecycle management functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from app.services.preview_service import PreviewService
from app.models.preview import PreviewInstance
from app.models.generation import Generation
from app.utils.port_allocator import PortAllocator


@pytest.mark.asyncio
class TestPreviewService:
    """Unit tests for PreviewService."""

    @pytest.fixture
    def preview_service(self):
        """Create PreviewService instance."""
        return PreviewService()

    @pytest.fixture
    def mock_generation(self):
        """Create mock generation."""
        generation = MagicMock(spec=Generation)
        generation.id = "test_gen_id"
        generation.user_id = "test_user_id"
        generation.output_files = {
            "app/main.py": "print('hello')",
            "requirements.txt": "fastapi==0.104.1"
        }
        return generation

    @pytest.fixture
    def mock_preview_instance(self):
        """Create mock preview instance."""
        preview = MagicMock(spec=PreviewInstance)
        preview.id = "test_preview_id"
        preview.generation_id = "test_gen_id"
        preview.port = 3001
        preview.status = "stopped"
        preview.base_url = "http://localhost:3001"
        preview.preview_token = "test_token"
        return preview

    async def test_launch_preview_success(
        self,
        preview_service: PreviewService,
        mock_generation: Generation,
        mock_preview_instance: PreviewInstance
    ):
        """Test successful preview launch."""
        mock_db = AsyncMock()

        with patch.object(preview_service, '_extract_generation_files') as mock_extract, \
             patch.object(preview_service, '_launch_preview_instance') as mock_launch, \
             patch.object(preview_service, '_wait_for_startup') as mock_wait, \
             patch.object(preview_service, '_get_active_preview') as mock_get_active, \
             patch.object(preview_service, '_count_user_active_previews') as mock_count, \
             patch('app.services.preview_service.PreviewInstance') as mock_model, \
             patch('app.utils.port_allocator.port_allocator.allocate') as mock_allocate:

            mock_generation.user_id = "test_user_id"
            mock_db.get.return_value = mock_generation
            mock_get_active.return_value = None
            mock_count.return_value = 0
            mock_allocate.return_value = 3001
            mock_model.return_value = mock_preview_instance
            mock_extract.return_value = Path("/tmp/test_preview")
            mock_launch.return_value = mock_preview_instance
            mock_wait.return_value = None  # _wait_for_startup doesn't return on success

            result = await preview_service.launch_preview("test_gen_id", "test_project_id", "test_user_id", mock_db)

            assert result == mock_preview_instance
            mock_launch.assert_called_once()

    async def test_launch_preview_generation_not_found(self, preview_service: PreviewService):
        """Test preview launch when generation not found."""
        mock_db = AsyncMock()
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="Generation test_gen_id not found"):
            await preview_service.launch_preview("test_gen_id", "test_project_id", "test_user_id", mock_db)

    async def test_launch_preview_not_owner(self, preview_service: PreviewService, mock_generation: Generation):
        """Test preview launch when user doesn't own generation."""
        mock_db = AsyncMock()
        mock_generation.user_id = "different_user_id"
        mock_db.get.return_value = mock_generation

        with pytest.raises(ValueError, match="User test_user_id does not own generation test_gen_id"):
            await preview_service.launch_preview("test_gen_id", "test_project_id", "test_user_id", mock_db)

    async def test_launch_preview_already_running(self, preview_service: PreviewService, mock_preview_instance: PreviewInstance):
        """Test preview launch when preview already running."""
        mock_db = AsyncMock()
        mock_generation = MagicMock()
        mock_generation.user_id = "test_user_id"
        mock_db.get.return_value = mock_generation

        with patch.object(preview_service, '_get_active_preview') as mock_get_active:
            mock_get_active.return_value = mock_preview_instance

            with pytest.raises(ValueError, match="Preview already running for generation test_gen_id"):
                await preview_service.launch_preview("test_gen_id", "test_project_id", "test_user_id", mock_db)

    async def test_stop_preview_success(
        self,
        preview_service: PreviewService,
        mock_preview_instance: PreviewInstance
    ):
        """Test successful preview stop."""
        mock_db = AsyncMock()
        mock_preview_instance.process_pid = 12345

        with patch('app.services.preview_service.PreviewLogStreamer') as mock_streamer, \
             patch('app.services.preview_service.get_streamer') as mock_get_streamer, \
             patch('psutil.Process') as mock_process_class, \
             patch('app.utils.port_allocator.port_allocator.release') as mock_release:

            mock_process = MagicMock()
            mock_process_class.return_value = mock_process
            mock_streamer_instance = AsyncMock()
            mock_streamer.return_value = mock_streamer_instance
            mock_get_streamer.return_value = mock_streamer_instance

            await preview_service.stop_preview(mock_preview_instance, mock_db)

            mock_streamer_instance.stop.assert_called_once()
            mock_release.assert_called_once_with(3001)
            assert mock_preview_instance.status == "stopped"

    async def test_stop_preview_no_pid(
        self,
        preview_service: PreviewService,
        mock_preview_instance: PreviewInstance
    ):
        """Test stopping preview with no process PID."""
        mock_db = AsyncMock()
        mock_preview_instance.process_pid = None

        with patch('app.utils.port_allocator.port_allocator.release') as mock_release:
            await preview_service.stop_preview(mock_preview_instance, mock_db)

            mock_release.assert_called_once_with(3001)
            assert mock_preview_instance.status == "stopped"

    async def test_get_preview_status_running(
        self,
        preview_service: PreviewService,
        mock_preview_instance: PreviewInstance
    ):
        """Test getting status of running preview."""
        mock_db = AsyncMock()

        with patch.object(preview_service, '_get_active_preview') as mock_get_active:
            mock_get_active.return_value = mock_preview_instance

            result = await preview_service.get_preview_status("test_gen_id", mock_db)

            assert result == mock_preview_instance
            mock_get_active.assert_called_once_with("test_gen_id", mock_db)

    async def test_get_preview_status_stopped(
        self,
        preview_service: PreviewService
    ):
        """Test getting status of stopped preview."""
        mock_db = AsyncMock()

        with patch.object(preview_service, '_get_active_preview') as mock_get_active:
            mock_get_active.return_value = None

            result = await preview_service.get_preview_status("test_gen_id", mock_db)

            assert result is None
            mock_get_active.assert_called_once_with("test_gen_id", mock_db)

    async def test_extract_generation_files_success(
        self,
        preview_service: PreviewService,
        mock_generation: Generation
    ):
        """Test successful file extraction."""
        with patch('tempfile.mkdtemp', return_value='/tmp/test_dir'), \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.write_text') as mock_write:

            result = await preview_service._extract_generation_files(mock_generation, Path("/tmp/test_dir"))

            assert result is None
            assert mock_write.call_count == 2  # Two files in mock generation

    async def test_extract_generation_files_no_files(
        self,
        preview_service: PreviewService
    ):
        """Test file extraction with no files in generation."""
        generation = MagicMock(spec=Generation)
        generation.output_files = {}

        with pytest.raises(ValueError, match="Missing required files: \\['app/main.py', 'requirements.txt'\\]"):
            await preview_service._extract_generation_files(generation, Path("/tmp/test_dir"))

    async def test_wait_for_startup_success(self, preview_service: PreviewService):
        """Test successful health check wait."""
        mock_preview = MagicMock(spec=PreviewInstance)
        mock_preview.base_url = "http://localhost:3001"
        mock_preview.id = "test_preview_id"

        with patch('httpx.AsyncClient') as mock_client_class, \
             patch('asyncio.sleep') as mock_sleep:

            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            # Should not raise exception
            await preview_service._wait_for_startup(mock_preview, timeout=5)

    async def test_wait_for_startup_timeout(self, preview_service: PreviewService):
        """Test health check timeout."""
        mock_preview = MagicMock(spec=PreviewInstance)
        mock_preview.base_url = "http://localhost:3001"
        mock_preview.id = "test_preview_id"

        with patch('httpx.AsyncClient') as mock_client_class, \
             patch('asyncio.sleep') as mock_sleep:

            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Connection failed")

            with pytest.raises(RuntimeError, match="Preview test_preview_id failed health check"):
                await preview_service._wait_for_startup(mock_preview, timeout=2)