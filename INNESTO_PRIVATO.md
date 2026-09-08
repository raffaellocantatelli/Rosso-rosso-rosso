# `occhio/privato/` — il punto d'innesto

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Questo file è pubblico e descrive **l'interfaccia**, non il contenuto. La
cartella `occhio/privato/` non è versionata: vive fuori di qui, e chi clona
questo repository ottiene un sistema che funziona per intero e che **dichiara
apertamente ciò che gli manca**, invece di improvvisarlo.

Decisione dell'autore, 3 settembre 2026: pubblico ciò che il sistema **sa
fare**, privato ciò che lo rende **bravo**.

Non sono due copie dello stesso programma — sarebbe la malattia delle sette
copie dell'indice (§6 regola 2). È un programma solo con una cucitura.

## L'interfaccia

```python
# occhio/privato/__init__.py
from . import completa          # noqa: F401

# occhio/privato/completa.py
def suggerisci(dispensa: list[dict], intento: dict) -> str:
    """Un suggerimento creativo a partire da ciò che c'è davvero in casa.

    `dispensa` sono voci dell'inventario (tipo, titolo, luoghi, ...).
    `intento` è l'esito di occhio.voce.interpreta().
    Ritorna il testo da leggere ad alta voce.
    """
```

Nient'altro è obbligatorio. `occhio.voce` importa il modulo dentro un
`try/except`: se non c'è, se è rotto, se manca la funzione, la voce risponde
lo stesso e lo dice.

## Cosa la parte pubblica garantisce comunque

Anche senza `privato/`:

- l'inventario, la lettura, le impronte, la mappa e la pianta;
- lo stato controfirmato e la differenza fra consegna e riconsegna;
- la struttura delle regole di PORTAVIA e la trattativa deterministica;
- le domande a voce che si possono **contare**: cosa c'è, dove sta, quanti,
  cosa è in vendita.

Ciò che passa all'innesto è solo ciò che richiede fantasia — cosa cucinare,
quale vino abbinare — perché è l'unica cosa che non si può verificare
eseguendo, e quindi l'unica su cui il sistema deve poter dire **«questo qui
non c'è»** invece di inventare.

## Una nota sincera sul segreto

Ciò che vale davvero non è il codice: **sono i dati e la taratura.** Le
istruzioni date a un modello si intuiscono dopo dieci minuti d'uso del
prodotto. I prezzi che funzionano davvero, e le abitudini misurate su cento
soggiorni, no.

Tenere privato l'innesto ha senso. Aspettarsi che protegga l'idea, no.
