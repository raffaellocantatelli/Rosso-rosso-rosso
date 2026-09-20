"""Il Layer 4 deve accorgersi dei file **nuovi**, non solo di quelli noti.

Perche' questo file esiste. Fino al 17/09 il manifesto copriva un elenco
scritto a mano piu' sei alberi filtrati per estensione: 434 file nel
repository, 308 sorvegliati. I 126 fuori non erano una scelta — erano quelli
a cui nessuno aveva pensato, `occhio/` (il prodotto intero) compreso. E ogni
file nuovo nasceva fuori: la guardia diceva «INTEGRITÀ OK» mentre un modulo
appena aggiunto non era guardato da nessuno.

Il difetto e' stato trovato da una verifica, non da un incidente. Questi test
esistono perche' non possa tornare in silenzio: il primo fallisce se un file
nuovo non entra nella copertura.

La maggior parte delle prove gira su un **repository finto** costruito in una
cartella temporanea. Interrogare il repository vero direbbe com'e' fatto il
repository vero; qui serve sapere cosa fa il programma quando qualcosa cambia,
e cambiare il repository vero dentro un test e' esattamente cio' che non si fa.

    python test_manifesto_integrita.py     # oppure: pytest
"""
import os
import pathlib
import re
import subprocess
import sys

import pytest

RADICE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RADICE))

import manifesto_integrita as m  # noqa: E402


@pytest.fixture
def repo_finto(tmp_path, monkeypatch):
    """Un repository git vero, piccolo, in una cartella temporanea."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "codice.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "documento.md").write_text("# titolo\n", encoding="utf-8")
    (tmp_path / "sotto").mkdir()
    (tmp_path / "sotto" / "altro.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("segreti.jsonl\n", encoding="utf-8")

    monkeypatch.setattr(m, "RADICE", str(tmp_path))
    monkeypatch.setattr(m, "MANIFESTO", str(tmp_path / "MANIFESTO_INTEGRITA.json"))
    monkeypatch.setattr(m, "ESCLUSI", {
        "MANIFESTO_INTEGRITA.json": "non puo' contenere il proprio hash",
    })
    return tmp_path


def _genera(capsys):
    assert m.genera() == 0
    capsys.readouterr()


# --------------------------------------------------------------------------
# Il difetto del 17/09, in forma di test.
# --------------------------------------------------------------------------

def test_un_file_nuovo_entra_nella_copertura(repo_finto, capsys):
    """Il test che il difetto avrebbe fatto fallire.

    Un file appena creato deve essere sorvegliato **senza** che nessuno
    aggiunga il suo nome a un elenco. Nomi e posizioni scelti apposta fuori
    da qualunque convenzione: estensione mai vista, cartella che non esiste.
    """
    _genera(capsys)

    nuovi = [
        repo_finto / "modulo_nuovo.py",
        repo_finto / "dato_nuovo.json",
        repo_finto / "appunto.txt",
        repo_finto / "script.sh",
        repo_finto / "cartella_mai_vista" / "dentro.py",
        repo_finto / "cartella_mai_vista" / "profondo" / "ancora.yaml",
    ]
    for f in nuovi:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("contenuto\n", encoding="utf-8")

    coperti = set(m.file_da_sorvegliare())
    scoperti = [
        str(f.relative_to(repo_finto)) for f in nuovi
        if str(f.relative_to(repo_finto)) not in coperti
    ]
    assert not scoperti, f"file nuovi non sorvegliati da nessuno: {scoperti}"


def test_la_verifica_nomina_il_file_nuovo(repo_finto, capsys):
    """Non basta coprirlo: `--verifica` deve dirlo, e uscire con 1."""
    _genera(capsys)
    assert m.verifica() == 0
    capsys.readouterr()

    (repo_finto / "arrivato_dopo.py").write_text("z = 3\n", encoding="utf-8")

    assert m.verifica() == 1
    detto = capsys.readouterr().out
    assert "NUOVO      arrivato_dopo.py" in detto
    assert "1 non nel manifesto" in detto


def test_la_verifica_vede_modifica_e_sparizione(repo_finto, capsys):
    _genera(capsys)

    (repo_finto / "codice.py").write_text("x = 999\n", encoding="utf-8")
    (repo_finto / "documento.md").unlink()

    assert m.verifica() == 1
    detto = capsys.readouterr().out
    assert "MODIFICATO codice.py" in detto
    assert "MANCANTE   documento.md" in detto


def test_un_file_ignorato_resta_fuori(repo_finto, capsys):
    """Il confine del manifesto e' `.gitignore`, che e' una decisione dell'autore.

    I registri di `occhio` portano le firme di un ospite e questo repository e'
    pubblico: stanno fuori apposta. Coprirli «per sicurezza» significherebbe
    che un nodo allarga da solo una scelta che non e' sua (CLAUDE.md §2.5).
    """
    _genera(capsys)
    (repo_finto / "segreti.jsonl").write_text("firma\n", encoding="utf-8")

    assert "segreti.jsonl" not in m.file_da_sorvegliare()
    assert m.verifica() == 0
    capsys.readouterr()


def test_senza_git_solleva_invece_di_indovinare(tmp_path, monkeypatch):
    """Due definizioni di «dentro il repository» darebbero due manifesti."""
    monkeypatch.setattr(m, "RADICE", str(tmp_path))
    with pytest.raises(m.RepositoryAssente):
        m.file_da_sorvegliare()


# --------------------------------------------------------------------------
# Proprieta' che si misurano sul repository vero (sola lettura).
# --------------------------------------------------------------------------

def test_nel_repository_vero_nulla_e_fuori_senza_un_motivo():
    """Ogni file scoperto deve corrispondere a una voce di `ESCLUSI`.

    E' la prova che la copertura e' per difetto: se qualcuno torna a un elenco
    scritto a mano, decine di file finiscono fuori senza motivo e questo test
    li nomina tutti.
    """
    fuori = set(m._file_del_repository()) - set(m.file_da_sorvegliare())
    senza_motivo = sorted(p for p in fuori if not m.escluso(p))
    assert not senza_motivo, f"fuori dal manifesto senza una regola: {senza_motivo}"


def test_il_nucleo_non_puo_restare_scoperto():
    coperti = set(m.file_da_sorvegliare())
    mancanti = [f for f in m.NUCLEO if f not in coperti]
    assert not mancanti, f"file del nucleo non sorvegliati: {mancanti}"


def test_le_esclusioni_sono_cio_che_la_action_riscrive_ogni_notte():
    """Il legame fra le due cose, verificato invece che ricordato.

    Se un domani la Action committa un percorso in piu' e nessuno lo dichiara
    in `ESCLUSI`, il manifesto andra' in divergenza ogni notte e l'avviso
    diventera' rumore. Questo test lo dice prima, non dopo.
    """
    testo = (RADICE / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")
    riga = re.search(r"^\s*git add (.+)$", testo, re.MULTILINE)
    assert riga, "la Action non committa piu' niente? cambiato il contratto"

    percorsi = []
    for pezzo in riga.group(1).split():
        # la riga vera finisce con `2>/dev/null || true`: e' shell, non percorsi
        if pezzo.startswith(("2>", "1>", ">", "|", "&")):
            break
        percorsi.append(pezzo.rstrip("/"))
    assert percorsi, riga.group(1)

    non_dichiarati = [p for p in percorsi if not m.escluso(p)]
    assert not non_dichiarati, (
        "la run giornaliera riscrive questi percorsi, ma il manifesto li "
        f"sorveglia: divergenza garantita ogni notte -> {non_dichiarati}"
    )


def test_ogni_esclusione_ha_un_motivo_scritto():
    for voce, motivo in m.ESCLUSI.items():
        assert motivo and len(motivo) > 15, f"esclusione senza motivo: {voce}"


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
