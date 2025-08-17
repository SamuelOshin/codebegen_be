from __future__ import annotations

from typing import Dict

from .base import FeatureModule, ProjectContext


class SearchModule:
    name = "search"

    def apply_to_project(self, project_files: Dict[str, str], ctx: ProjectContext) -> Dict[str, str]:
        project_files.setdefault("app/services/search.py", "# TODO: Implement search (Elasticsearch/PG FTS)\n")
        return project_files
