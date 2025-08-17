"""
AI Models package for codebegen.

Note: Avoid importing heavy model modules at package import time to keep
test environments lightweight and decoupled from optional AI deps.
Import required classes directly from their submodules when needed, e.g.:

    from ai_models.model_loader import model_loader, ModelType
"""

__all__: list[str] = []