# Unit tests for preview log streamer
"""
Tests for the PreviewLogStreamer service.
Tests SSE streaming, subprocess management, and log handling.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from app.services.preview_log_streamer import PreviewLogStreamer, register_streamer, unregister_streamer, get_streamer


class TestPreviewLogStreamer:
    """Test preview log streamer functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def streamer(self, temp_dir):
        """Create test streamer instance."""
        return PreviewLogStreamer(
            preview_id="test_preview_123",
            temp_dir=str(temp_dir),
            port=3001
        )

    def test_initialization(self, streamer, temp_dir):
        """Test streamer initialization."""
        assert streamer.preview_id == "test_preview_123"
        assert streamer.temp_dir == temp_dir
        assert streamer.port == 3001
        assert not streamer.is_running()

    @pytest.mark.asyncio
    async def test_start_preview_with_logging(self, streamer, temp_dir):
        """Test starting preview with logging."""
        # Create minimal FastAPI app for testing
        main_py = temp_dir / "app" / "main.py"
        main_py.parent.mkdir(parents=True, exist_ok=True)
        main_py.write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy"}
""")

        # Create requirements.txt
        (temp_dir / "requirements.txt").write_text("fastapi==0.104.1\nuvicorn==0.24.0")

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_process.stdout.readline.side_effect = [
                "INFO: Started server process [12345]",
                "INFO: Waiting for application startup.",
                "INFO: Application startup complete.",
                ""  # EOF
            ]
            mock_popen.return_value = mock_process

            process = await streamer.start_preview_with_logging()

            assert process == mock_process
            mock_popen.assert_called_once()
            assert streamer.is_running()

    @pytest.mark.asyncio
    async def test_stream_logs_basic(self, streamer):
        """Test basic log streaming functionality."""
        # Start the streamer
        streamer.running.set()

        # Put a log entry in the queue
        log_entry = {
            "timestamp": "2025-10-20T12:00:00Z",
            "level": "INFO",
            "message": "Test log message",
            "source": "preview"
        }
        streamer.log_queue.put_nowait(log_entry)

        # Collect streamed events
        events = []
        async for event in streamer.stream_logs():
            events.append(event)
            break  # Stop after first event

        # Should have received one SSE event
        assert len(events) == 1
        assert "data:" in events[0]
        assert "Test log message" in events[0]
        assert events[0].startswith("id: 1\n")

    @pytest.mark.asyncio
    async def test_stream_logs_heartbeat(self, streamer):
        """Test heartbeat messages when no logs available."""
        # Start the streamer
        streamer.running.set()

        # Mock to simulate heartbeat timing
        events = []
        with patch('asyncio.sleep') as mock_sleep:
            # Make sleep raise CancelledError to stop the generator
            mock_sleep.side_effect = asyncio.CancelledError()

            try:
                async for event in streamer.stream_logs():
                    events.append(event)
            except asyncio.CancelledError:
                pass

        # Should not have received events (no logs, heartbeat takes 30s)
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_stream_logs_stopped(self, streamer):
        """Test that streaming stops when streamer is stopped."""
        # Don't start the streamer (running not set)

        events = []
        async for event in streamer.stream_logs():
            events.append(event)

        # Should not yield any events when not running
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_stop_streamer(self, streamer):
        """Test stopping the streamer."""
        # Start streamer
        streamer.running.set()

        # Mock process
        mock_process = Mock()
        mock_process.poll.return_value = None
        streamer.process = mock_process

        # Stop streamer
        await streamer.stop()

        assert not streamer.is_running()
        mock_process.terminate.assert_called_once()
        assert streamer.process is None

    def test_get_stats(self, streamer):
        """Test getting streamer statistics."""
        stats = streamer.get_stats()

        assert stats["preview_id"] == "test_preview_123"
        assert "running" in stats
        assert "process_pid" in stats
        assert "logs_processed" in stats
        assert "queue_size" in stats

    def test_global_registry(self):
        """Test global streamer registry functions."""
        streamer = PreviewLogStreamer("test_id", "/tmp", 3001)

        # Register streamer
        register_streamer("test_id", streamer)
        assert get_streamer("test_id") == streamer

        # Unregister streamer
        unregister_streamer("test_id")
        assert get_streamer("test_id") is None

    def test_extract_log_level(self, streamer):
        """Test log level extraction from Uvicorn output."""
        test_cases = [
            ("INFO: Application started", "INFO"),
            ("WARNING: Deprecated feature", "WARN"),
            ("ERROR: Database connection failed", "ERROR"),
            ("DEBUG: Processing request", "DEBUG"),
            ("Some random message", "INFO"),  # Default
        ]

        for line, expected_level in test_cases:
            assert streamer._extract_log_level(line) == expected_level