"""Prove di esporta_grafici.py che non richiedono Chromium né mmdc."""
import importlib.util
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
SCRIPT = RADICE / "santuario" / "esporta_grafici.py"
spec = importlib.util.spec_from_file_location("esporta_grafici", SCRIPT)
eg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eg)


def test_tabella_in_mezzo_non_sposta_gli_id():
    # il difetto della guida: numerare in ordine sfasa tutto dopo G14/G17
    md = ("## G01 · Uno\n```mermaid\nflowchart TB\n a-->b\n```\n"
          "## G02 · Tabella\n| a | b |\n|---|---|\n"
          "```mermaid\n%% G03 · Tre\nflowchart LR\n c-->d\n```\n")
    b = eg.estrai(md)
    assert [x["id"] for x in b] == ["G01", "G03"]
    assert b[1]["titolo"] == "Tre"


def test_senza_id_usa_ordine_senza_collisioni():
    md = ("```mermaid\n%% G02 · Due\ngraph TB\n a\n```\n"
          "```mermaid\ngraph TB\n b\n```\n")
    b = eg.estrai(md)
    assert sorted(x["id"] for x in b) == ["G02", "G03"]
    assert b[1].get("id_da_ordine")


def test_id_duplicati_e_blocco_aperto_falliscono():
    with pytest.raises(SystemExit):
        eg.estrai("```mermaid\n%% G01\na\n```\n```mermaid\n%% G01\nb\n```\n")
    with pytest.raises(SystemExit):
        eg.estrai("```mermaid\ngraph TB\n a\n")


def test_solo_estrai_produce_sorgenti_indice_e_backup(tmp_path):
    out = tmp_path / "g"
    r = subprocess.run([sys.executable, str(SCRIPT),
                        str(RADICE / "santuario" / "esempio.md"),
                        "--uscita", str(out), "--solo-estrai"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in (out / "sorgenti").glob("*.mmd")) == \
        ["G01.mmd", "G03.mmd", "G04.mmd"]
    assert "fetch(" not in (out / "index.html").read_text()  # funziona da file://
    arch = next((out / "backup").glob("*.tar.gz"))
    with tarfile.open(arch) as t:
        nomi = {Path(m.name).name for m in t.getmembers()}
    assert {"esempio.md", "elenco.json", "G01.mmd", "G03.mmd", "G04.mmd"} <= nomi
    impronte = json.loads(next((out / "backup").glob("*.sha256.json")).read_text())
    assert impronte["file"]["G03.mmd"] == eg.sha256(out / "sorgenti" / "G03.mmd")


def test_slot_vuoto_non_viene_disegnato(tmp_path):
    # uno slot con solo `%%` non deve diventare un file che sembra un grafico
    b = eg.estrai("```mermaid\n%% G05 · Cinque\n%% tipo atteso: erDiagram\n```\n"
                  "```mermaid\n%% G06 · Sei\nflowchart TB\n a-->b\n```\n")
    assert [x["vuoto"] for x in b] == [True, False]
    r = subprocess.run([sys.executable, str(SCRIPT),
                        str(RADICE / "santuario" / "santuario-master.md"),
                        "--uscita", str(tmp_path), "--solo-estrai", "--senza-backup"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "25 slot vuoti" in r.stdout  # 27 voci meno le 2 tabelle G14, G17
    assert (tmp_path / "index.html").read_text().count("da incollare") == 25
