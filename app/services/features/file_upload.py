from __future__ import annotations

from typing import Dict

from .base import FeatureModule, ProjectContext


class FileUploadModule:
    name = "file_upload"

    def apply_to_project(self, project_files: Dict[str, str], ctx: ProjectContext) -> Dict[str, str]:
        project_files.setdefault("app/services/storage.py", "# TODO: Implement storage abstraction (S3/local)\n")
        project_files.setdefault("app/routers/uploads.py", "# TODO: Implement upload endpoints\n")
        return project_files
