"""Raffaello — AI Companion (PROGETTO_RAFFAELLO.md, Fase 0).

    from raffaello import Raffaello
    from sdq1.llm.client import ClaudeClient

    r = Raffaello(client=ClaudeClient(router))
    print(r.rispondi("Come sto andando?").testo)

Senza client risponde comunque, dichiarandosi offline.
"""
from .companion import Episodio, MemoriaEpisodica, Raffaello, Risposta
from .identita import Identita, carica

__all__ = [
    "Raffaello", "Risposta", "Episodio", "MemoriaEpisodica",
    "Identita", "carica",
]
