"""Il Core si accende senza una chiave dell'autore. Origine protetta: Claudio Terzi [CT-LGAI-001].

Cosa promettono queste prove, e come (CLAUDE.md §7-bis):

- «il Core pensa attraverso GitHub Models» -> una richiesta HTTP vera a un
  server vero, e il testo che torna e' quello che il server ha mandato;
- «il daily lo usa» -> `python -m sdq1 --daily` lanciato come processo, come
  lo lancia la Action, non una funzione chiamata in fila;
- «un token qualunque non lo accende» -> zero richieste arrivate al server.

Il server e' su loopback ed e' dichiarato: misura il trasporto, la scelta del
modello e cosa finisce nel file. NON misura che GitHub risponda: quello lo
dice solo una run della Action, ed e' scritto in PROSSIMO_PASSO.md come
previsione, non come fatto.
"""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from sdq1 import daily as daily_mod
from sdq1.llm.router import Router

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = "ghs_prova_NON_e_un_token_vero_0123456789"
PENSIERO = (
    "RECUPERATO: questa frase l'ha scritta il server di prova, non lo Stub. "
    "Contatti registrati: zero."
)
CHIAVI_ALTRUI = (
    "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY",
    "GITHUB_MODELS_TOKEN", "GITHUB_MODELS_MODEL", "GITHUB_TOKEN",
)


class _Finto:
    """Un endpoint chat-completions vero su loopback, con un comportamento per modello."""

    def __init__(self):
        self.richieste = []
        self.comportamento = lambda modello, intestazioni: (200, PENSIERO)
        esterno = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                corpo = json.loads(self.rfile.read(int(self.headers["content-length"])))
                esterno.richieste.append({"intestazioni": dict(self.headers), "corpo": corpo})
                stato, testo = esterno.comportamento(corpo.get("model"), self.headers)
                if stato == 200:
                    dati = json.dumps({"choices": [{"message": {"content": testo}}]}).encode()
                else:
                    dati = str(testo).encode()
                self.send_response(stato)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(dati)

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/inference/chat/completions"

    def chiudi(self):
        self.srv.shutdown()


@pytest.fixture
def finto():
    f = _Finto()
    yield f
    f.chiudi()


@pytest.fixture
def ambiente(monkeypatch, finto):
    """Nessuna chiave altrui, Ollama irraggiungibile, loopback fuori dal proxy."""
    for nome in CHIAVI_ALTRUI:
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.setenv("GITHUB_MODELS_URL", finto.url)
    return monkeypatch


def test_il_core_pensa_attraverso_github_models(ambiente, finto):
    ambiente.setenv("GITHUB_MODELS_TOKEN", TOKEN)
    router = Router()

    assert router.provider_reali_disponibili() == ["github_models"]
    testo, chi = router.generate("che giorno e'?", profile="default")

    assert testo == PENSIERO
    # Chi ha pensato, col nome del modello: non «github_models» e basta.
    assert chi == "github_models:openai/gpt-4.1"
    assert len(finto.richieste) == 1
    r = finto.richieste[0]
    assert r["intestazioni"]["Authorization"] == f"Bearer {TOKEN}"
    assert r["corpo"]["model"] == "openai/gpt-4.1"
    assert r["corpo"]["messages"] == [{"role": "user", "content": "che giorno e'?"}]


def test_un_github_token_qualunque_non_accende_il_core(ambiente, finto):
    """Un GITHUB_TOKEN presente per altri motivi non e' un Core acceso."""
    ambiente.setenv("GITHUB_TOKEN", TOKEN)
    router = Router()

    assert router.provider_reali_disponibili() == []
    with pytest.raises(RuntimeError):
        router.generate("che giorno e'?", profile="default")
    assert finto.richieste == []  # niente e' partito


def test_modello_scomparso_si_passa_al_successivo(ambiente, finto):
    ambiente.setenv("GITHUB_MODELS_TOKEN", TOKEN)
    finto.comportamento = lambda modello, h: (
        (404, '{"error":{"code":"unknown_model"}}') if modello == "openai/gpt-4.1" else (200, PENSIERO)
    )

    testo, chi = Router().generate("prova", profile="default")

    assert testo == PENSIERO
    assert chi == "github_models:openai/gpt-4o"
    assert [r["corpo"]["model"] for r in finto.richieste] == ["openai/gpt-4.1", "openai/gpt-4o"]


def test_risposta_vuota_non_e_pensiero(ambiente, finto):
    """Un 200 con niente dentro non deve diventare un daily senza banner."""
    ambiente.setenv("GITHUB_MODELS_TOKEN", TOKEN)
    finto.comportamento = lambda modello, h: (200, "   \n")

    with pytest.raises(RuntimeError) as exc:
        Router().generate("prova", profile="default")

    assert "risposta vuota" in str(exc.value)
    assert len(finto.richieste) == 3  # li ha provati tutti, nessuno ha pensato


def test_il_token_non_finisce_nel_messaggio_d_errore(ambiente, finto):
    """Il log della Action e' pubblico: un server che ripete il token non deve farlo uscire."""
    ambiente.setenv("GITHUB_MODELS_TOKEN", TOKEN)
    finto.comportamento = lambda modello, h: (401, f"bad credentials: {h['Authorization']}")

    with pytest.raises(RuntimeError) as exc:
        Router().providers["github_models"].generate("prova")

    assert "HTTP 401" in str(exc.value)  # il perche' resta leggibile
    assert TOKEN not in str(exc.value)


def test_il_modello_si_puo_scegliere(ambiente, finto):
    ambiente.setenv("GITHUB_MODELS_TOKEN", TOKEN)
    ambiente.setenv("GITHUB_MODELS_MODEL", "mistral-ai/altro, openai/gpt-4o-mini")

    _, chi = Router().generate("prova", profile="economia")

    assert chi == "github_models:mistral-ai/altro"
    assert finto.richieste[0]["corpo"]["model"] == "mistral-ai/altro"


def test_il_daily_conta_il_provider_nuovo_fra_i_reali(tmp_path, monkeypatch):
    """`raccogli_fatti` aveva i nomi dei provider scritti a mano: un giorno
    pensato da github_models sarebbe stato contato come «senza provider reale»,
    e il modello l'avrebbe letto nei DATI del giorno dopo."""
    def riga(acceso):
        return json.dumps({"data_iso": "2026-11-13T07:00:00Z", "providers": {
            "anthropic": {"disponibile": False}, "gemini": {"disponibile": False},
            "deepseek": {"disponibile": False}, "ollama": {"disponibile": False},
            "github_models": {"disponibile": acceso}, "stub": {"disponibile": True},
        }})
    (tmp_path / "health_log.jsonl").write_text(riga(True) + "\n" + riga(False) + "\n", encoding="utf-8")
    monkeypatch.setattr(daily_mod, "OUTPUT", str(tmp_path))

    health = daily_mod.raccogli_fatti()["health"]

    assert health["rilevazioni_totali"] == 2
    assert health["rilevazioni_senza_provider_reale"] == 1


# --- come lo lancia la Action: un processo, non una funzione ---------------

def _sdq1(finto, *argomenti, token=None):
    env = {k: v for k, v in os.environ.items() if k not in CHIAVI_ALTRUI}
    # Stringa vuota, non assente: un `.env` dell'autore con una chiave vera
    # non deve poter trasformare questa prova in una chiamata a pagamento.
    env.update({nome: "" for nome in CHIAVI_ALTRUI})
    env.update({
        "OLLAMA_BASE_URL": "http://127.0.0.1:9/v1",
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        "GITHUB_MODELS_URL": finto.url,
    })
    if token:
        env["GITHUB_MODELS_TOKEN"] = token
    return subprocess.run(
        [sys.executable, "-m", "sdq1", *argomenti],
        cwd=RADICE, env=env, capture_output=True, text=True, timeout=120,
    )


def test_il_daily_come_processo_e_pensato_e_dice_da_chi(finto):
    esito = _sdq1(finto, "--daily", token=TOKEN)

    assert esito.returncode == 0, esito.stderr
    assert PENSIERO in esito.stdout
    assert "IL CORE È SPENTO" not in esito.stdout
    # Sta nel file (stdout), non solo nel log: il verbale dice chi lo ha scritto.
    assert "[pensato da: github_models:openai/gpt-4.1 | profilo: default]" in esito.stdout
    # E al modello sono arrivati i DATI, non una frase vuota.
    assert "contatti_registrati" in finto.richieste[0]["corpo"]["messages"][0]["content"]


def test_senza_token_il_daily_fallisce_invece_di_fingere(finto):
    esito = _sdq1(finto, "--daily")

    assert esito.returncode == 2
    assert esito.stdout.strip() == ""
    assert finto.richieste == []


def test_check_dice_acceso_solo_col_token(finto):
    assert _sdq1(finto, "--check").returncode == 1
    acceso = _sdq1(finto, "--check", token=TOKEN)
    assert acceso.returncode == 0
    assert "CORE ACCESO" in acceso.stdout and "github_models" in acceso.stdout
