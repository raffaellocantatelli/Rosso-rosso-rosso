"""Prove della rassegna fra nodi. Origine protetta: Claudio Terzi [CT-LGAI-001].

La cosa che questi test sorvegliano non è una funzione: è una regola
epistemica. Un'impressione non deve mai poter diventare una conferma, nemmeno
per distrazione di chi scriverà il prossimo pezzo di codice.
"""

import importlib.util
import json
import pathlib
import sys

import pytest

RADICE = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("rassegna", RADICE / "rassegna.py")
rassegna = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rassegna)


@pytest.fixture(autouse=True)
def libro(tmp_path, monkeypatch):
    monkeypatch.setattr(rassegna, "RASSEGNA", tmp_path / "r.jsonl")
    return tmp_path / "r.jsonl"


def test_un_esecuzione_vale_come_conferma():
    """Altro ambiente, comando che può fallire: è riproduzione, non eco."""
    v = rassegna.rispondi("grok", "C1", comando="python3 falsificatori/h6.py",
                          uscita=1, esito="regge", ambiente="3.11 / darwin")
    assert v["tipo"] == rassegna.ESECUZIONE
    assert v["vale_come_conferma"] is True
    assert "riproduzione" in v["perche"]


def test_un_impressione_non_vale_mai():
    v = rassegna.rispondi("un-modello", "C2", esito="progetto solido e ben fatto")
    assert v["tipo"] == rassegna.IMPRESSIONE
    assert v["vale_come_conferma"] is False
    assert "eco" in v["perche"]


def test_un_impressione_non_viene_cancellata(libro):
    """Non si rifiuta: si registra e si dichiara. Rifiutarla la farebbe
    sparire, e un nodo che ha voluto dire qualcosa resta agli atti."""
    rassegna.rispondi("un-modello", "C2", esito="bello")
    righe = [json.loads(r) for r in libro.read_text(encoding="utf-8").splitlines() if r.strip()]
    assert len(righe) == 1 and righe[0]["esito"] == "bello"


@pytest.mark.parametrize("comando,uscita", [
    ("python3 x.py", None),   # comando senza esito: non si sa se è fallito
    ("", 0),                  # esito senza comando: non si sa cosa
    ("", None),
    ("   ", 1),
])
def test_mezza_esecuzione_non_e_un_esecuzione(comando, uscita):
    """Serve il comando E il codice d'uscita: senza uno dei due la risposta
    non è ricontrollabile, e ciò che non si ricontrolla non conferma."""
    v = rassegna.rispondi("nodo", "C1", comando=comando, uscita=uscita)
    assert v["vale_come_conferma"] is False


def test_uscita_zero_vale_quanto_uscita_uno():
    """0 significa «l'ipotesi CADE»: è la risposta più preziosa, non la
    peggiore. Se contasse meno di 1, il registro premierebbe le buone notizie."""
    caduta = rassegna.rispondi("n", "C1", comando="x", uscita=0, esito="cade")
    tiene = rassegna.rispondi("n", "C1", comando="x", uscita=1, esito="regge")
    assert caduta["vale_come_conferma"] == tiene["vale_come_conferma"] is True


def test_compito_sconosciuto_rifiutato():
    with pytest.raises(ValueError):
        rassegna.rispondi("n", "C99", comando="x", uscita=0)


def test_serve_dire_chi_sei():
    with pytest.raises(ValueError):
        rassegna.rispondi("  ", "C1", comando="x", uscita=0)


def test_il_riepilogo_non_conta_le_impressioni_fra_le_esecuzioni():
    rassegna.rispondi("a", "C1", comando="x", uscita=1)
    rassegna.rispondi("b", "C1", esito="mi pare ottimo")
    rassegna.rispondi("c", "C2", esito="anche a me")
    r = rassegna.riepilogo()
    assert r["risposte"] == 3 and r["esecuzioni"] == 1 and r["impressioni"] == 2
    # C2 ha due impressioni e zero esecuzioni: resta APERTO
    assert "C2" in r["aperti"] and "C1" not in r["aperti"]


def test_una_rassegna_vuota_lo_dice(capsys):
    """Se non ha aggiunto niente al mondo, deve dirlo invece di sembrare piena."""
    assert rassegna.main(["--leggi"]) == 0
    assert "non ha aggiunto niente al mondo" in capsys.readouterr().out


def test_ogni_compito_chiede_un_esecuzione_e_dice_cosa_si_impara():
    """Un compito che non dice cosa si impara dai due esiti non è un compito:
    è una richiesta di approvazione."""
    for chiave, c in rassegna.COMPITI.items():
        assert c["titolo"] and c["comando"] and c["cosa_si_impara"]
        assert len(c["cosa_si_impara"]) > 60, f"{chiave}: motivazione troppo vaga"


def test_la_lettera_esiste_e_rifiuta_le_impressioni():
    testo = (RADICE / "LETTERA_AI_NODI.md").read_text(encoding="utf-8")
    assert "Non mandare la tua impressione" in testo
    assert "rassegna.py --compiti" in testo
    # deve citare la ragione, non solo il divieto
    assert "amplificata sei volte" in testo
