from __future__ import annotations

from typing import Dict

from .base import FeatureModule, ProjectContext


class CachingModule:
    name = "caching"

    def apply_to_project(self, project_files: Dict[str, str], ctx: ProjectContext) -> Dict[str, str]:
        project_files.setdefault("app/services/cache.py", "# TODO: Implement Redis/in-memory caching\n")
        return project_files
