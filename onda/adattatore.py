"""Adattatore esplicito: dalle funzioni della pipeline SDQ-1 a servizi ONDA.

RAFFA-001, MEMO-002 e SENTIN-004 nella pipeline sono funzioni `run(ctx)`
chiamate in sequenza su un `Context` condiviso, dentro un solo processo
(`sdq1/agents/pipeline.py`). Non sono processi e non lo diventano: questo
modulo costruisce per ogni RICHIESTA un `Context` nuovo, chiama **la stessa
funzione** e restituisce soltanto il campo che quella funzione scrive.

Nessuna logica dell'agente è copiata qui. Se `raffa.run` cambia, cambia
anche ciò che RAFFA-001 risponde su ONDA.
"""
import os

from sdq1.agents import memo, raffa, sentin
from sdq1.context import Context
from sdq1.memory.vector_store import DEFAULT_PATH, VectorStore

TESTO_MAX = 4000


def _testo(corpo):
    testo = corpo.get("testo")
    if not isinstance(testo, str) or not testo.strip():
        raise ValueError("corpo.testo deve essere una stringa non vuota")
    if len(testo) > TESTO_MAX:
        raise ValueError(f"corpo.testo oltre {TESTO_MAX} caratteri")
    return testo


def servizio_raffa(corpo):
    ctx = raffa.run(Context(_testo(corpo)))
    return {"intent": ctx.intent}


def servizio_sentin(corpo):
    ctx = sentin.run(Context(_testo(corpo)))
    return {"manipulation": ctx.manipulation}


class _MemoriaSoloLettura:
    """MEMO-002 su ONDA legge e basta.

    La pipeline chiama `memory.add` dopo ogni risposta; il bus no. Un bus
    che scrivesse nella memoria vettoriale farebbe rileggere al sistema il
    proprio traffico come «contesto rilevante» — il loopback di CLAUDE.md §4.
    Il file si rilegge a ogni richiesta, così le memorie aggiunte dalla
    pipeline nel frattempo sono visibili.
    """

    def __init__(self, percorso):
        self.percorso = percorso

    def retrieve(self, query, top_k=3):
        return VectorStore(self.percorso).retrieve(query, top_k=top_k)


def servizio_memo(percorso=None):
    memoria = _MemoriaSoloLettura(percorso or os.environ.get("ONDA_MEMO_STORE", DEFAULT_PATH))

    def servizio(corpo):
        ctx = memo.run(Context(_testo(corpo)), memoria)
        return {"memory_hits": ctx.memory_hits}

    return servizio


def servizio_per(id_nodo):
    """Il servizio reale per un ID. Un ID senza implementazione non parte:
    meglio un errore all'avvio che un agente che sembra vivo e non fa niente."""
    if id_nodo == "RAFFA-001":
        return servizio_raffa
    if id_nodo == "SENTIN-004":
        return servizio_sentin
    if id_nodo == "MEMO-002":
        return servizio_memo()
    raise KeyError(f"nessuna implementazione reale per {id_nodo}")
