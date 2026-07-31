"""Router multi-provider con cascata, circuit breaker, cache e hedging."""
import threading

from .providers.anthropic_provider import AnthropicProvider
from .providers.gemini_provider import GeminiProvider
from .providers.deepseek_provider import DeepSeekProvider
from .providers.ollama_provider import OllamaProvider
from .providers.stub_provider import StubProvider
from .circuit_breaker import CircuitBreaker
from .cache import ResponseCache

PROFILES = {
    "default": ["anthropic", "gemini", "deepseek", "stub"],
    "economia": ["gemini", "deepseek", "stub"],
    "locale": ["ollama", "gemini", "stub"],
    "no-api": ["stub"],
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
                errors.append(f"{name}: {exc}")

        raise RuntimeError("Tutti i provider della cascata hanno fallito: " + "; ".join(errors))

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
