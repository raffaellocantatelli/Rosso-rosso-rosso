"""Registry in-memory: default locale / test. Non è il composition root."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryNodeRegistry:
    def __init__(self) -> None:
        self._keys: dict[str, dict[str, dict[str, Any]]] = {}

    def register(self, node_id: str, key_id: str, public_key: str) -> dict[str, Any]:
        bucket = self._keys.setdefault(node_id, {})
        if key_id in bucket and bucket[key_id]["status"] != "revoked":
            raise ValueError(f"key già registrata: {node_id}/{key_id}")
        rec = {
            "node_id": node_id,
            "key_id": key_id,
            "public_key": public_key,
            "status": "active",
            "created_at": _now(),
            "revoked_at": None,
        }
        bucket[key_id] = rec
        return dict(rec)

    def rotate(
        self,
        node_id: str,
        old_key_id: str,
        new_key_id: str,
        new_public_key: str,
    ) -> dict[str, Any]:
        old = self.revoke(node_id, old_key_id)
        new = self.register(node_id, new_key_id, new_public_key)
        return {"old": old, "new": new}

    def revoke(self, node_id: str, key_id: str) -> dict[str, Any]:
        bucket = self._keys.get(node_id) or {}
        rec = bucket.get(key_id)
        if not rec:
            raise KeyError(f"key sconosciuta: {node_id}/{key_id}")
        rec = dict(rec)
        rec["status"] = "revoked"
        rec["revoked_at"] = _now()
        bucket[key_id] = rec
        return rec

    def get_active(self, node_id: str) -> list[dict[str, Any]]:
        bucket = self._keys.get(node_id) or {}
        return [dict(v) for v in bucket.values() if v["status"] == "active"]
