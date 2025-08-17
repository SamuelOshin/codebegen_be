from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Optional


GROUPS_DEFAULT = {
    "control": 0.25,
    "enhanced_templates": 0.25,
    "better_prompts": 0.25,
    "full_enhancement": 0.25,
}


@dataclass
class ABAssignment:
    user_id: str
    group: str


class ABTestManager:
    """Deterministic A/B assignment based on user_id hashing.

    Keeps assignment stable across sessions without persistence.
    """

    def __init__(self, groups: Optional[Dict[str, float]] = None) -> None:
        self.groups = groups or GROUPS_DEFAULT
        total = sum(self.groups.values())
        if abs(total - 1.0) > 1e-6:
            # Normalize to 1.0 if not exact
            self.groups = {k: v / total for k, v in self.groups.items()}

        # Precompute cumulative ranges
        self._ranges = []
        cum = 0.0
        for name, weight in self.groups.items():
            start = cum
            cum += weight
            self._ranges.append((name, start, cum))

    def _hash01(self, user_id: str) -> float:
        h = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
        # Use first 8 hex digits as integer for reproducibility
        val = int(h[:8], 16)
        return (val % 10_000_000) / 10_000_000.0

    def assign(self, user_id: str) -> ABAssignment:
        r = self._hash01(user_id)
        for name, start, end in self._ranges:
            if start <= r < end:
                return ABAssignment(user_id=user_id, group=name)
        # Fallback to last group if rounding errors
        return ABAssignment(user_id=user_id, group=self._ranges[-1][0])

# Lightweight module-level instance for convenience
ab_test_manager = ABTestManager()
