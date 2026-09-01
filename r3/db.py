"""Metadati documenti + audit log append-only, su SQLite.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import os
import sqlite3
import time

from . import config

DB_PATH = os.path.join(config.DATA_DIR, "r3.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    signature TEXT NOT NULL,
    node_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event TEXT NOT NULL,
    document_id TEXT,
    node_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    detail TEXT
);
"""


def _connect():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def upsert_document(doc_id, size, signature, node_id):
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO documents (id, size, signature, node_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (doc_id, size, signature, node_id, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        )
        conn.commit()
    finally:
        conn.close()


def get_document(doc_id):
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_ids():
    conn = _connect()
    try:
        return [r["id"] for r in conn.execute("SELECT id FROM documents").fetchall()]
    finally:
        conn.close()


def list_documents():
    conn = _connect()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM documents").fetchall()]
    finally:
        conn.close()


def log_event(event, node_id, document_id=None, detail=None):
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO audit_log (event, document_id, node_id, timestamp, detail) VALUES (?, ?, ?, ?, ?)",
            (event, document_id, node_id, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), detail),
        )
        conn.commit()
    finally:
        conn.close()
