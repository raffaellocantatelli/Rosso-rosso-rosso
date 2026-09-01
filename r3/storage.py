"""Storage content-addressed: l'ID di un documento è lo SHA-256 del contenuto.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import hashlib
import os

from . import config

DOCS_DIR = os.path.join(config.DATA_DIR, "documents")


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def path_for(doc_id: str) -> str:
    return os.path.join(DOCS_DIR, doc_id)


def exists(doc_id: str) -> bool:
    return os.path.exists(path_for(doc_id))


def save(content: bytes) -> str:
    """Salva il contenuto e ne restituisce l'ID (SHA-256)."""
    os.makedirs(DOCS_DIR, exist_ok=True)
    doc_id = compute_hash(content)
    with open(path_for(doc_id), "wb") as f:
        f.write(content)
    return doc_id


def save_with_id(doc_id: str, content: bytes):
    """Salva un contenuto ricevuto da un peer, verificando che l'hash corrisponda all'ID dichiarato."""
    actual = compute_hash(content)
    if actual != doc_id:
        raise ValueError(f"Hash mismatch: atteso {doc_id}, calcolato {actual}")
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(path_for(doc_id), "wb") as f:
        f.write(content)


def read(doc_id: str) -> bytes:
    with open(path_for(doc_id), "rb") as f:
        return f.read()
