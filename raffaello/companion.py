"""Raffaello — AI Companion. Fase 0 di PROGETTO_RAFFAELLO.md.

Quello che esisteva in `lgai_core/raffaello.py` è il coach LGAI: ogni metodo
prende `PlayerStats` e risponde da template fissi, senza router né memoria.
Resta dov'è e continua a funzionare. Questo modulo è l'altra cosa che il
documento fondativo descrive: la voce del sistema, che parla attraverso il
router SDQ-1 e ricorda gli episodi.

Fase 0 copre classe funzionante, integrazione col router e memoria
in-memory. La persistenza su R3∞ è Fase 1 e qui non c'è: `MemoriaEpisodica`
espone `esporta()` proprio perché quel passaggio possa avvenire senza
riscrivere il companion.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from .identita import Identita, carica

MAX_EPISODI_RICHIAMATI = 3
SOGLIA_RICHIAMO = 0.35


@dataclass
class Episodio:
    messaggio: str
    risposta: str
    data: str
    provider: str | None = None


@dataclass
class Risposta:
    """Una risposta e la sua provenienza.

    `via_api=False` non è un dettaglio interno: significa che il testo non
    viene da un modello, e chi legge ha diritto di saperlo.
    """
    testo: str
    via_api: bool
    provider: str | None = None
    episodi_richiamati: list[Episodio] = field(default_factory=list)

    @property
    def offline(self) -> bool:
        return not self.via_api


class MemoriaEpisodica:
    """Ricordi con data, cercabili per similarità.

    Se `MemoriaVettoriale` di sdq1 è disponibile la usa; altrimenti ricade
    su una scansione lineare per sottoinsieme di parole. Il fallback serve a
    non legare l'esistenza del companion alla presenza di jax/numpy.
    """

    def __init__(self, backend="auto"):
        self._episodi: list[Episodio] = []
        if backend == "auto":
            try:
                from sdq1.memory.store import MemoriaVettoriale
                backend = MemoriaVettoriale(soglia_similarita=SOGLIA_RICHIAMO)
            except ImportError:
                backend = None
        # backend=None è una scelta esplicita (ricerca lineare), distinta da
        # "auto": senza questa distinzione non si può disattivare il backend.
        self._backend = backend

    def salva(self, episodio: Episodio) -> None:
        self._episodi.append(episodio)
        if self._backend is not None:
            self._backend.aggiungi(
                episodio.messaggio,
                {"indice": len(self._episodi) - 1, "data": episodio.data},
            )

    def cerca(self, query: str, k: int = MAX_EPISODI_RICHIAMATI) -> list[Episodio]:
        if not self._episodi:
            return []
        if self._backend is not None:
            trovati = []
            for r in self._backend.cerca(query, k=k, soglia=SOGLIA_RICHIAMO):
                indice = r.ricordo.metadata.get("indice")
                if indice is not None and indice < len(self._episodi):
                    trovati.append(self._episodi[indice])
            return trovati
        return self._cerca_lineare(query, k)

    def _cerca_lineare(self, query: str, k: int) -> list[Episodio]:
        parole = set(query.lower().split())
        if not parole:
            return []
        punteggi = []
        for ep in self._episodi:
            comuni = parole & set(ep.messaggio.lower().split())
            if comuni:
                punteggi.append((len(comuni) / len(parole), ep))
        punteggi.sort(key=lambda x: x[0], reverse=True)
        return [ep for punteggio, ep in punteggi[:k] if punteggio >= SOGLIA_RICHIAMO]

    def del_giorno(self, giorno: str | date) -> list[Episodio]:
        giorno = giorno.isoformat() if isinstance(giorno, date) else giorno
        return [e for e in self._episodi if e.data == giorno]

    def esporta(self) -> list[dict[str, Any]]:
        """Serializza gli episodi — punto di aggancio per R3∞ (Fase 1)."""
        return [vars(e) for e in self._episodi]

    def __len__(self) -> int:
        return len(self._episodi)


class Raffaello:
    """La voce del sistema.

    `client` è un `sdq1.llm.client.ClaudeClient` (o qualsiasi oggetto con
    `.completa(sistema, utente)`). Senza client il companion non tace e non
    finge: risponde dichiarando di essere offline.
    """

    def __init__(self, client=None, memoria: MemoriaEpisodica | None = None,
                 identita: Identita | None = None):
        self.identita = identita or carica()
        self.memoria = memoria if memoria is not None else MemoriaEpisodica()
        self.client = client

    def rispondi(self, messaggio: str, contesto: dict[str, Any] | None = None) -> Risposta:
        messaggio = (messaggio or "").strip()
        if not messaggio:
            return Risposta(
                testo="Non mi hai chiesto niente. Dimmi da dove partiamo.",
                via_api=False,
            )

        episodi = self.memoria.cerca(messaggio)
        risposta = self._genera(messaggio, episodi, contesto or {})

        self.memoria.salva(Episodio(
            messaggio=messaggio,
            risposta=risposta.testo,
            data=datetime.now(timezone.utc).date().isoformat(),
            provider=risposta.provider,
        ))
        risposta.episodi_richiamati = episodi
        return risposta

    def _genera(self, messaggio, episodi, contesto) -> Risposta:
        if self.client is None or not getattr(self.client, "disponibile", lambda: True)():
            return self._offline(messaggio, episodi)

        esito = self.client.completa(
            sistema=self.identita.prompt_sistema(),
            utente=self._prompt_utente(messaggio, episodi, contesto),
        )
        testo = (getattr(esito, "testo", "") or "").strip()
        if not testo:
            return self._offline(messaggio, episodi)

        return Risposta(
            testo=testo,
            via_api=getattr(esito, "via_api", True),
            provider=getattr(esito, "provider", None),
        )

    def _prompt_utente(self, messaggio, episodi, contesto) -> str:
        righe = [f"Messaggio: {messaggio}"]
        if episodi:
            righe.append("")
            righe.append("Episodi precedenti con questa persona:")
            for ep in episodi:
                righe.append(f"  [{ep.data}] ha detto: {ep.messaggio}")
                righe.append(f"             hai risposto: {ep.risposta[:160]}")
            righe.append("Se ti servono, usali. Non citarli per dimostrare di ricordare.")
        if contesto:
            righe.append("")
            righe.append("Dati di contesto:")
            for chiave, valore in contesto.items():
                righe.append(f"  {chiave}: {valore}")
        return "\n".join(righe)

    def _offline(self, messaggio, episodi) -> Risposta:
        """Nessun provider: si dichiara, non si simula.

        Il sistema preferisce dire "non ho un modello" piuttosto che
        produrre una risposta che sembri generata quando non lo è.
        """
        righe = [
            f"[{self.identita.nome} · offline — nessun provider LLM raggiungibile]",
            "",
            f"Ho ricevuto: {messaggio}",
        ]
        if episodi:
            righe.append("")
            righe.append(f"Nella memoria trovo {len(episodi)} episodio/i collegato/i:")
            for ep in episodi:
                righe.append(f"  [{ep.data}] {ep.messaggio}")
        righe.append("")
        righe.append(
            "Non ho un modello con cui elaborare una risposta: configura una "
            "chiave API in .env oppure un'istanza Ollama locale. Questo testo "
            "è strutturale, non è output di un modello linguistico."
        )
        return Risposta(testo="\n".join(righe), via_api=False, provider=None)
