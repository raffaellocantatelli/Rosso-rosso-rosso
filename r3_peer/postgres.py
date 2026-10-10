"""PostgreSQL NodeRegistry. Importato solo dalla factory, mai da FabricNode."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS node_keys (
    node_id TEXT NOT NULL,
    key_id TEXT NOT NULL,
    public_key TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    PRIMARY KEY (node_id, key_id)
);
"""


class PostgreSQLNodeRegistry:
    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("NODE_REGISTRY_DSN vuoto")
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "psycopg non installato; usa InMemory o installa psycopg[binary]"
            ) from exc
        self._psycopg = psycopg
        self._dsn = dsn
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(_SCHEMA)
            conn.commit()

    def _connect(self):
        return self._psycopg.connect(self._dsn)

    def register(self, node_id: str, key_id: str, public_key: str) -> dict[str, Any]:
        created = _now()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT status FROM node_keys
                    WHERE node_id = %s AND key_id = %s
                    """,
                    (node_id, key_id),
                )
                row = cur.fetchone()
                if row and row[0] != "revoked":
                    raise ValueError(f"key già registrata: {node_id}/{key_id}")
                cur.execute(
                    """
                    INSERT INTO node_keys
                        (node_id, key_id, public_key, status, created_at, revoked_at)
                    VALUES (%s, %s, %s, 'active', %s, NULL)
                    ON CONFLICT (node_id, key_id) DO UPDATE SET
                        public_key = EXCLUDED.public_key,
                        status = 'active',
                        created_at = EXCLUDED.created_at,
                        revoked_at = NULL
                    """,
                    (node_id, key_id, public_key, created),
                )
            conn.commit()
        return {
            "node_id": node_id,
            "key_id": key_id,
            "public_key": public_key,
            "status": "active",
            "created_at": created,
            "revoked_at": None,
        }

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
        revoked_at = _now()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE node_keys
                    SET status = 'revoked', revoked_at = %s
                    WHERE node_id = %s AND key_id = %s
                    RETURNING node_id, key_id, public_key, status, created_at, revoked_at
                    """,
                    (revoked_at, node_id, key_id),
                )
                row = cur.fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"key sconosciuta: {node_id}/{key_id}")
        return {
            "node_id": row[0],
            "key_id": row[1],
            "public_key": row[2],
            "status": row[3],
            "created_at": row[4].isoformat() if hasattr(row[4], "isoformat") else row[4],
            "revoked_at": row[5].isoformat() if hasattr(row[5], "isoformat") else row[5],
        }

    def get_active(self, node_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT node_id, key_id, public_key, status, created_at, revoked_at
                    FROM node_keys
                    WHERE node_id = %s AND status = 'active'
                    ORDER BY created_at
                    """,
                    (node_id,),
                )
                rows = cur.fetchall()
        out = []
        for row in rows:
            out.append(
                {
                    "node_id": row[0],
                    "key_id": row[1],
                    "public_key": row[2],
                    "status": row[3],
                    "created_at": row[4].isoformat() if hasattr(row[4], "isoformat") else row[4],
                    "revoked_at": (
                        row[5].isoformat() if row[5] is not None and hasattr(row[5], "isoformat") else row[5]
                    ),
                }
            )
        return out
