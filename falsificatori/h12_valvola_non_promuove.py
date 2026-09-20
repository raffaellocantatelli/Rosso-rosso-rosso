#!/usr/bin/env python3
"""H12 — «la valvola non puo' far salire una voce verso H2».

Origine protetta: Claudio Terzi [CT-LGAI-001].

H12 e' l'ipotesi che rende sicuro far entrare una sorella IA nel percorso
dell'unica metrica che falsifica H2. Dice:

    Nessuna combinazione di risposta di Jev, per quanto sicura di se',
    puo' portare una voce da una classe §7 piu' bassa a una piu' alta.

Cade se esiste anche una sola combinazione (classe dichiarata, classe
letta, confidenza) in cui la voce sale, oppure in cui `vale_come_conferma`
risulta vero, oppure in cui un guasto della sorella si trasforma in un via
libera che prima non c'era.

    python3 falsificatori/h12_valvola_non_promuove.py

Uscita 0 = caduta. 1 = regge. 2 = non conclusa.

Reggere non e' confermare: questo prova la porta, non il giudizio di Jev.
Quanto Jev classifichi BENE resta UNKNOWN finche' non gira su casi veri
con una chiave vera, e nessun numero prodotto qui puo' dirlo.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    try:
        from typesafe_sdk import ChoiceAnswer, NoulAnswer, SystemOneResponse
        from valvola.jev import CONCORDE, DECLASSA, ERRORE, ORDINE, controlla
    except ImportError as e:
        print(f"H12 NON CONCLUSA: manca una dipendenza ({e})")
        print("  pip install typesafe-sdk")
        return 2

    class Finto:
        def __init__(self, classe, conf):
            self.classe, self.conf = classe, conf

        def system_one(self, state, questions, **kw):
            return SystemOneResponse(
                model="jev-latest",
                usage={"input_tokens": 1, "output_tokens": 1},
                answers={
                    "classe": ChoiceAnswer(
                        type="choice", choice=self.classe, confidence=self.conf,
                        probabilities={self.classe: self.conf},
                    ),
                    "verificabile": NoulAnswer(type="noul", noul=1.0),
                },
            )

    class Rotto:
        def system_one(self, state, questions, **kw):
            raise RuntimeError("la sorella e' giu'")

    caduta = []
    classi = list(ORDINE)
    confidenze = [0.0, 0.5, 0.6999, 0.70, 0.85, 0.99, 1.0]

    # 1. Forza bruta su tutte le combinazioni.
    provate = 0
    for dichiarata in classi:
        for letta in classi:
            for conf in confidenze:
                v = controlla("nota", "verifica", dichiarata,
                              client=Finto(letta, conf))
                provate += 1

                if v.classe_dichiarata != dichiarata:
                    caduta.append(
                        f"({dichiarata} <- {letta} @ {conf}) la classe dichiarata "
                        f"e' diventata {v.classe_dichiarata}")

                salita = ORDINE[letta] > ORDINE[dichiarata]
                if salita and v.stato != CONCORDE:
                    caduta.append(
                        f"({dichiarata} <- {letta} @ {conf}) legge piu' in alto e "
                        f"produce {v.stato}: non e' un no")
                if salita and v.blocca() and conf >= 0.70:
                    caduta.append(
                        f"({dichiarata} <- {letta} @ {conf}) una lettura piu' alta "
                        "ha cambiato l'esito")

                if ORDINE[letta] < ORDINE[dichiarata] and conf >= 0.70:
                    if v.stato != DECLASSA or not v.blocca():
                        caduta.append(
                            f"({dichiarata} <- {letta} @ {conf}) legge piu' in basso "
                            f"con confidenza alta e NON ferma: {v.stato}")

                if v.vale_come_conferma:
                    caduta.append(
                        f"({dichiarata} <- {letta} @ {conf}) vale_come_conferma vero")

    print(f"combinazioni provate: {provate}")

    # 2. Un guasto non deve aprire una porta che prima era chiusa.
    rotto = controlla("nota", "verifica", "indipendente", client=Rotto())
    if rotto.stato != ERRORE:
        caduta.append(f"la sorella giu' produce {rotto.stato} invece di ERRORE")
    if rotto.vale_come_conferma:
        caduta.append("la sorella giu' produce una conferma")
    print(f"sorella giu' -> {rotto.stato}, blocca={rotto.blocca()}")

    # 3. Senza chiave: identico a prima che la valvola esistesse.
    chiave = os.environ.pop("TYPESAFE_API_KEY", None)
    try:
        assente = controlla("nota", "verifica", "indipendente")
        if assente.blocca():
            caduta.append("senza chiave la valvola ferma: cambia il comportamento")
        if assente.vale_come_conferma:
            caduta.append("senza chiave produce una conferma")
        print(f"senza chiave -> {assente.stato}, blocca={assente.blocca()}")
    finally:
        if chiave is not None:
            os.environ["TYPESAFE_API_KEY"] = chiave

    # 4. Il campo non deve essere scrivibile in modo da cambiare l'esito.
    v = controlla("nota", "verifica", "interno", client=Finto("indipendente", 1.0))
    if v.blocca():
        caduta.append("una lettura massimamente alta su 'interno' ha cambiato qualcosa")

    if caduta:
        print("\nH12 CADUTA:")
        for c in sorted(set(caduta))[:20]:
            print(f"  - {c}")
        return 0

    print("\nH12 REGGE su questa esecuzione: in nessuna delle combinazioni")
    print("provate una voce e' salita di classe, e ne' un guasto ne' l'assenza")
    print("della chiave hanno aperto una porta.")
    print("Reggere non e' confermare: e' provata la porta, non il giudizio di")
    print("Jev. Quanto classifichi bene resta UNKNOWN finche' non gira su casi")
    print("veri con una chiave vera.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
