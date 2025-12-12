# Preview service for managing preview instances
"""
Service layer for preview instance management.
Handles launch, stop, and status operations using existing infrastructure.
"""

import asyncio
import httpx
import secrets
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from loguru import logger

from app.models.preview import PreviewInstance
from app.models.generation import Generation
from app.services.preview_log_streamer import PreviewLogStreamer, get_streamer, register_streamer, unregister_streamer
from app.services.storage_manager import HybridStorageManager
from app.utils.port_allocator import port_allocator
from app.core.database import get_async_db


class PreviewService:
    """
    Service for managing preview instances.

    Handles the complete lifecycle of preview instances:
    - Launch with file extraction and subprocess startup
    - Health monitoring
    - Resource cleanup
    - Status tracking
    """

    def __init__(self, storage_manager: Optional[HybridStorageManager] = None):
        """
        Initialize preview service.

        Args:
            storage_manager: Storage manager for accessing generation files
        """
        self.storage_manager = storage_manager or HybridStorageManager()

    async def launch_preview(
        self,
        generation_id: str,
        project_id: str,
        user_id: str,
        db: AsyncSession
    ) -> PreviewInstance:
        """
        Launch a new preview instance.

        Args:
            generation_id: Generation to preview
            project_id: Project ID
            user_id: User launching preview
            db: Database session

        Returns:
            Created preview instance

        Raises:
            ValueError: If generation invalid or files missing
            RuntimeError: If port allocation or startup fails
        """
        # Validate generation exists and user has access
        generation = await db.get(Generation, generation_id)
        if not generation:
            raise ValueError(f"Generation {generation_id} not found")

        if generation.user_id != user_id:
            raise ValueError(f"User {user_id} does not own generation {generation_id}")

        # Check for existing active preview
        existing = await self._get_active_preview(generation_id, db)
        if existing:
            logger.info(f"Stopping existing preview {existing.id} for generation {generation_id}")
            await self.stop_preview(existing, db)

        # Check user preview limit (1 for MVP) - after stopping existing
        user_active_count = await self._count_user_active_previews(user_id, db)
        if user_active_count >= 1:
            raise ValueError(f"User {user_id} has reached preview limit (1)")

        # Allocate port
        port = port_allocator.allocate()
        if not port:
            raise RuntimeError("No available ports for preview instance")

        # Create preview record
        preview = PreviewInstance(
            generation_id=generation_id,
            project_id=project_id,
            user_id=user_id,
            port=port,
            base_url=f"http://localhost:{port}",
            status="launching",
            preview_token=self._generate_preview_token(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            token_expires_at=datetime.utcnow() + timedelta(hours=1)
        )

        db.add(preview)
        await db.commit()
        await db.refresh(preview)

        # Start async launch process
        asyncio.create_task(self._launch_preview_instance(preview, generation, db))

        logger.info(f"Preview {preview.id} launched for generation {generation_id}")
        return preview

    async def _launch_preview_instance(
        self,
        preview: PreviewInstance,
        generation: Generation,
        db: AsyncSession
    ):
        """
        Async task to launch preview instance.
        Handles file extraction, subprocess startup, and health checks.
        """
        temp_dir = None
        streamer = None

        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix=f"preview_{preview.id}_")
            temp_path = Path(temp_dir)

            # Extract generation files
            await self._extract_generation_files(generation, temp_path)

            # Create log streamer
            streamer = PreviewLogStreamer(
                preview_id=preview.id,
                temp_dir=temp_dir,
                port=preview.port
            )
            register_streamer(preview.id, streamer)

            # Start subprocess with logging
            process = await streamer.start_preview_with_logging()
            preview.process_id = process.pid

            # Wait for startup and perform health checks
            await self._wait_for_startup(preview)

            # Update status
            preview.started_at = datetime.utcnow()
            preview.status = "running"
            preview.health_status = "healthy"
            preview.temp_directory = temp_dir

            await db.commit()

            logger.info(f"Preview {preview.id} started successfully")

        except Exception as e:
            logger.error(f"Preview launch failed for {preview.id}: {e}", exc_info=True)

            # Cleanup on failure
            if streamer:
                await streamer.stop()
                unregister_streamer(preview.id)

            # Keep temp directory for debugging
            # if temp_dir and Path(temp_dir).exists():
            #     shutil.rmtree(temp_dir, ignore_errors=True)

            # Update preview status
            preview.status = "failed"
            preview.health_status = "unhealthy"
            preview.error_message = str(e)

            await db.commit()

    async def _extract_generation_files(self, generation: Generation, temp_dir: Path):
        """
        Extract generation files to temporary directory.

        Args:
            generation: Generation to extract
            temp_dir: Target directory
        """
        # Get files from generation output_files
        files = generation.output_files or {}
        # Get files from storage
        # files = await self.storage_manager.get_generation_files(generation.id)        

        # Validate required files exist
        required_files = ["app/main.py", "requirements.txt"]
        missing_files = [f for f in required_files if f not in files]
        if missing_files:
            raise ValueError(f"Missing required files: {missing_files}")

        # Write files to temp directory
        for file_path, content in files.items():
            full_path = temp_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(content, str):
                full_path.write_text(content)
            else:
                # Binary content
                full_path.write_bytes(content)

            logger.info(f"Extracted file: {file_path} ({len(content) if isinstance(content, str) else len(content)} chars)")

        logger.info(f"Extracted {len(files)} files for generation {generation.id}: {list(files.keys())}")

    async def _wait_for_startup(self, preview: PreviewInstance, timeout: int = 30):
        """
        Wait for preview instance to start and pass health checks.

        Args:
            preview: Preview instance
            timeout: Maximum time to wait in seconds

        Raises:
            RuntimeError: If startup fails or times out
        """
        health_url = f"{preview.base_url}/"

        for attempt in range(3):  # 3 attempts
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(health_url)
                    if response.status_code in [200, 404]:  # Accept both 200 (FastAPI docs) and 404 (no root route)
                        logger.info(f"Preview {preview.id} health check passed")
                        return
            except Exception as e:
                logger.debug(f"Health check attempt {attempt + 1} failed: {e}")

            await asyncio.sleep(1)  # Wait 1 second between attempts

        raise RuntimeError(f"Preview {preview.id} failed health check after {timeout}s")

    async def stop_preview(self, preview: PreviewInstance, db: AsyncSession):
        """
        Stop a preview instance and cleanup resources.

        Args:
            preview: Preview instance to stop
        """
        logger.info(f"Stopping preview {preview.id}")

        # Stop streamer
        streamer = get_streamer(preview.id)
        if streamer:
            await streamer.stop()
            unregister_streamer(preview.id)

        # Release port
        if preview.port:
            port_allocator.release(preview.port)

        # Clean up temp directory
        if preview.temp_directory and Path(preview.temp_directory).exists():
            try:
                shutil.rmtree(preview.temp_directory)
                logger.info(f"Cleaned up temp directory for preview {preview.id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {preview.temp_directory}: {e}")

        # Update status
        preview.status = "stopped"
        preview.stopped_at = datetime.utcnow()
        preview.health_status = "unknown"

        await db.commit()

        logger.info(f"Preview {preview.id} stopped successfully")

    async def get_preview_status(self, generation_id: str, db: AsyncSession) -> Optional[PreviewInstance]:
        """
        Get active preview for a generation.

        Args:
            generation_id: Generation ID

        Returns:
            Active preview instance or None
        """
        return await self._get_active_preview(generation_id, db)

    async def _get_active_preview(self, generation_id: str, db: AsyncSession) -> Optional[PreviewInstance]:
        """Get active preview for generation."""
        result = await db.execute(
            text("""
            SELECT id FROM preview_instances
            WHERE generation_id = :generation_id
            AND status IN ('launching', 'running')
            AND expires_at > :now
            ORDER BY created_at DESC
            LIMIT 1
            """),
            {"generation_id": generation_id, "now": datetime.utcnow()}
        )
        row = result.first()
        if row:
            return await db.get(PreviewInstance, row.id)
        return None

    async def _count_user_active_previews(self, user_id: str, db: AsyncSession) -> int:
        """Count active previews for user."""
        result = await db.execute(
            text("""
            SELECT COUNT(*) FROM preview_instances
            WHERE user_id = :user_id
            AND status IN ('launching', 'running')
            AND expires_at > :now
            """),
            {"user_id": user_id, "now": datetime.utcnow()}
        )
        return result.scalar()

    def _generate_preview_token(self) -> str:
        """Generate secure preview token."""
        return secrets.token_urlsafe(32)

    async def cleanup_expired_previews(self, db: AsyncSession):
        """
        Cleanup expired preview instances.
        Called by background task.
        """
        expired_previews = await db.execute(
            text("""
            SELECT id FROM preview_instances
            WHERE status IN ('launching', 'running')
            AND expires_at <= :now
            """),
            {"now": datetime.utcnow()}
        )

        expired_ids = [row.id for row in expired_previews.fetchall()]

        for preview_id in expired_ids:
            preview = await db.get(PreviewInstance, preview_id)
            if preview:
                logger.info(f"Cleaning up expired preview {preview.id}")
                await self.stop_preview(preview, db)