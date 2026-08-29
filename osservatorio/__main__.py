#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Punto di ingresso.  python -m osservatorio [--porta N] [--resoconto]

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import argparse
import sys

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
    a = ap.parse_args(argv)

    if a.resoconto:
        c = Collettore()
        c.giro()
        print(resoconto(c.istantanea()))
        return 0

    avvia(porta=a.porta, indirizzo=a.indirizzo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
