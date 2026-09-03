# -*- coding: utf-8 -*-
"""Congela l'applicazione in una pagina sola, con dentro un'istantanea reale.

Perche' esiste: una pagina pubblicata su claude.ai non puo' interrogare USGS,
NASA o NOAA — la CSP del visualizzatore blocca ogni `fetch` verso l'esterno, e
anche le tessere di una mappa a immagini. Non e' aggirabile, ed e' giusto che
non lo sia.

Quindi la pagina pubblicata non e' l'applicazione: e' l'applicazione con
l'orologio fermo. La differenza va **dichiarata dentro la pagina**, non
nascosta sperando che nessuno guardi la data, ed e' esattamente cio' che fa la
fascia in alto che questo script accende.

    python -m sentinella.costruisci_artefatto artefatti/sentinella/sentinella.html

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

QUI = os.path.dirname(os.path.abspath(__file__))


def _estrai(html):
    """Dalla pagina completa alla forma che l'Artifact accetta: niente <html>, <head>, <body>."""
    testa = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    corpo = re.search(r"<body>(.*?)</body>", html, re.S).group(1)
    # il visualizzatore mette da se' charset e viewport
    testa = re.sub(r'<meta[^>]*charset[^>]*>\s*', "", testa)
    testa = re.sub(r'<meta[^>]*viewport[^>]*>\s*', "", testa)
    return testa.strip(), corpo.strip()


def costruisci(destinazione, quadro=None):
    from . import server

    quadro = quadro if quadro is not None else server.quadro_completo()
    # la serie Kp non serve alla pagina: pesa e non si vede
    quadro.get("strati", {}).pop("kp", None)

    with open(os.path.join(QUI, "mappa.html"), encoding="utf-8") as f:
        testa, corpo = _estrai(f.read())
    with open(os.path.join(QUI, "mondo.json"), encoding="utf-8") as f:
        mondo = f.read()

    presa = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    innesto = (
        'var INNESTO = { modo: "istantanea", presa: ' + json.dumps(presa) + ",\n"
        "  quadro: " + json.dumps(quadro, ensure_ascii=False, separators=(",", ":")) + ",\n"
        "  mondo: " + mondo + " };"
    )
    corpo = corpo.replace('var INNESTO = { modo: "vivo" };', innesto)
    if "istantanea" not in corpo:
        raise SystemExit("l'innesto non e' stato sostituito: mappa.html e' cambiata?")

    os.makedirs(os.path.dirname(os.path.abspath(destinazione)), exist_ok=True)
    with open(destinazione, "w", encoding="utf-8") as f:
        f.write(testa + "\n\n" + corpo + "\n")

    quante = len(quadro.get("segnalazioni") or [])
    giu = [d["sorgente"] for d in (quadro.get("sorgenti_degradate") or [])]
    print(f"scritto {destinazione} — {os.path.getsize(destinazione)/1024:.0f} kB, "
          f"{quante} segnalazioni, presa alle {presa} UTC")
    if giu:
        print("  ATTENZIONE: sorgenti degradate nell'istantanea: " + ", ".join(giu))
    return destinazione


if __name__ == "__main__":
    costruisci(sys.argv[1] if len(sys.argv) > 1 else "sentinella_istantanea.html")
