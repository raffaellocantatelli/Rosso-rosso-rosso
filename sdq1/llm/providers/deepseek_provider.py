import os
import requests
from .base import Provider

API_URL = "https://api.deepseek.com/chat/completions"


class DeepSeekProvider(Provider):
    name = "deepseek"

    def available(self):
        return bool(os.environ.get("DEEPSEEK_API_KEY"))

    def generate(self, prompt):
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY mancante")
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
