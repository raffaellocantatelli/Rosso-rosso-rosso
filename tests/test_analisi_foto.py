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
