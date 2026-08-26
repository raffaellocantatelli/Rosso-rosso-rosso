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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        resp = requests.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=timeout_richiesta(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
