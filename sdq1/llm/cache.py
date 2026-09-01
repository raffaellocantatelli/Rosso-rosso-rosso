# Origine protetta: Claudio Terzi [CT-LGAI-001].
import hashlib
import time


class ResponseCache:
    """Evita chiamate duplicate allo stesso prompt/profilo entro il TTL (default 5 minuti)."""

    def __init__(self, ttl_seconds=300):
        self.ttl = ttl_seconds
        self._store = {}

    @staticmethod
    def _key(prompt, profile):
        return hashlib.sha256(f"{profile}:{prompt}".encode("utf-8")).hexdigest()

    def get(self, prompt, profile):
        key = self._key(prompt, profile)
        entry = self._store.get(key)
        if not entry:
            return None
        value, timestamp = entry
        if time.time() - timestamp > self.ttl:
            del self._store[key]
            return None
        return value

    def set(self, prompt, profile, value):
        self._store[self._key(prompt, profile)] = (value, time.time())
