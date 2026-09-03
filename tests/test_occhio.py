"""Prove di occhio. Origine protetta: Claudio Terzi [CT-LGAI-001].

Nessuna di queste prove chiama un modello: girano senza chiavi, nella Action,
sempre. Cio' che non si puo' provare senza un modello — se il riconoscimento
dei titoli sia buono — non viene finto qui: si misura camminando, ed e'
scritto in OCCHIO.md fra le cose ancora UNKNOWN.
"""

import json
import threading
import urllib.request
import urllib.error

import pytest

from occhio import inventario as inv
from occhio import visione as vis
from occhio import server as srv


# --------------------------------------------------------------------------
# identita' degli oggetti
# --------------------------------------------------------------------------

@pytest.mark.parametrize("a,b", [
    ("The Matrix", "MATRIX, THE"),
    ("Il Padrino", "il  padrino"),
    ("Amélie", "Amelie"),
    ("Blade Runner!", "blade-runner"),
])
def test_stessa_chiave(a, b):
    assert inv.chiave("dvd", a) == inv.chiave("dvd", b)


@pytest.mark.parametrize("a,b", [
    ("Rocky 2", "Rocky 3"),          # i numeri distinguono le edizioni
    ("Alien", "Aliens"),
    ("Heat", "Heat"),                 # stesso titolo, tipo diverso -> sotto
])
def test_chiavi_diverse(a, b):
    if a == b:
        assert inv.chiave("dvd", a) != inv.chiave("libro", b)
    else:
        assert inv.chiave("dvd", a) != inv.chiave("dvd", b)


def test_titolo_troppo_corto_non_fa_chiave():
    """Meglio nessuna chiave che una chiave debole: una debole fonde due
    oggetti diversi e il registro perde una voce senza dirlo."""
    assert inv.chiave("dvd", "A") is None
    assert inv.chiave("dvd", "") is None
    assert inv.chiave("dvd", "  -- ") is None


def test_distanza_impronta():
    assert inv.distanza_impronta("ff00ff00ff00ff00", "ff00ff00ff00ff00") == 0
    assert inv.distanza_impronta("ff00ff00ff00ff00", "ff00ff00ff00ff01") == 1
    assert inv.distanza_impronta("abc", None) == 64      # assente != simile
    assert inv.distanza_impronta("nonesa", "nonesa") == 64  # malformata != simile


# --------------------------------------------------------------------------
# il registro
# --------------------------------------------------------------------------

def test_ripasso_non_gonfia(tmp_path):
    r = inv.Inventario(tmp_path / "i.jsonl")
    r.registra("dvd", "The Matrix", "f0e1d2c3b4a59687")
    r.registra("dvd", "MATRIX, THE", "f0e1d2c3b4a59683")
    r.registra("DVD", "the matrix", None)
    assert len(r.voci) == 1
    assert r.voci[0]["avvistamenti"] == 3


def test_stato_viene_dal_file_non_dalla_sessione(tmp_path):
    """Il verde deve sopravvivere al riavvio, altrimenti e' un'impressione."""
    p = tmp_path / "i.jsonl"
    inv.Inventario(p).registra("dvd", "Heat", "1234123412341234")
    assert inv.Inventario(p).riconosci("dvd", "HEAT")[0] == "CATALOGATO"


def test_riconoscimento_per_impronta_senza_titolo(tmp_path):
    r = inv.Inventario(tmp_path / "i.jsonl")
    r.registra("dvd", "Solaris", "0f0f0f0f0f0f0f0f")
    # titolo illeggibile, ma e' visibilmente lo stesso dorso
    stato, voce = r.riconosci("dvd", "", "0f0f0f0f0f0f0f0e")
    assert stato == "RIVISTO" and voce["titolo"] == "Solaris"


def test_impronta_lontana_non_riconosce(tmp_path):
    r = inv.Inventario(tmp_path / "i.jsonl")
    r.registra("dvd", "Solaris", "0000000000000000")
    assert r.riconosci("dvd", "", "ffffffffffffffff")[0] == "INCERTO"


def test_senza_chiave_non_si_scrive(tmp_path):
    """Il chiamante deve decidere — chiedere all'umano o lasciar perdere —
    invece di depositare una voce che nessuno ritrovera'."""
    r = inv.Inventario(tmp_path / "i.jsonl")
    with pytest.raises(ValueError):
        r.registra("dvd", "X")
    assert len(r.voci) == 0


def test_righe_rotte_contate_non_silenziate(tmp_path):
    p = tmp_path / "i.jsonl"
    p.write_text('{"chiave":"dvd:heat","tipo":"dvd","titolo":"Heat"}\n'
                 'questa non e JSON\n', encoding="utf-8")
    r = inv.Inventario(p)
    assert len(r.voci) == 1 and r.righe_illeggibili == 1


def test_csv(tmp_path):
    r = inv.Inventario(tmp_path / "i.jsonl")
    r.registra("dvd", "Heat", None)
    righe = r.csv().strip().splitlines()
    assert righe[0].startswith("tipo,titolo") and "Heat" in righe[1]


# --------------------------------------------------------------------------
# lettura della risposta del modello
# --------------------------------------------------------------------------

def test_json_dentro_markdown():
    t = '```json\n{"oggetti":[{"tipo":"dvd","titolo":"Heat","riquadro":[0,0,1,1],"confidenza":0.9}]}\n```'
    assert vis.estrai_oggetti(t)[0]["titolo"] == "Heat"


def test_riquadro_e_confidenza_fuori_scala_vengono_riportati_dentro():
    t = '{"oggetti":[{"tipo":"dvd","titolo":"X","riquadro":[-1,0.5,9,9],"confidenza":7}]}'
    o = vis.estrai_oggetti(t)[0]
    x, y, w, h = o["riquadro"]
    assert 0 <= x <= 1 and 0 <= y <= 1 and x + w <= 1.001 and y + h <= 1.001
    assert o["confidenza"] == 1.0


def test_risposta_non_json_da_lista_vuota():
    assert vis.estrai_oggetti("Mi dispiace, non riesco a vedere nulla.") == []
    assert vis.estrai_oggetti("") == []


def test_lettura_non_accetta_l_inventario():
    """La garanzia anti-eco e' nella firma: non c'e' dove infilarlo (§4)."""
    import inspect
    parametri = set(inspect.signature(vis.leggi).parameters)
    assert parametri == {"immagine_b64", "mime", "cascata"}


def test_senza_provider_si_solleva_invece_di_restituire_vuoto(monkeypatch):
    """Una lista vuota significa «ho guardato e non c'era niente»: e' un'altra
    affermazione rispetto a «non ho guardato»."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(vis.VisioneNonDisponibile):
        vis.leggi("x", cascata=("anthropic", "gemini"))


def test_stub_si_dichiara():
    esito = vis.leggi("x", cascata=("stub",))
    assert esito["stub"] is True
    # ogni oggetto con un titolo lo dichiara finto; quello senza titolo e'
    # l'esempio di lettura illeggibile, e non puo' entrare nel registro.
    assert all("FINTO" in o["titolo"] for o in esito["oggetti"] if o["titolo"])
    assert any(inv.chiave(o["tipo"], o["titolo"]) is None for o in esito["oggetti"])


# --------------------------------------------------------------------------
# sovrapposizione dei riquadri
# --------------------------------------------------------------------------

def test_sovrapposizione():
    assert srv.sovrapposizione([0, 0, 1, 1], [0, 0, 1, 1]) == 1.0
    assert srv.sovrapposizione([0, 0, 1, 1], [1, 1, 1, 1]) == 0.0
    assert srv.sovrapposizione([0, 0, 0, 0], [0, 0, 1, 1]) == 0.0


def test_impronta_vicina_solo_se_sovrapposta():
    imp = [{"riquadro": [0.11, 0.21, 0.10, 0.50], "impronta": "abc"}]
    assert srv.impronta_vicina([0.10, 0.20, 0.10, 0.50], imp) == "abc"
    assert srv.impronta_vicina([0.80, 0.20, 0.10, 0.50], imp) is None
    assert srv.impronta_vicina([0.1, 0.2, 0.1, 0.5], [{"riquadro": "rotto"}]) is None


# --------------------------------------------------------------------------
# il server, davvero in ascolto
# --------------------------------------------------------------------------

@pytest.fixture
def occhio_in_ascolto(tmp_path):
    from http.server import ThreadingHTTPServer
    srv.Handler.stato = srv.Stato(tmp_path / "i.jsonl", ("stub",), True, 0.75)
    s = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{s.server_address[1]}"
    s.shutdown(); s.server_close()


def chiama(url, dati=None):
    corpo = json.dumps(dati).encode() if dati is not None else None
    req = urllib.request.Request(
        url, data=corpo,
        headers={"Content-Type": "application/json"} if corpo else {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_stato_e_pagina(occhio_in_ascolto):
    codice, d = chiama(occhio_in_ascolto + "/api/stato")
    assert codice == 200 and d["stub"] is True
    with urllib.request.urlopen(occhio_in_ascolto + "/", timeout=10) as r:
        assert r.status == 200 and b"<title>occhio" in r.read()


def test_lo_stub_non_scrive_mai(occhio_in_ascolto):
    """Il modo stub puo' mostrare la grafica, non puo' sporcare il registro."""
    codice, d = chiama(occhio_in_ascolto + "/api/fotogramma",
                       {"immagine": "data:image/jpeg;base64,AAAA"})
    assert codice == 200 and d["stub"] is True
    assert d["totale_inventario"] == 0
    assert all(o["scritto_ora"] is False for o in d["oggetti"])


def test_conferma_umana_scrive_e_marca_la_fonte(occhio_in_ascolto):
    codice, d = chiama(occhio_in_ascolto + "/api/conferma",
                       {"tipo": "dvd", "titolo": "Stalker", "impronta": "abcdabcdabcdabcd"})
    assert codice == 200 and d["totale_inventario"] == 1
    assert d["voce"]["fonte"] == "umano"
    # e ripassarci sopra non ne aggiunge un'altra
    codice, d = chiama(occhio_in_ascolto + "/api/conferma", {"tipo": "dvd", "titolo": "STALKER"})
    assert d["totale_inventario"] == 1


def test_conferma_rifiuta_un_titolo_inutilizzabile(occhio_in_ascolto):
    assert chiama(occhio_in_ascolto + "/api/conferma", {"tipo": "dvd", "titolo": "Z"})[0] == 400
    assert chiama(occhio_in_ascolto + "/api/conferma", {"tipo": "dvd"})[0] == 400


def test_niente_risalita_di_directory(occhio_in_ascolto):
    """Il server gira nella cartella di casa di qualcuno, e `.env` ha le chiavi."""
    for cattivo in ("/../.env", "/..%2f.env", "/web/../../.env"):
        codice, _ = chiama(occhio_in_ascolto + cattivo)
        assert codice in (400, 404)


def test_esporta_csv(occhio_in_ascolto):
    chiama(occhio_in_ascolto + "/api/conferma", {"tipo": "dvd", "titolo": "Nostalghia"})
    with urllib.request.urlopen(occhio_in_ascolto + "/api/esporta.csv", timeout=10) as r:
        assert r.status == 200 and b"Nostalghia" in r.read()


# --------------------------------------------------------------------------
# costo — i numeri devono essere ricalcolabili, non ricordati
# --------------------------------------------------------------------------

def test_costo_cresce_con_i_pixel_non_con_l_informazione():
    """Raddoppiare il lato quadruplica il costo e non legge un titolo in piu'."""
    from occhio import costo
    assert costo.token_immagine(2048) == pytest.approx(costo.token_immagine(1024) * 4, rel=0.01)


def test_costo_ordina_i_modelli_come_i_listini():
    from occhio import costo
    c = {m: costo.costo_fotogramma(m) for m in costo.PREZZI}
    assert c["haiku-4.5"] < c["sonnet-5"] < c["opus-5"]


def test_lo_sconto_a_lotti_e_meta():
    from occhio import costo
    assert costo.costo_fotogramma("haiku-4.5", lotti=True) == pytest.approx(
        costo.costo_fotogramma("haiku-4.5") / 2)


def test_il_ritmo_governa_la_spesa():
    """Il doppio del ritmo e' la meta' della spesa: e' la leva, non la grafica."""
    from occhio import costo
    lento = costo.passata(10, 5.0)["costo_passata"]
    veloce = costo.passata(10, 2.5)["costo_passata"]
    assert veloce == pytest.approx(lento * 2, rel=0.02)
