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
