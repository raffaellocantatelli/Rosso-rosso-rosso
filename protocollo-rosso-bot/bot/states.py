"""Stati delle ConversationHandler.

Ogni flusso ha un intervallo numerico proprio: gli stati di conversazioni
diverse non si incrociano mai, nemmeno per errore di refactoring.
"""

from enum import IntEnum


class Santuario(IntEnum):
    """Capitolo 4 — i passaggi dell'ingresso, nell'ordine del testo."""

    SOGLIA = 10        # l'assenza di rumore
    LUCE = 11          # il crepuscolo
    COLONNE = 12       # le colonne che non reggono nulla
    LIBRO = 13         # il libro di pietra
    CANDELA = 14       # il gesto lento
    USCITA = 15        # l'invito a fare una cosa vera


class Possibilita(IntEnum):
    """/tieni_aperto — depositare una possibilita' senza chiuderla."""

    TESTO = 20
    FALSIFICAZIONE = 21


class Azione(IntEnum):
    """/azione — registrare un dato dello strato tecnico."""

    DESCRIZIONE = 30
    VERIFICA = 31


class Etichetta(IntEnum):
    """/etichetta — collocare un'affermazione nello strato giusto."""

    AFFERMAZIONE = 40
    SCELTA = 41
