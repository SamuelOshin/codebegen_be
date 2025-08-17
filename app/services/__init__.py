"""Services package.

Avoid importing heavy singletons at package import time to keep tests light.
Import specific services directly from their modules when needed.
"""

__all__ = []
