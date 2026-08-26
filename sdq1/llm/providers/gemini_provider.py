import os
import requests
from .base import Provider, timeout_richiesta

# gemini-2.0-flash e' stato ritirato: l'API rispondeva 404 indicando il
# sostituto. Verificato alla fonte il 24/08/2026. Sovrascrivibile con GEMINI_MODEL.
DEFAULT_MODEL = "gemini-3.6-flash"


class GeminiProvider(Provider):
    name = "gemini"

    def available(self):
        return bool(os.environ.get("GOOGLE_API_KEY"))

    def generate(self, prompt):
        key = os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY mancante")
        model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        # La chiave viaggia in header, non nella query string. Prima stava
        # nella query: il 26/08/2026 un 429 ha stampato l'URL intero —
        # chiave compresa — in stderr, e da li' finiva nell'output catturato dal
        # verificatore, che questo repository committa in PUBBLICO. Non e'
        # uscita per un troncamento a 800 caratteri: fortuna, non progetto.
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        resp = requests.post(
            url,
            headers={"x-goog-api-key": key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=timeout_richiesta(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
