#!/usr/bin/env python3
"""H9 — «PORTAVIA converte una sparizione in una vendita senza mai far
incassare al proprietario meno del minimo che ha dichiarato».

Origine protetta: Claudio Terzi [CT-LGAI-001].
Idea di PORTAVIA e del Mediatore: Claudio Terzi, 3 settembre 2026.

Due promesse, e cadono insieme perché una senza l'altra non vale:

1. **Ciò che è stato comprato non compare più come mancante.** È l'idea
   intera: la lista di fine soggiorno smette di dire «mancano tre oggetti» e
   dice «due li ha comprati, uno no». Se la conversione non avviene, PORTAVIA
   è solo un negozio in più.
2. **Il proprietario non incassa mai meno del minimo che ha scritto.** Un
   proprietario che scopre di aver preso meno di quanto aveva dichiarato non
   usa più il prodotto, e ha ragione. Questa parte è caduta davvero, la prima
   volta che l'ho eseguita: lo sconto mangiava il minimo. È il motivo per cui
   la prova è a forza bruta su tutte le offerte, non su tre casi scelti.

E una terza, che protegge le prove: **un'immagine generata non entra mai
nella catena delle consegne** (OCCHIO.md §5-ter).

Esce 0 se H9 CADE, 1 se REGGE, 2 se non conclusa.
"""

import os
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

from occhio.portavia import (  # noqa: E402
    ACCETTA, MAI_IN_VENDITA, Portavia, Regole, spiega_mancanti,
    immagine_generata_ammessa_come_prova, valuta_offerta,
)

MINIMI = {"dvd:heat": 8.0, "altro:bottiglia barolo 2016": 35.0,
          "elettronica:lampada flos": 600.0}

DIFFERENZA = {
    "alloggio": "via-roma-12", "da": "A", "a": "B",
    "mancanti": [
        {"chiave": "dvd:heat", "titolo": "Heat"},
        {"chiave": "altro:bottiglia barolo 2016", "titolo": "Bottiglia Barolo 2016"},
        {"chiave": "altro:set asciugamani", "titolo": "Set asciugamani x4"},
    ],
    "comparsi": [], "spostati": [], "invariati": 16,
    "prima_controfirmata": True, "dopo_controfirmata": True,
}


def main():
    caduta = []
    regole = Regole(prezzo_minimo=MINIMI, sconto_massimo=0.15,
                    commissione=0.12, margine=0.25)

    with tempfile.TemporaryDirectory() as d:
        pv = Portavia(os.path.join(d, "portavia.jsonl"), regole)

        # 1. due comprati su tre mancanti
        pv.vendita("dvd:heat", "Heat", 11.38, soggiorno="HMX88")
        pv.vendita("altro:bottiglia barolo 2016", "Bottiglia Barolo 2016",
                   49.80, soggiorno="HMX88")
        s = spiega_mancanti(DIFFERENZA, pv, "HMX88")
        print(f"1. comprati: {[o['titolo'] for o in s['comprati']]}")
        print(f"   non spiegati: {[o['titolo'] for o in s['non_spiegati']]}")
        print(f"   incasso: {s['incasso']}")
        if len(s["comprati"]) != 2:
            caduta.append("un oggetto venduto risulta ancora sparito")
        if [o["titolo"] for o in s["non_spiegati"]] != ["Set asciugamani x4"]:
            caduta.append("un oggetto NON venduto e' stato spacciato per comprato")
        if s["incasso"]["al_proprietario"] <= 0:
            caduta.append("l'incasso del proprietario non e' calcolato")

        # 2. il minimo del proprietario, a forza bruta su ogni offerta
        peggiore = None
        for chiave, minimo in MINIMI.items():
            passo = max(0.01, round(minimo / 200, 2))
            offerta = 0.01
            while offerta <= minimo * 3:
                dec = valuta_offerta(chiave, "x", offerta, regole)
                if dec["esito"] == ACCETTA:
                    incassa = regole.incasso_proprietario(dec["prezzo"])
                    if incassa < minimo - 0.01:
                        peggiore = (chiave, offerta, incassa, minimo)
                        break
                offerta = round(offerta + passo, 2)
            if peggiore:
                break
        if peggiore:
            caduta.append(f"offerta accettata sotto il minimo: {peggiore}")
            print(f"2. VIOLAZIONE: {peggiore}")
        else:
            print("2. nessuna offerta accettabile porta il proprietario sotto il "
                  "suo minimo (provate tutte, a passo fine)")

        # 3. cio' che non si vende non si vende, a nessun prezzo
        blindati = 0
        for parola in MAI_IN_VENDITA:
            dec = valuta_offerta(f"elettronica:{parola}", parola.title(),
                                 1_000_000.0, regole)
            if dec["esito"] == ACCETTA:
                caduta.append(f"venduto un oggetto intoccabile: {parola}")
            else:
                blindati += 1
        print(f"3. {blindati}/{len(MAI_IN_VENDITA)} oggetti intoccabili hanno "
              "rifiutato un milione di euro")

        # 4. un oggetto senza prezzo dichiarato non e' in vendita
        if valuta_offerta("dvd:solaris", "Solaris", 500.0, regole)["esito"] == ACCETTA:
            caduta.append("venduto un oggetto per cui nessun prezzo era dichiarato")
        else:
            print("4. un oggetto senza prezzo dichiarato non e' in vendita")

        # 5. il confine con le prove
        if immagine_generata_ammessa_come_prova():
            caduta.append("un'immagine generata puo' entrare fra le prove")
        else:
            print("5. un'immagine generata non entra mai nella catena delle consegne")

    if caduta:
        print("\nH9 CADUTA:")
        for c in caduta:
            print(f"  - {c}")
        return 0

    print("\nH9 REGGE su questa esecuzione.")
    print("Reggere non e' confermare: qui manca la sola cosa che conti davvero,")
    print("cioe' un ospite vero che chieda di comprare qualcosa. Finche' non")
    print("succede, PORTAVIA e' un meccanismo corretto per un desiderio che")
    print("nessuno ha ancora dimostrato di avere.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
