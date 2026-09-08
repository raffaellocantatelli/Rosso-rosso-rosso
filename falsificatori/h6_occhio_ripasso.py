#!/usr/bin/env python3
"""H6 — «Ripassare con la telecamera sugli stessi oggetti non gonfia l'inventario».

Origine protetta: Claudio Terzi [CT-LGAI-001].

Perché questa ipotesi e non un'altra. Un inventario che cresce a ogni passata
non misura gli oggetti: misura le passate. È il difetto di CLAUDE.md §4 —
il sistema che registra la propria eco come dato — applicato a un armadio,
e in questo caso il numero che cresce è persino gratificante: sembra che il
lavoro proceda. È esattamente la forma di errore che questo repository
esiste per riconoscere.

Come si falsifica, in una riga: si dà in pasto due volte la stessa lettura e
si guarda il totale. Se cresce, H6 è caduta.

Il test non chiama nessun modello e non tocca il file reale: lavora su un
inventario temporaneo. Deve poter girare nella Action, senza chiavi, sempre.

Esce 0 se H6 CADE, 1 se REGGE, 2 se non conclusa (convenzione dei
falsificatori di questo repository, verificata su h3_italiano.py).
"""

import os
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

from occhio.inventario import Inventario  # noqa: E402
from occhio.server import impronta_vicina  # noqa: E402

# Una passata plausibile su uno scaffale: due titoli leggibili, uno illeggibile.
PASSATA = [
    {"tipo": "dvd", "titolo": "The Matrix", "impronta": "f0e1d2c3b4a59687"},
    {"tipo": "dvd", "titolo": "Il Padrino", "impronta": "0123456789abcdef"},
    {"tipo": "libro", "titolo": "Se questo è un uomo", "impronta": "aaaa5555aaaa5555"},
]

# La seconda passata è la stessa scena da un passo più in là: stessi oggetti,
# titoli scritti come li leggerebbe un OCR diverso, impronte leggermente
# diverse perché la luce e l'inquadratura sono cambiate.
RIPASSA = [
    {"tipo": "dvd", "titolo": "MATRIX, THE", "impronta": "f0e1d2c3b4a59683"},
    {"tipo": "DVD", "titolo": "il padrino", "impronta": "0123456789abcde7"},
    {"tipo": "libro", "titolo": "Se questo e un uomo", "impronta": "aaaa5555aaaa5551"},
]


def prova_ripasso(registro):
    for o in PASSATA:
        registro.registra(o["tipo"], o["titolo"], o["impronta"], fonte="prova")
    dopo_prima = len(registro.voci)

    for o in RIPASSA:
        stato, _ = registro.riconosci(o["tipo"], o["titolo"], o["impronta"])
        if stato in ("NUOVO",):
            registro.registra(o["tipo"], o["titolo"], o["impronta"], fonte="prova")
    return dopo_prima, len(registro.voci)


def prova_persistenza(percorso):
    """Il verde deve sopravvivere al riavvio: viene dal file, non dalla sessione.

    Se il riconoscimento dipendesse dallo stato in memoria, chiudere il server
    e riaprirlo farebbe tornare rosso ciò che era verde — e l'inventario
    raddoppierebbe alla passata successiva, in silenzio.
    """
    fresco = Inventario(percorso)
    stato, _ = fresco.riconosci("dvd", "MATRIX, THE", None)
    return stato


def prova_distinzione(registro):
    """Il contrario dell'eco: due oggetti diversi devono restare due.

    Un sistema che deduplica troppo passa il test del ripasso in modo banale —
    fondendo tutto in una voce sola. Va misurato anche questo, altrimenti H6
    si potrebbe far reggere peggiorando il prodotto.
    """
    prima = len(registro.voci)
    registro.registra("dvd", "Rocky 2", "1111222233334444", fonte="prova")
    registro.registra("dvd", "Rocky 3", "5555666677778888", fonte="prova")
    return len(registro.voci) - prima


def main():
    with tempfile.TemporaryDirectory() as d:
        percorso = os.path.join(d, "inventario_prova.jsonl")
        registro = Inventario(percorso)

        dopo_prima, dopo_ripasso = prova_ripasso(registro)
        print(f"prima passata:   {dopo_prima} oggetti")
        print(f"dopo il ripasso: {dopo_ripasso} oggetti")

        stato_riavvio = prova_persistenza(percorso)
        print(f"dopo riavvio, «MATRIX, THE» risulta: {stato_riavvio}")

        distinti = prova_distinzione(registro)
        print(f"due titoli diversi aggiungono: {distinti} voci")

        # impronte: due riquadri sovrapposti condividono l'impronta, due
        # lontani no. Senza questo, un titolo illeggibile verrebbe richiesto
        # in conferma a ogni fotogramma.
        vicina = impronta_vicina([0.10, 0.20, 0.10, 0.50],
                                 [{"riquadro": [0.11, 0.21, 0.10, 0.50], "impronta": "abc"}])
        lontana = impronta_vicina([0.10, 0.20, 0.10, 0.50],
                                  [{"riquadro": [0.80, 0.20, 0.10, 0.50], "impronta": "abc"}])
        print(f"impronta riusata su riquadro vicino: {vicina} — su lontano: {lontana}")

        caduta = []
        if dopo_ripasso != dopo_prima:
            caduta.append(f"il ripasso ha aggiunto {dopo_ripasso - dopo_prima} voci")
        if stato_riavvio not in ("CATALOGATO", "RIVISTO"):
            caduta.append(f"dopo il riavvio l'oggetto non è più riconosciuto ({stato_riavvio})")
        if distinti != 2:
            caduta.append(f"due oggetti diversi hanno prodotto {distinti} voci invece di 2")
        if vicina != "abc" or lontana is not None:
            caduta.append("l'associazione delle impronte per sovrapposizione non funziona")

        if caduta:
            print("\nH6 CADUTA:")
            for c in caduta:
                print(f"  - {c}")
            return 0

        print("\nH6 REGGE su questa esecuzione: ripassare non ha aggiunto niente,")
        print("il riconoscimento sopravvive al riavvio, oggetti diversi restano distinti.")
        print("Reggere non è confermare: serve una passata su oggetti veri, con un")
        print("modello vero, contata a mano da qualcuno che apre l'armadio.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
