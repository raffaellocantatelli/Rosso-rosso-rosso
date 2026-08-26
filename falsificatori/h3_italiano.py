#!/usr/bin/env python3
"""H3 — "La regola dell'italiano garantisce trasparenza".

Era CONFERMATA senza che nessuno avesse mai controllato niente. Questo
script è ciò che avrebbe dovuto esistere prima di scriverlo: legge tutti i
daily in output/ e misura la densità di parole funzionali italiane.

Non prova che la regola "garantisca trasparenza" — quella è un'altra
affermazione, e più grande. Prova solo la parte falsificabile: che gli
output siano effettivamente in italiano.
"""
import os
import re
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(RADICE, "output")

FUNZIONALI = {
    "di", "il", "la", "che", "non", "per", "con", "una", "uno", "del",
    "della", "sono", "come", "più", "anche", "questo", "essere", "se",
    "ma", "nel", "alla", "dei", "le", "un", "è", "si", "da", "in",
}

#: Sotto questa quota di parole funzionali un testo non è italiano corrente.
SOGLIA = 0.06
#: Testi più corti non danno un campione affidabile: non si giudicano.
MINIMO_PAROLE = 40

PAROLA = re.compile(r"[a-zàèéìòùA-ZÀÈÉÌÒÙ]+")


def quota_italiano(testo):
    parole = [p.lower() for p in PAROLA.findall(testo)]
    if len(parole) < MINIMO_PAROLE:
        return None, len(parole)
    funzionali = sum(1 for p in parole if p in FUNZIONALI)
    return funzionali / len(parole), len(parole)


def main():
    if not os.path.isdir(OUTPUT):
        print("output/ non esiste: verifica non conclusa", file=sys.stderr)
        return 2

    file_daily = sorted(n for n in os.listdir(OUTPUT) if n.startswith("daily_"))
    if not file_daily:
        print("nessun daily da controllare: verifica non conclusa", file=sys.stderr)
        return 2

    fuori_norma = []
    saltati = 0
    for nome in file_daily:
        with open(os.path.join(OUTPUT, nome), "r", encoding="utf-8") as f:
            quota, parole = quota_italiano(f.read())
        if quota is None:
            saltati += 1
            continue
        if quota < SOGLIA:
            fuori_norma.append((nome, quota, parole))

    controllati = len(file_daily) - saltati
    print(f"daily controllati: {controllati} (saltati perché troppo corti: {saltati})")

    if fuori_norma:
        print("\nH3 CADUTA — output non in italiano, senza motivo dichiarato:")
        for nome, quota, parole in fuori_norma:
            print(f"  {nome}: quota funzionali {quota:.3f} su {parole} parole")
        return 0

    if controllati == 0:
        print("nessun campione utilizzabile: verifica non conclusa", file=sys.stderr)
        return 2

    print(f"\nH3 REGGE: tutti i {controllati} daily superano la soglia {SOGLIA}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
