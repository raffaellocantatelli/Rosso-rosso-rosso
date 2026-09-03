# -*- coding: utf-8 -*-
"""Il server locale di Sentinella. Solo libreria standard.

Gira sulla macchina di chi lo avvia. Non espone niente all'esterno se non
glielo si chiede (`--bind 0.0.0.0`), non registra chi apre la pagina, non
manda niente a nessuno: le uniche connessioni in uscita sono verso USGS,
NASA/JPL e NOAA, e sono le stesse che farebbe un browser aperto sui loro siti.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import fonti, riconoscitore

QUI = os.path.dirname(os.path.abspath(__file__))

RACCOLTA = {
    "sismi": fonti.sismi,
    "passaggi": fonti.passaggi,
    "bolidi": fonti.bolidi,
    "meteo_spaziale": fonti.meteo_spaziale,
    "geomagnetismo": fonti.geomagnetismo,
}


def raccogli_tutto():
    """Le cinque sorgenti in parallelo: cinque attese sequenziali sarebbero un minuto."""
    esiti = {}
    fili = []

    def prendi(nome, funzione):
        try:
            esiti[nome] = funzione()
        except Exception as exc:  # una sorgente che esplode non deve spegnere le altre
            esiti[nome] = fonti.inviluppo(nome, status=fonti.ERRORE,
                                          error=f"errore interno leggendo {nome}: {exc.__class__.__name__}")

    for nome, funzione in RACCOLTA.items():
        f = threading.Thread(target=prendi, args=(nome, funzione), daemon=True)
        f.start()
        fili.append(f)
    for f in fili:
        f.join(timeout=45)
    for nome in RACCOLTA:
        esiti.setdefault(nome, fonti.inviluppo(nome, status=fonti.ERRORE, error="tempo scaduto"))
    return esiti


def quadro_completo():
    inviluppi = raccogli_tutto()
    dati = riconoscitore.quadro(inviluppi)
    dati["sorgenti"] = {k: {c: v[c] for c in ("source", "status", "total", "returned", "cap",
                                              "truncated", "error", "updated")
                            if c in v} for k, v in inviluppi.items()}
    dati["strati"] = {
        "sismi": [s for s in (inviluppi["sismi"].get("items") or []) if s.get("lat") is not None],
        "bolidi": inviluppi["bolidi"].get("items") or [],
        "kp": inviluppi["geomagnetismo"].get("items") or [],
    }
    return dati


class Manico(BaseHTTPRequestHandler):
    server_version = "Sentinella"

    def _manda(self, corpo, tipo="application/json; charset=utf-8", codice=200):
        if isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        self.send_response(codice)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _file(self, nome, tipo):
        percorso = os.path.join(QUI, nome)
        if not os.path.exists(percorso):
            return self._manda(json.dumps({"errore": f"manca {nome}"}), codice=404)
        with open(percorso, "rb") as f:
            self._manda(f.read(), tipo)

    def do_GET(self):
        rotta = self.path.split("?")[0].rstrip("/") or "/"
        try:
            if rotta in ("/", "/index.html"):
                return self._file("mappa.html", "text/html; charset=utf-8")
            if rotta == "/mondo.json":
                return self._file("mondo.json", "application/json; charset=utf-8")
            if rotta == "/api/salute":
                return self._manda(json.dumps({
                    "ok": True, "servizio": "sentinella", "versione": "1.0",
                    "sorgenti": list(RACCOLTA), "chiavi_richieste": [],
                }))
            if rotta == "/api/quadro":
                return self._manda(json.dumps(quadro_completo(), ensure_ascii=False))
            nome = rotta[len("/api/"):] if rotta.startswith("/api/") else None
            if nome in RACCOLTA:
                return self._manda(json.dumps(RACCOLTA[nome](), ensure_ascii=False))
            self._manda(json.dumps({"errore": "rotta sconosciuta", "rotte": [
                "/", "/api/quadro", "/api/salute", *[f"/api/{n}" for n in RACCOLTA]]}), codice=404)
        except BrokenPipeError:
            pass
        except Exception as exc:
            self._manda(json.dumps({"errore": exc.__class__.__name__, "dettaglio": str(exc)}), codice=500)

    def log_message(self, formato, *args):  # niente log di accesso: non serve saperlo
        pass


def avvia(porta=8800, bind="127.0.0.1"):
    servitore = ThreadingHTTPServer((bind, porta), Manico)
    return servitore
