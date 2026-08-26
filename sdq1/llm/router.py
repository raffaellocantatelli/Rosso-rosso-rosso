"""Router multi-provider con cascata, circuit breaker, cache e hedging."""
import os
import threading

#: Variabili che contengono credenziali. Il loro valore non deve comparire in
#: nessun messaggio d'errore: i messaggi finiscono in stderr, nei log, e
#: nell'output che il verificatore deposita in un repository pubblico.
VARIABILI_SEGRETE = (
    "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY", "OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN",
)


def oscura_segreti(testo):
    """Sostituisce ogni credenziale presente nell'ambiente con un segnaposto.

    Rete di sicurezza, non prima difesa: la prima difesa e' non mettere mai
    una chiave in un URL. Questa serve per il giorno in cui un provider nuovo
    se ne dimentica.
    """
    testo = str(testo)
    for nome in VARIABILI_SEGRETE:
        valore = os.environ.get(nome)
        if valore and len(valore) >= 8 and valore in testo:
            testo = testo.replace(valore, f"<{nome} oscurata>")
    return testo

from .providers.anthropic_provider import AnthropicProvider
from .providers.gemini_provider import GeminiProvider
from .providers.deepseek_provider import DeepSeekProvider
from .providers.ollama_provider import OllamaProvider
from .providers.stub_provider import StubProvider
from .circuit_breaker import CircuitBreaker
from .cache import ResponseCache

# Lo stub NON compare nelle cascate reali: se ci fosse, ogni profilo
# riuscirebbe sempre e il fallback esplicito (--economia, --no-api) non
# verrebbe mai raggiunto. Chi vuole lo stub lo chiede con --no-api.
PROFILES = {
    "default": ["anthropic", "gemini", "deepseek"],
    "economia": ["gemini", "deepseek"],
    "locale": ["ollama", "gemini"],
    "no-api": ["stub"],
}

# Provider che parlano davvero con un modello linguistico.
REAL_PROVIDERS = ("anthropic", "gemini", "deepseek", "ollama")

# Come si accende ciascun provider, per la diagnostica di `--check`.
COME_ATTIVARE = {
    "anthropic": "ANTHROPIC_API_KEY in .env (o nei secrets della Action)",
    "gemini": "GOOGLE_API_KEY in .env (o nei secrets della Action)",
    "deepseek": "DEEPSEEK_API_KEY in .env (o nei secrets della Action)",
    "ollama": "un'istanza Ollama in ascolto su OLLAMA_BASE_URL (default http://localhost:11434/v1)",
}


class Router:
    def __init__(self):
        self.providers = {
            "anthropic": AnthropicProvider(),
            "gemini": GeminiProvider(),
            "deepseek": DeepSeekProvider(),
            "ollama": OllamaProvider(),
            "stub": StubProvider(),
        }
        self.breaker = CircuitBreaker()
        self.cache = ResponseCache(ttl_seconds=300)

    def cascade(self, profile):
        return PROFILES.get(profile, PROFILES["default"])

    def stato_provider(self):
        """Disponibilità di ogni provider, per la diagnostica e l'health check."""
        return {name: p.available() for name, p in self.providers.items()}

    def provider_reali_disponibili(self):
        """Provider che possono davvero generare testo con un modello."""
        return [n for n in REAL_PROVIDERS if self.providers[n].available()]

    def generate(self, prompt, profile="default", hedge=False):
        cached = self.cache.get(prompt, profile)
        if cached is not None:
            text, provider = cached
            return text, f"{provider}(cache)"

        order = self.cascade(profile)

        if hedge and len(order) >= 2:
            hedged = self._hedge(prompt, order[:2])
            if hedged:
                self.cache.set(prompt, profile, hedged)
                return hedged

        errors = []
        for name in order:
            provider = self.providers[name]
            if self.breaker.is_open(name):
                continue
            if not provider.available():
                continue
            try:
                text = provider.generate(prompt)
                self.breaker.record_success(name)
                self.cache.set(prompt, profile, (text, name))
                return text, name
            except Exception as exc:  # provider non affidabile: registra e prova il prossimo
                self.breaker.record_failure(name)
                errors.append(oscura_segreti(f"{name}: {exc}"))

        if errors:
            raise RuntimeError(
                f"Tutti i provider del profilo '{profile}' hanno fallito: " + "; ".join(errors)
            )
        raise RuntimeError(
            f"Nessun provider del profilo '{profile}' è disponibile "
            f"({', '.join(order)}). Il Core non può generare. "
            "Esegui `python -m sdq1 --check` per sapere cosa manca."
        )

    def _hedge(self, prompt, names):
        results = {}

        def worker(name):
            provider = self.providers[name]
            if self.breaker.is_open(name) or not provider.available():
                return
            try:
                text = provider.generate(prompt)
                results.setdefault(name, text)
                self.breaker.record_success(name)
            except Exception:
                self.breaker.record_failure(name)

        threads = [threading.Thread(target=worker, args=(n,)) for n in names]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        for name in names:
            if name in results:
                return results[name], name
        return None
