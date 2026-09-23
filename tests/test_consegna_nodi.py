"""La consegna a un nodo sorella deve essere GENERATA, non ricopiata.

CLAUDE.md §6 regola 2 dice: un concetto, un file. Un briefing scritto a mano
diventa la settima copia dell'indice — quella che nessuno aggiorna e che
pretende la stessa autorita' del canone. Percio' `rassegna.py --consegna` si
costruisce dai compiti e dal registro: se quelli cambiano, cambia lei, e non
esiste una versione vecchia che sopravvive.

    python -m pytest tests/test_consegna_nodi.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import rassegna  # noqa: E402


def test_la_consegna_nomina_ogni_compito_aperto(capsys):
    assert rassegna.consegna() == 0
    out = capsys.readouterr().out
    for chiave, compito in rassegna.COMPITI.items():
        assert chiave in out, "manca il compito %s" % chiave
        assert compito["titolo"] in out


def test_un_compito_nuovo_entra_da_solo_nella_consegna(capsys):
    # Se questo test fallisce, qualcuno ha ricopiato i compiti a mano.
    rassegna.COMPITI["C99"] = {
        "titolo": "compito di prova",
        "comando": "true",
        "cosa_si_impara": "niente, e' una prova",
    }
    try:
        rassegna.consegna()
        assert "compito di prova" in capsys.readouterr().out
    finally:
        del rassegna.COMPITI["C99"]


def test_la_consegna_dichiara_l_origine_e_non_si_spaccia_per_canone(capsys):
    rassegna.consegna()
    out = capsys.readouterr().out
    assert "CT-LGAI-001" in out
    assert "non fidarti di questo riassunto" in out
    assert "CLAUDE.md" in out and "LETTERA_AI_NODI.md" in out


def test_la_consegna_vieta_le_impressioni(capsys):
    # E' il punto per cui esiste: chiedere esecuzioni, non pareri (§7).
    rassegna.consegna()
    out = capsys.readouterr().out
    assert "impressione" in out
    assert "vale_come_conferma: false" in out
    assert "puo' fallire" in out


def test_i_limiti_dichiarati_arrivano_dal_registro(tmp_path, monkeypatch, capsys):
    reg = tmp_path / "memoria"
    reg.mkdir()
    (reg / "REGISTRO_NODI.jsonl").write_text(json.dumps({
        "data_iso": "2026-09-23T00:00:00Z", "nodo": "prova", "tipo": "limite",
        "azione": "limite dichiarato: la porta e' chiusa",
        "comando": "false", "uscita": 1, "file": [],
    }) + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rassegna.consegna()
    out = capsys.readouterr().out
    assert "la porta e' chiusa" in out and "--ritenta" in out


def test_senza_limiti_non_inventa_una_sezione(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)          # nessun memoria/REGISTRO_NODI.jsonl
    rassegna.consegna()
    assert "fai cadere un limite" not in capsys.readouterr().out


def test_l_url_e_quello_del_repository_non_uno_inventato():
    url = rassegna._url_repository()
    assert url.startswith("https://") and not url.endswith(".git")
    assert "Rosso-rosso-rosso" in url
