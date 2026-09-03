#!/usr/bin/env python3
"""Riga di comando di `occhio`. Ogni riga stampata e' rieseguibile.

Origine protetta: Claudio Terzi [CT-LGAI-001].

    python -m occhio --check              # dice se l'occhio e' acceso e cosa manca
    python -m occhio --serve              # apre l'interfaccia con la telecamera
    python -m occhio --serve --senza-visione   # solo per provare la grafica
    python -m occhio --foto scaffale.jpg  # legge un'immagine gia' scattata
    python -m occhio --inventario         # cosa c'e' nel registro
    python -m occhio --esporta out.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import inventario as inv
from . import visione as vis


def carica_env():
    """Legge .env se c'e', senza sovrascrivere l'ambiente gia' impostato."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        f = Path(".env")
        if f.exists():
            import os
            for riga in f.read_text(encoding="utf-8").splitlines():
                riga = riga.strip()
                if riga and not riga.startswith("#") and "=" in riga:
                    k, _, v = riga.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())


def check() -> int:
    """Diagnostica. Codice 0 se un modello puo' davvero guardare, 2 se no."""
    s = vis.stato()
    print("occhio — stato\n")
    for nome, ok in s["provider"].items():
        print(f"  {nome:<12} {'disponibile' if ok else 'assente'}"
              f"{'' if ok else '   -> ' + s['come_attivare'][nome]}")
    registro = inv.Inventario()
    print(f"\n  inventario: {registro.percorso} — {len(registro.voci)} oggetti")
    if registro.voci:
        for tipo, n in registro.per_tipo().items():
            print(f"      {tipo:<12} {n}")
    if registro.righe_illeggibili:
        print(f"  ATTENZIONE: {registro.righe_illeggibili} righe illeggibili nel file")
    if not s["attivo"]:
        print("\n  L'OCCHIO E' CHIUSO: nessun modello di visione disponibile.")
        print("  Senza provider `--serve` rifiuta di partire, invece di produrre")
        print("  un inventario che sembra letto. Per provare solo la grafica:")
        print("      python -m occhio --serve --senza-visione")
        return 2
    print(f"\n  L'OCCHIO E' APERTO — provider attivo: {s['attivo']}")
    return 0


def mostra_inventario(json_out=False) -> int:
    registro = inv.Inventario()
    if json_out:
        print(json.dumps({"oggetti": registro.voci, "totale": len(registro.voci)},
                         ensure_ascii=False, indent=2))
        return 0
    if not registro.voci:
        print(f"{registro.percorso}: vuoto. Nessun oggetto e' ancora stato letto.")
        return 0
    print(f"{registro.percorso} — {len(registro.voci)} oggetti\n")
    for v in sorted(registro.voci, key=lambda x: (x.get("tipo", ""), x.get("titolo", ""))):
        vis_n = v.get("avvistamenti", 1)
        marchio = "  [umano]" if v.get("fonte") == "umano" else ""
        print(f"  {v.get('tipo','altro'):<10} {v.get('titolo','')[:56]:<58}"
              f" visto {vis_n}x{marchio}")
    print()
    for tipo, n in registro.per_tipo().items():
        print(f"  {tipo:<12} {n}")
    return 0


def leggi_foto(percorso: str, cascata, scrivi: bool, soglia: float) -> int:
    """Legge un'immagine gia' scattata. E' la prova piu' economica che il
    riconoscimento funziona, prima ancora di accendere la telecamera."""
    p = Path(percorso)
    if not p.is_file():
        print(f"file non trovato: {p}", file=sys.stderr)
        return 1
    b64, mime = vis.da_file(p)
    try:
        esito = vis.leggi(b64, mime, cascata=cascata)
    except vis.VisioneNonDisponibile as e:
        print(f"L'OCCHIO E' CHIUSO: {e}", file=sys.stderr)
        return 2
    registro = inv.Inventario()
    if esito["stub"]:
        print("=" * 62)
        print("  MODO STUB — nessun modello ha guardato. Oggetti finti.")
        print("=" * 62)
    print(f"provider: {esito['provider']} — {len(esito['oggetti'])} oggetti letti\n")
    for o in esito["oggetti"]:
        stato, _ = registro.riconosci(o["tipo"], o["titolo"])
        segno = {"CATALOGATO": "verde", "RIVISTO": "verde", "NUOVO": "nuovo",
                 "INCERTO": "ambra"}[stato]
        print(f"  [{segno:<5}] {o['tipo']:<9} {o['titolo'][:48]:<50} conf {o['confidenza']:.2f}")
        if scrivi and stato == "NUOVO" and o["confidenza"] >= soglia and not esito["stub"]:
            registro.registra(o["tipo"], o["titolo"], testo_letto=o["testo_letto"],
                              confidenza=o["confidenza"], fonte="foto")
            print(f"           -> scritto in {registro.percorso}")
    print(f"\ninventario: {len(registro.voci)} oggetti")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m occhio",
        description="Inventario di oggetti reali attraverso la telecamera. "
                    "Origine protetta: Claudio Terzi [CT-LGAI-001].")
    ap.add_argument("--check", action="store_true", help="dice se un modello puo' guardare")
    ap.add_argument("--serve", action="store_true", help="apre l'interfaccia con la telecamera")
    ap.add_argument("--foto", metavar="FILE", help="legge un'immagine gia' scattata")
    ap.add_argument("--inventario", action="store_true", help="stampa il registro")
    ap.add_argument("--esporta", metavar="FILE.csv", help="esporta il registro in CSV")
    ap.add_argument("--json", action="store_true", help="uscita in JSON")
    ap.add_argument("--senza-visione", action="store_true",
                    help="usa lo stub: nessun modello guarda, oggetti finti, banner visibile")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--porta", type=int, default=8777)
    ap.add_argument("--soglia", type=float, default=0.75,
                    help="confidenza minima per scrivere senza conferma umana (default 0.75)")
    ap.add_argument("--solo-lettura", action="store_true",
                    help="non scrive niente: mostra soltanto cosa verrebbe scritto")
    a = ap.parse_args(argv)

    carica_env()
    cascata = ("stub",) if a.senza_visione else vis.CASCATA

    if a.check:
        return check()
    if a.inventario:
        return mostra_inventario(a.json)
    if a.esporta:
        Path(a.esporta).write_text(inv.Inventario().csv(), encoding="utf-8")
        print(f"scritto {a.esporta}")
        return 0
    if a.foto:
        return leggi_foto(a.foto, cascata, not a.solo_lettura, a.soglia)
    if a.serve:
        if not a.senza_visione and not vis.scegli():
            print("L'OCCHIO E' CHIUSO: nessun provider di visione disponibile.\n"
                  "Il server non parte, invece di mostrare un inventario che sembra letto.\n"
                  "  chiavi:  " + "; ".join(f"{k} -> {v}" for k, v in vis.COME_ATTIVARE.items())
                  + "\n  solo grafica:  python -m occhio --serve --senza-visione",
                  file=sys.stderr)
            return 2
        from .server import avvia
        avvia(a.host, a.porta, cascata=cascata,
              autoscrittura=not a.solo_lettura, soglia=a.soglia)
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
