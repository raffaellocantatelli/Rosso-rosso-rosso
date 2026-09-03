#!/usr/bin/env python3
"""H8 — «Lo stato di consegna rileva ciò che manca e non si può riscrivere
senza accorgersene».

Origine protetta: Claudio Terzi [CT-LGAI-001].

L'ipotesi che regge il prodotto per gli affitti brevi: fra un ospite e
l'altro il sistema deve dire cosa manca, e nessuna delle due parti deve
poter riscrivere il passato in silenzio.

Quattro prove. Le prime tre sono quelle che uno si aspetta. **La quarta è
quella che conta**, ed è costruita per rompere il modulo che la contiene:
dimostra che una catena rigenerata da capo dal solo proprietario risulta
perfettamente «integra» — perché lo è. Coerente con se stessa e senza alcun
valore in una lite. Se il modulo presentasse `catena_integra` come prova,
H8 cadrebbe qui, ed è giusto così: è il difetto di CLAUDE.md §4 travestito
da crittografia, ed è il modo più elegante di ingannarsi che questo
progetto abbia incontrato finora.

Ciò che rende opponibile uno stato non è l'impronta: è la **controfirma**
dell'altra parte, che ha interesse opposto.

Esce 0 se H8 CADE, 1 se REGGE, 2 se non conclusa.
"""

import json
import os
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

from occhio.consegna import Consegne, differenza  # noqa: E402

CODICE = "HMX88-2026"
OGGETTI = [
    {"chiave": "elettronica:nespresso", "titolo": "Nespresso Vertuo",
     "luogo": {"stanza": "cucina"}, "foto_sha": "a" * 64},
    {"chiave": "elettronica:tv", "titolo": "LG OLED 55",
     "luogo": {"stanza": "salotto"}, "foto_sha": "b" * 64},
    {"chiave": "dvd:heat", "titolo": "Heat",
     "luogo": {"stanza": "salotto"}, "foto_sha": "c" * 64},
]


def main():
    caduta = []
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "consegne.jsonl")
        c = Consegne(p)

        # 1. la differenza trova ciò che manca e ciò che si è spostato
        s1 = c.deposita("via-roma-12", "consegna", OGGETTI, "sogg-1")
        c.controfirma(s1["impronta"], CODICE)
        riconsegnati = [OGGETTI[2], dict(OGGETTI[1], luogo={"stanza": "cucina"})]
        s2 = c.deposita("via-roma-12", "riconsegna", riconsegnati, "sogg-1")
        c.controfirma(s2["impronta"], CODICE)
        diff = differenza(s1, s2)
        print(f"1. mancanti: {[o['titolo'] for o in diff['mancanti']]}")
        print(f"   spostati: {[o['titolo'] for o in diff['spostati']]}")
        if [o["titolo"] for o in diff["mancanti"]] != ["Nespresso Vertuo"]:
            caduta.append("la differenza non ha trovato l'oggetto mancante")
        if len(diff["spostati"]) != 1:
            caduta.append("la differenza non ha visto l'oggetto spostato")

        # 2. la catena integra si riconosce
        v = c.verifica(CODICE)
        print(f"2. catena integra: {v['catena_integra']}, "
              f"controfirme: {v['controfirme']}/{v['stati']}")
        if not v["catena_integra"] or v["controfirme"] != 2:
            caduta.append("una catena sana non risulta sana")

        # 3. una riga riscritta a mano rompe la verifica
        righe = open(p, encoding="utf-8").read().splitlines()
        voce = json.loads(righe[0])
        voce["oggetti"][0]["titolo"] = "Caffettiera da tre euro"
        righe[0] = json.dumps(voce, ensure_ascii=False)
        manomessa = os.path.join(d, "manomessa.jsonl")
        open(manomessa, "w", encoding="utf-8").write("\n".join(righe) + "\n")
        vm = Consegne(manomessa).verifica(CODICE)
        print(f"3. dopo aver riscritto una riga: integra={vm['catena_integra']}, "
              f"rotture={len(vm['rotture'])}")
        if vm["catena_integra"] or not vm["rotture"]:
            caduta.append("una riga riscritta a mano non è stata rilevata")

        # 4. LA PROVA CHE CONTA: catena rifatta da capo da una parte sola
        rifatto = os.path.join(d, "rifatto.jsonl")
        c2 = Consegne(rifatto)
        falso = [dict(o, titolo="Caffettiera da tre euro") if o["chiave"].endswith("nespresso")
                 else o for o in OGGETTI]
        c2.deposita("via-roma-12", "consegna", falso, "sogg-1")
        c2.deposita("via-roma-12", "riconsegna", riconsegnati, "sogg-1")
        vr = c2.verifica(CODICE)
        print(f"4. catena RIFATTA da capo dal solo proprietario: "
              f"integra={vr['catena_integra']}, "
              f"controfirme={vr['controfirme']}/{vr['stati']}, "
              f"stati senza controfirma={len(vr['senza_controfirma'])}")
        if not vr["catena_integra"]:
            caduta.append("la prova 4 non dimostra niente se la catena rifatta "
                          "non risulta integra: rivedere il test")
        if vr["controfirme"] != 0 or len(vr["senza_controfirma"]) != 2:
            caduta.append("una catena rifatta non viene marcata come non "
                          "controfirmata: il sistema starebbe offrendo come "
                          "prova qualcosa che non lo è")

        # e la differenza deve dirlo da sé, senza che nessuno lo chieda
        d2 = differenza(c2.stati[0], c2.stati[1])
        if d2["prima_controfirmata"] or d2["dopo_controfirmata"]:
            caduta.append("la differenza dichiara controfirmato ciò che non lo è")

    if caduta:
        print("\nH8 CADUTA:")
        for x in caduta:
            print(f"  - {x}")
        return 0

    print("\nH8 REGGE su questa esecuzione.")
    print("Ma leggi bene la prova 4: la catena RIFATTA da capo risulta integra.")
    print("È corretto, ed è il limite del modulo — l'impronta prova la coerenza")
    print("con sé stessi, non l'anteriorità. Ciò che rende opponibile uno stato")
    print("è la controfirma dell'altra parte, che ha interesse opposto.")
    print("\nReggere non è confermare: il valore legale di questa controfirma")
    print("è UNKNOWN e lo dice un avvocato, non un file Python.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
