#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Registro Osservazioni — la piastra che non si butta.

Nel 1928 Fleming non aveva un criterio di falsificazione. Aveva una piastra
contaminata da una muffa e l'occhio per accorgersi dell'alone. Il criterio
arrivò dodici anni dopo, a Oxford: otto topi, quattro trattati e quattro no.

Il Registro Ipotesi applica P6 — niente si conferma senza dichiarare come
potrebbe essere smentito. Giusto per un'ipotesi. Sbagliato per un fenomeno:
pretendere il criterio prima di aver visto la cosa significa buttare la
piastra perché non era prevista. `aggiungi()` avrebbe rifiutato Fleming.

Qui si deposita l'anomalia com'è, datata, prima di sapere cosa significhi.
Un'osservazione non si conferma e non si falsifica: si registra, e resta. Se
poi diventa un'ipotesi, quella dichiara il suo criterio e cita l'osservazione
da cui è nata — e i topi restano da fare.

Il file è append-only: le righe si aggiungono, mai si riscrivono. È la
protezione contro l'errore ricorrente di CLAUDE.md §4 — un'osservazione che
si può ritoccare dopo smette di essere una prova e diventa un ricordo, e il
ricordo è precisamente ciò che il sistema corrompe rileggendo sé stesso.

    python registro_osservazioni.py
    python registro_osservazioni.py --annota "cosa è successo" --strano "perché è strano"
    python registro_osservazioni.py --collega OSS-0001 H4
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

PERCORSO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registro_osservazioni.jsonl")

OSSERVAZIONE = "osservazione"
COLLEGAMENTO = "collegamento"


def _adesso():
    return datetime.now(timezone.utc).isoformat()


def _righe():
    if not os.path.exists(PERCORSO):
        return []
    righe = []
    with open(PERCORSO, "r", encoding="utf-8") as f:
        for numero, riga in enumerate(f, 1):
            riga = riga.strip()
            if not riga:
                continue
            try:
                righe.append(json.loads(riga))
            except json.JSONDecodeError as e:
                raise ValueError(f"{PERCORSO}: riga {numero} illeggibile: {e}") from e
    return righe


def _accoda(record):
    """L'unica scrittura permessa. Non esiste una funzione che riscriva o cancelli."""
    with open(PERCORSO, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _prossimo_id(righe):
    numeri = [
        int(r["id"].split("-")[1])
        for r in righe
        if r.get("tipo") == OSSERVAZIONE and r.get("id", "").startswith("OSS-")
    ]
    return f"OSS-{max(numeri, default=0) + 1:04d}"


def annota(cosa, perche_strano, contesto=None):
    """Deposita un'anomalia. Nessun criterio richiesto: non è ancora una tesi.

    `perche_strano` è obbligatorio: è la mente preparata. L'alone di Fleming
    contava perché lui sapeva dire cosa ci fosse di anomalo. Senza quella
    riga, fra un anno, la riga non si distingue dal rumore.
    """
    if not cosa or not cosa.strip():
        raise ValueError("Serve dire cosa è successo.")
    if not perche_strano or not perche_strano.strip():
        raise ValueError(
            "Serve dire perché è strano. Un'anomalia che non sai dire in cosa "
            "devia da ciò che ti aspettavi, fra un anno è indistinguibile dal rumore."
        )
    righe = _righe()
    record = {
        "tipo": OSSERVAZIONE,
        "id": _prossimo_id(righe),
        "data": _adesso(),
        "cosa": cosa.strip(),
        "perche_strano": perche_strano.strip(),
        "contesto": (contesto or "").strip() or None,
    }
    _accoda(record)
    return record


def collega(id_osservazione, id_ipotesi):
    """Lega un'osservazione all'ipotesi che ne è nata.

    L'ipotesi deve esistere nel Registro Ipotesi e dichiarare un criterio: qui
    passa il confine. L'osservazione è libera, la tesi che ne ricavi no. È il
    passaggio dalla piastra ai topi.
    """
    import registro_ipotesi

    if not any(
        r.get("tipo") == OSSERVAZIONE and r.get("id") == id_osservazione for r in _righe()
    ):
        raise KeyError(f"Osservazione {id_osservazione} non trovata")

    for h in registro_ipotesi.stato_corrente():
        if h["id"] == id_ipotesi:
            if not registro_ipotesi.criterio_definito(h.get("criterio_falsificazione", "")):
                raise ValueError(
                    f"{id_ipotesi} non dichiara ancora come potrebbe essere falsificata. "
                    f"L'osservazione può restare senza criterio; l'ipotesi che ne ricavi no."
                )
            break
    else:
        raise KeyError(f"Ipotesi {id_ipotesi} non trovata nel Registro Ipotesi")

    record = {
        "tipo": COLLEGAMENTO,
        "osservazione": id_osservazione,
        "ipotesi": id_ipotesi,
        "data": _adesso(),
    }
    _accoda(record)
    return record


def stato_corrente():
    """Ricostruisce le osservazioni ripiegando gli eventi. Niente viene riscritto."""
    osservazioni = {}
    collegamenti = []
    for r in _righe():
        if r.get("tipo") == OSSERVAZIONE:
            osservazioni[r["id"]] = dict(r, ipotesi=[])
        elif r.get("tipo") == COLLEGAMENTO:
            collegamenti.append(r)
    for c in collegamenti:
        voce = osservazioni.get(c["osservazione"])
        if voce is not None and c["ipotesi"] not in voce["ipotesi"]:
            voce["ipotesi"].append(c["ipotesi"])
    return list(osservazioni.values())


def stampa_stato():
    osservazioni = stato_corrente()
    print("=== Registro Osservazioni R³∞ ===")
    print("La piastra si deposita prima di sapere cosa significa.")
    print("Un'osservazione non si conferma e non si falsifica: resta.\n")
    if not osservazioni:
        print("Nessuna osservazione depositata.")
        print("Quando vedi qualcosa che non torna, annotalo prima di interpretarlo:")
        print('  python registro_osservazioni.py --annota "..." --strano "..."')
        return
    for o in osservazioni:
        print(f"[{o['id']}] {o['data'][:10]}")
        print(f"   {o['cosa']}")
        print(f"   Perché è strano: {o['perche_strano']}")
        if o.get("contesto"):
            print(f"   Contesto: {o['contesto']}")
        if o["ipotesi"]:
            print(f"   Ipotesi derivate: {', '.join(o['ipotesi'])}")
        else:
            print("   Nessuna ipotesi derivata: è ancora solo una piastra.")
        print()


def _cli(argv=None):
    parser = argparse.ArgumentParser(description="Registro Osservazioni R³∞ — anomalie prima delle tesi.")
    parser.add_argument("--annota", metavar="COSA", help="cosa è successo")
    parser.add_argument("--strano", metavar="PERCHE", help="perché devia da ciò che ti aspettavi")
    parser.add_argument("--contesto", metavar="DOVE", help="dove, quando, in quale sessione o file")
    parser.add_argument("--collega", nargs=2, metavar=("OSS", "IPOTESI"),
                        help="lega un'osservazione all'ipotesi che ne è nata")
    args = parser.parse_args(argv)

    try:
        if args.annota or args.strano:
            record = annota(args.annota, args.strano, args.contesto)
            print(f"Depositata {record['id']}.\n")
        if args.collega:
            collega(*args.collega)
            print(f"{args.collega[0]} → {args.collega[1]}.\n")
    except (ValueError, KeyError) as e:
        print(f"Rifiutato: {e.args[0] if e.args else e}", file=sys.stderr)
        return 1
    stampa_stato()
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
