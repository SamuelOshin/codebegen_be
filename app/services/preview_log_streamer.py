# Preview log streamer for SSE real-time logging
"""
Manages real-time log streaming from preview subprocess to frontend via SSE.
Captures stdout/stderr from Uvicorn subprocess and streams via Server-Sent Events.
"""

import asyncio
import threading
import subprocess
import json
import logging
import os
import sys
from datetime import datetime
from queue import Queue, Full, Empty as QueueEmpty
from typing import Optional, AsyncGenerator
from pathlib import Path

from app.models.preview import PreviewLog
from app.core.database import get_async_db
from loguru import logger

# Global registry of active streamers
preview_log_streamers: dict[str, 'PreviewLogStreamer'] = {}


def get_streamer(preview_id: str) -> Optional['PreviewLogStreamer']:
    """Get the streamer for a preview instance."""
    return preview_log_streamers.get(preview_id)


def register_streamer(preview_id: str, streamer: 'PreviewLogStreamer'):
    """Register a new streamer."""
    preview_log_streamers[preview_id] = streamer
    logger.info(f"Registered streamer for preview {preview_id}")


def unregister_streamer(preview_id: str):
    """Unregister a streamer."""
    if preview_id in preview_log_streamers:
        del preview_log_streamers[preview_id]
        logger.info(f"Unregistered streamer for preview {preview_id}")


class PreviewLogStreamer:
    """
    Manages real-time log streaming from preview subprocess to frontend.

    Features:
    - Subprocess execution with stdout/stderr capture
    - Real-time SSE streaming to frontend
    - Async log persistence to database
    - Thread-safe resource management
    - Automatic cleanup on errors
    """

    def __init__(self, preview_id: str, temp_dir: str, port: int):
        """
        Initialize log streamer.

        Args:
            preview_id: Unique preview instance ID
            temp_dir: Temporary directory containing project files
            port: Port number for Uvicorn server
        """
        self.preview_id = preview_id
        self.temp_dir = Path(temp_dir)
        self.port = port

        # Subprocess management
        self.process: Optional[subprocess.Popen] = None
        self.reader_thread: Optional[threading.Thread] = None
        self.running = threading.Event()

        # Log streaming
        self.log_queue: Queue = Queue(maxsize=1000)  # Bounded queue to prevent memory issues
        self.log_count = 0

        logger.info(f"PreviewLogStreamer initialized for {preview_id} on port {port}")

    async def start_preview_with_logging(self) -> subprocess.Popen:
        """
        Start Uvicorn subprocess and set up log streaming.

        Critical: PYTHONUNBUFFERED=1 ensures immediate output capture.

        Returns:
            Started subprocess
        """
        self.running.set()

        # Prepare environment - MUST inherit parent env or PATH/PYTHONPATH will be empty
        # But clear PYTHONPATH and sys.path to avoid importing from backend directory
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)  # Remove PYTHONPATH to avoid import conflicts
        env.update({
            "DATABASE_URL": "sqlite:///./preview.db",
            "PYTHONUNBUFFERED": "1",  # CRITICAL: No buffering
            "LOG_LEVEL": "INFO"
        })

        # Create a simple wrapper script that isolates imports
        wrapper_script = os.path.join(self.temp_dir, "_run_uvicorn.py")
        wrapper_code = f"""
import sys
import os
import traceback

try:
    # Remove backend app directory from sys.path to avoid import conflicts
    # But keep venv/site-packages for dependencies like uvicorn, sqlalchemy, etc.
    backend_dir = r'{os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}'
    sys.path = [p for p in sys.path if not (backend_dir in p and 'site-packages' not in p)]
    # Add current dir as first entry to find local app
    sys.path.insert(0, os.getcwd())

    # Now run uvicorn
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port={self.port},
        log_level="info",
        access_log=True
    )
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
"""
        with open(wrapper_script, 'w') as f:
            f.write(wrapper_code)

        # Start Uvicorn via wrapper script
        self.process = subprocess.Popen(
            [
                sys.executable,
                "_run_uvicorn.py"
            ],
            cwd=self.temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr into stdout
            text=True,
            bufsize=1,  # Line buffered for immediate output
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )

        # Start background thread to read subprocess output
        self.reader_thread = threading.Thread(
            target=self._read_process_output,
            name=f"LogReader-{self.preview_id}",
            daemon=True
        )
        self.reader_thread.start()

        # Wait briefly to capture any immediate startup errors
        await asyncio.sleep(1.0)
        
        # Check if process crashed immediately
        if self.process.poll() is not None:
            # Process exited - read what's in the log queue
            startup_logs = []
            while not self.log_queue.empty():
                try:
                    startup_logs.append(self.log_queue.get_nowait())
                except QueueEmpty:
                    break
            
            log_text = "\n".join([log["message"] for log in startup_logs])
            logger.error(f"Preview {self.preview_id} crashed on startup. Return code: {self.process.returncode}\nCaptured output:\n{log_text}")
            raise RuntimeError(f"Preview process exited immediately with code {self.process.returncode}")

        logger.info(f"Preview {self.preview_id} started with PID {self.process.pid}")

        return self.process

    def _read_process_output(self):
        """
        Continuously read subprocess stdout/stderr.
        Runs in background thread to avoid blocking main event loop.
        """
        try:
            while self.running.is_set() and self.process and self.process.stdout:
                # Read one line (blocks until newline)
                line = self.process.stdout.readline()

                if not line:
                    # EOF - process ended
                    returncode = self.process.poll()
                    if returncode != 0:
                        logger.warning(f"Process ended for {self.preview_id} with return code: {returncode}")
                    break

                # Capture subprocess output but don't log each line individually
                # (it's stored in log_queue for streaming)

                # Parse log level from Uvicorn output
                level = self._extract_log_level(line.strip())

                # Create log entry
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": level,
                    "message": line.strip(),
                    "source": "preview"
                }

                # Add to queue for streaming (non-blocking)
                try:
                    self.log_queue.put_nowait(log_entry)
                    self.log_count += 1
                except Full:
                    # Queue full - drop oldest entry to make room
                    try:
                        self.log_queue.get_nowait()
                        self.log_queue.put_nowait(log_entry)
                    except:
                        pass  # If we can't make room, drop the log

        except Exception as e:
            logger.error(f"Error reading process output for {self.preview_id}: {e}", exc_info=True)

        finally:
            logger.info(f"Reader thread stopping for {self.preview_id}")

    def _extract_log_level(self, line: str) -> str:
        """
        Extract log level from Uvicorn log format.

        Uvicorn formats: INFO, WARNING, ERROR, CRITICAL
        """
        line_upper = line.upper()

        if "ERROR" in line_upper or "CRITICAL" in line_upper:
            return "ERROR"
        elif "WARNING" in line_upper or "WARN" in line_upper:
            return "WARN"
        elif "DEBUG" in line_upper:
            return "DEBUG"
        else:
            return "INFO"

    async def stream_logs(self) -> AsyncGenerator[str, None]:
        """
        SSE generator - yields log entries as they arrive from subprocess.
        Frontend connects via GET /preview/logs/stream

        Yields:
            SSE formatted log entries
        """
        log_id = 0
        no_data_count = 0

        while self.running.is_set():
            try:
                # Non-blocking queue get with timeout
                log_entry = await asyncio.get_event_loop().run_in_executor(
                    None, self.log_queue.get, True, 0.1  # 100ms timeout
                )

                # Reset no data counter
                no_data_count = 0

                # Save to database asynchronously
                asyncio.create_task(self._save_log_to_db(log_entry))

                # Format as SSE
                log_id += 1
                sse_data = f"id: {log_id}\ndata: {json.dumps(log_entry)}\n\n"

                yield sse_data

            except Exception as e:
                # Handle queue empty or other exceptions
                if isinstance(e, QueueEmpty):
                    # No new logs in past 100ms
                    no_data_count += 1

                    # If no data for 30 seconds, send heartbeat
                    if no_data_count >= 300:  # 300 * 100ms = 30 seconds
                        no_data_count = 0
                        heartbeat = {
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "level": "INFO",
                            "message": "Connection active - waiting for logs",
                            "source": "heartbeat"
                        }
                        sse_data = f"id: {log_id}\ndata: {json.dumps(heartbeat)}\n\n"
                        yield sse_data

                    await asyncio.sleep(0.1)
                else:
                    # Unexpected error - log and continue
                    logger.error(f"Error in log streaming for {self.preview_id}: {e}")
                    await asyncio.sleep(0.1)

    async def _save_log_to_db(self, log_entry: dict):
        """
        Save log entry to database asynchronously.
        Non-blocking - doesn't affect SSE stream.
        """
        try:
            async for db in get_async_db():
                log = PreviewLog(
                    preview_instance_id=self.preview_id,
                    timestamp=datetime.fromisoformat(log_entry["timestamp"][:-1]),  # Remove 'Z'
                    level=log_entry["level"],
                    message=log_entry["message"]
                )
                db.add(log)
                await db.commit()
                break

        except Exception as e:
            logger.error(f"Failed to save log to DB for {self.preview_id}: {e}")

    async def stop(self):
        """
        Stop streaming and cleanup resources.
        Idempotent - safe to call multiple times.
        """
        if not self.running.is_set():
            return  # Already stopped

        logger.info(f"Stopping streamer for preview {self.preview_id}")

        # Signal threads to stop
        self.running.clear()

        # Terminate subprocess gracefully
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Process {self.preview_id} didn't terminate, killing")
                self.process.kill()

        # Wait for reader thread
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2)

        # Clear resources
        self.process = None
        self.reader_thread = None

        logger.info(f"Streamer stopped for preview {self.preview_id}")

    def is_running(self) -> bool:
        """Check if streamer is actively running."""
        return self.running.is_set()

    def get_stats(self) -> dict:
        """Get streamer statistics."""
        return {
            "preview_id": self.preview_id,
            "running": self.running.is_set(),
            "process_pid": self.process.pid if self.process else None,
            "logs_processed": self.log_count,
            "queue_size": self.log_queue.qsize()
        }