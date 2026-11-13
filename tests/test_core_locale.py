"""Il Core si accende senza una chiave dell'autore. Origine protetta: Claudio Terzi [CT-LGAI-001].

Cosa promettono queste prove, e come (CLAUDE.md §7-bis):

- «il daily pensa attraverso un modello locale» -> `python -m sdq1 --daily
  --locale` lanciato come processo, come lo lancia la Action, contro un
  server HTTP vero che parla il protocollo di Ollama;
- «il file dice chi lo ha pensato» -> la riga sta nello stdout del processo,
  che e' cio' che la Action scrive nel file;
- «senza modello non finge» -> codice d'uscita 2 e stdout vuoto.

Il server e' su loopback ed e' dichiarato: misura il trasporto e cosa finisce
nel file. NON misura che un modello vero risponda su un runner di GitHub:
quello lo dice solo una run della Action (PROSSIMO_PASSO.md §2).
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
MODELLO = "modello-di-prova:1b"
PENSIERO = (
    "RECUPERATO: questa frase l'ha scritta il server di prova, non lo Stub. "
    "Contatti registrati: zero."
)
CHIAVI = ("ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY")


class _OllamaFinto:
    """Le due rotte che il provider usa davvero: /api/tags e /v1/chat/completions."""

    def __init__(self):
        self.richieste = []
        self.risposta = PENSIERO
        esterno = self

        class H(BaseHTTPRequestHandler):
            def _manda(self, oggetto):
                dati = json.dumps(oggetto).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(dati)

            def do_GET(self):
                self._manda({"models": []})

            def do_POST(self):
                corpo = json.loads(self.rfile.read(int(self.headers["content-length"])))
                esterno.richieste.append({"percorso": self.path, "corpo": corpo})
                self._manda({"choices": [{"message": {"content": esterno.risposta}}]})

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base_url = f"http://127.0.0.1:{self.srv.server_address[1]}/v1"

    def chiudi(self):
        self.srv.shutdown()


@pytest.fixture
def ollama():
    f = _OllamaFinto()
    yield f
    f.chiudi()


@pytest.fixture
def ambiente(monkeypatch, ollama):
    for nome in CHIAVI:
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.setenv("OLLAMA_BASE_URL", ollama.base_url)
    monkeypatch.setenv("OLLAMA_MODEL", MODELLO)
    return monkeypatch


def test_il_router_dice_quale_modello_ha_pensato(ambiente, ollama):
    router = Router()
    assert router.provider_reali_disponibili() == ["ollama"]

    testo, chi = router.generate("che giorno e'?", profile="locale")

    assert testo == PENSIERO
    assert chi == f"ollama:{MODELLO}"  # non «ollama» e basta
    assert ollama.richieste[0]["percorso"] == "/v1/chat/completions"
    assert ollama.richieste[0]["corpo"]["model"] == MODELLO


def test_risposta_vuota_non_e_pensiero(ambiente, ollama):
    """Un 200 con niente dentro non deve diventare un daily senza banner."""
    ollama.risposta = "  \n"

    with pytest.raises(RuntimeError) as exc:
        Router().generate("prova", profile="locale")

    assert "risposta vuota" in str(exc.value)


def test_il_daily_conta_ogni_provider_che_non_sia_lo_stub(tmp_path, monkeypatch):
    """`raccogli_fatti` aveva i nomi dei provider scritti a mano: un giorno
    pensato da un provider aggiunto dopo sarebbe stato contato come «senza
    provider reale», e il modello l'avrebbe letto nei DATI del giorno dopo."""
    def riga(acceso):
        return json.dumps({"data_iso": "2026-11-13T07:00:00Z", "providers": {
            "anthropic": {"disponibile": False}, "ollama": {"disponibile": False},
            "provider_di_domani": {"disponibile": acceso}, "stub": {"disponibile": True},
        }})
    (tmp_path / "health_log.jsonl").write_text(riga(True) + "\n" + riga(False) + "\n", encoding="utf-8")
    monkeypatch.setattr(daily_mod, "OUTPUT", str(tmp_path))

    health = daily_mod.raccogli_fatti()["health"]

    assert health["rilevazioni_totali"] == 2
    assert health["rilevazioni_senza_provider_reale"] == 1


# --- come lo lancia la Action: un processo, non una funzione ---------------

def _sdq1(*argomenti, base_url):
    env = dict(os.environ)
    # Stringa vuota, non assente: un `.env` dell'autore con una chiave vera
    # non deve poter trasformare questa prova in una chiamata a pagamento.
    env.update({nome: "" for nome in CHIAVI})
    env.update({
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        "OLLAMA_BASE_URL": base_url, "OLLAMA_MODEL": MODELLO,
    })
    return subprocess.run(
        [sys.executable, "-m", "sdq1", *argomenti],
        cwd=RADICE, env=env, capture_output=True, text=True, timeout=120,
    )


def test_il_daily_locale_e_pensato_e_dice_da_chi(ollama):
    esito = _sdq1("--daily", "--locale", base_url=ollama.base_url)

    assert esito.returncode == 0, esito.stderr
    assert PENSIERO in esito.stdout
    assert "IL CORE È SPENTO" not in esito.stdout
    # Sta nello stdout, cioe' nel file: il verbale dice chi lo ha scritto.
    assert f"[pensato da: ollama:{MODELLO} | profilo: locale]" in esito.stdout
    # E al modello sono arrivati i DATI, non una frase vuota.
    assert "contatti_registrati" in ollama.richieste[0]["corpo"]["messages"][0]["content"]


def test_senza_modello_il_daily_locale_fallisce_invece_di_fingere():
    esito = _sdq1("--daily", "--locale", base_url="http://127.0.0.1:9/v1")

    assert esito.returncode == 2
    assert esito.stdout.strip() == ""


def test_lo_stub_si_dichiara_anche_nella_riga_di_chi_ha_pensato():
    esito = _sdq1("--daily", "--no-api", base_url="http://127.0.0.1:9/v1")

    assert esito.returncode == 0
    assert "IL CORE È SPENTO" in esito.stdout
    assert "[pensato da: stub" in esito.stdout


def test_il_daily_predefinito_non_usa_il_locale_di_nascosto(ollama):
    """La cascata `default` e' di chi ha una chiave. Il locale si chiede con
    `--locale`: cosi' il file dice sempre con quale profilo e' stato pensato,
    e una run senza chiavi fallisce al primo passo invece di cambiare fonte
    senza dirlo."""
    esito = _sdq1("--daily", base_url=ollama.base_url)

    assert esito.returncode == 2
    assert ollama.richieste == []
