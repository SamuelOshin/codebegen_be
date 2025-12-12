# Port allocator utility for preview instances
"""
Manages port allocation for preview instances.
Ensures no port conflicts in the 3001-3100 range.
"""

import socket
import threading
from typing import Set, Optional
from loguru import logger


class PortAllocator:
    """
    Thread-safe port allocator for preview instances.

    Manages allocation of ports in the 3001-3100 range to prevent conflicts
    between multiple preview instances running simultaneously.
    """

    def __init__(self, min_port: int = 3001, max_port: int = 3100):
        """
        Initialize port allocator.

        Args:
            min_port: Minimum port number (inclusive)
            max_port: Maximum port number (inclusive)
        """
        self.min_port = min_port
        self.max_port = max_port
        self._allocated_ports: Set[int] = set()
        self._lock = threading.Lock()

        logger.info(f"PortAllocator initialized: ports {min_port}-{max_port}")

    def allocate(self) -> Optional[int]:
        """
        Allocate an available port.

        Returns:
            Available port number, or None if no ports available
        """
        with self._lock:
            # Find available port
            for port in range(self.min_port, self.max_port + 1):
                if port not in self._allocated_ports and self._is_port_available(port):
                    self._allocated_ports.add(port)
                    logger.debug(f"Allocated port {port}")
                    return port

            logger.warning("No available ports in range")
            return None

    def release(self, port: int) -> bool:
        """
        Release a previously allocated port.

        Args:
            port: Port number to release

        Returns:
            True if port was released, False if it wasn't allocated
        """
        with self._lock:
            if port in self._allocated_ports:
                self._allocated_ports.remove(port)
                logger.debug(f"Released port {port}")
                return True
            else:
                logger.warning(f"Attempted to release unallocated port {port}")
                return False

    def is_allocated(self, port: int) -> bool:
        """
        Check if a port is currently allocated.

        Args:
            port: Port number to check

        Returns:
            True if port is allocated, False otherwise
        """
        with self._lock:
            return port in self._allocated_ports

    def get_allocated_ports(self) -> Set[int]:
        """
        Get set of currently allocated ports.

        Returns:
            Set of allocated port numbers
        """
        with self._lock:
            return self._allocated_ports.copy()

    def get_available_count(self) -> int:
        """
        Get number of available ports.

        Returns:
            Number of ports available for allocation
        """
        with self._lock:
            allocated_count = len(self._allocated_ports)
            total_ports = self.max_port - self.min_port + 1
            return total_ports - allocated_count

    def _is_port_available(self, port: int) -> bool:
        """
        Check if a port is available (not in use by any process).

        Args:
            port: Port number to check

        Returns:
            True if port is available, False if in use
        """
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('localhost', port))
                return True
        except OSError:
            # Port is in use
            return False

    def __repr__(self) -> str:
        allocated = len(self._allocated_ports)
        total = self.max_port - self.min_port + 1
        return f"<PortAllocator(allocated={allocated}/{total}, range={self.min_port}-{self.max_port})>"


# Global port allocator instance
port_allocator = PortAllocator()