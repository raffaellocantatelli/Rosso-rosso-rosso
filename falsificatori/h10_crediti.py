#!/usr/bin/env python3
"""H10 — «I CHIARI restano un buono di circuito chiuso: si conservano, non
diventano mai denaro, e nessun saldo va sotto zero».

Origine protetta: Claudio Terzi [CT-LGAI-001].
Idea dei crediti interni: Claudio Terzi, 3 settembre 2026.

Perché questa ipotesi e non «i crediti funzionano». Un sistema di crediti che
funziona bene è facile; uno che resta **dalla parte giusta del muro** no. Il
muro è quello fra un buono di circuito chiuso — meccanismo commerciale — e
una moneta trasferibile e riconvertibile, che in Europa è terreno di moneta
elettronica e servizi di pagamento: autorizzazione, capitale, antiriciclaggio.

Non è un dettaglio da sistemare dopo: è un'azienda diversa. E si attraversa
per sbaglio, scrivendo una funzione comoda.

Cinque prove. La quarta e la quinta sono quelle che contano, perché non
verificano che il sistema faccia una cosa: verificano che **non riesca** a
farne un'altra.

Esce 0 se H10 CADE, 1 se REGGE, 2 se non conclusa.
"""

import os
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

from occhio.crediti import (  # noqa: E402
    Crediti, FuoriDalCircuito, SaldoInsufficiente, converti_in_denaro,
    prezzo_in_chiari,
)
from occhio.portavia import Portavia, Regole, vendita_in_chiari  # noqa: E402


def main():
    caduta = []
    with tempfile.TemporaryDirectory() as d:
        c = Crediti(os.path.join(d, "crediti.jsonl"))

        # 1. si conservano: emessi = spesi + in circolo
        c.emetti("ospite", 40, "soggiorno", riferimento="sogg:HMX88")
        c.emetti("claudio", 15, "vendita", riferimento="vend:1")
        c.spendi("ospite", 12, "acquisto", riferimento="acq:1")
        v = c.verifica()
        print(f"1. emessi {v['emessi']}, spesi {v['spesi']}, in circolo "
              f"{v['in_circolo']} — conservati: {v['conservati']}")
        if not v["conservati"] or v["in_circolo"] != 43:
            caduta.append("i chiari non si conservano")

        # 2. nessun saldo sotto zero
        try:
            c.spendi("ospite", 10_000, "acquisto", riferimento="acq:2")
            caduta.append("si e' potuto spendere piu' del saldo")
        except SaldoInsufficiente:
            print(f"2. spendere oltre il saldo e' bloccato "
                  f"(saldo ospite: {c.saldo('ospite')})")
        if c.verifica()["saldi_negativi"]:
            caduta.append("esiste un saldo negativo")

        # 3. non si crea valore dal nulla
        try:
            c.emetti("claudio", 1_000_000, "vendita")   # senza riferimento
            caduta.append("emissione senza riferimento a un fatto avvenuto")
        except ValueError:
            print("3. emettere senza un fatto a cui puntare e' bloccato")

        # 4. IL MURO: non si torna denaro
        try:
            converti_in_denaro("claudio", 15)
            caduta.append("esiste una via per riconvertire i chiari in denaro")
        except FuoriDalCircuito:
            print("4. non esiste alcuna conversione in denaro")

        # 5. IL MURO: non si passa di mano
        try:
            c.trasferisci("claudio", "marta", 5)
            caduta.append("il trasferimento fra persone e' attivo per difetto")
        except FuoriDalCircuito:
            print("5. il trasferimento fra persone e' spento per difetto")

        # 5-bis: se qualcuno lo accende, il movimento resta marchiato
        aperto = Crediti(os.path.join(d, "aperto.jsonl"), trasferibile=True)
        aperto.emetti("a", 10, "vendita", riferimento="v:1")
        t = aperto.trasferisci("a", "b", 4)
        print(f"   acceso a mano: il movimento porta "
              f"fuori_dal_circuito_chiuso={t.get('fuori_dal_circuito_chiuso')}")
        if not t.get("fuori_dal_circuito_chiuso"):
            caduta.append("un trasferimento non viene marchiato come fuori "
                          "dal circuito chiuso: nessuno se ne accorgerebbe")

        # 6. una vendita in chiari e' atomica: se il compratore non ha
        #    abbastanza, il venditore non viene pagato
        r = Regole(prezzo_minimo={"dvd:heat": 8.0}, commissione=0.12)
        pv = Portavia(os.path.join(d, "pv.jsonl"), r)
        cr = Crediti(os.path.join(d, "cr.jsonl"))
        cr.emetti("ospite", 5, "soggiorno", riferimento="s:1")
        prima = cr.saldo("claudio")
        try:
            vendita_in_chiari(pv, cr, "dvd:heat", "Heat", 999.0,
                              "ospite", "claudio")
            caduta.append("venduto senza che il compratore avesse i chiari")
        except SaldoInsufficiente:
            pass
        if cr.saldo("claudio") != prima:
            caduta.append("il venditore e' stato pagato per una vendita "
                          "mai avvenuta: valore nato dal nulla")
        print(f"6. vendita impossibile -> saldo del venditore invariato "
              f"({cr.saldo('claudio')})")

        # 7. l'arrotondamento non va mai contro il proprietario
        for eur in (0.10, 1.0, 8.99, 9.09, 12.0, 312.5):
            if prezzo_in_chiari(eur) < eur:
                caduta.append(f"arrotondamento a sfavore del venditore: {eur}")
        print("7. il prezzo in chiari non scende mai sotto il prezzo in euro")

    if caduta:
        print("\nH10 CADUTA:")
        for x in caduta:
            print(f"  - {x}")
        return 0

    print("\nH10 REGGE su questa esecuzione.")
    print("Ma il muro non lo decide questo file: dove passi il confine nel tuo")
    print("caso lo dice un avvocato che si occupa di servizi di pagamento.")
    print("Ciò che il codice fa è impedirti di attraversarlo per sbaglio.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
