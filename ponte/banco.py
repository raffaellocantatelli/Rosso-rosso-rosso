#!/usr/bin/env python3
"""Un NAS finto, in memoria, per provare il ponte senza NAS.

Origine protetta: Claudio Terzi [CT-LGAI-001].

ATTENZIONE, ed e' il motivo per cui questo file porta un nome e non e'
nascosto dentro i test: **passare qui non dimostra niente sul NAS di
Claudio.** Dimostra che il client parla WebDAV. E' esattamente la trappola di
CLAUDE.md §4 — il sistema che interroga se stesso e registra l'eco come
risposta — quindi ogni comando che usa questo banco lo stampa a voce alta.

Cosa prova davvero: PROPFIND, MKCOL, PUT, GET, DELETE, l'autenticazione
Basic, il rifiuto dei percorsi fuori radice, la codifica dei nomi con spazi.
Cosa non prova: che il NAS esista, che la porta sia aperta, che l'account
abbia i permessi, che il certificato sia valido.
"""

from __future__ import annotations

import base64
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def crea_banco(utente="r3", password="prova", radice="/R3"):
    """Avvia il NAS finto su una porta libera. Ritorna (url, archivio, stop)."""
    archivio: dict[str, bytes | None] = {radice: None}  # None = cartella
    atteso = "Basic " + base64.b64encode(f"{utente}:{password}".encode()).decode()

    class Gestore(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        # -- utilita' ---------------------------------------------------
        def _percorso(self):
            return "/" + urllib.parse.unquote(
                urllib.parse.urlsplit(self.path).path
            ).strip("/")

        def _autorizzato(self):
            if self.headers.get("Authorization") == atteso:
                return True
            self._rispondi(401, intestazioni={"WWW-Authenticate": 'Basic realm="finto"'})
            return False

        def _corpo(self):
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else b""

        def _rispondi(self, stato, corpo=b"", intestazioni=None):
            self.send_response(stato)
            for k, v in (intestazioni or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            if corpo:
                self.wfile.write(corpo)

        # -- metodi WebDAV ----------------------------------------------
        def do_OPTIONS(self):
            self._rispondi(200, intestazioni={
                "DAV": "1,2",
                "Allow": "OPTIONS,GET,PUT,DELETE,PROPFIND,MKCOL",
            })

        def do_PROPFIND(self):
            if not self._autorizzato():
                return
            self._corpo()
            p = self._percorso()
            if p not in archivio:
                return self._rispondi(404)
            profondita = self.headers.get("Depth", "1")
            voci = [p]
            if profondita == "1" and archivio[p] is None:
                voci += [q for q in archivio
                         if q != p and q.startswith(p.rstrip("/") + "/")
                         and "/" not in q[len(p.rstrip("/")) + 1:]]
            pezzi = ['<?xml version="1.0" encoding="utf-8"?><d:multistatus xmlns:d="DAV:">']
            for q in voci:
                cartella = archivio[q] is None
                tipo = "<d:collection/>" if cartella else ""
                lunghezza = "" if cartella else f"<d:getcontentlength>{len(archivio[q])}</d:getcontentlength>"
                pezzi.append(
                    f"<d:response><d:href>{urllib.parse.quote(q)}</d:href><d:propstat>"
                    f"<d:prop><d:resourcetype>{tipo}</d:resourcetype>{lunghezza}</d:prop>"
                    "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"
                )
            pezzi.append("</d:multistatus>")
            self._rispondi(207, "".join(pezzi).encode("utf-8"),
                           {"Content-Type": "application/xml; charset=utf-8"})

        def do_MKCOL(self):
            if not self._autorizzato():
                return
            p = self._percorso()
            if p in archivio:
                return self._rispondi(405)
            padre = p.rsplit("/", 1)[0] or "/"
            if padre not in archivio:
                return self._rispondi(409)
            archivio[p] = None
            self._rispondi(201)

        def do_PUT(self):
            if not self._autorizzato():
                return
            dati = self._corpo()
            p = self._percorso()
            padre = p.rsplit("/", 1)[0] or "/"
            if padre not in archivio or archivio[padre] is not None:
                return self._rispondi(409)
            nuovo = p not in archivio
            archivio[p] = dati
            self._rispondi(201 if nuovo else 204)

        def do_GET(self):
            if not self._autorizzato():
                return
            p = self._percorso()
            if p not in archivio or archivio[p] is None:
                return self._rispondi(404)
            self._rispondi(200, archivio[p], {"Content-Type": "application/octet-stream"})

        def do_DELETE(self):
            if not self._autorizzato():
                return
            p = self._percorso()
            if p not in archivio:
                return self._rispondi(404)
            for q in [q for q in archivio if q == p or q.startswith(p + "/")]:
                del archivio[q]
            self._rispondi(204)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Gestore)
    filo = threading.Thread(target=server.serve_forever, daemon=True)
    filo.start()

    def stop():
        server.shutdown()
        server.server_close()
        filo.join(timeout=5)

    return f"http://127.0.0.1:{server.server_address[1]}", archivio, stop
