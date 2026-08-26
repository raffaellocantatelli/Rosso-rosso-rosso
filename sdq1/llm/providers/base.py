class Provider:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def generate(self, prompt: str) -> str:
        raise NotImplementedError


def timeout_richiesta(default=120):
    """Secondi di attesa per una risposta del provider.

    Era 30 in tutti i provider, ed e' troppo poco: con un prompt lungo — un
    dossier di fatti, un contraddittorio — il modello non fa in tempo a
    rispondere e il router lo dichiara morto per un limite nostro, non suo.
    Verificato il 26/08: la prima esecuzione del contraddittore e' fallita
    esattamente cosi'. Sovrascrivibile con LLM_TIMEOUT.
    """
    import os
    try:
        return float(os.environ.get("LLM_TIMEOUT", default))
    except ValueError:
        return float(default)
