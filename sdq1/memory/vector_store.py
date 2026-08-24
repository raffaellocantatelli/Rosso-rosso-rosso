"""Vector State Store — memoria persistente basata su similarità coseno.

Nessuna dipendenza esterna: l'embedding è un semplice conteggio di token
(bag-of-words) e la similarità è coseno calcolato a mano. Sufficiente per
far condividere agli agenti "puntatori" a memoria pregressa invece di
ripetere testo.
"""
import json
import math
import os
import re
import time
from collections import Counter

TOKEN_RE = re.compile(r"[a-zàèéìòùA-Z]{3,}")
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "store.json")


class VectorStore:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self._entries = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _vector(text):
        tokens = [t.lower() for t in TOKEN_RE.findall(text)]
        return Counter(tokens)

    @staticmethod
    def _cosine(v1, v2):
        comuni = set(v1) & set(v2)
        dot = sum(v1[t] * v2[t] for t in comuni)
        norm1 = math.sqrt(sum(c * c for c in v1.values()))
        norm2 = math.sqrt(sum(c * c for c in v2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def add(self, input_text, response_text, provider=None):
        """Registra uno scambio. Gli output Stub non entrano mai in memoria.

        Uno Stub non e' un pensiero: e' la dichiarazione che il pensiero non
        e' avvenuto. Memorizzarlo significa che il giorno dopo il sistema lo
        rilegge come "contesto rilevante" e si alimenta del proprio vuoto.
        E' successo per 23 giorni consecutivi.
        """
        if provider and provider.startswith("stub"):
            return None
        entry = {
            "id": len(self._entries) + 1,
            "input": input_text,
            "response": response_text,
            "provider": provider,
            "timestamp": time.time(),
        }
        self._entries.append(entry)
        self._save()
        return entry

    def purga_stub(self):
        """Rimuove le voci che sono output Stub. Restituisce quante ne toglie."""
        prima = len(self._entries)
        self._entries = [
            e for e in self._entries
            if not (
                (e.get("provider") or "").startswith("stub")
                or "modalità offline/stub" in (e.get("response") or "")
            )
        ]
        for nuovo_id, entry in enumerate(self._entries, start=1):
            entry["id"] = nuovo_id
        self._save()
        return prima - len(self._entries)

    def retrieve(self, query, top_k=3):
        qv = self._vector(query)
        scored = []
        for entry in self._entries:
            score = self._cosine(qv, self._vector(entry["input"]))
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"score": round(s, 3), "input": e["input"], "response": e["response"]}
            for s, e in scored[:top_k]
        ]

    def __len__(self):
        return len(self._entries)
