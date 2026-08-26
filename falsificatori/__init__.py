"""Falsificatori — un comando per ipotesi, che risponde a una sola domanda.

Contratto degli exit code, uguale per tutti:

    0  la condizione di falsificazione E' avvenuta  -> l'ipotesi e' caduta
    1  la condizione non e' avvenuta                -> l'ipotesi regge
    2  la verifica stessa non ha potuto concludere  -> UNKNOWN, non conta

Il 2 esiste perche' "non ho potuto controllare" non e' "va tutto bene".
Confonderli sarebbe il difetto che questo progetto esiste per impedire.
"""

CADUTA = 0
REGGE = 1
NON_CONCLUSA = 2


def main_protetto(funzione):
    """Esegue un falsificatore senza lasciar scappare eccezioni.

    Serve perche' Python esce con codice 1 quando un'eccezione non e' gestita,
    e 1 in questo contratto significa REGGE. Il 26/08/2026 H5 e' risultata
    RETTA per un falsificatore andato in crash su un 429: "non ho potuto
    controllare" registrato come "va tutto bene" — la confusione che l'exit 2
    esiste per impedire, dentro lo strumento costruito per impedirla.
    """
    import sys
    import traceback
    try:
        return funzione()
    except Exception as errore:
        print(f"il falsificatore non ha potuto concludere: "
              f"{type(errore).__name__}: {errore}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return NON_CONCLUSA
