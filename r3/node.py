"""API del nodo R3-infinito.

Ogni nodo espone la stessa app: upload/download di documenti content-addressed,
endpoint di sync per il confronto degli hash tra pari, e due task in background
(sync periodico e verifica di integrità) se sono configurati dei peer.
"""
import asyncio
import time

import httpx
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

from . import config, crypto, db, storage

app = FastAPI(title=f"R3-infinito node ({config.NODE_ID})")
_started_at = time.time()
_last_integrity_check = 0.0


def _check_auth(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization Bearer token mancante")
    if authorization.removeprefix("Bearer ").strip() != config.API_TOKEN:
        raise HTTPException(status_code=401, detail="Token non valido")


def _auth_headers():
    return {"Authorization": f"Bearer {config.API_TOKEN}"}


# ---------------------------------------------------------------- integrità

def run_integrity_check():
    """Ricalcola l'hash di ogni documento su disco e lo confronta col DB.
    In caso di corruzione o file mancante, tenta il ripristino dal primo peer sano."""
    for doc in db.list_documents():
        doc_id = doc["id"]
        sano = storage.exists(doc_id) and storage.compute_hash(storage.read(doc_id)) == doc_id
        if sano:
            continue
        db.log_event("integrity_fail", config.NODE_ID, document_id=doc_id)
        _repair_from_peers(doc_id)


def _repair_from_peers(doc_id):
    for peer in config.PEERS:
        try:
            resp = httpx.get(f"{peer}/documents/{doc_id}", headers=_auth_headers(), timeout=30)
        except httpx.HTTPError:
            continue
        if resp.status_code == 200 and storage.compute_hash(resp.content) == doc_id:
            storage.save_with_id(doc_id, resp.content)
            db.log_event("auto_repair", config.NODE_ID, document_id=doc_id, detail=f"da {peer}")
            return True
    db.log_event("auto_repair_failed", config.NODE_ID, document_id=doc_id)
    return False


# --------------------------------------------------------------------- sync

def sync_with_peers():
    local_ids = set(db.list_ids())
    for peer in config.PEERS:
        try:
            resp = httpx.get(f"{peer}/sync/hashes", headers=_auth_headers(), timeout=30)
            resp.raise_for_status()
            peer_ids = set(resp.json()["hashes"])
        except httpx.HTTPError as exc:
            db.log_event("sync_peer_unreachable", config.NODE_ID, detail=f"{peer}: {exc}")
            continue

        for doc_id in peer_ids - local_ids:
            _pull_from_peer(peer, doc_id)
        for doc_id in local_ids - peer_ids:
            _push_to_peer(peer, doc_id)


def _pull_from_peer(peer, doc_id):
    try:
        resp = httpx.get(f"{peer}/documents/{doc_id}", headers=_auth_headers(), timeout=30)
        resp.raise_for_status()
        content = resp.content
        if storage.compute_hash(content) != doc_id:
            db.log_event("sync_pull_hash_mismatch", config.NODE_ID, document_id=doc_id, detail=peer)
            return
        storage.save_with_id(doc_id, content)
        db.upsert_document(doc_id, len(content), crypto.sign(doc_id.encode()), config.NODE_ID)
        db.log_event("sync_pull", config.NODE_ID, document_id=doc_id, detail=f"da {peer}")
    except httpx.HTTPError as exc:
        db.log_event("sync_pull_failed", config.NODE_ID, document_id=doc_id, detail=str(exc))


def _push_to_peer(peer, doc_id):
    try:
        content = storage.read(doc_id)
        resp = httpx.post(
            f"{peer}/sync/receive",
            headers=_auth_headers(),
            files={"file": (doc_id, content)},
            data={"id": doc_id},
            timeout=30,
        )
        resp.raise_for_status()
        db.log_event("sync_push", config.NODE_ID, document_id=doc_id, detail=f"verso {peer}")
    except httpx.HTTPError as exc:
        db.log_event("sync_push_failed", config.NODE_ID, document_id=doc_id, detail=str(exc))


async def _background_loop():
    global _last_integrity_check
    while True:
        await asyncio.sleep(config.SYNC_INTERVAL)
        try:
            await asyncio.to_thread(sync_with_peers)
        except Exception as exc:
            db.log_event("sync_error", config.NODE_ID, detail=str(exc))

        if time.time() - _last_integrity_check >= config.INTEGRITY_INTERVAL:
            _last_integrity_check = time.time()
            try:
                await asyncio.to_thread(run_integrity_check)
            except Exception as exc:
                db.log_event("integrity_error", config.NODE_ID, detail=str(exc))


@app.on_event("startup")
async def on_startup():
    db.init()
    if config.PEERS:
        asyncio.create_task(_background_loop())


# --------------------------------------------------------------------- API

@app.get("/health")
async def health():
    return {"status": "ok", "node_id": config.NODE_ID}


@app.get("/status")
async def status(authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    return {
        "node_id": config.NODE_ID,
        "verify_key": crypto.verify_key_hex(),
        "num_documents": len(db.list_ids()),
        "peers": config.PEERS,
        "started_at": _started_at,
        "sync_interval": config.SYNC_INTERVAL,
        "integrity_interval": config.INTEGRITY_INTERVAL,
    }


@app.post("/documents")
async def upload_document(authorization: str | None = Header(default=None), file: UploadFile = File(...)):
    _check_auth(authorization)
    content = await file.read()
    doc_id = storage.save(content)
    signature = crypto.sign(doc_id.encode())
    db.upsert_document(doc_id, len(content), signature, config.NODE_ID)
    db.log_event("upload", config.NODE_ID, document_id=doc_id, detail=file.filename)
    return {"id": doc_id, "signature": signature, "size": len(content)}


@app.get("/documents/{doc_id}")
async def download_document(doc_id: str, authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    if not storage.exists(doc_id):
        raise HTTPException(status_code=404, detail="Documento non trovato")
    return Response(content=storage.read(doc_id), media_type="application/octet-stream")


@app.get("/documents/{doc_id}/info")
async def document_info(doc_id: str, authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    return doc


@app.get("/sync/hashes")
async def sync_hashes(authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    return {"node_id": config.NODE_ID, "hashes": db.list_ids()}


@app.post("/sync/receive")
async def sync_receive(
    authorization: str | None = Header(default=None),
    id: str = Form(...),
    file: UploadFile = File(...),
):
    _check_auth(authorization)
    content = await file.read()
    if storage.compute_hash(content) != id:
        raise HTTPException(status_code=400, detail="Hash del contenuto non corrisponde all'id dichiarato")
    storage.save_with_id(id, content)
    signature = crypto.sign(id.encode())
    db.upsert_document(id, len(content), signature, config.NODE_ID)
    db.log_event("sync_receive", config.NODE_ID, document_id=id)
    return {"id": id, "status": "received"}
