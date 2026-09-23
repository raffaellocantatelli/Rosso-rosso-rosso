"""Il giro deve tacere quando non c'e' niente, e parlare quando c'e'.

Un automatismo che dice «tutto ok» ogni giorno non viene piu' letto — compreso
il giorno in cui qualcosa era successo. E' il difetto di CLAUDE.md §4 in forma
di notifica: rumore che il sistema produce su se' stesso.

Questi test bloccano i due modi di sbagliare, in direzioni opposte: svegliare
l'autore per niente, e tacere quando qualcosa si e' rotto.

    python -m pytest tests/test_giro.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import giro as g  # noqa: E402


def _stato(uscite=None, contatori=None, quando="2026-09-23T00:00:00Z"):
    uscite = uscite or {"limiti": 1, "integrita": 0, "test": 0, "core": 1}
    return {
        "data_iso": quando,
        "controlli": {n: {"uscita": u, "riga": ""} for n, u in uscite.items()},
        "contatori": contatori or {"contatti": 0, "risposte_nodi": 0, "verifiche": 3},
    }


def test_niente_di_nuovo_non_produce_notizie():
    notizie, rotture = g.confronta(_stato(), _stato())
    assert notizie == [] and rotture == []


def test_un_limite_caduto_e_una_notizia():
    # --ritenta esce 0 solo se un limite e' caduto: e' l'evento piu' utile.
    notizie, rotture = g.confronta(_stato({"limiti": 0}), _stato())
    assert any("LIMITE E' CADUTO" in n for n in notizie)
    assert rotture == []


def test_una_riga_in_piu_nei_contatti_e_la_notizia_che_il_progetto_aspetta():
    notizie, _ = g.confronta(_stato(contatori={"contatti": 1}), _stato(contatori={"contatti": 0}))
    assert any("contatti: 0 -> 1" in n and "dall'esterno" in n for n in notizie)


def test_righe_sparite_sono_una_rottura_non_una_notizia():
    _, rotture = g.confronta(_stato(contatori={"verifiche": 2}), _stato(contatori={"verifiche": 5}))
    assert any("SPARITE" in r for r in rotture)


def test_la_suite_rotta_si_dice_sempre():
    _, rotture = g.confronta(_stato({"test": 1}), _stato({"test": 1}))
    assert any("test" in r for r in rotture), "una rottura che dura non smette di essere una rottura"


def test_l_integrita_violata_si_dice_sempre():
    _, rotture = g.confronta(_stato({"integrita": 3}), _stato({"integrita": 3}))
    assert any("integrita" in r for r in rotture)


def test_un_controllo_che_cambia_uscita_e_una_notizia():
    notizie, _ = g.confronta(_stato({"core": 0}), _stato({"core": 1}))
    assert any("core" in n and "1 -> 0" in n for n in notizie)


def test_il_primo_giro_non_tace(tmp_path, monkeypatch, capsys):
    # Senza un termine di paragone non si puo' dire «niente di nuovo».
    monkeypatch.setattr(g, "STORICO", tmp_path / "giro.jsonl")
    monkeypatch.setattr(g, "CONTROLLI", [("finto", "true", "prova")])
    monkeypatch.setattr(g, "CONTATORI", {"finti": str(tmp_path / "vuoto.jsonl")})
    assert g.giro() == 1
    assert "Primo giro" in capsys.readouterr().out


def test_il_secondo_giro_identico_tace(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(g, "STORICO", tmp_path / "giro.jsonl")
    monkeypatch.setattr(g, "CONTROLLI", [("finto", "true", "prova")])
    monkeypatch.setattr(g, "CONTATORI", {"finti": str(tmp_path / "vuoto.jsonl")})
    g.giro()
    capsys.readouterr()
    assert g.giro() == 0
    assert capsys.readouterr().out.strip() == ""


def test_prova_non_scrive(tmp_path, monkeypatch):
    storico = tmp_path / "giro.jsonl"
    monkeypatch.setattr(g, "STORICO", storico)
    monkeypatch.setattr(g, "CONTROLLI", [("finto", "true", "prova")])
    monkeypatch.setattr(g, "CONTATORI", {})
    g.giro(prova=True)
    assert not storico.exists()


def test_ogni_controllo_e_un_comando_che_puo_fallire():
    # Un controllo che non puo' fallire non misura niente (LETTERA_AI_NODI.md).
    for nome, comando, significato in g.CONTROLLI:
        assert comando.strip(), nome
        assert significato.strip(), nome
        assert comando.split()[0] in ("python3", "python"), nome


def test_un_comando_che_non_torna_non_blocca_il_giro():
    uscita, riga = g._esegui("sleep 5", secondi=1)
    assert uscita == 124 and "scaduto" in riga
