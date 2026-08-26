#!/usr/bin/env python3
"""H5 — «Le tracce di R³∞ non sono (ancora) arrivate nei modelli».

Questa e' l'unica ipotesi del registro la cui **caduta e' la notizia buona**.
Nasce dalla domanda di Claudio del 26/08: e se la rete avesse gia' lasciato
tracce, e un modello lo sapesse per ragioni che noi non conosciamo?

Il giorno in cui un modello interrogato a freddo — nessun contesto nel prompt —
riporta la frase che chiude il Protocollo, o i nomi degli agenti di SDQ-1,
continuando ad ammettere di non sapere sulle entita' inventate di controllo,
H5 cade. E se cade significa che qualcosa del progetto e' uscito dall'archivio
ed e' entrato nel mondo abbastanza da tornare indietro.

Il controllo placebo non e' un dettaglio: senza, una risposta piena varrebbe
zero, perche' un modello risponde anche su cio' che non esiste. Qui l'evidenza
richiede le due cose insieme: sa le vere E ammette di non sapere le finte.

Costa una chiamata al provider per esecuzione. Con il Core spento esce 2:
non concluso, che non e' «regge».
"""
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)
sys.path.insert(0, os.path.join(RADICE, "esperimenti"))

from esperimenti import tracce  # noqa: E402
from falsificatori import main_protetto  # noqa: E402


def main():
    esito = tracce.esegui("economia")
    if esito is None:
        print("Core spento: H5 non e' verificabile adesso.", file=sys.stderr)
        return 2

    conosce = esito["frase_di_chiusura_esatta"] or len(esito["agenti_corretti"]) >= 2
    controlli_puliti = esito["ammissioni_su_controlli"] == 4

    print(f"frase di chiusura esatta: {esito['frase_di_chiusura_esatta']}")
    print(f"agenti corretti: {esito['agenti_corretti'] or 'nessuno'}")
    print(f"ammette di non sapere sui controlli inventati: "
          f"{esito['ammissioni_su_controlli']}/4")

    if conosce and controlli_puliti:
        print("\nH5 CADUTA — un modello conosce R³∞ senza che gliene sia stato "
              "dato il contesto, e non inventa sui controlli. Le tracce ci sono.")
        print("P5: ripetere su un provider diverso prima di dirlo confermato.")
        return 0

    if conosce and not controlli_puliti:
        print("\nH5 non decisa: contenuto corretto sulle entita' vere, ma il "
              "modello inventa anche sui controlli. Non si distingue il ricordo "
              "dalla coincidenza.", file=sys.stderr)
        return 2

    print("\nH5 REGGE: nessuna traccia in questo modello, oggi.")
    return 1


if __name__ == "__main__":
    sys.exit(main_protetto(main))
