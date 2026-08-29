#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server locale: serve il quadro e lo stato, e nient'altro.

Gira sulla macchina di chi lo lancia. Non espone nulla su internet, non
tiene stato fra un'esecuzione e l'altra oltre alla traccia append-only,
e quando il processo termina non resta niente in esecuzione.

  python -m osservatorio                 # http://127.0.0.1:8787
  python -m osservatorio --porta 9000
  python -m osservatorio --resoconto     # una lettura sola, su stdout

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .raccolta import Collettore, LIVE, VECCHIO, SENZA_CHIAVE, NON_IMPLEMENTATA, ERRORE

QUI = os.path.dirname(os.path.abspath(__file__))


def resoconto(ist: dict) -> str:
    """Il resoconto che nel reel scriveva un modello, qui lo scrive una
    funzione: stesse domande, ma ogni riga porta la fonte e l'eta', e le
    conclusioni restano vuote perche' nessuno le ha verificate."""
    r = []
    t = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ist["adesso"]))
    r.append("RESOCONTO OSSERVATORIO — %s" % t)
    r.append("Generato da codice, non da un modello. Nessuna riga qui sotto")
    r.append("e' un'interpretazione.")
    r.append("")

    vive = [f for f in ist["fonti"] if f["stato"] == LIVE and f["conteggio"] is not None]
    r.append("LETTURE VIVE  (%d)" % len(vive))
    for f in sorted(vive, key=lambda x: -(x["conteggio"] or 0)):
        r.append("  %-36s %8d   eta %5ss   %s"
                 % (f["nome"], f["conteggio"], f["eta_s"], f["copertura"]))
    if not vive:
        r.append("  nessuna")
    r.append("")

    tron = [f for f in ist["fonti"] if f.get("troncato")]
    r.append("LETTURE TRONCATE  (%d)   il valore vero e' >= a quello mostrato, ed e' ignoto" % len(tron))
    for f in tron:
        r.append("  %-36s %8d   %s" % (f["nome"], f["conteggio"], f["dettaglio"]))
    if not tron:
        r.append("  nessuna")
    r.append("")

    spente = [f for f in ist["fonti"]
              if f["stato"] in (SENZA_CHIAVE, NON_IMPLEMENTATA, ERRORE, VECCHIO)]
    r.append("LAYER SENZA DATO  (%d)   nessuno di questi vale zero" % len(spente))
    for f in spente:
        perche = f["chiave_env"] or (f["errore"] or "")[:60] or "—"
        r.append("  %-36s %-18s %s" % (f["nome"], f["stato"], perche))
    if not spente:
        r.append("  nessuno")
    r.append("")

    parziali = [f for f in ist["fonti"] if "SOLO" in f["copertura"].upper()]
    if parziali:
        r.append("COPERTURA PARZIALE   una fonte che vede meta' mondo non descrive il mondo")
        for f in parziali:
            r.append("  %-36s %s" % (f["nome"], f["copertura"]))
        r.append("")

    r.append("INTERPRETAZIONE")
    r.append("  vuota per costruzione. Questo programma conta e data; non")
    r.append("  correla, non deduce e non spiega. Una correlazione fra layer")
    r.append("  diversi richiede una verifica su fonte primaria, e va scritta")
    r.append("  a mano da chi l'ha fatta.  (CLAUDE.md, §1 e §4)")
    return "\n".join(r)


class Gestore(BaseHTTPRequestHandler):
    collettore: Collettore = None      # iniettato da avvia()

    def _invia(self, corpo: bytes, tipo: str, codice: int = 200) -> None:
        self.send_response(codice)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):                                  # noqa: N802 (API stdlib)
        percorso = self.path.split("?")[0]
        if percorso in ("/", "/index.html"):
            with open(os.path.join(QUI, "quadro.html"), "rb") as f:
                self._invia(f.read(), "text/html; charset=utf-8")
        elif percorso == "/stato.json":
            corpo = json.dumps(self.collettore.istantanea(), ensure_ascii=False).encode("utf-8")
            self._invia(corpo, "application/json; charset=utf-8")
        elif percorso == "/resoconto.txt":
            corpo = resoconto(self.collettore.istantanea()).encode("utf-8")
            self._invia(corpo, "text/plain; charset=utf-8")
        else:
            self._invia(b"non trovato", "text/plain; charset=utf-8", 404)

    def log_message(self, formato, *args):
        pass                                            # niente rumore sul terminale


def avvia(porta: int = 8787, indirizzo: str = "127.0.0.1") -> None:
    collettore = Collettore()
    collettore.avvia()
    Gestore.collettore = collettore
    srv = ThreadingHTTPServer((indirizzo, porta), Gestore)
    print("Osservatorio in ascolto su http://%s:%d" % (indirizzo, porta))
    print("Lo schermo si aggiorna ogni 2 secondi. I DATI no: ogni fonte ha")
    print("la sua cadenza reale, ed e' scritta accanto a ogni riquadro.")
    print("Ctrl-C per chiudere. Chiuso il processo, non resta nulla in esecuzione.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nchiusura...")
    finally:
        collettore.ferma()
        srv.server_close()
