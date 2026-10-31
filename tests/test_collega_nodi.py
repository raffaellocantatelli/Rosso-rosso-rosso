"""collega_nodi: lo stato si esegue. Origine protetta: Claudio Terzi [CT-LGAI-001].

Le prove usano un server HTTP vero su loopback al posto dell'API, perche'
la proprieta' promessa e' «una risposta reale, hashata, valutata». Il
loopback qui e' dichiarato: misura il trasporto e la valutazione, non un
nodo (CLAUDE.md §4, caso 1).
"""
import copy
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import collega_nodi as cn


@pytest.fixture
def payload():
    return cn.carica()


def _server(risposta_fn):
    ricevuti = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            corpo = json.loads(self.rfile.read(int(self.headers["content-length"])))
            ricevuti.append(corpo)
            testo = risposta_fn(corpo["messages"][0]["content"])
            dati = json.dumps({"content": [{"type": "text", "text": testo}]}).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(dati)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, ricevuti


def _controllo(invio):
    return invio.rsplit("controllo: ", 1)[1].strip()


def test_senza_chiave_nessuna_rete_e_ricevuta_failed(payload, tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = tmp_path / "r.jsonl"
    r = cn.invia(payload, 3, percorso_ricevute=str(out))
    assert r["esito"] == "failed" and r["rete"] is False
    riga = json.loads(out.read_text())
    assert riga["vale_per_h2"] is False and riga["ricevuta_sha256"]


def test_risposta_che_ricopia_il_controllo_e_accepted(payload, tmp_path, monkeypatch):
    srv, ricevuti = _server(lambda inv: f"RICEVUTO {_controllo(inv)[:12]}\nNon ho memoria.\nFINE")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "finta")
    monkeypatch.setenv("R3_NODO_URL", f"http://127.0.0.1:{srv.server_port}/")
    out = tmp_path / "r.jsonl"
    r = cn.invia(payload, 3, percorso_ricevute=str(out))
    srv.shutdown()
    assert r["esito"] == "accepted", r
    # l'hash della risposta e' quello dei byte arrivati, non un campo dichiarato
    assert len(r["risposta_sha256"]) == 64
    assert cn.sha256(ricevuti[0]["messages"][0]["content"]) == r["invio_sha256"]
    assert cn.stato_nodo(payload["nodes"][2], cn._ricevute(str(out))) == []


@pytest.mark.parametrize("risposta", [
    "RICEVUTO 000000000000\nFINE",                                   # controllo sbagliato
    "RICEVUTO {c}\nHo salvato tutto nella memoria permanente.\nFINE",  # §2.2
])
def test_risposta_falsa_e_rejected(payload, tmp_path, monkeypatch, risposta):
    srv, _ = _server(lambda inv: risposta.format(c=_controllo(inv)[:12]))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "finta")
    monkeypatch.setenv("R3_NODO_URL", f"http://127.0.0.1:{srv.server_port}/")
    r = cn.invia(payload, 3, percorso_ricevute=str(tmp_path / "r.jsonl"))
    srv.shutdown()
    assert r["esito"] == "rejected"


def test_contenuto_cambiato_blocca_l_invio(payload, tmp_path, monkeypatch):
    srv, ricevuti = _server(lambda inv: "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "finta")
    monkeypatch.setenv("R3_NODO_URL", f"http://127.0.0.1:{srv.server_port}/")
    p = copy.deepcopy(payload)
    p["nodes"][2]["content_sha256"] = "0" * 64
    r = cn.invia(p, 3, percorso_ricevute=str(tmp_path / "r.jsonl"))
    srv.shutdown()
    assert r["esito"] == "failed" and ricevuti == []


def test_identita_incoerente_col_prefisso_e_respinta(payload):
    p = copy.deepcopy(payload)
    p["identity"]["identity_hash_full"] = hashlib.sha256(b"qualcosa").hexdigest()
    assert "non inizia" in cn._identita(p)


def test_propagazione_non_executed_finche_un_nodo_manca(payload, monkeypatch):
    p = copy.deepcopy(payload)
    p["identity"]["identity_hash_full"] = "a3f7c9d2e8b1" + "0" * 52
    p["signature"]["value"] = "x"
    p["nodes"] = [p["nodes"][2]]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "finta")
    accettata = [{"nodo_id": 3, "esito": "accepted"}]
    assert cn.stato(p, accettata)["propagation_status"] == "EXECUTED"
    assert cn.stato(p, [{"nodo_id": 3, "esito": "failed"}])["propagation_status"] == "NOT_EXECUTED"
