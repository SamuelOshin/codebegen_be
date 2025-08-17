from __future__ import annotations

from typing import Dict

from .base import FeatureModule, ProjectContext


class RealTimeModule:
    name = "real_time"

    def apply_to_project(self, project_files: Dict[str, str], ctx: ProjectContext) -> Dict[str, str]:
        project_files.setdefault("app/routers/realtime.py", "# TODO: Implement WebSocket/SSE endpoints\n")
        return project_files
