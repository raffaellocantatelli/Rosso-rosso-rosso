import os
import requests
from .base import Provider, timeout_richiesta


class OllamaProvider(Provider):
    """Un modello aperto che gira sulla macchina stessa: nessuna chiave,
    nessun fornitore. E' il provider del profilo `locale`, e dal 13/11/2026
    quello che il daily automatico usa quando nei secrets non c'e' niente.
    """

    name = "ollama"

    def __init__(self):
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.ultima_etichetta = None

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
            timeout=timeout_richiesta(),
        )
        resp.raise_for_status()
        testo = resp.json()["choices"][0]["message"]["content"]
        # Un 200 con niente dentro non e' pensiero. Se passasse, il daily
        # uscirebbe vuoto e SENZA banner: lo Stub rientrato dalla finestra.
        if not testo or not testo.strip():
            raise RuntimeError(f"risposta vuota dal modello {model}")
        # Quale modello ha pensato: un 4 miliardi di parametri su CPU e un
        # modello di frontiera non sono la stessa fonte, e il verbale lo dice.
        self.ultima_etichetta = f"{self.name}:{model}"
        return testo
