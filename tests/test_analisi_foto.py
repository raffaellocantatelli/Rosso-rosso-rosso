"""Test di analisi_foto: le impronte reggono la ricompressione, i metadati
assenti restano UNKNOWN e la ricerca inversa senza chiave non finge di aver cercato."""

import json

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

import analisi_foto as af  # noqa: E402


def _immagine(tmp_path, nome, colore_fondo=(20, 20, 20), riquadro=None, dim=(400, 300), qualita=95):
    img = Image.new("RGB", dim, colore_fondo)
    if riquadro:
        img.paste((230, 230, 220), riquadro)
    percorso = tmp_path / nome
    img.save(percorso, quality=qualita)
    return percorso


def test_sha256_distingue_i_file_le_impronte_percettive_no(tmp_path):
    """Due file diversi con la stessa immagine: sha256 diverso, dhash vicino."""
    a = _immagine(tmp_path, "a.jpg", riquadro=(50, 50, 200, 200), qualita=95)
    b = _immagine(tmp_path, "b.jpg", riquadro=(50, 50, 200, 200), qualita=40)

    assert af.sha256(a) != af.sha256(b)
    with Image.open(a) as ia, Image.open(b) as ib:
        assert af.distanza(af.dhash(ia), af.dhash(ib)) <= 4


def test_impronte_distinguono_immagini_diverse(tmp_path):
    a = _immagine(tmp_path, "a.jpg", riquadro=(10, 10, 120, 120))
    b = _immagine(tmp_path, "b.jpg", colore_fondo=(240, 240, 240))
    with Image.open(a) as ia, Image.open(b) as ib:
        assert af.distanza(af.dhash(ia), af.dhash(ib)) > 6


def test_metadati_assenti_sono_dichiarati_non_inventati(tmp_path):
    percorso = _immagine(tmp_path, "senza_exif.jpg")
    m = af.metadati(percorso)
    assert m["fotocamera"] is None and m["data_scatto"] is None and m["gps"] is None
    assert set(m["mancanti"]) == {"fotocamera", "data_scatto", "gps"}
    assert m["pixel"] == [400, 300]


def test_area_stampata_none_su_immagine_chiara(tmp_path):
    """Su una stampa chiara il metodo non deve tirare a indovinare."""
    percorso = _immagine(tmp_path, "chiara.jpg", colore_fondo=(245, 245, 245))
    with Image.open(percorso) as img:
        assert af.rileva_stampa(img) is None


def test_area_stampata_trova_il_rettangolo_scuro(tmp_path):
    img = Image.new("RGB", (400, 300), (250, 250, 250))
    img.paste((15, 15, 15), (100, 60, 300, 240))
    percorso = tmp_path / "stampa.jpg"
    img.save(percorso, quality=95)
    with Image.open(percorso) as aperta:
        esito = af.rileva_stampa(aperta)
    assert esito is not None
    x0, y0, x1, y1 = esito["box"]
    assert abs(x0 - 100) < 15 and abs(y0 - 60) < 15
    assert abs(x1 - 300) < 15 and abs(y1 - 240) < 15


def test_ricerca_inversa_senza_chiave_non_finge(tmp_path, monkeypatch):
    monkeypatch.delenv("TINEYE_API_KEY", raising=False)
    monkeypatch.delenv("SAUCENAO_API_KEY", raising=False)
    percorso = _immagine(tmp_path, "x.jpg")

    esito = af.ricerca_inversa(percorso)
    assert esito["eseguita"] is False
    assert esito["risultati"] == []
    assert "NON ESEGUITA" in esito["motivo"]
    assert set(esito["da_aprire_a_mano"]) >= {"google_lens", "tineye", "yandex"}


def test_link_per_url_pubblico_contengono_l_url(tmp_path):
    percorso = _immagine(tmp_path, "x.jpg")
    esito = af.ricerca_inversa(percorso, url_pubblico="https://esempio.it/f oto.jpg")
    assert "esempio.it" in esito["da_aprire_a_mano"]["tineye"]
    assert " " not in esito["da_aprire_a_mano"]["tineye"]


def test_indice_trova_doppioni_e_quasi_doppioni(tmp_path):
    cartella = tmp_path / "archivio"
    cartella.mkdir()
    _immagine(cartella, "uno.jpg", riquadro=(50, 50, 200, 200), qualita=95)
    _immagine(cartella, "uno_copia.jpg", riquadro=(50, 50, 200, 200), qualita=95)
    _immagine(cartella, "uno_ricompressa.jpg", riquadro=(50, 50, 200, 200), qualita=35)
    _immagine(cartella, "altra.jpg", colore_fondo=(250, 250, 250))

    esito = af.indicizza(cartella, tmp_path / "indice.jsonl")
    assert esito["immagini"] == 4 and esito["leggibili"] == 4
    assert esito["stesso_id_immagine"] == []  # nessun file di test porta un ImageUniqueID
    assert len(esito["file_identici"]) == 1
    assert any("ricompressa" in c["a"] or "ricompressa" in c["b"] for c in esito["quasi_doppioni"])

    righe = (tmp_path / "indice.jsonl").read_text().strip().splitlines()
    assert len(righe) == 4 and json.loads(righe[0])["dhash"]


def test_cli_json_su_file_reale(tmp_path, capsys):
    percorso = _immagine(tmp_path, "cli.jpg", riquadro=(60, 60, 180, 180))
    assert af.main([str(percorso), "--json"]) == 0
    scheda = json.loads(capsys.readouterr().out)
    assert scheda["sha256"] and scheda["dhash"] and scheda["misure"]["nitidezza"] >= 0


def test_cli_file_inesistente(tmp_path):
    assert af.main([str(tmp_path / "nessuno.jpg")]) == 2


# --- miniatura EXIF: la versione precedente del file, quando c'e' -----------

def _blob_exif_con_miniatura(mini: Image.Image) -> bytes:
    """Blob EXIF sintetico: intestazione, riempimento, poi la miniatura JPEG."""
    import io
    buf = io.BytesIO()
    mini.save(buf, "JPEG", quality=70)
    return b"Exif\x00\x00" + b"\x00" * 120 + buf.getvalue()


def test_miniatura_coerente_quando_mostra_la_stessa_scena(tmp_path):
    grande = Image.new("RGB", (400, 300), (30, 30, 30))
    grande.paste((220, 210, 200), (120, 80, 300, 240))
    grande.info["exif"] = _blob_exif_con_miniatura(grande.resize((160, 120)))

    esito = af.miniatura_exif(tmp_path / "finto.jpg", grande)
    assert esito is not None and esito["presente"]
    assert esito["coerente"] is True
    assert esito["distanza_dall_immagine"] <= 16


def test_miniatura_incoerente_rivela_il_ritaglio(tmp_path):
    """La miniatura conserva l'inquadratura larga, l'immagine e' stata ritagliata."""
    originale = Image.new("RGB", (400, 300), (240, 240, 240))
    originale.paste((10, 10, 10), (0, 0, 200, 300))
    ritagliata = Image.new("RGB", (300, 300), (240, 240, 240))
    ritagliata.paste((10, 10, 10), (0, 0, 40, 60))
    ritagliata.info["exif"] = _blob_exif_con_miniatura(originale.resize((160, 120)))

    esito = af.miniatura_exif(tmp_path / "finto.jpg", ritagliata)
    assert esito is not None
    assert esito["coerente"] is False


def test_miniatura_assente_non_e_un_errore(tmp_path):
    nuda = Image.new("RGB", (100, 100), (128, 128, 128))
    assert af.miniatura_exif(tmp_path / "x.jpg", nuda) is None


def test_creator_tool_da_xmp():
    xmp = b'<x:xmpmeta><rdf:Description xmp:CreatorTool="Picasa"/></x:xmpmeta>'
    assert af._creator_tool(xmp) == "Picasa"
    assert af._creator_tool(b"") is None
    assert af._creator_tool(b"<x:xmpmeta/>") is None


# --- formato della stampa istantanea dalla geometria dei bordi --------------

def _stampa_finta(piano, stampa_wh, finestra_box, colore_immagine=(40, 45, 60)):
    """Costruisce una stampa su un piano scuro: carta bianca con una finestra."""
    tela = Image.new("RGB", piano, (25, 25, 30))
    carta = Image.new("RGB", stampa_wh, (248, 246, 240))
    carta.paste(colore_immagine, finestra_box)
    tela.paste(carta, ((piano[0] - stampa_wh[0]) // 2, (piano[1] - stampa_wh[1]) // 2))
    return tela


def test_formato_integrale_quadrata():
    """Proporzioni SX-70/600: stampa 88x107, finestra 79x79 in alto."""
    tela = _stampa_finta((700, 800), (440, 535), (22, 20, 417, 415))
    esito = af.formato_stampa(tela)
    assert esito is not None
    assert esito["formato"] == "integrale_quadrata"
    assert esito["bordo_largo"] == "basso"
    assert esito["asimmetria"] >= 2.5


def test_formato_integrale_rettangolare():
    """Proporzioni Spectra: stampa 101x108, finestra 91x73 in alto."""
    tela = _stampa_finta((700, 800), (505, 540), (25, 20, 480, 385))
    esito = af.formato_stampa(tela)
    assert esito is not None
    assert esito["formato"] == "integrale_rettangolare"
    assert esito["bordo_largo"] == "basso"


def test_formato_bordi_uniformi_non_e_integrale():
    """Quattro bordi simili: pellicola a strappo o stampa da laboratorio."""
    tela = _stampa_finta((700, 800), (440, 535), (20, 24, 420, 511))
    esito = af.formato_stampa(tela)
    assert esito is not None
    assert esito["formato"] == "bordi_uniformi"
    assert esito["asimmetria"] < 2.5


def test_formato_none_se_la_stampa_e_tagliata():
    """Stampa che esce dall'inquadratura: nessuna cornice chiusa, nessuna ipotesi."""
    tela = _stampa_finta((700, 800), (440, 535), (22, 20, 417, 415))
    tagliata = tela.crop((200, 100, 700, 700))
    assert af.formato_stampa(tagliata) is None


def test_formato_none_su_piano_bianco():
    """Piano chiaro quanto la carta: il metodo non puo' isolare la stampa."""
    tela = Image.new("RGB", (700, 800), (250, 250, 250))
    tela.paste((40, 45, 60), (150, 150, 550, 550))
    esito = af.formato_stampa(tela)
    assert esito is None or esito["formato"] == "bordi_uniformi"


def test_riquadro_limita_la_misura_del_formato(tmp_path):
    """Con un oggetto chiaro estraneo accanto alla stampa, il riquadro salva la misura."""
    scena = Image.new("RGB", (1400, 800), (25, 25, 30))
    stampa = _stampa_finta((700, 800), (440, 535), (22, 20, 417, 415))
    scena.paste(stampa, (700, 0))
    scena.paste((252, 252, 250), (60, 100, 620, 700))   # oggetto bianco che confonde
    percorso = tmp_path / "scena.jpg"
    scena.save(percorso, quality=95)

    senza = af.analizza(percorso)["formato_stampa"]
    con = af.analizza(percorso, riquadro=(700, 0, 1400, 800))["formato_stampa"]
    assert con is not None and con["formato"] == "integrale_quadrata"
    assert senza is None or senza["formato"] != "integrale_quadrata"


def test_cli_riquadro_malformato(tmp_path):
    percorso = _immagine(tmp_path, "x.jpg")
    assert af.main([str(percorso), "--riquadro", "10,20,30"]) == 2
    assert af.main([str(percorso), "--riquadro", "300,10,100,90"]) == 2
    assert af.main([str(percorso), "--riquadro", "a,b,c,d"]) == 2
