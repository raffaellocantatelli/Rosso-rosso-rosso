#!/usr/bin/env python3
"""H4 — "Un contraddittorio interno riesce ancora a dire di no".

L'ipotesi nata il 25/08/2026, quando il vincolo è diventato: nessun terzo,
solo l'autore e la macchina che esegue.

Un verificatore che per un mese non trova mai niente non sta verificando:
sta timbrando. È la stessa forma dell'eco che il progetto conosce già —
il sistema che si rilegge e si trova pertinente — e va sorvegliata qui,
dove sarebbe più difficile accorgersene.

Falsificata se, negli ultimi 30 giorni, ci sono almeno 10 verifiche e
nessuna ha prodotto una caduta o un declassamento.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFICHE = os.path.join(RADICE, "output", "verifiche.jsonl")

FINESTRA_GIORNI = 30
MINIMO_VERIFICHE = 10
#: Un no del verificatore: o l'ipotesi e' caduta, o e' stata declassata.
ESITI_NEGATIVI = {"caduta"}


def carica_finestra():
    if not os.path.exists(VERIFICHE):
        return None
    limite = datetime.now(timezone.utc) - timedelta(days=FINESTRA_GIORNI)
    dentro = []
    with open(VERIFICHE, "r", encoding="utf-8") as f:
        for riga in f:
            riga = riga.strip()
            if not riga:
                continue
            try:
                voce = json.loads(riga)
                quando = datetime.fromisoformat(voce["data_iso"])
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
            if quando.tzinfo is None:
                quando = quando.replace(tzinfo=timezone.utc)
            if quando >= limite:
                dentro.append(voce)
    return dentro


def main():
    dentro = carica_finestra()
    if dentro is None:
        print("output/verifiche.jsonl non esiste ancora: verifica non conclusa",
              file=sys.stderr)
        return 2

    negativi = [
        v for v in dentro
        if v.get("esito") in ESITI_NEGATIVI or v.get("declassamento")
    ]
    print(f"verifiche negli ultimi {FINESTRA_GIORNI} giorni: {len(dentro)}")
    print(f"di cui negative (caduta o declassamento): {len(negativi)}")

    if len(dentro) >= MINIMO_VERIFICHE and not negativi:
        print(f"\nH4 CADUTA: {len(dentro)} verifiche e nessun no. "
              "Il contraddittorio è diventato un timbro.")
        return 0

    if len(dentro) < MINIMO_VERIFICHE:
        print(f"\nH4 REGGE per ora — campione ancora sotto {MINIMO_VERIFICHE} "
              "verifiche: il verdetto vero arriva più avanti.")
        return 1

    print("\nH4 REGGE: il contraddittorio ha ancora prodotto dei no.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
