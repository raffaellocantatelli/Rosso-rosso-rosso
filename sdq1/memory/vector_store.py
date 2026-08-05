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
PRIVATE_RE = re.compile(r"<private>.*?</private>", re.IGNORECASE | re.DOTALL)
REDACTED_MARKER = "[contenuto privato omesso]"
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
    def _redact(text):
        """Rimuove i blocchi <private>...</private> prima della persistenza.

        Il testo originale (non redatto) resta disponibile nel Context per
        la generazione della risposta corrente; solo ciò che viene salvato
        su disco passa da qui.
        """
        redatto = PRIVATE_RE.sub(REDACTED_MARKER, text)
        return redatto if redatto.strip() else REDACTED_MARKER

    @staticmethod
    def _cosine(v1, v2):
        comuni = set(v1) & set(v2)
        dot = sum(v1[t] * v2[t] for t in comuni)
        norm1 = math.sqrt(sum(c * c for c in v1.values()))
        norm2 = math.sqrt(sum(c * c for c in v2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def add(self, input_text, response_text):
        entry = {
            "id": len(self._entries) + 1,
            "input": self._redact(input_text),
            "response": self._redact(response_text),
            "timestamp": time.time(),
        }
        self._entries.append(entry)
        self._save()
        return entry

    def retrieve(self, query, top_k=3, min_score=0.0):
        qv = self._vector(query)
        scored = []
        for entry in self._entries:
            score = self._cosine(qv, self._vector(entry["input"]))
            if score > min_score:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"id": e["id"], "score": round(s, 3), "input": e["input"], "response": e["response"]}
            for s, e in scored[:top_k]
        ]

    def __len__(self):
        return len(self._entries)
