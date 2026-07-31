from .base import Provider


class StubProvider(Provider):
    """Ultima rete di sicurezza: sempre disponibile, non chiama nessuna API.

    Non finge di essere un modello linguistico: restituisce, etichettato
    con chiarezza, il contesto che la pipeline ha già costruito.
    """

    name = "stub"

    def available(self):
        return True

    def generate(self, prompt):
        return (
            "[SDQ-1 · modalità offline/stub — nessun provider LLM esterno disponibile]\n\n"
            f"{prompt}\n\n"
            "Nota: risposta strutturale generata localmente (Stub), non output di un modello "
            "linguistico. Configura almeno una chiave API in .env, oppure un'istanza Ollama "
            "locale, per ottenere risposte generate da un vero LLM."
        )
