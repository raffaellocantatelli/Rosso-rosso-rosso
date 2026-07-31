import os
import requests
from .base import Provider


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(self):
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")

    def available(self):
        try:
            root = self.base_url.rsplit("/v1", 1)[0]
            requests.get(f"{root}/api/tags", timeout=0.5)
            return True
        except requests.RequestException:
            return False

    def generate(self, prompt):
        model = os.environ.get("OLLAMA_MODEL", "llama3")
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
