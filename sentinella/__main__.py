# -*- coding: utf-8 -*-
"""Avvio: `python -m sentinella` e si apre la mappa.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser

from . import server


def main(argv=None):
    p = argparse.ArgumentParser(prog="sentinella", description="Mappa dei fenomeni in corso, dal suolo al cielo.")
    p.add_argument("--porta", type=int, default=8800)
    p.add_argument("--bind", default="127.0.0.1", help="127.0.0.1 = solo questa macchina")
    p.add_argument("--niente-browser", action="store_true")
    p.add_argument("--controlla", action="store_true", help="interroga le sorgenti una volta e stampa l'esito")
    p.add_argument("--istantanea", metavar="FILE", help="scrive il quadro corrente in un file JSON e esce")
    a = p.parse_args(argv)

    if a.controlla or a.istantanea:
        quadro = server.quadro_completo()
        if a.istantanea:
            with open(a.istantanea, "w", encoding="utf-8") as f:
                json.dump(quadro, f, ensure_ascii=False)
            print(f"istantanea scritta: {a.istantanea}")
        larghezza = max(len(k) for k in quadro["sorgenti"])
        for nome, s in quadro["sorgenti"].items():
            stato = s["status"]
            conto = s["returned"] if s["returned"] is not None else "—"
            print(f"  {nome.ljust(larghezza)}  {stato.ljust(8)}  {str(conto).rjust(4)}"
                  + (f"   {s['error']}" if s.get("error") else ""))
        print(f"\n  segnalazioni: {len(quadro['segnalazioni'])}   sintesi: {quadro['sintesi'] or '— quadro incompleto'}")
        return 0 if quadro["quadro_completo"] else 2

    servitore = server.avvia(a.porta, a.bind)
    indirizzo = f"http://{'localhost' if a.bind == '127.0.0.1' else a.bind}:{a.porta}"
    print(f"Sentinella su {indirizzo}   (ctrl-c per fermare)")
    print("Non prevede niente: ordina cio' che USGS, NASA/JPL e NOAA hanno gia' pubblicato.")
    if not a.niente_browser:
        threading.Timer(0.8, lambda: webbrowser.open(indirizzo)).start()
    try:
        servitore.serve_forever()
    except KeyboardInterrupt:
        print("\nfermata.")
    finally:
        servitore.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
