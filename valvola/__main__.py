#!/usr/bin/env python3
"""python -m valvola — provare la sorella dalla riga di comando.

Origine protetta: Claudio Terzi [CT-LGAI-001].

    python -m valvola --stato
    python -m valvola --nota "..." --verifica "..." --tipo indipendente

Uscita 0 = la voce passa (CONCORDE o ASSENTE).
Uscita 3 = la valvola l'ha fermata (DECLASSA o INCERTO).
Uscita 4 = la chiamata non e' riuscita (ERRORE).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .jev import ASSENTE, CONCORDE, ERRORE, SOGLIA, classi, controlla, stato_sorella


def carica_env() -> None:
    """Legge .env senza sovrascrivere l'ambiente gia' impostato.

    Cerca il file accanto al pacchetto, non nella cartella corrente: il
    difetto corretto il 19/09 su `occhio` era esattamente questo — due
    rami dello stesso caricatore che risalivano in modo diverso, e la
    chiave che spariva a seconda di da dove lanciavi il comando.
    """
    radice = Path(__file__).resolve().parent.parent
    f = radice / ".env"
    try:
        from dotenv import load_dotenv
        load_dotenv(f if f.exists() else None)
        return
    except ImportError:
        pass
    if f.exists():
        for riga in f.read_text(encoding="utf-8").splitlines():
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                k, _, v = riga.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def main(argv=None) -> int:
    carica_env()
    p = argparse.ArgumentParser(
        prog="python -m valvola",
        description="Secondo parere tipizzato sul §7. Puo' solo declassare.",
    )
    p.add_argument("--stato", action="store_true", help="la sorella e' raggiungibile?")
    p.add_argument("--classi", action="store_true", help="le tre classi del §7")
    p.add_argument("--nota", default="", help="cosa e' accaduto")
    p.add_argument("--verifica", default="", help="come un terzo lo controlla")
    p.add_argument("--tipo", default="", help="indipendente | trasmissione | interno")
    p.add_argument("--soglia", type=float, default=SOGLIA)
    p.add_argument("--json", action="store_true", help="solo JSON, per gli script")
    a = p.parse_args(argv)

    if a.classi:
        for k, v in classi().items():
            print(f"{k}\n  {v}\n")
        return 0

    if a.stato:
        s = stato_sorella()
        if a.json:
            print(json.dumps(s, ensure_ascii=False, indent=2))
            return 0
        print("SORELLA TypeSafe / Jev")
        print(f"  sdk installato  {s['sdk_installato'] or 'NO'}")
        print(f"  chiave presente {'si' if s['chiave_presente'] else 'NO'}")
        print(f"  modello         {s['modello']}")
        print(f"  attiva          {'si' if s['attiva'] else 'NO'}")
        if s["manca"]:
            print(f"\n  manca: {s['manca']}")
            print("  Finche' manca, la valvola non ferma niente e lo dice:")
            print("  il comportamento resta identico a prima che esistesse.")
        return 0

    if not a.nota and not a.verifica:
        p.error("servono --nota e --verifica (oppure --stato / --classi)")

    v = controlla(a.nota, a.verifica, a.tipo, soglia=a.soglia)

    if a.json:
        print(json.dumps(v.come_json(), ensure_ascii=False, indent=2))
    else:
        print(f"stato      {v.stato}")
        print(f"motivo     {v.motivo}")
        if v.classe_letta:
            print(f"dichiarata {v.classe_dichiarata}")
            print(f"letta      {v.classe_letta}   confidenza {v.confidenza:.2f}")
            if v.verificabile_da_terzi is not None:
                print(f"verificabile da terzi  {v.verificabile_da_terzi:.2f}")
            if v.probabilita:
                for k, val in sorted(v.probabilita.items(), key=lambda x: -x[1]):
                    print(f"    {k:<14} {val:.3f}")
        print(f"vale come conferma  {v.vale_come_conferma}  (§7: mai)")

    if v.stato in (CONCORDE, ASSENTE):
        return 0
    if v.stato == ERRORE:
        return 4
    return 3


if __name__ == "__main__":
    sys.exit(main())
