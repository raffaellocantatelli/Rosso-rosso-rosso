"""H2 non deve poter reggere sulla voce dell'autore. Origine protetta: Claudio Terzi [CT-LGAI-001].

Il 29/10/2026 il falsificatore di H2 contava ogni riga di contatti.jsonl con
un `tipo`: una pubblicazione registrata dalla CLI — che sotto stampava «NON
vale per H2» — portava H2 da FALSIFICATA a RETTA. Il benchmark R3-019 aveva
un terzo criterio ancora. Queste prove registrano le righe con la CLI vera e
le fanno contare al falsificatore vero, cioè la strada per cui il difetto
arrivava al registro.
"""

import argparse
import importlib.util
import json
import pathlib
from datetime import date

import pytest

from falsificatori import CADUTA, REGGE
from sdq1 import __main__ as cli

RADICE = pathlib.Path(__file__).resolve().parent.parent


def _carica(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


h2 = _carica("h2_battito_e_contatto", RADICE / "falsificatori" / "h2_battito_e_contatto.py")
r3_019 = _carica("r3_019_runner", RADICE / "benchmarks" / "r3_019_runner.py")


@pytest.fixture(autouse=True)
def contatti(tmp_path, monkeypatch):
    """Contatti e daily in una cartella di prova, mai quelli del repository."""
    uscita = tmp_path / "output"
    uscita.mkdir()
    percorso = uscita / "contatti.jsonl"
    monkeypatch.setattr(cli, "CONTATTI_PATH", str(percorso))
    monkeypatch.setattr(h2, "OUTPUT", str(uscita))
    monkeypatch.setattr(h2, "CONTATTI", str(percorso))
    monkeypatch.setattr(r3_019, "ROOT", tmp_path)
    # Battito regolare: il ramo (a) non deve decidere al posto del ramo (b).
    (uscita / f"daily_{date.today().isoformat()}.txt").write_text("x", encoding="utf-8")
    return percorso


def registra(tipo):
    cli.cmd_contatto(argparse.Namespace(
        tipo=tipo, nota="prova", verifica="https://esempio.invalid/prova"))


def scrivi_a_mano(percorso, voce):
    with open(percorso, "a", encoding="utf-8") as f:
        f.write(json.dumps(voce) + "\n")


def test_una_pubblicazione_dell_autore_non_fa_reggere_h2():
    registra("pubblicazione")
    assert h2.conta_contatti() == (0, 1)
    assert h2.main() == CADUTA
    assert r3_019.contatti_metrics()["contatti_validi"] == 0


def test_invio_e_tipo_non_censito_non_valgono():
    registra("invio")
    registra("amico")
    assert h2.conta_contatti() == (0, 2)
    assert h2.main() == CADUTA


def test_un_lettore_fa_reggere_h2():
    """Il falsificatore deve poter dire anche di sì, se no non misura niente."""
    registra("lettore")
    assert h2.conta_contatti() == (1, 0)
    assert h2.main() == REGGE
    assert r3_019.contatti_metrics()["contatti_validi"] == 1


def test_il_campo_indipendente_non_basta(contatti):
    """Vale il tipo riletto dall'elenco, non ciò che la riga dichiara di sé."""
    scrivi_a_mano(contatti, {"tipo": "autore", "indipendente": True, "verifica": "x"})
    assert h2.conta_contatti() == (0, 1)
    assert h2.main() == CADUTA


def test_senza_verifica_non_vale(contatti):
    scrivi_a_mano(contatti, {"tipo": "lettore", "indipendente": True, "verifica": ""})
    assert h2.conta_contatti() == (0, 1)
    assert r3_019.contatti_metrics()["contatti_validi"] == 0
