import os
import requests
from .base import Provider

DEFAULT_MODEL = "gemini-2.0-flash"


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
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
