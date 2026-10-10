"""ChannelRegistry in-memory: observed vs canonical head (R3-PEER/1.1c)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryChannelRegistry:
    def __init__(self) -> None:
        self._channels: dict[str, dict[str, Any]] = {}

    def _row(self, channel_id: str) -> dict[str, Any]:
        return self._channels.setdefault(
            channel_id,
            {
                "channel_id": channel_id,
                "observed_head": None,
                "canonical_head": None,
                "updated_at": _now(),
            },
        )

    def observe(self, channel_id: str, observed_head: str) -> dict[str, Any]:
        row = self._row(channel_id)
        row["observed_head"] = observed_head
        row["updated_at"] = _now()
        return self.get_heads(channel_id)

    def set_canonical(self, channel_id: str, canonical_head: str) -> dict[str, Any]:
        row = self._row(channel_id)
        row["canonical_head"] = canonical_head
        row["updated_at"] = _now()
        return self.get_heads(channel_id)

    def get_heads(self, channel_id: str) -> dict[str, Any]:
        row = dict(self._row(channel_id))
        observed = row["observed_head"]
        canonical = row["canonical_head"]
        row["aligned"] = bool(observed and canonical and observed == canonical)
        return row
