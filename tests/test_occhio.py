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
