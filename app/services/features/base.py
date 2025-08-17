from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Protocol


@dataclass
class ProjectContext:
    domain: str
    tech_stack: Dict[str, str]
    constraints: Dict[str, str]


class FeatureModule(Protocol):
    name: str

    def apply_to_project(self, project_files: Dict[str, str], ctx: ProjectContext) -> Dict[str, str]:
        """Augment or edit generated files in-place and return updated mapping.
        Implementations should be idempotent.
        """
        ...
