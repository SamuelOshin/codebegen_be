from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


DEFAULT_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class GenerationEvent:
    generation_id: str
    user_id: Optional[str]
    timestamp: str
    event: str  # success|failure|modifications|abandonment|metric
    details: Dict[str, Any]


class ValidationMetrics:
    """Lightweight JSONL logger for baseline metrics without DB changes."""

    def __init__(self, log_file: Optional[Path] = None) -> None:
        self.log_file = log_file or (DEFAULT_LOG_DIR / "validation_metrics.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, event: GenerationEvent) -> None:
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    def _event(self, generation_id: str, user_id: Optional[str], event: str, details: Dict[str, Any]) -> None:
        self._write(
            GenerationEvent(
                generation_id=generation_id,
                user_id=user_id,
                timestamp=datetime.utcnow().isoformat() + "Z",
                event=event,
                details=details,
            )
        )

    # Public API
    def track_generation_success(self, generation_id: str, user_id: Optional[str], success: bool, duration_ms: Optional[int] = None, errors: Optional[List[str]] = None) -> None:
        self._event(
            generation_id,
            user_id,
            "success" if success else "failure",
            {
                "duration_ms": duration_ms,
                "errors": errors or [],
            },
        )

    def track_user_modifications(self, generation_id: str, user_id: Optional[str], files_modified: List[str]) -> None:
        self._event(
            generation_id,
            user_id,
            "modifications",
            {
                "count": len(files_modified),
                "files": files_modified,
            },
        )

    def track_abandonment(self, generation_id: str, user_id: Optional[str], stage: str) -> None:
        self._event(
            generation_id,
            user_id,
            "abandonment",
            {
                "stage": stage,
            },
        )

    def track_metric(self, generation_id: str, user_id: Optional[str], name: str, value: Any) -> None:
        self._event(
            generation_id,
            user_id,
            "metric",
            {
                "name": name,
                "value": value,
            },
        )

# Lightweight module-level instance for convenience
validation_metrics = ValidationMetrics()
