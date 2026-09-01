"""Script di sync manuale/periodico tra un nodo locale e i suoi peer, via HTTP.

Uso:
    R3_LOCAL_URL=http://localhost:8001 \\
    R3_PEERS=http://localhost:8002,http://localhost:8003 \\
    R3_API_TOKEN=changeme \\
    python r3/sync.py [--loop]

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import argparse
import hashlib
import os
import sys
import time

import httpx


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _get_hashes(base_url, token):
    resp = httpx.get(f"{base_url}/sync/hashes", headers=_headers(token), timeout=30)
    resp.raise_for_status()
    return set(resp.json()["hashes"])


def _pull(local_url, peer_url, doc_id, token):
    resp = httpx.get(f"{peer_url}/documents/{doc_id}", headers=_headers(token), timeout=30)
    resp.raise_for_status()
    content = resp.content
    if hashlib.sha256(content).hexdigest() != doc_id:
        print(f"  [SKIP] {doc_id[:12]}... hash non corrispondente da {peer_url}", file=sys.stderr)
        return False
    resp2 = httpx.post(
        f"{local_url}/sync/receive",
        headers=_headers(token),
        files={"file": (doc_id, content)},
        data={"id": doc_id},
        timeout=30,
    )
    resp2.raise_for_status()
    return True


def _push(local_url, peer_url, doc_id, token):
    resp = httpx.get(f"{local_url}/documents/{doc_id}", headers=_headers(token), timeout=30)
    resp.raise_for_status()
    content = resp.content
    resp2 = httpx.post(
        f"{peer_url}/sync/receive",
        headers=_headers(token),
        files={"file": (doc_id, content)},
        data={"id": doc_id},
        timeout=30,
    )
    resp2.raise_for_status()
    return True


def sync_once(local_url, peers, token):
    riepilogo = {"pull": [], "push": [], "errori": []}
    try:
        local_ids = _get_hashes(local_url, token)
    except httpx.HTTPError as exc:
        riepilogo["errori"].append(f"nodo locale {local_url}: {exc}")
        return riepilogo

    for peer in peers:
        try:
            peer_ids = _get_hashes(peer, token)
        except httpx.HTTPError as exc:
            riepilogo["errori"].append(f"peer {peer}: {exc}")
            continue

        for doc_id in peer_ids - local_ids:
            try:
                if _pull(local_url, peer, doc_id, token):
                    riepilogo["pull"].append(doc_id)
                    local_ids.add(doc_id)
            except httpx.HTTPError as exc:
                riepilogo["errori"].append(f"pull {doc_id} da {peer}: {exc}")

        for doc_id in local_ids - peer_ids:
            try:
                if _push(local_url, peer, doc_id, token):
                    riepilogo["push"].append(doc_id)
            except httpx.HTTPError as exc:
                riepilogo["errori"].append(f"push {doc_id} verso {peer}: {exc}")

    return riepilogo


def main():
    parser = argparse.ArgumentParser(description="Sync manuale/periodico tra nodi R3-infinito")
    parser.add_argument("--loop", action="store_true", help="Esegue in loop continuo invece che una sola volta")
    args = parser.parse_args()

    local_url = os.environ.get("R3_LOCAL_URL", "http://localhost:8001").rstrip("/")
    peers = [p.strip().rstrip("/") for p in os.environ.get("R3_PEERS", "").split(",") if p.strip()]
    token = os.environ.get("R3_API_TOKEN", "changeme")
    interval = int(os.environ.get("R3_SYNC_INTERVAL", "300"))

    if not peers:
        print("Nessun peer configurato in R3_PEERS: nulla da sincronizzare.", file=sys.stderr)
        sys.exit(1)

    while True:
        riepilogo = sync_once(local_url, peers, token)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(f"[{stamp}] pull={len(riepilogo['pull'])} push={len(riepilogo['push'])} errori={len(riepilogo['errori'])}")
        for e in riepilogo["errori"]:
            print(f"  ! {e}", file=sys.stderr)
        if not args.loop:
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
