# Unit tests for port allocator
"""
Tests for the PortAllocator utility.
Ensures proper port allocation and release functionality.
"""

import pytest
from app.utils.port_allocator import PortAllocator


class TestPortAllocator:
    """Test port allocation utility in isolation."""

    def test_allocate_returns_valid_port(self):
        """Should return port within configured range."""
        allocator = PortAllocator(min_port=3001, max_port=3100)
        port = allocator.allocate()
        assert 3001 <= port <= 3100

    def test_allocate_returns_different_ports(self):
        """Should return different ports on consecutive allocations."""
        allocator = PortAllocator(min_port=3001, max_port=3100)
        port1 = allocator.allocate()
        port2 = allocator.allocate()
        assert port1 != port2
        assert 3001 <= port1 <= 3100
        assert 3001 <= port2 <= 3100

    def test_release_port_makes_it_available(self):
        """Released port should be reusable."""
        allocator = PortAllocator(min_port=3001, max_port=3100)
        port = allocator.allocate()
        allocator.release(port)
        reused_port = allocator.allocate()
        assert port == reused_port

    def test_release_unknown_port_no_error(self):
        """Releasing unknown port should not raise error."""
        allocator = PortAllocator()
        # Should not raise exception
        allocator.release(9999)

    def test_get_allocated_ports_returns_copy(self):
        """get_allocated_ports should return a copy, not reference."""
        allocator = PortAllocator(min_port=3001, max_port=3100)
        port = allocator.allocate()
        allocated = allocator.get_allocated_ports()
        allocated.add(9999)  # Modify the returned set
        # Original should be unchanged
        assert 9999 not in allocator.get_allocated_ports()

    def test_get_available_count(self):
        """Should correctly count available ports."""
        allocator = PortAllocator(min_port=3001, max_port=3005)  # 5 ports total
        initial_available = allocator.get_available_count()
        assert initial_available == 5

        # Allocate 2 ports
        allocator.allocate()
        allocator.allocate()
        assert allocator.get_available_count() == 3

        # Release 1 port
        allocated_ports = allocator.get_allocated_ports()
        port_to_release = next(iter(allocated_ports))
        allocator.release(port_to_release)
        assert allocator.get_available_count() == 4

    def test_allocate_none_when_no_ports_available(self):
        """Should return None when no ports are available."""
        allocator = PortAllocator(min_port=3001, max_port=3002)  # Only 2 ports

        # Allocate both ports
        port1 = allocator.allocate()
        port2 = allocator.allocate()
        assert port1 is not None
        assert port2 is not None

        # Next allocation should return None
        port3 = allocator.allocate()
        assert port3 is None

    def test_is_allocated_correct(self):
        """is_allocated should correctly report port status."""
        allocator = PortAllocator(min_port=3001, max_port=3100)
        port = allocator.allocate()

        assert allocator.is_allocated(port)
        assert not allocator.is_allocated(port + 1)  # Different port

        allocator.release(port)
        assert not allocator.is_allocated(port)

    def test_repr_includes_stats(self):
        """__repr__ should include useful statistics."""
        allocator = PortAllocator(min_port=3001, max_port=3100)
        repr_str = repr(allocator)
        assert "PortAllocator" in repr_str
        assert "allocated=0/100" in repr_str  # 3100-3001+1 = 100

        allocator.allocate()
        repr_str = repr(allocator)
        assert "allocated=1/100" in repr_str