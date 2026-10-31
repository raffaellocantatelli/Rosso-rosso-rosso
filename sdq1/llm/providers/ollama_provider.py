import os
import requests
from .base import Provider, timeout_richiesta


# Preferenza generale del nodo locale. I gate pesanti (daily,
# contraddittorio, H5) possono scegliere esplicitamente un modello base più
# rapido senza cambiare l'identità operativa predefinita.
PREFERITI = (
    "raffaello-r3:3b",
    "qwen3.5:4b",
    "seme:4b",
    "raffaello-r3:llama-backup",
    "seme:latest",
)


def scegli_modello(nomi, richiesto=None):
    """Sceglie solo fra modelli realmente installati."""
    nomi = list(nomi)
    if richiesto:
        return richiesto if richiesto in nomi else None
    for nome in PREFERITI:
        if nome in nomi:
            return nome
    return nomi[0] if nomi else None


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(self):
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        self.root = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
        self._modello = None

    def _modelli_installati(self):
        resp = requests.get(f"{self.root}/api/tags", timeout=1.5)
        resp.raise_for_status()
        return [m.get("name") or m.get("model") for m in resp.json().get("models", []) if m.get("name") or m.get("model")]

    def modello(self):
        if self._modello:
            return self._modello
        richiesto = os.environ.get("OLLAMA_MODEL")
        modello = scegli_modello(self._modelli_installati(), richiesto)
        if modello:
            self._modello = modello
        return modello

    def available(self):
        try:
            return self.modello() is not None
        except requests.RequestException:
            return False

    def generate(self, prompt):
        model = self.modello()
        if not model:
            richiesto = os.environ.get("OLLAMA_MODEL")
            if richiesto:
                raise RuntimeError(f"OLLAMA_MODEL={richiesto!r} non è installato")
            raise RuntimeError("Nessun modello Ollama installato")

        timeout = timeout_richiesta()
        messages = [{"role": "user", "content": prompt}]
        thinking = os.environ.get("OLLAMA_THINKING", "").lower() in ("1", "true", "yes", "on")
        options = {}
        if os.environ.get("OLLAMA_NUM_PREDICT"):
            try:
                options["num_predict"] = int(os.environ["OLLAMA_NUM_PREDICT"])
            except ValueError:
                pass

        # L'API nativa è il contratto stabile di Ollama. Per i gate e il daily
        # il thinking esteso è spento per difetto: su CPU può moltiplicare la
        # latenza senza aggiungere evidenza. Si riattiva con OLLAMA_THINKING=1.
        native = requests.post(
            f"{self.root}/api/chat",
            json={"model": model, "messages": messages, "stream": False, "think": thinking, "options": options},
            timeout=timeout,
        )
        if native.status_code != 404:
            native.raise_for_status()
            return native.json()["message"]["content"]

        # Fallback per server/proxy che espongono solo l'API OpenAI-compatible.
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json={"model": model, "messages": messages},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
