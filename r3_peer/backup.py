"""Backup store minimo: snapshot append-only in memoria."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


class InMemoryBackupStore:
    def __init__(self) -> None:
        self.snapshots: list[dict[str, Any]] = []

    def snapshot(self, node_id: str, record: Mapping[str, Any]) -> None:
        self.snapshots.append(
            {
                "node_id": node_id,
                "at": datetime.now(timezone.utc).isoformat(),
                "record": dict(record),
            }
        )
