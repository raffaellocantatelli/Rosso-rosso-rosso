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


def leggi_cartella(percorso, cascata, scrivi, soglia, limite) -> int:
    """Il modo a fotografie: meno spesa, foto migliori, e niente https."""
    from .cartella import percorri
    try:
        conti, registro = percorri(percorso, cascata=cascata, soglia=soglia,
                                   scrivi=scrivi, limite=limite)
    except NotADirectoryError as e:
        print(f"non è una cartella: {e}", file=sys.stderr)
        return 1
    except vis.VisioneNonDisponibile as e:
        print(f"L'OCCHIO È CHIUSO: {e}", file=sys.stderr)
        return 2
    print(f"\n  fotografie lette:  {conti['foto']}"
          f"   (saltate perché già lette: {conti['saltate']})")
    print(f"  oggetti letti:     {conti['letti']}")
    print(f"  nuovi nel registro:{conti['nuovi']:>4}")
    print(f"  già noti:          {conti['gia_noti']:>4}")
    print(f"  incerti, scartati: {conti['incerti']:>4}   <- questi li perdi finché "
          "non li confermi a mano")
    if conti["errori"]:
        print(f"  errori:            {conti['errori']:>4}")
    print(f"\n  inventario: {len(registro.voci)} oggetti in "
          f"{len(registro.per_luogo())} luoghi")
    print("  la mappa:   python -m occhio --mappa mappa.html")
    if conti["letti"]:
        print(f"\n  Il numero che decide tutto è letti/presenti, e questo NON è "
              "quello:\n  conta a mano gli oggetti in una di quelle foto e "
              "confronta.")
    return 0


def consegne(a) -> int:
    """Lo stato controfirmato di un alloggio: consegna, riconsegna, differenza."""
    from .consegna import Consegne, differenza, stampa_differenza
    c = Consegne()

    if a.verifica_consegne:
        v = c.verifica(a.codice)
        print(f"catena: {c.percorso}")
        print(f"  stati: {v['stati']}   controfirme: {v['controfirme']}")
        print(f"  integra: {'sì' if v['catena_integra'] else 'NO'}")
        for r in v["rotture"]:
            print(f"    ROTTURA {r}")
        if v["firme_non_valide"]:
            print(f"  FIRME NON VALIDE con questo codice: {v['firme_non_valide']}")
        if v["senza_controfirma"]:
            print(f"\n  {len(v['senza_controfirma'])} stati SENZA controfirma:")
            for x in v["senza_controfirma"]:
                print(f"    {x['momento']}  {x['tipo']}  {x['alloggio']}")
            print("\n  Una catena che una parte sola può rigenerare dimostra solo")
            print("  di essere coerente con sé stessa. È la controfirma dell'altra")
            print("  parte a renderla opponibile — non l'impronta.")
        return 0 if v["catena_integra"] else 1

    if a.controfirma:
        if not a.codice:
            print("serve --codice: la controfirma senza il codice del soggiorno "
                  "non prova niente", file=sys.stderr)
            return 1
        try:
            v = c.controfirma(a.controfirma, a.codice)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 1
        print(f"controfirmato {a.controfirma[:16]}… il {v['momento']}")
        return 0

    if a.differenza:
        prima = c.ultimo(a.differenza, "consegna")
        dopo = c.ultimo(a.differenza, "riconsegna")
        if not prima or not dopo:
            print(f"servono una consegna e una riconsegna per {a.differenza}: "
                  f"trovate {'consegna' if prima else '—'} / "
                  f"{'riconsegna' if dopo else '—'}", file=sys.stderr)
            return 1
        print(stampa_differenza(differenza(prima, dopo)))
        return 0

    alloggio = a.consegna or a.riconsegna
    tipo = "consegna" if a.consegna else "riconsegna"
    registro = inv.Inventario()
    if not registro.voci:
        print("l'inventario è vuoto: non c'è nessuno stato da consegnare.\n"
              "  python -m occhio --cartella ~/foto", file=sys.stderr)
        return 1
    s = c.deposita(alloggio, tipo, registro.voci, soggiorno=a.soggiorno)
    print(f"{tipo} di {alloggio}: {len(s['oggetti'])} oggetti")
    print(f"  momento:  {s['momento']}")
    print(f"  impronta: {s['impronta']}")
    print(f"\n  NON è ancora controfirmato. Falla controfirmare all'ospite:")
    print(f"    python -m occhio --controfirma {s['impronta']} --codice <codice>")
    print("  Finché non lo è, questo stato dimostra solo che tu sei coerente")
    print("  con te stesso — in una lite non basta.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m occhio",
        description="Inventario di oggetti reali attraverso la telecamera. "
                    "Origine protetta: Claudio Terzi [CT-LGAI-001].")
    ap.add_argument("--check", action="store_true", help="dice se un modello puo' guardare")
    ap.add_argument("--serve", action="store_true", help="apre l'interfaccia con la telecamera")
    ap.add_argument("--foto", metavar="FILE", help="legge un'immagine gia' scattata")
    ap.add_argument("--cartella", metavar="DIR",
                    help="legge una cartella di fotografie; le sottocartelle "
                         "dichiarano stanza/mobile/ripiano")
    ap.add_argument("--mappa", metavar="FILE.html", nargs="?", const="-",
                    help="dove sta cosa: a schermo, o in una pagina HTML se dai un file")
    ap.add_argument("--limite", type=int, help="quante fotografie al massimo (per provare)")
    g = ap.add_argument_group("affitto breve — lo stato controfirmato")
    g.add_argument("--consegna", metavar="ALLOGGIO",
                   help="deposita lo stato attuale come consegna all ospite")
    g.add_argument("--riconsegna", metavar="ALLOGGIO",
                   help="deposita lo stato attuale come riconsegna")
    g.add_argument("--controfirma", metavar="IMPRONTA",
                   help="l altra parte dichiara di aver visto lo stesso stato")
    g.add_argument("--codice", help="codice del soggiorno, noto a entrambe le parti")
    g.add_argument("--soggiorno", default="", help="riferimento della prenotazione")
    g.add_argument("--differenza", metavar="ALLOGGIO",
                   help="cosa manca fra l ultima consegna e l ultima riconsegna")
    g.add_argument("--verifica-consegne", action="store_true",
                   help="ricalcola la catena e dice cosa non e controfirmato")
    ap.add_argument("--inventario", action="store_true", help="stampa il registro")
    ap.add_argument("--esporta", metavar="FILE.csv", help="esporta il registro in CSV")
    ap.add_argument("--costo", action="store_true",
                    help="quanto costa una passata, ricalcolato dai listini dichiarati")
    ap.add_argument("--minuti", type=float, default=10.0, help="minuti di cammino per --costo")
    ap.add_argument("--ritmo", type=float, default=2.5, help="secondi fra un fotogramma e l altro")
    ap.add_argument("--modello", help="un solo modello per --costo (es. haiku-4.5)")
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

    if a.costo:
        from .costo import stampa
        stampa(a.minuti, a.ritmo, a.modello)
        return 0
    if a.check:
        return check()
    if a.inventario:
        return mostra_inventario(a.json)
    if a.esporta:
        Path(a.esporta).write_text(inv.Inventario().csv(), encoding="utf-8")
        print(f"scritto {a.esporta}")
        return 0
    if (a.consegna or a.riconsegna or a.controfirma or a.differenza
            or a.verifica_consegne):
        return consegne(a)
    if a.mappa:
        from .cartella import mappa_html, mappa_testo
        registro = inv.Inventario()
        if a.mappa == "-":
            print(mappa_testo(registro))
        else:
            Path(a.mappa).write_text(mappa_html(registro), encoding="utf-8")
            print(f"scritto {a.mappa} — {len(registro.voci)} oggetti in "
                  f"{len(registro.per_luogo())} luoghi")
        return 0
    if a.cartella:
        return leggi_cartella(a.cartella, cascata, not a.solo_lettura,
                              a.soglia, a.limite)
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
