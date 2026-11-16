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
    """Un modello aperto che gira sulla macchina stessa: nessuna chiave,
    nessun fornitore. E' il provider del profilo `locale`, e dal 16/11/2026
    quello che il daily automatico usa quando nei secrets non c'e' niente.

    Due provenienze, fuse il 16/11/2026 (CLAUDE.md §7-bis: un canone operativo,
    le provenienze preservate):
    - dal ramo `omniroute-3851-candidate-a` (31/10): la scelta fra i modelli
      davvero installati, l'API nativa di Ollama, il thinking spento per difetto;
    - dal ramo `rrr-onda-verification` (13/11): una risposta vuota non e'
      pensiero, e l'etichetta dice quale modello ha risposto.
    """

    name = "ollama"

    def __init__(self):
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        self.root = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
        self._modello = None
        self.ultima_etichetta = None

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
        """Acceso vuol dire che c'e' un modello da usare, non che un server
        risponde: un Ollama senza modelli non puo' pensare."""
        try:
            return self.modello() is not None
        except (requests.RequestException, ValueError):
            return False

    def _pensato(self, testo, model):
        # Un 200 con niente dentro non e' pensiero. Se passasse, il daily
        # uscirebbe vuoto e SENZA banner: lo Stub rientrato dalla finestra.
        if not testo or not testo.strip():
            raise RuntimeError(f"risposta vuota dal modello {model}")
        # Quale modello ha pensato: un 4 miliardi di parametri su CPU e un
        # modello di frontiera non sono la stessa fonte, e il verbale lo dice.
        self.ultima_etichetta = f"{self.name}:{model}"
        return testo

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
            return self._pensato(native.json()["message"]["content"], model)

        # Fallback per server/proxy che espongono solo l'API OpenAI-compatible.
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json={"model": model, "messages": messages},
            timeout=timeout,
        )
        resp.raise_for_status()
        return self._pensato(resp.json()["choices"][0]["message"]["content"], model)
