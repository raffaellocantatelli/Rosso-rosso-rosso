"""Prove di occhio. Origine protetta: Claudio Terzi [CT-LGAI-001].

Nessuna di queste prove chiama un modello: girano senza chiavi, nella Action,
sempre. Cio' che non si puo' provare senza un modello — se il riconoscimento
dei titoli sia buono — non viene finto qui: si misura camminando, ed e'
scritto in OCCHIO.md fra le cose ancora UNKNOWN.
"""

import json
import os
import sys
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


# --------------------------------------------------------------------------
# dove sta un oggetto — EXIF letto a mano, e il luogo che invece si dichiara
# --------------------------------------------------------------------------

from occhio import luogo as lg  # noqa: E402
from tests._jpeg_finto import jpeg_con_exif  # noqa: E402


def test_exif_legge_gps_e_errore_dichiarato(tmp_path):
    """Il telefono dichiara da sé di quanto può sbagliare: quel campo è il
    perno di H7, e deve arrivare intero fino al falsificatore."""
    f = tmp_path / "a.jpg"
    f.write_bytes(jpeg_con_exif(45.4642, 9.1900, 18.5))
    d = lg.exif(f)
    assert d["gps"]["lat"] == pytest.approx(45.4642, abs=1e-4)
    assert d["gps"]["lon"] == pytest.approx(9.1900, abs=1e-4)
    assert d["errore_gps_m"] == 18.5
    assert "iPhone" in d["fotocamera"]
    assert d["scattata"].startswith("2026:09:03")


def test_exif_senza_gps_resta_none(tmp_path):
    """Un campo assente non viene mai riempito con una stima: una data
    inventata in un inventario è peggio di una data mancante."""
    f = tmp_path / "b.jpg"
    f.write_bytes(jpeg_con_exif())
    d = lg.exif(f)
    assert d["gps"] is None and d["errore_gps_m"] is None
    assert d["exif_presente"] is True


def test_exif_su_file_non_jpeg_non_esplode(tmp_path):
    f = tmp_path / "c.txt"
    f.write_bytes(b"non sono un jpeg")
    assert lg.exif(f)["exif_presente"] is False
    assert lg.exif(tmp_path / "non-esisto.jpg")["exif_presente"] is False


def test_luogo_dalle_cartelle():
    l = lg.dal_percorso("/f/salotto/libreria/ripiano-3/IMG.jpg", "/f")
    assert (l["stanza"], l["mobile"], l["ripiano"]) == ("salotto", "libreria", "ripiano-3")
    assert lg.etichetta(l) == "salotto › libreria › ripiano-3"


def test_luogo_oltre_tre_livelli_non_si_perde():
    """Meglio conservare quello che qualcuno ha scritto che buttarlo per far
    tornare uno schema."""
    l = lg.dal_percorso("/f/a/b/c/d/e/IMG.jpg", "/f")
    assert l["dettaglio"] == "d/e" and "d/e" in lg.etichetta(l)


def test_luogo_assente_si_dichiara():
    assert lg.etichetta(lg.dal_percorso("/f/IMG.jpg", "/f")) == "(non dichiarato)"


def test_distanza_metri():
    assert lg.distanza_m({"lat": 45.0, "lon": 9.0},
                         {"lat": 45.000045, "lon": 9.0}) == pytest.approx(5.0, abs=0.3)


def test_il_gps_non_decide_mai_una_stanza(tmp_path):
    """La garanzia sta nella firma: `registra` prende un luogo dichiarato, e
    non esiste alcuna funzione che deduca una stanza da una coordinata."""
    import inspect
    from occhio import cartella
    assert "gps" not in inspect.signature(inv.Inventario.registra).parameters
    sorgente = inspect.getsource(cartella)
    # il gps viene letto e mostrato, mai passato a registra()
    assert "luogo=posto" in sorgente
    assert "luogo=dati" not in sorgente and "luogo=gps" not in sorgente


# --------------------------------------------------------------------------
# il modo a fotografie
# --------------------------------------------------------------------------

def test_una_foto_gia_letta_non_si_ripaga(tmp_path):
    """Rieseguire la stessa cartella non deve ricomprare le stesse letture:
    è H6 applicato al portafoglio."""
    from occhio import cartella
    cart = tmp_path / "foto" / "salotto"
    cart.mkdir(parents=True)
    (cart / "IMG_1.jpg").write_bytes(jpeg_con_exif(45.0, 9.0, 20.0))
    registro = inv.Inventario(tmp_path / "i.jsonl")
    registro.registra("dvd", "Heat", fonte="foto",
                      foto_sha=cartella.sha256(cart / "IMG_1.jpg"))
    conti, _ = cartella.percorri(tmp_path / "foto", registro,
                                 cascata=("stub",), verboso=False)
    assert conti["saltate"] == 1 and conti["foto"] == 0


def test_lo_stub_non_scrive_neanche_dalle_foto(tmp_path):
    from occhio import cartella
    cart = tmp_path / "foto" / "cucina"
    cart.mkdir(parents=True)
    (cart / "IMG_1.jpg").write_bytes(jpeg_con_exif())
    registro = inv.Inventario(tmp_path / "i.jsonl")
    conti, _ = cartella.percorri(tmp_path / "foto", registro,
                                 cascata=("stub",), verboso=False)
    assert conti["foto"] == 1 and conti["nuovi"] == 0 and len(registro.voci) == 0


def test_la_mappa_raggruppa_per_luogo(tmp_path):
    from occhio import cartella
    r = inv.Inventario(tmp_path / "i.jsonl")
    salotto = lg.dal_percorso("/f/salotto/libreria/x.jpg", "/f")
    cucina = lg.dal_percorso("/f/cucina/x.jpg", "/f")
    r.registra("dvd", "Heat", luogo=salotto, fonte="foto")
    r.registra("dvd", "Solaris", luogo=salotto, fonte="foto")
    r.registra("libro", "La tregua", luogo=cucina, fonte="foto")
    mappa = r.per_luogo()
    assert len(mappa) == 2
    assert len(mappa["salotto › libreria"]) == 2
    pagina = cartella.mappa_html(r)
    assert "salotto › libreria" in pagina and "Heat" in pagina
    assert "dichiarato" in pagina  # la pagina spiega da sé perché non usa il GPS


def test_lo_stesso_oggetto_in_due_luoghi_li_conserva_entrambi(tmp_path):
    """I libri si spostano: due luoghi sono un fatto, non un conflitto."""
    r = inv.Inventario(tmp_path / "i.jsonl")
    r.registra("libro", "La tregua", luogo=lg.dal_percorso("/f/studio/x.jpg", "/f"))
    r.registra("libro", "LA TREGUA", luogo=lg.dal_percorso("/f/salotto/x.jpg", "/f"))
    assert len(r.voci) == 1
    assert len(r.voci[0]["luoghi"]) == 2


def test_il_titolo_html_della_mappa_e_sfuggito(tmp_path):
    """I titoli arrivano da un modello che legge fotografie: non sono HTML."""
    from occhio import cartella
    r = inv.Inventario(tmp_path / "i.jsonl")
    r.registra("dvd", "<script>alert(1)</script> Heat", fonte="foto")
    assert "<script>alert" not in cartella.mappa_html(r)


# --------------------------------------------------------------------------
# affitto breve — lo stato controfirmato
# --------------------------------------------------------------------------

from occhio import consegna as cons  # noqa: E402

CODICE = "HMX88-2026"
TRE = [
    {"chiave": "elettronica:nespresso", "titolo": "Nespresso Vertuo",
     "luogo": {"stanza": "cucina"}, "foto_sha": "a" * 64},
    {"chiave": "elettronica:tv", "titolo": "LG OLED 55",
     "luogo": {"stanza": "salotto"}, "foto_sha": "b" * 64},
    {"chiave": "dvd:heat", "titolo": "Heat",
     "luogo": {"stanza": "salotto"}, "foto_sha": "c" * 64},
]


def test_la_differenza_trova_cio_che_manca(tmp_path):
    c = cons.Consegne(tmp_path / "c.jsonl")
    a = c.deposita("casa", "consegna", TRE)
    b = c.deposita("casa", "riconsegna", TRE[1:])
    d = cons.differenza(a, b)
    assert [o["titolo"] for o in d["mancanti"]] == ["Nespresso Vertuo"]
    assert d["invariati"] == 2


def test_la_differenza_vede_uno_spostamento(tmp_path):
    c = cons.Consegne(tmp_path / "c.jsonl")
    a = c.deposita("casa", "consegna", TRE)
    b = c.deposita("casa", "riconsegna",
                   [dict(TRE[0], luogo={"stanza": "salotto"})] + TRE[1:])
    d = cons.differenza(a, b)
    assert not d["mancanti"] and len(d["spostati"]) == 1


def test_uno_stato_nasce_sempre_non_controfirmato(tmp_path):
    """Anche quando il codice c'è già: la controfirma è un atto separato,
    con un momento suo."""
    c = cons.Consegne(tmp_path / "c.jsonl")
    s = c.deposita("casa", "consegna", TRE)
    assert s["controfirma"] is None
    assert c.verifica(CODICE)["controfirme"] == 0


def test_la_controfirma_porta_il_proprio_momento(tmp_path):
    """Non si può aggiungere a posteriori fingendo che ci fosse dall'inizio."""
    c = cons.Consegne(tmp_path / "c.jsonl")
    s = c.deposita("casa", "consegna", TRE)
    v = c.controfirma(s["impronta"], CODICE)
    assert v["momento"] and v["riferimento"] == s["impronta"]
    assert c.verifica(CODICE)["controfirme"] == 1


def test_una_riga_riscritta_rompe_la_verifica(tmp_path):
    p = tmp_path / "c.jsonl"
    c = cons.Consegne(p)
    c.deposita("casa", "consegna", TRE)
    righe = p.read_text(encoding="utf-8").splitlines()
    v = json.loads(righe[0])
    v["oggetti"][0]["titolo"] = "Caffettiera da tre euro"
    p.write_text(json.dumps(v, ensure_ascii=False) + "\n", encoding="utf-8")
    assert cons.Consegne(p).verifica()["catena_integra"] is False


def test_una_firma_con_il_codice_sbagliato_si_vede(tmp_path):
    c = cons.Consegne(tmp_path / "c.jsonl")
    s = c.deposita("casa", "consegna", TRE)
    c.controfirma(s["impronta"], "codice-di-un-altro")
    assert c.verifica(CODICE)["firme_non_valide"]


def test_una_catena_rifatta_da_capo_risulta_integra_e_va_detto(tmp_path):
    """LA PROVA CHE CONTA, e che rompe il modulo che la contiene.

    Una catena rigenerata dal solo proprietario è perfettamente coerente con
    sé stessa — quindi «integra» non è una prova. Se il sistema presentasse
    l'integrità come prova, offrirebbe come garanzia il proprio riflesso: §4
    travestito da crittografia. Ciò che salva è che gli stati senza
    controfirma restino contati e dichiarati.
    """
    c = cons.Consegne(tmp_path / "rifatta.jsonl")
    c.deposita("casa", "consegna", [dict(TRE[0], titolo="Caffettiera da 3 euro")])
    c.deposita("casa", "riconsegna", [])
    v = c.verifica(CODICE)
    assert v["catena_integra"] is True          # lo è davvero
    assert v["controfirme"] == 0                # e non prova niente
    assert len(v["senza_controfirma"]) == 2     # il sistema lo dice da sé
    d = cons.differenza(c.stati[0], c.stati[1])
    assert not d["prima_controfirmata"] and not d["dopo_controfirmata"]
    assert "non e' controfirmato" in cons.stampa_differenza(d)


def test_la_controfirma_non_si_attacca_a_uno_stato_inesistente(tmp_path):
    c = cons.Consegne(tmp_path / "c.jsonl")
    with pytest.raises(ValueError):
        c.controfirma("f" * 64, CODICE)


def test_tipo_di_stato_sconosciuto_rifiutato(tmp_path):
    c = cons.Consegne(tmp_path / "c.jsonl")
    with pytest.raises(ValueError):
        c.deposita("casa", "sequestro", TRE)


def test_occhio_non_scrive_mai_un_file_immagine():
    """Airbnb esclude dalle prove le immagini generate o alterate dall'IA
    (dal 20/04/2026, fonti in OCCHIO.md §7). Quindi la fotografia ORIGINALE
    non va mai toccata: `occhio` la legge, ne calcola l'impronta, e non
    scrive mai un'immagine da nessuna parte. La copia ridotta che va al
    modello vive in memoria e non tocca il disco.
    """
    import inspect
    from occhio import cartella, luogo, server, visione
    for modulo in (cartella, luogo, server, visione):
        sorgente = inspect.getsource(modulo)
        # solo scritture vere: l'elenco delle estensioni ammesse non conta.
        for sospetto in ("write_bytes", '"wb"', "'wb'", "PIL", "ImageDraw"):
            assert sospetto not in sorgente, (
                f"{modulo.__name__} sembra scrivere immagini: {sospetto}")


# --------------------------------------------------------------------------
# la pianta — il disegno sì, il posizionamento no
# --------------------------------------------------------------------------

from occhio import planimetria as pln  # noqa: E402

PIANTA = {
    "alloggio": "via-roma-12",
    "zone": [
        # stanza a L: il centro del riquadro cade FUORI dalla stanza
        {"nome": "soggiorno", "scatto": 1,
         "punti": [[26, 0], [78, 0], [78, 40], [52, 40], [52, 22], [26, 22]]},
        {"nome": "bagno", "scatto": 2, "punti": [[0, 52], [30, 52], [30, 80], [0, 80]]},
    ],
}


def _dentro(punto, poligono):
    """Punto dentro poligono, a raggi. Serve solo a questa prova."""
    x, y = punto
    dentro = False
    n = len(poligono)
    for i in range(n):
        x0, y0 = poligono[i]
        x1, y1 = poligono[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xi = (x1 - x0) * (y - y0) / (y1 - y0) + x0
            if x < xi:
                dentro = not dentro
    return dentro


def test_l_etichetta_di_una_stanza_a_L_resta_dentro_la_stanza():
    """Col centro del riquadro l'etichetta finirebbe nella stanza accanto,
    e il disegno direbbe una cosa falsa.

    La L del soggiorno di PIANTA non basta a provarlo: il suo centro del
    riquadro cade per caso dentro la stanza. Serve una L più marcata —
    trovato eseguendo il test, che infatti è passato dalla parte sbagliata.
    """
    a_elle = [[0, 0], [60, 0], [60, 20], [20, 20], [20, 60], [0, 60]]
    riq = pln._riquadro(a_elle)
    centro_riquadro = ((riq[0] + riq[2]) / 2, (riq[1] + riq[3]) / 2)
    assert not _dentro(centro_riquadro, a_elle)            # il difetto esiste
    # e nemmeno il baricentro dell'area basta, su una L marcata:
    assert not _dentro(pln._baricentro(a_elle), a_elle)
    # ciò che regge è cercare il punto più interno, non scegliere una formula
    assert _dentro(pln._punto_etichetta(a_elle), a_elle)


@pytest.mark.parametrize("forma", [
    [[0, 0], [60, 0], [60, 20], [20, 20], [20, 60], [0, 60]],          # L
    [[26, 0], [78, 0], [78, 40], [52, 40], [52, 22], [26, 22]],        # L dolce
    [[0, 0], [40, 0], [40, 40], [0, 40]],                              # rettangolo
    [[0, 0], [50, 0], [50, 10], [30, 10], [30, 30], [50, 30],
     [50, 40], [0, 40]],                                              # C
])
def test_il_punto_etichetta_sta_sempre_dentro(forma):
    assert _dentro(pln._punto_etichetta(forma), forma)


def test_una_zona_con_un_oggetto_mancante_diventa_rossa(tmp_path):
    r = inv.Inventario(tmp_path / "i.jsonl")
    r.registra("elettronica", "Phon Dyson", luogo=lg.dal_percorso("/f/bagno/x.jpg", "/f"))
    r.registra("dvd", "Heat", luogo=lg.dal_percorso("/f/soggiorno/x.jpg", "/f"))
    diff = {"mancanti": [{"titolo": "Phon Dyson", "luogo": {"stanza": "bagno"}}]}
    s = pln.stato_zone(r, diff, fatte={"soggiorno"})
    assert s["zone"]["bagno"] == pln.MANCA
    assert s["zone"]["soggiorno"] == pln.FATTA
    assert s["mancanti"]["bagno"] == ["Phon Dyson"]


def test_una_zona_non_ancora_vista_resta_ambra(tmp_path):
    r = inv.Inventario(tmp_path / "i.jsonl")
    r.registra("altro", "Ombrellone", luogo=lg.dal_percorso("/f/terrazzo/x.jpg", "/f"))
    assert pln.stato_zone(r)["zone"]["terrazzo"] == pln.DA_FARE


def test_il_disegno_porta_i_nomi_e_l_ordine_degli_scatti():
    d = pln.svg(PIANTA, {"zone": {"soggiorno": pln.FATTA, "bagno": pln.MANCA}})
    assert "soggiorno" in d and "bagno" in d
    assert pln.COLORI[pln.FATTA] in d and pln.COLORI[pln.MANCA] in d
    assert 'data-stato="manca"' in d
    assert d.startswith("<svg") and d.endswith("</svg>")


def test_il_nome_di_una_zona_e_sfuggito():
    d = pln.svg({"zone": [{"nome": "<script>x</script>",
                           "punti": [[0, 0], [10, 0], [10, 10], [0, 10]]}]})
    assert "<script>" not in d


def test_la_pianta_di_partenza_esce_dalle_stanze_dell_inventario(tmp_path):
    """Il foglio bianco è il vero motivo per cui una pianta non viene fatta."""
    r = inv.Inventario(tmp_path / "i.jsonl")
    for stanza in ("cucina", "bagno", "camera"):
        r.registra("altro", f"oggetto in {stanza}",
                   luogo=lg.dal_percorso(f"/f/{stanza}/x.jpg", "/f"))
    modello = pln.modello_da_inventario(r, "via-roma-12")
    assert {z["nome"] for z in modello["zone"]} == {"cucina", "bagno", "camera"}
    assert all(len(z["punti"]) == 4 for z in modello["zone"])
    assert [z["scatto"] for z in modello["zone"]] == [1, 2, 3]
    # e deve essere ricaricabile senza perdere niente
    f = tmp_path / "p.json"
    f.write_text(json.dumps(modello, ensure_ascii=False), encoding="utf-8")
    assert pln.carica(f) == modello


def test_la_pianta_non_ha_bisogno_di_niente(tmp_path):
    """Nessuna dipendenza, nessun sensore: si scrive a mano in dieci minuti."""
    import inspect
    sorgente = inspect.getsource(pln)
    for sospetto in ("import numpy", "import PIL", "ARKit", "RoomPlan", "requests"):
        assert f"\n{sospetto}" not in sorgente


def test_la_pianta_entra_nella_mappa(tmp_path):
    from occhio import cartella
    r = inv.Inventario(tmp_path / "i.jsonl")
    r.registra("dvd", "Heat", luogo=lg.dal_percorso("/f/soggiorno/x.jpg", "/f"))
    pagina = cartella.mappa_html(r, PIANTA, fatte={"soggiorno"})
    assert "<svg" in pagina and "zona verificata" in pagina
    # e senza pianta la mappa resta valida
    assert "<svg" not in cartella.mappa_html(r)


# --------------------------------------------------------------------------
# PORTAVIA — idea di Claudio Terzi, 3 settembre 2026
# --------------------------------------------------------------------------

import pathlib  # noqa: E402
import tempfile  # noqa: E402

from occhio import portavia as pv  # noqa: E402

MINIMI = {"dvd:heat": 8.0, "altro:barolo": 35.0, "elettronica:sonos": 260.0}


def regole(**kw):
    base = dict(prezzo_minimo=MINIMI, sconto_massimo=0.15,
                commissione=0.12, margine=0.25)
    base.update(kw)
    return pv.Regole(**base)


@pytest.mark.parametrize("chiave", list(MINIMI))
def test_il_proprietario_non_incassa_mai_meno_del_suo_minimo(chiave):
    """È caduta davvero, la prima volta: lo sconto mangiava il minimo.
    Da qui la prova a forza bruta invece di tre casi scelti."""
    r = regole()
    minimo = MINIMI[chiave]
    offerta = 0.01
    while offerta <= minimo * 3:
        d = pv.valuta_offerta(chiave, "x", offerta, r)
        if d["esito"] == pv.ACCETTA:
            assert r.incasso_proprietario(d["prezzo"]) >= minimo - 0.01, (
                f"accettata {offerta} su minimo {minimo}")
        offerta = round(offerta + max(0.01, minimo / 200), 2)


def test_esposto_maggiore_di_limite_maggiore_di_soglia():
    r = regole()
    assert r.esposto("dvd:heat") > r.limite("dvd:heat") >= r.soglia("dvd:heat")


def test_senza_margine_non_c_e_trattativa():
    r = regole(margine=0.0)
    assert r.limite("dvd:heat") == r.soglia("dvd:heat") == r.esposto("dvd:heat")


def test_cio_che_non_si_vende_non_si_vende_a_nessun_prezzo():
    r = regole()
    for parola in pv.MAI_IN_VENDITA:
        d = pv.valuta_offerta(f"elettronica:{parola}", parola, 1_000_000.0, r)
        assert d["esito"] == pv.RIFIUTA


def test_un_oggetto_senza_prezzo_dichiarato_non_e_in_vendita():
    """Il default è il più protettivo: nulla è in vendita finché non lo dici."""
    assert pv.valuta_offerta("dvd:solaris", "Solaris", 500.0,
                             regole())["esito"] == pv.RIFIUTA
    assert pv.Regole().vendibile("dvd:heat", "Heat")[0] is False


def test_il_proprietario_puo_escludere_altro():
    r = regole(mai=("poltrona",))
    assert pv.valuta_offerta("altro:poltrona verde", "Poltrona verde", 999.0,
                             r)["esito"] == pv.RIFIUTA


def test_offerta_non_valida():
    for brutta in (0, -5):
        assert pv.valuta_offerta("dvd:heat", "Heat", brutta,
                                 regole())["esito"] == pv.RIFIUTA


def test_regole_incoerenti_rifiutate():
    for kw in ({"sconto_massimo": 1.5}, {"commissione": 1.0}, {"margine": -0.1}):
        with pytest.raises(ValueError):
            regole(**kw)


def test_le_parole_del_mediatore_non_decidono_niente():
    """Il modello parla, le regole decidono: la frase è derivata dalla
    decisione, e nessun modello partecipa a `valuta_offerta`."""
    import inspect
    sorgente = inspect.getsource(pv.valuta_offerta)
    for sospetto in ("visione", "Router", "requests", "generate", "leggi("):
        assert sospetto not in sorgente
    r = regole()
    d = pv.valuta_offerta("dvd:heat", "Heat", 5.0, r)
    assert "8" in pv.parole_del_mediatore(d, "Heat", r) or "9" in pv.parole_del_mediatore(d, "Heat", r)


def test_cio_che_e_stato_comprato_non_e_sparito(tmp_path):
    """Il cuore dell'idea: la lista smette di dire «mancano tre oggetti»
    e dice «due li ha comprati, uno no»."""
    p = pv.Portavia(tmp_path / "pv.jsonl", regole())
    p.vendita("dvd:heat", "Heat", 11.38, soggiorno="S1")
    d = {"mancanti": [{"chiave": "dvd:heat", "titolo": "Heat"},
                      {"chiave": "altro:asciugamani", "titolo": "Asciugamani"}]}
    s = pv.spiega_mancanti(d, p, "S1")
    assert [o["titolo"] for o in s["comprati"]] == ["Heat"]
    assert [o["titolo"] for o in s["non_spiegati"]] == ["Asciugamani"]
    assert s["comprati"][0]["vendita"]["prezzo"] == 11.38


def test_una_vendita_di_un_altro_soggiorno_non_spiega_questo(tmp_path):
    """Altrimenti basterebbe una vendita vecchia per giustificare ogni
    sparizione futura: sarebbe l'eco di §4 con una fattura in mano."""
    p = pv.Portavia(tmp_path / "pv.jsonl", regole())
    p.vendita("dvd:heat", "Heat", 11.38, soggiorno="S1")
    d = {"mancanti": [{"chiave": "dvd:heat", "titolo": "Heat"}]}
    s = pv.spiega_mancanti(d, p, "S2")
    assert s["comprati"] == [] and len(s["non_spiegati"]) == 1


def test_la_commissione_e_una_sola_e_torna(tmp_path):
    p = pv.Portavia(tmp_path / "pv.jsonl", regole(commissione=0.12))
    v = p.vendita("dvd:heat", "Heat", 100.0)
    assert v["commissione"] == 12.0 and v["al_proprietario"] == 88.0
    assert p.incasso()["lordo"] == 100.0


def test_un_immagine_generata_non_e_mai_una_prova():
    """La VETRINA può generare l'immagine bella. La fotografia che dimostra
    che l'oggetto c'era, no: è esclusa dalle prove nei reclami danni."""
    assert pv.immagine_generata_ammessa_come_prova() is False
    # La catena delle consegne non ha nessun punto d'ingresso per un'immagine:
    # di ogni oggetto conserva quattro campi, e uno solo riguarda la
    # fotografia — la sua IMPRONTA, non i suoi byte. Non c'è posto dove
    # infilare un'immagine generata, ed è la garanzia per costruzione.
    c = cons.Consegne(pathlib.Path(tempfile.mkdtemp()) / "c.jsonl")
    s = c.deposita("casa", "consegna", TRE)
    assert set(s["oggetti"][0]) == {"chiave", "titolo", "luogo", "foto_sha"}
    assert len(s["oggetti"][0]["foto_sha"]) == 64  # è un'impronta, non un file


# --------------------------------------------------------------------------
# LA VOCE — idea di Claudio Terzi, 3 settembre 2026
# --------------------------------------------------------------------------

from occhio import voce as vc  # noqa: E402


@pytest.fixture
def casa(tmp_path):
    r = inv.Inventario(tmp_path / "i.jsonl")
    roba = [("vino", "Barolo Serralunga 2016", "cucina/credenza"),
            ("vino", "Franciacorta Saten", "cucina/frigo"),
            ("cibo", "Spaghetti Gragnano", "cucina/dispensa"),
            ("dvd", "Cinema Paradiso", "soggiorno/mobile-tv"),
            ("dvd", "La grande bellezza", "soggiorno/mobile-tv"),
            ("elettronica", "Phon Dyson Supersonic", "bagno")]
    for tipo, titolo, dove in roba:
        r.registra(tipo, titolo, luogo=lg.dal_percorso(f"/f/{dove}/x.jpg", "/f"))
    return r


def test_cucina_e_una_stanza_e_un_verbo(casa):
    """«che vini ho in cucina» finiva interpretato come richiesta di ricette.
    Il difetto è stato trovato eseguendo, non rileggendo."""
    e = vc.rispondi(casa, "che vini ho in cucina")
    assert e["intento"] == vc.ELENCA and e["luogo"] == "cucina"
    assert "Barolo" in e["testo_risposta"] and "Franciacorta" in e["testo_risposta"]
    assert vc.interpreta("cosa posso cucinare stasera")["intento"] == vc.CUCINA


def test_cercare_non_e_elencare(casa):
    """«dov'è il phon» deve trovare UN oggetto, non tutta l'elettronica."""
    e = vc.rispondi(casa, "dov'è il phon")
    assert e["intento"] == vc.DOVE
    assert e["testo_risposta"].count(":") == 1
    assert "bagno" in e["testo_risposta"]


def test_una_parola_su_tre_basta_a_riconoscere_un_titolo(casa):
    assert vc._somiglianza("Phon Dyson Supersonic", "dov e il phon") == pytest.approx(1 / 3)
    assert vc._somiglianza("Phon Dyson Supersonic", "dov e il gatto") == 0.0
    assert 1 / 3 >= vc.SOGLIA_TITOLO  # la soglia deve lasciar passare questo caso


def test_contare(casa):
    assert vc.rispondi(casa, "quanti dvd ho")["testo_risposta"].startswith("2")


def test_una_domanda_non_capita_non_diventa_l_inventario_intero(casa):
    """A «che trattori ho in garage» il sistema elencava tutta la casa: senza
    tipo né luogo il filtro non filtrava niente. Non aver capito è una
    risposta, e va data — nominando il luogo quando c'è, perché «non conosco
    nessun garage» è preciso e «non ho capito» fa ripetere a vuoto."""
    e = vc.rispondi(casa, "che trattori ho in garage")
    assert e["intento"] == vc.IGNOTO and e["oggetti"] == []
    assert "garage" in e["testo_risposta"]
    assert "Barolo" not in e["testo_risposta"]
    # senza nessun luogo nominato, la risposta è l'elenco di ciò che sa fare
    generica = vc.rispondi(casa, "raccontami una barzelletta")
    assert "Non ho capito" in generica["testo_risposta"]


def test_una_stanza_che_non_esiste_si_dice_per_nome(casa):
    """«Non conosco nessun luogo che si chiami cantina» è preciso;
    «non ho capito» fa ripetere la domanda a vuoto."""
    e = vc.rispondi(casa, "cosa c'è in cantina")
    assert "cantina" in e["testo_risposta"] and "Non conosco" in e["testo_risposta"]
    assert "cucina" in e["testo_risposta"]      # dice quali conosce
    assert e["oggetti"] == []


def test_una_stanza_nota_ma_senza_l_oggetto_chiesto(casa):
    e = vc.rispondi(casa, "che vini ho in bagno")
    assert "Non risulta niente in bagno" in e["testo_risposta"]


def test_senza_parte_privata_non_si_inventa_una_ricetta(casa, monkeypatch):
    """Il punto dell'innesto: ciò che manca si dichiara, non si improvvisa."""
    monkeypatch.setattr(vc, "_privato", lambda: None)
    e = vc.rispondi(casa, "cosa posso cucinare stasera")
    assert e["intento"] == vc.CUCINA and e["parte_privata"] is False
    assert "non me lo invento" in e["testo_risposta"]
    assert "Spaghetti" in e["testo_risposta"]   # ciò che sa, lo dice


def test_con_la_parte_privata_si_innesta(casa, monkeypatch):
    class Finto:
        @staticmethod
        def suggerisci(dispensa, intento):
            return f"visti {len(dispensa)} ingredienti"
    monkeypatch.setattr(vc, "_privato", lambda: Finto)
    e = vc.rispondi(casa, "cosa cucino")
    assert e["parte_privata"] is True and "visti 3 ingredienti" in e["testo_risposta"]


def test_un_innesto_rotto_non_rompe_la_voce(casa, monkeypatch):
    """Se la parte privata esplode, la casa risponde lo stesso."""
    monkeypatch.setattr(vc, "_privato", lambda: None)
    assert vc.rispondi(casa, "cosa cucino")["testo_risposta"]


def test_la_voce_non_scrive_mai(casa):
    """A una voce non si può chiedere chi sta parlando: in un alloggio in
    affitto la stanza è piena di gente che non è il proprietario."""
    assert vc.puo_scrivere() is False
    import inspect
    sorgente = inspect.getsource(vc)
    for scrittura in ("registra(", "deposita(", "vendita(", "controfirma("):
        assert scrittura not in sorgente
    prima = len(casa.voci)
    for frase in ("vendi il televisore a dieci euro", "cancella tutto",
                  "aggiungi una Ferrari", "consegna l'alloggio"):
        vc.rispondi(casa, frase)
    assert len(casa.voci) == prima


def test_la_rotta_della_voce_dichiara_di_non_scrivere(occhio_in_ascolto):
    codice, d = chiama(occhio_in_ascolto + "/api/voce", {"frase": "quanti dvd ho"})
    assert codice == 200 and d["scrive"] is False
    assert chiama(occhio_in_ascolto + "/api/voce", {"frase": "  "})[0] == 400


# --------------------------------------------------------------------------
# I CHIARI — idea di Claudio Terzi, 3 settembre 2026
# --------------------------------------------------------------------------

from occhio import crediti as cd  # noqa: E402


def libro(tmp_path, **kw):
    return cd.Crediti(tmp_path / "cr.jsonl", **kw)


def test_i_chiari_si_conservano(tmp_path):
    c = libro(tmp_path)
    c.emetti("ospite", 40, "soggiorno", riferimento="s:1")
    c.spendi("ospite", 12, "acquisto", riferimento="a:1")
    v = c.verifica()
    assert v["emessi"] == 40 and v["spesi"] == 12 and v["in_circolo"] == 28
    assert v["conservati"] is True and c.saldo("ospite") == 28


def test_il_saldo_non_va_mai_sotto_zero(tmp_path):
    c = libro(tmp_path)
    c.emetti("ospite", 5, "soggiorno", riferimento="s:1")
    with pytest.raises(cd.SaldoInsufficiente):
        c.spendi("ospite", 6, "acquisto", riferimento="a:1")
    assert c.saldo("ospite") == 5 and not c.verifica()["saldi_negativi"]


def test_non_si_emette_senza_un_fatto_a_cui_puntare(tmp_path):
    """Un saldo che cresce senza che nulla sia entrato dall'esterno è §4
    con un simbolo di valuta davanti."""
    c = libro(tmp_path)
    with pytest.raises(ValueError):
        c.emetti("furbo", 1_000_000, "vendita")
    with pytest.raises(ValueError):
        c.emetti("furbo", 10, "vendita", riferimento="   ")
    assert c.saldo("furbo") == 0


def test_causali_sconosciute_rifiutate(tmp_path):
    c = libro(tmp_path)
    with pytest.raises(ValueError):
        c.emetti("a", 1, "magia", riferimento="x")
    c.emetti("a", 5, "vendita", riferimento="x")
    with pytest.raises(ValueError):
        c.spendi("a", 1, "regalo", riferimento="x")


@pytest.mark.parametrize("quanti", [0, -3, 1.5, "molti", None])
def test_quantita_non_valide(tmp_path, quanti):
    c = libro(tmp_path)
    with pytest.raises(ValueError):
        c.emetti("a", quanti, "vendita", riferimento="x")


def test_il_muro_non_si_converte_in_denaro():
    """Nel momento in cui un chiaro torna euro, il buono diventa moneta e il
    prodotto cambia mestiere."""
    with pytest.raises(cd.FuoriDalCircuito):
        cd.converti_in_denaro("claudio", 15)
    import inspect
    sorgente = inspect.getsource(cd)
    for via in ("def rimborsa", "def incassa", "def preleva", "stripe", "iban"):
        assert via not in sorgente.lower()


def test_il_muro_non_si_passa_di_mano_per_difetto(tmp_path):
    c = libro(tmp_path)
    c.emetti("a", 10, "vendita", riferimento="x")
    with pytest.raises(cd.FuoriDalCircuito):
        c.trasferisci("a", "b", 5)
    assert c.saldo("a") == 10 and c.saldo("b") == 0


def test_se_lo_accendi_il_movimento_resta_marchiato(tmp_path):
    """Accenderlo è una decisione d'impresa: deve restare visibile nel libro,
    altrimenti nessuno si accorge di aver cambiato mestiere."""
    c = libro(tmp_path, trasferibile=True)
    c.emetti("a", 10, "vendita", riferimento="x")
    m = c.trasferisci("a", "b", 4)
    assert m["fuori_dal_circuito_chiuso"] is True
    assert c.saldo("a") == 6 and c.saldo("b") == 4
    assert c.verifica()["conservati"] is True


@pytest.mark.parametrize("eur", [0.10, 1.0, 8.99, 9.09, 12.0, 312.5])
def test_l_arrotondamento_non_va_mai_contro_il_venditore(eur):
    """Mezzo chiaro non esiste, e la metà mancante non la può mettere il
    venditore senza accorgersene."""
    assert cd.prezzo_in_chiari(eur) >= eur
    assert isinstance(cd.prezzo_in_chiari(eur), int)


def test_il_saldo_si_ricalcola_dal_libro(tmp_path):
    """Conservare il saldo a parte significa avere due verità che prima o poi
    divergono, e allora nessuno sa quale sia quella giusta."""
    p = tmp_path / "cr.jsonl"
    c = cd.Crediti(p)
    c.emetti("a", 30, "soggiorno", riferimento="s:1")
    c.spendi("a", 11, "acquisto", riferimento="a:1")
    assert cd.Crediti(p).saldo("a") == 19


def test_una_vendita_in_chiari_e_atomica(tmp_path):
    """Prima si toglie al compratore, poi si dà al venditore: invertendo, un
    saldo insufficiente pagherebbe il venditore per una vendita mai avvenuta."""
    r = pv.Regole(prezzo_minimo={"dvd:heat": 8.0}, commissione=0.12)
    negozio = pv.Portavia(tmp_path / "pv.jsonl", r)
    c = cd.Crediti(tmp_path / "cr.jsonl")
    c.emetti("ospite", 5, "soggiorno", riferimento="s:1")
    with pytest.raises(cd.SaldoInsufficiente):
        pv.vendita_in_chiari(negozio, c, "dvd:heat", "Heat", 999.0,
                             "ospite", "claudio")
    assert c.saldo("claudio") == 0 and c.saldo("ospite") == 5
    assert negozio.movimenti == []


def test_una_vendita_in_chiari_che_riesce(tmp_path):
    r = pv.Regole(prezzo_minimo={"dvd:heat": 8.0}, commissione=0.12)
    negozio = pv.Portavia(tmp_path / "pv.jsonl", r)
    c = cd.Crediti(tmp_path / "cr.jsonl")
    c.emetti("ospite", 40, "soggiorno", riferimento="s:1")
    v = pv.vendita_in_chiari(negozio, c, "dvd:heat", "Heat",
                             r.esposto("dvd:heat"), "ospite", "claudio", "S1")
    assert v["valuta"] == "chiari"
    assert v["prezzo"] == v["commissione"] + v["al_proprietario"]
    assert c.saldo("ospite") == 40 - v["prezzo"]
    assert c.saldo("claudio") == v["al_proprietario"]
    assert c.verifica()["conservati"] is True


def test_non_si_vende_in_chiari_cio_che_non_e_in_vendita(tmp_path):
    r = pv.Regole(prezzo_minimo={"dvd:heat": 8.0})
    negozio = pv.Portavia(tmp_path / "pv.jsonl", r)
    c = cd.Crediti(tmp_path / "cr.jsonl")
    c.emetti("ospite", 999, "soggiorno", riferimento="s:1")
    with pytest.raises(ValueError):
        pv.vendita_in_chiari(negozio, c, "elettronica:caldaia", "Caldaia",
                             10.0, "ospite", "claudio")
    assert c.saldo("ospite") == 999


# --------------------------------------------------------------------------
# l'interfaccia: ogni id cercato dal JavaScript deve esistere nell'HTML
# --------------------------------------------------------------------------

def test_ogni_id_cercato_dal_javascript_esiste():
    """Un `$("#x").onclick` su un elemento assente rompe l'INTERO file — la
    telecamera compresa — con un solo TypeError, e la pagina sembra viva.

    È già successo: una modifica all'HTML non ha combaciato, app.js ha
    continuato a cercare #microfono, e il difetto è arrivato fino al ramo
    remoto. Un browser l'avrebbe preso; questo test lo prende senza browser,
    che è la ragione per cui esiste.
    """
    import re
    web = pathlib.Path(__file__).resolve().parent.parent / "occhio" / "web"
    html = (web / "index.html").read_text(encoding="utf-8")
    js = (web / "app.js").read_text(encoding="utf-8")
    presenti = set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))
    cercati = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', js))
    cercati |= set(re.findall(r'querySelector\("#([A-Za-z0-9_-]+)"\)', js))
    mancanti = cercati - presenti
    assert not mancanti, f"app.js cerca id che l'HTML non ha: {sorted(mancanti)}"


def test_le_classi_e_i_dati_usati_dal_javascript_esistono():
    import re
    web = pathlib.Path(__file__).resolve().parent.parent / "occhio" / "web"
    html = (web / "index.html").read_text(encoding="utf-8")
    js = (web / "app.js").read_text(encoding="utf-8")
    for selettore in re.findall(r'querySelectorAll\("\.([A-Za-z0-9_-]+)"\)', js):
        assert selettore in html, f"app.js usa .{selettore}, assente dall'HTML"
    # le viste a schede: ogni data-vista deve avere il suo #vista-...
    for vista in re.findall(r'data-vista="([a-z-]+)"', html):
        assert f'id="vista-{vista}"' in html, f"manca il riquadro vista-{vista}"


def test_il_foglio_di_stile_e_lo_script_sono_serviti(occhio_in_ascolto):
    for risorsa in ("/stile.css", "/app.js"):
        with urllib.request.urlopen(occhio_in_ascolto + risorsa, timeout=10) as r:
            assert r.status == 200 and len(r.read()) > 200


def test_la_dimostrazione_gira_intera(tmp_path, monkeypatch, capsys):
    """La dimostrazione è uno script e non dei file archiviati proprio perché
    non possa divergere dal codice: se si rompe, questo test lo dice."""
    import importlib.util
    for var in ("OCCHIO_INVENTARIO", "OCCHIO_CONSEGNE",
                "OCCHIO_PORTAVIA", "OCCHIO_CREDITI"):
        monkeypatch.delenv(var, raising=False)
    percorso = (pathlib.Path(__file__).resolve().parent.parent
                / "esempi" / "dimostrazione.py")
    spec = importlib.util.spec_from_file_location("dimostrazione", percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    assert modulo.main([]) == 0
    uscita = capsys.readouterr().out
    # il punto della dimostrazione: due comprati, uno no — e il terzo
    # incasso, la serata in vasca, NON compare fra i comprati perché non
    # spiega nessuna assenza: l'oggetto è ancora lì
    assert "COMPRATI: ['Perfetti sconosciuti', 'Barolo Serralunga 2016']" in uscita
    assert "NON SPIEGATI: ['Phon Dyson Supersonic']" in uscita
    assert "RESTACI" in uscita and "Serata in vasca" in uscita
    assert "Tutti i dati sono inventati" in uscita


# --------------------------------------------------------------------------
# CAPACITA.json — il manifesto non deve poter divergere dal codice
# --------------------------------------------------------------------------

from occhio import capacita as cap  # noqa: E402


def _manifesto_depositato():
    p = pathlib.Path(__file__).resolve().parent.parent / "CAPACITA.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_il_manifesto_copre_ogni_comando():
    """Se aggiungi un'opzione e non rigeneri, questa prova fallisce. È la
    differenza fra una documentazione e una promessa."""
    fresco = {c["opzione"] for c in cap._comandi()}
    depositato = {c["opzione"] for c in _manifesto_depositato()["comandi"]}
    mancanti = fresco - depositato
    assert not mancanti, (
        f"comandi non nel manifesto: {sorted(mancanti)} — "
        "rigenera con: python -m occhio --capacita CAPACITA.json")
    assert not (depositato - fresco), "il manifesto elenca comandi che non esistono più"


def test_il_manifesto_copre_ogni_funzione_pubblica():
    depositato = _manifesto_depositato()["moduli"]
    for nome in cap.MODULI:
        fresco = {e["nome"] for e in cap._funzioni(nome)}
        assert nome in depositato, f"modulo {nome} assente dal manifesto"
        noto = {e["nome"] for e in depositato[nome]["elementi"]}
        assert not (fresco - noto), (
            f"{nome}: non nel manifesto {sorted(fresco - noto)} — rigenera")


def test_il_manifesto_dichiara_le_porte_chiuse():
    """Chi legge il manifesto per integrare il prodotto deve incontrare i tre
    divieti prima di provarci."""
    v = {x["dove"] for x in _manifesto_depositato()["vincoli_non_negoziabili"]}
    assert "crediti.converti_in_denaro" in v
    assert "voce.puo_scrivere" in v
    assert any("trasferibile" in x for x in v)


def test_la_forma_dei_dati_viene_da_record_veri(tmp_path):
    """Uno schema dichiarato a mano può mentire; un record scritto dal codice
    no. I campi del manifesto devono combaciare con una voce vera."""
    forme = cap._forma_dei_dati()
    r = inv.Inventario(tmp_path / "i.jsonl")
    voce = r.registra("dvd", "Prova", luogo=lg.dal_percorso("/f/salotto/x.jpg", "/f"))
    assert set(forme["voce_inventario"]["campi"]) == set(voce)
    assert "impronta" in forme["stato_consegna_TALLY"]["campi"]
    assert forme["file_su_disco"]["formato"].startswith("JSON Lines")


def test_il_manifesto_si_rigenera_uguale_a_meno_dell_ora():
    """Due generazioni di fila devono differire solo per il momento: se no,
    dentro c'è qualcosa di non deterministico e il manifesto non è una fonte."""
    a, b = cap.genera(), cap.genera()
    for m in (a, b):
        m.pop("generato")
    assert a == b


# --------------------------------------------------------------------------
# i nomi caduti non devono tornare
# --------------------------------------------------------------------------

#: Nomi bruciati il 04/09/2026. Possono comparire solo dove si spiega che
#: sono caduti — mai come nome del prodotto.
NOMI_CADUTI = ("CASACHIARA", "Casachiara", "InventariuMapp",
               "InventariumApp", "inventariumapp")

#: Le parole che rendono lecita la menzione: si sta raccontando la caduta,
#: non si sta usando il nome.
PAROLE_DI_CADUTA = ("cadut", "scartat", "bloccat", "esiste già", "esiste gia",
                    "non è utilizzabile", "App Store", "anteriorit",
                    "restringe", "descrittiv", "marchio grafico", "maniglia")


def test_i_nomi_caduti_non_tornano_come_marchio():
    """Due nomi sono caduti, il secondo dopo aver rinominato tutto. Questo
    test è ciò che impedisce al terzo di entrare senza che nessuno se ne
    accorga: possono comparire solo dove si spiega che sono caduti."""
    radice = pathlib.Path(__file__).resolve().parent.parent
    sbagliate = []
    for f in list(radice.glob("*.md")) + list(radice.glob("occhio/*.py")) + \
             list(radice.glob("esempi/*.py")) + list(radice.glob("falsificatori/*.py")):
        for riga, testo in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for nome in NOMI_CADUTI:
                if nome in testo and not any(p in testo for p in PAROLE_DI_CADUTA):
                    sbagliate.append(f"{f.name}:{riga}  «{nome}»  {testo.strip()[:60]}")
    assert not sbagliate, ("un nome caduto usato senza dire che è caduto:\n  "
                           + "\n  ".join(sbagliate))


def test_il_codice_non_dipende_da_un_marchio():
    """Il secondo nome è caduto DOPO che tutto il repository era stato
    rinominato. Da qui in poi il marchio è un dato, non una struttura: se
    cambia, cambia una riga."""
    assert cap.MOTORE == "occhio"
    assert cap.NOME_COMMERCIALE is None      # non ancora scelto, e lo dice
    assert len(cap.NOMI_SCARTATI) == 2
    assert all("motivo" in n for n in cap.NOMI_SCARTATI)
    assert cap.CRITERI_DEL_NOME[0].startswith("non nominare la LISTA")
    m = _manifesto_depositato()
    assert m["nome_commerciale"] is None and m["motore"] == "occhio"


def test_ogni_registro_del_prodotto_e_fuori_dal_repository_pubblico():
    """Era ignorato solo inventario.jsonl. Consegne (con le firme dell'ospite),
    vendite (prezzi e compratori) e crediti (saldi delle persone) sarebbero
    finiti in un repository PUBBLICO alla prima esecuzione vera.

    La prova non guarda un elenco scritto a mano: chiede ai moduli dove
    scrivono. Un modulo nuovo che deposita altrove viene scoperto qui.

    Lo chiede in un processo separato e SENZA le variabili d'ambiente: la
    suite le punta alla sandbox (conftest), e chiedere qui darebbe i percorsi
    della sandbox — sempre fuori dal repository, quindi una prova che passa
    sempre. È il difetto di §4 in miniatura: la prova che interroga la propria
    configurazione invece della realtà che deve proteggere.
    """
    import subprocess
    radice = pathlib.Path(__file__).resolve().parent.parent
    ambiente = {k: v for k, v in os.environ.items() if not k.startswith("OCCHIO_")}
    letto = subprocess.run(
        [sys.executable, "-c",
         "from occhio import consegna, crediti, inventario, portavia as pv;"
         "print(inventario.ARCHIVIO); print(consegna.CATENA);"
         "print(pv.CATALOGO); print(crediti.LIBRO)"],
        cwd=radice, env=ambiente, capture_output=True, text=True)
    assert letto.returncode == 0, letto.stderr
    percorsi = [x for x in letto.stdout.split("\n") if x.strip()]
    assert len(percorsi) == 4, percorsi
    # e devono essere percorsi DENTRO il repository, se no non provano niente
    for x in percorsi:
        assert not pathlib.Path(x).is_absolute(), (
            f"{x} è assoluto: la prova non direbbe niente sul repository")
    non_protetti = []
    for p in percorsi:
        esito = subprocess.run(["git", "check-ignore", "-q", str(p)],
                               cwd=radice, capture_output=True)
        if esito.returncode != 0:
            non_protetti.append(str(p))
    assert not non_protetti, (
        "registri non ignorati, finirebbero nel repository pubblico: "
        + ", ".join(non_protetti))


# --------------------------------------------------------------------------
# due difetti trovati depurando, e i test che li tengono chiusi
# --------------------------------------------------------------------------

def test_la_scorciatoia_sul_titolo_non_compete_col_tipo_dichiarato(tmp_path):
    """«che vini ho in cucina» rispondeva anche «Divano rosso» e «Cassa di
    bottiglie vuote»: «rosso» e «bottiglie» stavano fra le parole usate per
    riconoscere un vino dal titolo. Un ripiego non deve competere col dato."""
    r = inv.Inventario(tmp_path / "i.jsonl")
    cucina = lg.dal_percorso("/f/cucina/x.jpg", "/f")
    for tipo, titolo in [("altro", "Divano rosso"), ("vino", "Barolo 2016"),
                         ("vino", "Franciacorta Saten"),
                         ("altro", "Cassa di bottiglie vuote")]:
        r.registra(tipo, titolo, luogo=cucina)
    e = vc.rispondi(r, "che vini ho in cucina")
    titoli = {o["titolo"] for o in e["oggetti"]}
    assert titoli == {"Barolo 2016", "Franciacorta Saten"}
    assert "Divano rosso" not in e["testo_risposta"]


def test_il_ripiego_sul_titolo_serve_ancora_quando_serve(tmp_path):
    """Se nessun oggetto è catalogato come vino, il titolo è l'unica strada —
    ma solo con termini inequivocabili."""
    r = inv.Inventario(tmp_path / "i.jsonl")
    cucina = lg.dal_percorso("/f/cucina/x.jpg", "/f")
    for titolo in ("Divano rosso", "Barolo Serralunga 2016",
                   "Cassa di bottiglie vuote"):
        r.registra("altro", titolo, luogo=cucina)
    e = vc.rispondi(r, "che vini ho in cucina")
    assert {o["titolo"] for o in e["oggetti"]} == {"Barolo Serralunga 2016"}


def test_una_fusione_di_titoli_non_e_mai_silenziosa(tmp_path):
    """«The Matrix» e «MATRIX, THE» devono fondersi — è il motivo per cui
    l'articolo si toglie. Ma allora si fondono anche «Heat» e «The Heat», che
    sono due film. Non si può avere l'una senza l'altra: quindi la fusione si
    vede. Una fusione visibile è un problema; una silenziosa è un registro
    che mente."""
    r = inv.Inventario(tmp_path / "i.jsonl")
    for titolo in ("Heat", "The Heat", "MATRIX, THE", "The Matrix", "Solaris"):
        r.registra("dvd", titolo)
    assert len(r.voci) == 3
    fusioni = {v["chiave"]: v["titoli_visti"] for v in r.fusioni()}
    assert fusioni["dvd:heat"] == ["Heat", "The Heat"]
    assert fusioni["dvd:matrix"] == ["MATRIX, THE", "The Matrix"]
    # un titolo visto una volta sola non è una fusione
    assert "dvd:solaris" not in fusioni


def test_le_fusioni_sopravvivono_alla_rilettura(tmp_path):
    p = tmp_path / "i.jsonl"
    r = inv.Inventario(p)
    r.registra("dvd", "Heat")
    r.registra("dvd", "The Heat")
    assert len(inv.Inventario(p).fusioni()) == 1


# --------------------------------------------------------------------------
# LA CONSOLE — una schermata sola, e deve dire la verità
# --------------------------------------------------------------------------

def _console(nome):
    web = pathlib.Path(__file__).resolve().parent.parent / "occhio" / "web"
    return (web / nome).read_text(encoding="utf-8")


def test_ogni_id_cercato_dalla_console_esiste():
    """Stessa ragione di `test_ogni_id_cercato_dal_javascript_esiste`: un
    `$("#x")` su un elemento assente rompe l'intero file con un TypeError, e
    la pagina resta lì bella e morta. Il difetto è già arrivato al ramo
    remoto una volta."""
    import re
    html, js = _console("console.html"), _console("console.js")
    presenti = set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))
    cercati = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', js))
    cercati |= set(re.findall(r'querySelector(?:All)?\("#([A-Za-z0-9_-]+)', js))
    mancanti = cercati - presenti
    assert not mancanti, f"console.js cerca id assenti dall'HTML: {sorted(mancanti)}"


def test_la_console_dichiara_i_suoi_fogli():
    html = _console("console.html")
    assert 'href="console.css"' in html and 'src="console.js"' in html
    # il segno in alto porta alla telecamera: la console non è un vicolo cieco
    assert 'href="/"' in html


def test_le_classi_disegnate_dalla_console_esistono_nel_foglio():
    """Una classe scritta dal JavaScript e assente dal CSS non dà errore:
    dà una schermata senza stile, che è peggio perché sembra funzionare."""
    import re
    js, css = _console("console.js"), _console("console.css")
    for classe in ("zona", "spenta", "allarme", "buono", "riga", "segnale",
                   "comprato", "manca", "vuoto", "firma", "fatto", "aperto",
                   "banco", "resta"):
        assert classe in js, f"la classe {classe} non è più usata: aggiorna il test"
        assert f".{classe}" in css, f"console.css non definisce .{classe}"
    # tre stati e tre colori: se qualcuno ne aggiunge un quarto, la pianta
    # colora una zona con `undefined` e non lo dice a nessuno
    colori = re.search(r"const COLORI = \{([^}]*)\}", js).group(1)
    assert sorted(re.findall(r"(\w+):", colori)) == ["da_fare", "fatta", "manca"]


def test_la_console_e_i_suoi_fogli_sono_serviti(occhio_in_ascolto):
    for risorsa in ("/console", "/console.css", "/console.js"):
        with urllib.request.urlopen(occhio_in_ascolto + risorsa, timeout=10) as r:
            assert r.status == 200 and len(r.read()) > 200


def test_il_quadro_e_uno_e_arriva_intero(occhio_in_ascolto):
    """Cinque letture separate disegnerebbero cinque schermate incoerenti
    mentre arrivano: `/api/quadro` o c'è tutto o non c'è."""
    codice, q = chiama(occhio_in_ascolto + "/api/quadro")
    assert codice == 200
    for chiave in ("oggetti", "zone", "totale", "fusioni", "pianta", "stub",
                   "consegne", "differenza", "vendite", "chiari"):
        assert chiave in q, f"il quadro non porta {chiave}"
    assert q["stub"] is True          # la fixture gira in modo stub
    assert q["oggetti"] == [] and q["totale"] == 0


def test_il_quadro_conta_gli_oggetti_che_il_registro_contiene(occhio_in_ascolto):
    """Il numero in alto e l'elenco sotto vengono dalla stessa lettura: se
    divergono, la schermata mente su sé stessa."""
    with srv.Handler.stato.lock:
        r = srv.Handler.stato.inventario
        r.registra("dvd", "Heat", luogo={"stanza": "salotto"})
        r.registra("dvd", "Solaris", luogo={"stanza": "salotto"})
        r.registra("altro", "Phon", luogo={"stanza": "bagno"})
    codice, q = chiama(occhio_in_ascolto + "/api/quadro")
    assert codice == 200
    assert q["totale"] == 3 == len(q["oggetti"])
    assert sum(q["zone"].values()) == 3
    assert set(q["zone"]) == {"salotto", "bagno"}
    # ogni oggetto porta la zona con cui la pianta lo filtrerà
    assert {o["titolo"]: o["zona"] for o in q["oggetti"]} == {
        "Heat": "salotto", "Solaris": "salotto", "Phon": "bagno"}


def test_una_fusione_arriva_fino_alla_console(occhio_in_ascolto):
    """Il registro non nasconde le fusioni; nemmeno il quadro."""
    with srv.Handler.stato.lock:
        r = srv.Handler.stato.inventario
        r.registra("dvd", "Heat")
        r.registra("dvd", "The Heat")
    _, q = chiama(occhio_in_ascolto + "/api/quadro")
    assert [f["titoli"] for f in q["fusioni"]] == [["Heat", "The Heat"]]


def test_il_quadro_regge_i_registri_mancanti(occhio_in_ascolto):
    """Consegne, PORTAVIA e CHIARI sono file a sé: se non esistono ancora —
    ed è il caso di chiunque apra la console il primo giorno — il quadro
    resta valido e lo dice con dei vuoti, non con un errore 500."""
    _, q = chiama(occhio_in_ascolto + "/api/quadro")
    assert q["consegne"] == [] and q["differenza"] is None
    assert "consegne_errore" not in q, q.get("consegne_errore")


# --------------------------------------------------------------------------
# l'incasso: due valute non si sommano
# --------------------------------------------------------------------------

def test_l_incasso_non_somma_mai_euro_e_chiari(tmp_path):
    """La console lo ha reso visibile: mostrava un totale e accanto l'unità
    dell'ultima vendita. Sommare euro e CHIARI dà un numero che non esiste in
    nessuna delle due valute."""
    p = pv.Portavia(tmp_path / "pv.jsonl", regole(commissione=0.10))
    p.vendita("dvd:heat", "Heat", 100.0)
    p._scrivi({"tipo": "vendita", "chiave": "dvd:solaris", "titolo": "Solaris",
               "prezzo": 15, "commissione": 2, "al_proprietario": 13,
               "valuta": "chiari", "soggiorno": "", "alloggio": "",
               "momento": "2026-09-05T00:00:00Z"})
    i = p.incasso()
    assert i["vendite"] == 2
    assert i["valute"] == ["EUR", "chiari"]
    assert i["per_valuta"]["EUR"]["lordo"] == 100.0
    assert i["per_valuta"]["chiari"]["lordo"] == 15.0
    # i campi piatti valgono solo con una valuta sola: qui devono tacere
    assert i["lordo"] is None and i["al_proprietario"] is None
    assert i["valuta"] is None


def test_con_una_valuta_sola_i_campi_piatti_restano(tmp_path):
    p = pv.Portavia(tmp_path / "pv.jsonl", regole(commissione=0.12))
    p.vendita("dvd:heat", "Heat", 100.0)
    i = p.incasso()
    assert i["valuta"] == "EUR" and i["lordo"] == 100.0
    assert i["al_proprietario"] == 88.0
    assert i["per_valuta"]["EUR"]["commissione"] == 12.0


def test_nascondere_un_elemento_lo_nasconde_davvero():
    """`el.hidden = true` non fa niente se il foglio dà a quell'elemento un
    `display` esplicito. È successo due volte: il pannello sopra il video, e
    la legenda che spiegava tre colori assenti dalla schermata. Un elenco di
    eccezioni invecchia; una regola per tutti no."""
    import re
    for foglio in ("stile.css", "console.css"):
        css = re.sub(r"\s+", "", _console(foglio))
        # il selettore dev'essere `[hidden]` da solo, non `#x li[hidden]`:
        # prima di lui può esserci solo la fine di una regola o di un commento
        assert re.search(r"(^|[}/;])\[hidden\]\{display:none!important;?\}", css), (
            f"{foglio} non neutralizza [hidden]: nascondere non nasconderà")


# --------------------------------------------------------------------------
# i falsificatori: un crash non è mai «REGGE»
# --------------------------------------------------------------------------

def test_nessun_falsificatore_muore_prima_di_essere_protetto():
    """`main_protetto` trasforma un'eccezione in esito 2 — ma solo dentro
    `main()`. Un import in testa al file avviene PRIMA, e Python esce con 1,
    che in questo contratto significa REGGE.

    È successo il 05/09: `h5_tracce` importava `esperimenti.tracce`, che
    importa `dotenv`, assente qui. H5 risultava «regge» senza che una sola
    domanda fosse mai partita — il difetto di §4 dentro lo strumento
    costruito per impedirlo, per la seconda volta.
    """
    import subprocess
    radice = pathlib.Path(__file__).resolve().parent.parent
    falsificatori = sorted((radice / "falsificatori").glob("h*.py"))
    assert len(falsificatori) >= 9, "falsificatori spariti?"
    for f in falsificatori:
        esito = subprocess.run(
            [sys.executable, "-c",
             f"import importlib; importlib.import_module('falsificatori.{f.stem}')"],
            cwd=radice, capture_output=True, text=True)
        assert esito.returncode == 0, (
            f"{f.name} non si importa nemmeno: uscirebbe con 1, cioè «REGGE».\n"
            + esito.stderr)


# --------------------------------------------------------------------------
# i tre generi — idea di Claudio Terzi, 5 settembre 2026
# --------------------------------------------------------------------------

def test_cio_che_non_e_dichiarato_e_merce(tmp_path):
    """Il difetto sta dal lato sicuro: un genere non dichiarato vale MERCE,
    cioè qualcosa che può uscire di casa e va riconciliato. Sbagliare in
    questa direzione fa vedere un'assenza in più; l'altra la nasconde."""
    r = pv.Regole(prezzo_minimo={"dvd:heat": 8.0})
    assert r.genere("dvd:heat") == pv.MERCE
    assert r.genere("mai visto prima") == pv.MERCE


def test_un_genere_inventato_non_entra(tmp_path):
    with pytest.raises(ValueError):
        pv.Regole(generi={"x": "abbonamento"})
    p = pv.Portavia(tmp_path / "pv.jsonl", regole())
    with pytest.raises(ValueError):
        p.vendita("dvd:heat", "Heat", 9.0, genere="noleggio")


def test_un_esperienza_venduta_non_spiega_nessuna_assenza(tmp_path):
    """L'invariante di H11. Se cadesse, il registro imparerebbe a
    giustificare le assenze con incassi che non c'entrano — §4 con i soldi."""
    p = pv.Portavia(tmp_path / "pv.jsonl", pv.Regole(
        prezzo_minimo={"altro:vasca": 20.0, "dvd:heat": 8.0},
        generi={"altro:vasca": pv.ESPERIENZA}))
    p.vendita("altro:vasca", "Serata in vasca", 30.0)
    p.vendita("dvd:heat", "Heat", 12.0)
    d = {"mancanti": [{"chiave": "altro:vasca", "titolo": "Serata in vasca"},
                      {"chiave": "dvd:heat", "titolo": "Heat"}]}
    s = pv.spiega_mancanti(d, p)
    assert [o["titolo"] for o in s["comprati"]] == ["Heat"]
    assert [o["titolo"] for o in s["non_spiegati"]] == ["Serata in vasca"]
    # ma l'incasso le conta tutte e due: il divieto è di spiegare, non di incassare
    assert s["incasso"]["vendite"] == 2


def test_il_consumo_spiega_l_assenza_perche_e_finito(tmp_path):
    """La bottiglia bevuta manca quanto il phon rubato. È il genere della
    vendita a separarle, non l'inventario, che le vede uguali."""
    p = pv.Portavia(tmp_path / "pv.jsonl", pv.Regole(
        prezzo_minimo={"vino:barolo": 28.0}, generi={"vino:barolo": pv.CONSUMO}))
    p.vendita("vino:barolo", "Barolo", 40.0)
    s = pv.spiega_mancanti({"mancanti": [{"chiave": "vino:barolo", "titolo": "Barolo"}]}, p)
    assert [o["titolo"] for o in s["comprati"]] == ["Barolo"]


def test_una_vendita_scritta_prima_dei_generi_vale_merce(tmp_path):
    """Compatibilità all'indietro dalla parte che non nasconde niente."""
    p = pv.Portavia(tmp_path / "pv.jsonl", regole())
    p._scrivi({"tipo": "vendita", "chiave": "dvd:heat", "titolo": "Heat",
               "prezzo": 9.0, "commissione": 1.0, "al_proprietario": 8.0,
               "valuta": "EUR", "soggiorno": "", "alloggio": "",
               "momento": "2026-09-04T00:00:00Z"})
    s = pv.spiega_mancanti({"mancanti": [{"chiave": "dvd:heat", "titolo": "Heat"}]}, p)
    assert [o["titolo"] for o in s["comprati"]] == ["Heat"]
    assert p.incasso()["per_genere"]["merce"]["vendite"] == 1


def test_l_incasso_tiene_i_generi_separati(tmp_path):
    p = pv.Portavia(tmp_path / "pv.jsonl", pv.Regole(
        prezzo_minimo={"a": 1.0, "b": 1.0, "c": 1.0},
        commissione=0.10,
        generi={"b": pv.CONSUMO, "c": pv.ESPERIENZA}))
    p.vendita("a", "Lampada", 100.0)
    p.vendita("b", "Barolo", 40.0)
    p.vendita("c", "Serata in vasca", 30.0)
    i = p.incasso()
    assert sorted(i["per_genere"]) == ["consumo", "esperienza", "merce"]
    assert i["per_genere"]["merce"]["lordo"] == 100.0
    assert i["per_genere"]["esperienza"]["al_proprietario"] == 27.0
    # una valuta sola: i campi piatti restano, e sommano i tre generi
    assert i["lordo"] == 170.0


@pytest.mark.parametrize("quanti", [0, -1, 2.5])
def test_una_quantita_che_non_e_un_intero_positivo_non_entra(tmp_path, quanti):
    p = pv.Portavia(tmp_path / "pv.jsonl", regole())
    with pytest.raises(ValueError):
        p.vendita("dvd:heat", "Heat", 9.0, quantita=quanti)


def test_la_quantita_e_un_fatto_sulla_vendita_non_una_giacenza(tmp_path):
    """Due bottiglie vendute si scrivono; quante ce ne fossero, questo
    modulo non lo sa e non finge di saperlo — l'inventario tiene una voce
    per titolo, non un conteggio."""
    p = pv.Portavia(tmp_path / "pv.jsonl", regole())
    v = p.vendita("vino:barolo", "Barolo", 80.0, genere=pv.CONSUMO, quantita=2)
    assert v["quantita"] == 2
    assert "giacenza" not in v and "rimanenti" not in v


def test_il_quadro_porta_i_nomi_dei_tre_generi(occhio_in_ascolto):
    """La console non deve inventarsi i nomi commerciali: li riceve."""
    _, q = chiama(occhio_in_ascolto + "/api/quadro")
    assert q["generi"] == {"merce": "PORTAVIA", "consumo": "APRILA",
                           "esperienza": "RESTACI"}


def test_la_console_distingue_l_esperienza_dalle_altre_due():
    """Il segnale «resta in casa» sta accanto al solo genere che non spiega
    un'assenza: è l'unica differenza che conta a fine soggiorno, e deve
    vedersi senza aprire il codice."""
    js = _console("console.js")
    assert 'ordine = ["merce", "consumo", "esperienza"]' in js
    assert 'g === "esperienza" ? \'<span class="resta">resta in casa</span>\'' in js


def test_la_pianta_non_disegna_niente_che_non_sia_stato_misurato():
    """Pareti spesse, pavimento e ombra si calcolano dai poligoni. Una porta
    o un mobile no: disegnarli sarebbe inventare una casa, e questa
    schermata sta accanto a una catena di prove."""
    js = _console("console.js")
    for inventato in ("porta", "finestra", "divano", "letto", "mobile"):
        # nessun disegno di arredo: la parola può comparire solo nei commenti
        codice = "\n".join(r for r in js.split("\n") if not r.strip().startswith(("//", "*", "/*")))
        assert f'"{inventato}"' not in codice.lower(), (
            f"la pianta disegna un {inventato} che nessuno ha misurato")
