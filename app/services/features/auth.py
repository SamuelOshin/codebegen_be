from __future__ import annotations

from typing import Dict

from .base import FeatureModule, ProjectContext


class AuthModule:
    name = "auth"

    def apply_to_project(self, project_files: Dict[str, str], ctx: ProjectContext) -> Dict[str, str]:
        # Placeholder: Ensure auth scaffolding exists; add notes for later implementation
        project_files.setdefault("app/auth/__init__.py", "")
        project_files.setdefault("app/auth/handlers.py", "# TODO: Implement auth handlers (JWT/OAuth/RBAC)\n")
        project_files.setdefault("app/auth/dependencies.py", "# TODO: Implement security dependencies\n")
        return project_files
