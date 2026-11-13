"""GitHub Models — il provider che non chiede una chiave all'autore.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Perche' esiste
--------------
Dal 02/09 al 13/11/2026 il daily automatico ha prodotto Stub perche' nessuna
chiave e' mai arrivata nei secrets della Action. Per 72 giorni il progetto ha
aspettato un gesto che non e' avvenuto. Dentro una GitHub Action, pero', un
token esiste gia': `GITHUB_TOKEN`, che con `permissions: models: read` puo'
interrogare GitHub Models. Nessun secret da aggiungere, nessun costo.

Cosa NON fa
-----------
- Non si accende da solo dove trova un `GITHUB_TOKEN` qualunque: legge solo
  `GITHUB_MODELS_TOKEN`, che il workflow imposta apposta. Un token presente
  per altri motivi (Codespaces, una sessione di un nodo) non deve far
  risultare «Core acceso» un ambiente che non puo' pensare.
- Non considera pensiero una risposta vuota: la tratta come un fallimento e
  passa al modello successivo. Un daily vuoto senza banner sarebbe lo Stub
  rientrato dalla finestra.
- Non nasconde chi ha pensato: `ultima_etichetta` porta il nome del modello,
  e il router la restituisce al posto del solo nome del provider.

Configurazione (tutta opzionale, tranne il token):
    GITHUB_MODELS_TOKEN   il token; nella Action e' ${{ secrets.GITHUB_TOKEN }}
    GITHUB_MODELS_MODEL   uno o piu' modelli separati da virgola, in ordine
    GITHUB_MODELS_URL     endpoint (serve alle prove, che usano un server vero)
"""
import os

import requests

from .base import Provider, timeout_richiesta

API_URL = "https://models.github.ai/inference/chat/completions"
VARIABILE_TOKEN = "GITHUB_MODELS_TOKEN"

#: In ordine di preferenza. Un catalogo cambia: se il primo non esiste piu',
#: si prova il successivo invece di spegnere il Core per un nome scaduto.
MODELLI_PREDEFINITI = ("openai/gpt-4.1", "openai/gpt-4o", "openai/gpt-4o-mini")


class GitHubModelsProvider(Provider):
    name = "github_models"

    def __init__(self):
        self.ultima_etichetta = None

    def available(self):
        return bool(os.environ.get(VARIABILE_TOKEN))

    @staticmethod
    def modelli():
        grezzo = os.environ.get("GITHUB_MODELS_MODEL", "")
        scelti = [m.strip() for m in grezzo.split(",") if m.strip()]
        return scelti or list(MODELLI_PREDEFINITI)

    def generate(self, prompt):
        token = os.environ.get(VARIABILE_TOKEN)
        if not token:
            raise RuntimeError(f"{VARIABILE_TOKEN} mancante")
        url = os.environ.get("GITHUB_MODELS_URL", API_URL)

        errori = []
        for modello in self.modelli():
            try:
                resp = requests.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                    },
                    json={"model": modello, "messages": [{"role": "user", "content": prompt}]},
                    timeout=timeout_richiesta(),
                )
                if resp.status_code != 200:
                    # Il corpo dice PERCHE' (modello sconosciuto, permesso
                    # mancante, limite superato): senza, dal log della Action
                    # si puo' solo indovinare. Mai il token, pero'.
                    corpo = resp.text[:300].replace(token, f"<{VARIABILE_TOKEN} oscurata>")
                    raise RuntimeError(f"HTTP {resp.status_code}: {corpo}")
                testo = resp.json()["choices"][0]["message"]["content"]
                if not testo or not testo.strip():
                    raise RuntimeError("risposta vuota")
            except Exception as exc:  # questo modello no: si prova il prossimo
                errori.append(f"{modello} -> {exc}")
                continue
            self.ultima_etichetta = f"{self.name}:{modello}"
            return testo

        raise RuntimeError("nessun modello ha risposto — " + " | ".join(errori))
