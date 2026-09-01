"""Stato condiviso della pipeline SDQ-1.

Gli agenti ricevono questo oggetto e lo mutano in place (condivisione
per puntatore, non per testo serializzato tra uno stadio e l'altro).

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""


class Context:
    def __init__(self, user_input: str):
        self.input = user_input
        self.intent = None
        self.subgoals = []
        self.memory_hits = []
        self.manipulation = {"detected": False, "signals": [], "bisogno_nascosto": None}
        self.draft = None
        self.final = None
        self.provider_used = None
        self.meta = {}
