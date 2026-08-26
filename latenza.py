#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Latenza — da quanto una lettura è vera mentre non cambia niente.

Ogni strumento di questo repository misura uno stato: il provider risponde,
l'hash combacia, quante voci in memoria. Nessuno misura l'intervallo fra una
lettura vera e la prima cosa che cambia per causa sua.

È lì che è successo tutto. Il Core è stato spento dal 31/07 al 22/08 e
`output/health_log.jsonl` lo ha scritto correttamente ogni singolo giorno: il
rilevamento non ha mai fallito. Ha fallito la conseguenza, arrivata al giorno
23. Fleming aveva pubblicato l'alone nel 1929 e i topi sono del 1940: anche lì
il problema non era vedere, era che nessuna lettura obbligava a niente.

Questo strumento non aggiunge un occhio. Cerca le letture che si ripetono
identiche, perché una lettura che non cambia da N rilevazioni è una lettura su
cui nessuno sta agendo.

Limite dichiarato (P6 applicato a sé stesso): rileva che *la lettura* non è
cambiata, non che *nessuno abbia agito*. Una correzione che non muove il
sensore — come togliere lo Stub dalle cascate il 23/08, che lascia i provider
comunque a zero — qui resta invisibile. Chi legge deve saperlo.

    python latenza.py
    python latenza.py --soglia 5
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

RADICE = os.path.dirname(os.path.abspath(__file__))
HEALTH = os.path.join(RADICE, "output", "health_log.jsonl")
CONTATTI = os.path.join(RADICE, "output", "contatti.jsonl")

SOGLIA_DEFAULT = 3


def _giorni(da_iso, a_iso=None):
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    a = datetime.strptime(a_iso, fmt) if a_iso else datetime.now(timezone.utc).replace(tzinfo=None)
    return (a - datetime.strptime(da_iso, fmt)).days


def letture_health():
    """Riduce ogni check alla sua lettura essenziale: quali provider reali rispondono."""
    if not os.path.exists(HEALTH):
        return []
    letture = []
    for riga in open(HEALTH, encoding="utf-8"):
        riga = riga.strip()
        if not riga:
            continue
        d = json.loads(riga)
        reali = sorted(k for k, v in d.get("providers", {}).items() if k != "stub" and v.get("disponibile"))
        letture.append((d["data_iso"], tuple(reali)))
    return letture


def serie_immobili(letture, soglia):
    """Tratti massimali in cui la lettura non è mai cambiata."""
    serie, corrente = [], []
    for data, lettura in letture:
        if corrente and corrente[0][1] != lettura:
            serie.append(corrente)
            corrente = []
        corrente.append((data, lettura))
    if corrente:
        serie.append(corrente)
    return [s for s in serie if len(s) >= soglia]


def rapporto(soglia=SOGLIA_DEFAULT):
    righe = []
    letture = letture_health()

    for s in serie_immobili(letture, soglia):
        prima, ultima = s[0][0], s[-1][0]
        lettura = s[0][1]
        descrizione = ", ".join(lettura) if lettura else "nessun provider reale"
        righe.append({
            "fonte": "output/health_log.jsonl",
            "lettura": descrizione,
            "dal": prima[:10],
            "al": ultima[:10],
            "rilevazioni": len(s),
            "giorni": _giorni(prima, ultima),
            "ancora_in_corso": bool(letture) and s[-1][0] == letture[-1][0],
        })

    if os.path.exists(CONTATTI) and os.path.getsize(CONTATTI) == 0 and letture:
        righe.append({
            "fonte": "output/contatti.jsonl",
            "lettura": "zero contatti reali (ramo b di H2)",
            "dal": letture[0][0][:10],
            "al": letture[-1][0][:10],
            "rilevazioni": len(letture),
            "giorni": _giorni(letture[0][0], letture[-1][0]),
            "ancora_in_corso": True,
        })

    return righe


def _cli(argv=None):
    parser = argparse.ArgumentParser(description="Latenza — letture vere che non producono conseguenze.")
    parser.add_argument("--soglia", type=int, default=SOGLIA_DEFAULT,
                        help=f"rilevazioni identiche consecutive oltre cui segnalare (default {SOGLIA_DEFAULT})")
    args = parser.parse_args(argv)

    righe = rapporto(args.soglia)
    print("=== Latenza R³∞ ===")
    print("Non «cosa è vero», ma «da quanto è vero mentre non cambia niente».\n")
    if not righe:
        print(f"Nessuna lettura immobile oltre {args.soglia} rilevazioni.")
        return 0

    for r in righe:
        stato = "ANCORA IN CORSO" if r["ancora_in_corso"] else "chiusa"
        print(f"[{stato}] {r['fonte']}")
        print(f"   Lettura immobile: {r['lettura']}")
        g = r["giorni"]
        print(f"   Dal {r['dal']} al {r['al']} — {r['rilevazioni']} rilevazioni, "
              f"{g} {'giorno' if g == 1 else 'giorni'}")
        print()

    aperte = [r for r in righe if r["ancora_in_corso"]]
    print(f"{len(righe)} letture immobili, di cui {len(aperte)} ancora in corso.")
    print("Una lettura che non cambia non è stabilità: è una misura su cui nessuno sta agendo.")
    print("Limite: rileva l'immobilità del sensore, non l'assenza di azione.")
    return 1 if aperte else 0


if __name__ == "__main__":
    try:
        sys.exit(_cli())
    except BrokenPipeError:
        # Uscita incanalata in `head` o simili: chiudere in silenzio, non con un traceback.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
