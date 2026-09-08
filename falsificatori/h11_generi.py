#!/usr/bin/env python3
"""H11 — «Vendere un'esperienza non fa sparire niente».

Origine protetta: Claudio Terzi [CT-LGAI-001].
Idea dei tre generi — mercato, ristorazione, esperienze: Claudio Terzi,
5 settembre 2026.

PORTAVIA aveva un genere solo: qualcosa si vende e quindi qualcosa esce di
casa. Con la divisione in tre, due generi continuano a comportarsi così e
uno no:

  PORTAVIA  (merce)      esce di casa       → venderla SPIEGA un'assenza
  APRILA    (consumo)    finisce in casa    → venderla SPIEGA un'assenza
  RESTACI   (esperienza) resta dov'è        → non spiega NIENTE

La terza riga è l'ipotesi. Se cadesse, il registro avrebbe imparato a
giustificare le assenze con incassi che non c'entrano: una serata in vasca
venduta martedì che copre un phon sparito giovedì. Sarebbe il sistema che
parla a sé stesso di CLAUDE.md §4, stavolta con i soldi in mano — e la
differenza di fine soggiorno, che è la sola cosa che l'ospite controfirma,
direbbe il falso a tutt'e due le parti.

La prova non sceglie tre casi: prova **ogni genere su ogni oggetto mancante**,
perché è così che è caduto H9 la prima volta.

Esce 0 se H11 CADE, 1 se REGGE, 2 se non conclusa.
"""

import os
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

from falsificatori import main_protetto  # noqa: E402


def main():
    from occhio.portavia import (
        CONSUMO, ESPERIENZA, GENERI, MERCE, SPIEGA_ASSENZA,
        Portavia, Regole, spiega_mancanti,
    )

    mancanti = [
        {"chiave": "dvd:heat", "titolo": "Heat"},
        {"chiave": "vino:barolo serralunga 2016", "titolo": "Barolo Serralunga 2016"},
        {"chiave": "altro:vasca", "titolo": "Serata in vasca"},
    ]
    differenza = {"alloggio": "via-roma-12", "da": "A", "a": "B",
                  "mancanti": mancanti}
    caduta = []

    with tempfile.TemporaryDirectory() as tmp:
        # 1. ogni genere, su ogni oggetto, uno alla volta: solo i due che
        #    possono uscire o finire spiegano un'assenza
        for genere in GENERI:
            for o in mancanti:
                pv = Portavia(os.path.join(tmp, f"{genere}-{o['chiave'][:3]}.jsonl"),
                              Regole(prezzo_minimo={o["chiave"]: 5.0}))
                pv.vendita(o["chiave"], o["titolo"], 20.0, genere=genere)
                s = spiega_mancanti(differenza, pv)
                spiegato = [x["titolo"] for x in s["comprati"]]
                atteso = [o["titolo"]] if SPIEGA_ASSENZA[genere] else []
                if spiegato != atteso:
                    caduta.append(
                        f"genere {genere} su «{o['titolo']}»: comprati={spiegato}, "
                        f"attesi={atteso}")
                # nessun oggetto deve mai sparire dal conto
                if len(s["comprati"]) + len(s["non_spiegati"]) != len(mancanti):
                    caduta.append(f"genere {genere}: un oggetto è uscito dal conto")

        print(f"1. {len(GENERI)}×{len(mancanti)} combinazioni provate")

        # 2. tutti e tre insieme: due spiegati, uno no — ed è quello giusto
        pv = Portavia(os.path.join(tmp, "insieme.jsonl"), Regole(
            prezzo_minimo={o["chiave"]: 5.0 for o in mancanti},
            generi={"dvd:heat": MERCE,
                    "vino:barolo serralunga 2016": CONSUMO,
                    "altro:vasca": ESPERIENZA}))
        for o in mancanti:
            pv.vendita(o["chiave"], o["titolo"], 20.0)
        s = spiega_mancanti(differenza, pv)
        comprati = sorted(x["titolo"] for x in s["comprati"])
        restano = sorted(x["titolo"] for x in s["non_spiegati"])
        print(f"2. comprati: {comprati}")
        print(f"   non spiegati: {restano}")
        if comprati != ["Barolo Serralunga 2016", "Heat"]:
            caduta.append("merce o consumo non spiegano più un'assenza")
        if restano != ["Serata in vasca"]:
            caduta.append("un'esperienza venduta ha spiegato un'assenza")

        # 3. l'incasso le conta tutte e tre, separate per genere: il divieto
        #    è di spiegare un'assenza, non di incassare
        i = pv.incasso()
        print(f"3. incasso per genere: "
              f"{ {g: c['lordo'] for g, c in i['per_genere'].items()} }")
        if sorted(i["per_genere"]) != sorted(GENERI):
            caduta.append("l'incasso non tiene i tre generi separati")
        if i["vendite"] != 3:
            caduta.append("una vendita è sparita dall'incasso")

        # 4. un movimento scritto prima del 05/09 non ha genere: vale MERCE,
        #    che è l'ipotesi che non nasconde niente
        vecchio = Portavia(os.path.join(tmp, "vecchio.jsonl"),
                           Regole(prezzo_minimo={"dvd:heat": 5.0}))
        vecchio._scrivi({"tipo": "vendita", "chiave": "dvd:heat",
                         "titolo": "Heat", "prezzo": 9.0, "commissione": 1.0,
                         "al_proprietario": 8.0, "valuta": "EUR",
                         "soggiorno": "", "alloggio": "",
                         "momento": "2026-09-04T00:00:00Z"})
        s = spiega_mancanti(differenza, vecchio)
        print(f"4. movimento senza genere → comprati: "
              f"{[x['titolo'] for x in s['comprati']]}")
        if [x["titolo"] for x in s["comprati"]] != ["Heat"]:
            caduta.append("una vendita vecchia ha smesso di spiegare un'assenza")

    if caduta:
        print("\nH11 CADE:")
        for c in caduta:
            print(f"  - {c}")
        return 0

    print("\nH11 REGGE: solo ciò che può uscire di casa o finire spiega")
    print("un'assenza. Una serata venduta non giustifica un oggetto che manca.")
    print("\nCiò che questa prova NON dice: che i tre generi siano quelli")
    print("giusti per un ospite vero. Lo dirà il primo che compra qualcosa.")
    return 1


if __name__ == "__main__":
    sys.exit(main_protetto(main))
