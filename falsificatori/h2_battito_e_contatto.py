#!/usr/bin/env python3
"""H2 — "Il disegno darà ragione a entrambi entro 6 mesi (battito + contatto)".

Il criterio è di Claudio, parola per parola, e non lo riscrivo io:
falsificata se (a) output/ non contiene daily regolari — sistema morto —
oppure (b) output/contatti.jsonl ha zero voci valide — sistema vivo che non
tocca il mondo.

Questo script non giudica se il criterio sia quello giusto. Esegue quello
dichiarato. Cambiarlo è una decisione dell'autore, non del verificatore.
"""
import json
import os
import re
import sys
from datetime import date, timedelta

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(RADICE, "output")
CONTATTI = os.path.join(OUTPUT, "contatti.jsonl")

sys.path.insert(0, RADICE)

from sdq1.contatti import vale_per_h2  # noqa: E402

#: Quanti giorni possono passare senza un daily prima di chiamarlo "fermo".
GIORNI_BATTITO = 3

NOME_DAILY = re.compile(r"^daily_(\d{4})-(\d{2})-(\d{2})\.txt$")


def ultimo_daily():
    if not os.path.isdir(OUTPUT):
        return None
    date_trovate = []
    for nome in os.listdir(OUTPUT):
        m = NOME_DAILY.match(nome)
        if m:
            date_trovate.append(date(int(m[1]), int(m[2]), int(m[3])))
    return max(date_trovate) if date_trovate else None


def conta_contatti():
    """(valide, escluse): le righe che valgono per H2 e quelle che non valgono.

    Vale solo un tipo indipendente, dall'elenco di sdq1/contatti.py. Fino al
    29/10/2026 qui contava ogni riga con un `tipo` non vuoto: una
    pubblicazione dell'autore, che la CLI nello stesso momento dichiarava
    «NON vale per H2», bastava a portare H2 a RETTA. Trasmettere non è
    essere raggiunti.
    """
    valide = escluse = 0
    if not os.path.exists(CONTATTI):
        return valide, escluse
    with open(CONTATTI, "r", encoding="utf-8") as f:
        for riga in f:
            riga = riga.strip()
            if not riga:
                continue
            try:
                voce = json.loads(riga)
            except json.JSONDecodeError:
                continue
            if vale_per_h2(voce):
                valide += 1
            else:
                escluse += 1
    return valide, escluse


def main():
    ultimo = ultimo_daily()
    n_contatti, n_esclusi = conta_contatti()
    oggi = date.today()

    if ultimo is None:
        print("(a) BATTITO: nessun daily in output/ — sistema morto")
        battito = False
    else:
        eta = (oggi - ultimo).days
        battito = eta <= GIORNI_BATTITO
        stato = "regolare" if battito else f"fermo da {eta} giorni"
        print(f"(a) BATTITO: ultimo daily {ultimo.isoformat()} — {stato}")

    contatto = n_contatti > 0
    print(f"(b) CONTATTO: {n_contatti} voci valide in output/contatti.jsonl")
    if n_esclusi:
        print(f"    {n_esclusi} registrate che non valgono per H2: atti tuoi verso "
              f"l'esterno, o tipi non indipendenti (sdq1/contatti.py)")

    if not battito or not contatto:
        rami = []
        if not battito:
            rami.append("a")
        if not contatto:
            rami.append("b")
        print(f"\nH2 CADUTA sul ramo ({'), ('.join(rami)}).")
        return 0

    print("\nH2 REGGE: battito regolare e almeno un contatto registrato.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
