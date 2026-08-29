#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Punto di ingresso.  python -m osservatorio [--porta N] [--resoconto]

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import argparse
import json
import sys

from .fotogramma import scatta, stampa
from .raccolta import Collettore
from .server import avvia, resoconto


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="osservatorio",
                                 description="Quadro OSINT locale, con la provenienza in chiaro.")
    ap.add_argument("--porta", type=int, default=8787)
    ap.add_argument("--indirizzo", default="127.0.0.1",
                    help="127.0.0.1 di default: il quadro non esce dalla macchina")
    ap.add_argument("--resoconto", action="store_true",
                    help="una sola lettura di tutte le fonti, stampata su stdout")
    ap.add_argument("--fotogramma", action="store_true",
                    help="scatta un fotogramma: stato del mondo + ancore pubbliche "
                         "+ posizione, ridotti a una chiave")
    ap.add_argument("--lat", type=float, help="latitudine dell'osservatore, in gradi")
    ap.add_argument("--lon", type=float, help="longitudine dell'osservatore, in gradi")
    ap.add_argument("--json", action="store_true", help="stampa il fotogramma grezzo")
    a = ap.parse_args(argv)

    if a.fotogramma:
        f = scatta(lat=a.lat, lon=a.lon)
        print(json.dumps(f, ensure_ascii=False, indent=1) if a.json else stampa(f))
        return 0

    if a.resoconto:
        c = Collettore()
        c.giro()
        print(resoconto(c.istantanea()))
        return 0

    avvia(porta=a.porta, indirizzo=a.indirizzo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
