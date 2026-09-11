"""Gli strumenti di pubblicazione: cosa preparano, e cosa si rifiutano di fare.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Nessuna di queste prove tocca Vercel, il sito pubblico o la rete. Lavorano su
un sito finto costruito nel momento, e su un `vercel` finto che stampa un
indirizzo. Che la pubblicazione vera funzioni resta UNKNOWN da qui: lo dice
`py tools\\publish.py "..\\Claudio-release"` sulla macchina di Claudio.

La cosa che sorvegliano davvero non è che gli script funzionino: è che si
FERMINO. Uno script di pubblicazione che va avanti comunque è il modo più
rapido di mettere in rete qualcosa che nessuno ha guardato.
"""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "tools"))

import prepare_release as pr  # noqa: E402
import publish as pub  # noqa: E402


# ------------------------------------------------------------- un sito finto

def sito_finto(cartella: Path) -> Path:
    """Un clone plausibile: public/, vercel.json, un file da correggere."""
    sito = cartella / "Claudio-sito"
    (sito / "public").mkdir(parents=True)
    (sito / "public" / "pagina.html").write_text("<p>vecchio</p>\n", encoding="utf-8")
    (sito / "public" / "nav.js").write_text("// vecchia barra\n", encoding="utf-8")
    (sito / "vercel.json").write_text('{"version": 2}', encoding="utf-8")
    (sito / ".env").write_text("CHIAVE=segreta\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=sito, check=True)
    subprocess.run(["git", "add", "-A"], cwd=sito, check=True)
    subprocess.run(["git", "-c", "user.email=p@p", "-c", "user.name=prova",
                    "commit", "-qm", "sito"], cwd=sito, check=True)
    return sito


def consegna_finta(cartella: Path) -> Path:
    consegna = cartella / "consegna"
    (consegna / "nuovi").mkdir(parents=True)
    (consegna / "patch").mkdir(parents=True)
    (consegna / "nuovi" / "nav.js").write_text("// barra nuova, flex-wrap\n", encoding="utf-8")
    (consegna / "patch" / "prova.patch").write_text(
        "diff --git a/public/pagina.html b/public/pagina.html\n"
        "--- a/public/pagina.html\n"
        "+++ b/public/pagina.html\n"
        "@@ -1 +1 @@\n"
        "-<p>vecchio</p>\n"
        "+<p>corretto</p>\n",
        encoding="utf-8",
    )
    return consegna


@pytest.fixture
def scena(tmp_path, monkeypatch):
    sito = sito_finto(tmp_path)
    consegna = consegna_finta(tmp_path)
    monkeypatch.setattr(pr, "COPIE", [("nuovi/nav.js", "public/nav.js")])
    monkeypatch.setattr(pr, "PATCH", ["patch/prova.patch"])
    monkeypatch.setattr(pr, "PROVE", [
        ("public/pagina.html", "corretto", True, "la patch deve essere entrata"),
        ("public/nav.js", "flex-wrap", True, "il file nuovo deve aver sostituito il vecchio"),
    ])
    monkeypatch.setattr(pr, "PRESENTI", ["vercel.json", "public/nav.js"])
    monkeypatch.setattr(pr, "TEST_DELLA_CONSEGNA", "tests/non-esistono.py")
    return sito, consegna, tmp_path / "Claudio-release"


def prepara(scena, extra=()):
    sito, consegna, release = scena
    return pr.main([str(sito), str(release), "--consegna", str(consegna), *extra])


# ------------------------------------------------------------------ prepara

def test_prepara_applica_patch_e_file(scena):
    _, _, release = scena
    assert prepara(scena) == 0
    assert (release / "public" / "pagina.html").read_text(encoding="utf-8") == "<p>corretto</p>\n"
    assert "flex-wrap" in (release / "public" / "nav.js").read_text(encoding="utf-8")


def test_la_sorgente_resta_intatta(scena):
    sito, _, _ = scena
    assert prepara(scena) == 0
    assert (sito / "public" / "pagina.html").read_text(encoding="utf-8") == "<p>vecchio</p>\n"
    sporco = subprocess.run(["git", "status", "--porcelain"], cwd=sito,
                            capture_output=True, text=True)
    assert sporco.stdout.strip() == ""


def test_env_e_git_non_entrano_nella_release(scena):
    """Una release contiene solo ciò che si può pubblicare. `.env` non lo è."""
    _, _, release = scena
    assert prepara(scena) == 0
    assert not (release / ".env").exists()
    assert not (release / ".git").exists()


def test_il_manifesto_dice_da_quale_commit(scena):
    _, _, release = scena
    assert prepara(scena) == 0
    manifesto = json.loads((release / pr.MANIFESTO).read_text(encoding="utf-8"))
    assert len(manifesto["sorgente"]["commit"]) == 40
    assert manifesto["patch"][0]["esito"] == "applicata"


def test_sorgente_sbagliata_si_ferma(tmp_path, scena):
    _, consegna, release = scena
    vuota = tmp_path / "non-il-sito"
    vuota.mkdir()
    assert pr.main([str(vuota), str(release), "--consegna", str(consegna)]) == 2
    assert not release.exists()


def test_sorgente_inesistente_si_ferma(tmp_path, scena):
    _, consegna, release = scena
    assert pr.main([str(tmp_path / "mai"), str(release), "--consegna", str(consegna)]) == 2


def test_sorgente_uguale_a_destinazione_si_ferma(scena):
    sito, consegna, _ = scena
    assert pr.main([str(sito), str(sito), "--consegna", str(consegna)]) == 2
    assert (sito / "public" / "pagina.html").read_text(encoding="utf-8") == "<p>vecchio</p>\n"


def test_non_cancella_una_cartella_che_non_ha_preparato(scena, tmp_path):
    """Il punto è irreversibile: `--forza` su una cartella altrui la cancellerebbe."""
    sito, consegna, _ = scena
    altrui = tmp_path / "roba-mia"
    altrui.mkdir()
    (altrui / "importante.txt").write_text("non cancellarmi", encoding="utf-8")
    assert pr.main([str(sito), str(altrui), "--consegna", str(consegna), "--forza"]) == 2
    assert (altrui / "importante.txt").read_text(encoding="utf-8") == "non cancellarmi"


def test_release_gia_fatta_chiede_forza(scena):
    assert prepara(scena) == 0
    assert prepara(scena) == 2              # senza --forza non la rifà
    assert prepara(scena, ["--forza"]) == 0


def test_patch_che_non_si_applica_piu_ferma_tutto(scena):
    """Se il sito è cambiato, la consegna va rifatta a mano — non forzata."""
    sito, consegna, release = scena
    (sito / "public" / "pagina.html").write_text("<p>qualcun altro ha scritto qui</p>\n",
                                                 encoding="utf-8")
    assert prepara(scena) == 2
    assert not (release / pr.MANIFESTO).exists()


def test_patch_gia_applicata_non_e_un_errore(scena):
    sito, consegna, release = scena
    (sito / "public" / "pagina.html").write_text("<p>corretto</p>\n", encoding="utf-8")
    assert prepara(scena) == 0


def test_una_prova_che_cade_impedisce_il_manifesto(scena, monkeypatch):
    """Senza RELEASE.json, publish.py si rifiuta: le due guardie sono in fila."""
    _, _, release = scena
    monkeypatch.setattr(pr, "PROVE", [
        ("public/pagina.html", "questo testo non c'è", True, "prova che deve cadere"),
    ])
    assert prepara(scena) == 2
    assert not (release / pr.MANIFESTO).exists()


# ------------------------------------------------------------------ pubblica

@pytest.fixture
def vercel_finto(tmp_path, monkeypatch):
    """Un `vercel` che risponde, per provare tutto tranne la pubblicazione vera."""
    cartella = tmp_path / "bin"
    cartella.mkdir()
    finto = cartella / "vercel"
    finto.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        '  whoami) echo claudioterzi; exit 0;;\n'
        '  deploy) echo "Preview: https://claudio-prova.vercel.app"; exit 0;;\n'
        "esac\nexit 1\n",
        encoding="utf-8",
    )
    finto.chmod(finto.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{cartella}{os.pathsep}{os.environ['PATH']}")
    return finto


@pytest.mark.skipif(os.name == "nt", reason="il vercel finto è uno script sh")
def test_pubblica_anteprima(scena, vercel_finto, capsys):
    _, _, release = scena
    assert prepara(scena) == 0
    capsys.readouterr()
    assert pub.main([str(release)]) == 0
    uscita = capsys.readouterr().out
    assert "https://claudio-prova.vercel.app" in uscita
    # Nel comando eseguito `--prod` viene dopo `--yes`: cercarlo da solo
    # troverebbe la riga di suggerimento «--produzione», che è un'altra cosa.
    assert "--yes --prod" not in uscita    # l'anteprima non tocca il sito vero
    assert "il sito pubblico non è cambiato" in uscita.replace("e'", "è")


@pytest.mark.skipif(os.name == "nt", reason="il vercel finto è uno script sh")
def test_produzione_senza_conferma_non_pubblica(scena, vercel_finto, monkeypatch, capsys):
    _, _, release = scena
    assert prepara(scena) == 0
    monkeypatch.setattr("builtins.input", lambda _: "vabbè dai")
    assert pub.main([str(release), "--produzione"]) == 2
    assert "Niente e' stato pubblicato" in capsys.readouterr().out


@pytest.mark.skipif(os.name == "nt", reason="il vercel finto è uno script sh")
def test_produzione_con_la_parola_giusta_pubblica(scena, vercel_finto, monkeypatch, capsys):
    _, _, release = scena
    assert prepara(scena) == 0
    monkeypatch.setattr("builtins.input", lambda _: "  PUBBLICA \n")
    assert pub.main([str(release), "--produzione"]) == 0
    assert "--yes --prod" in capsys.readouterr().out


def test_non_pubblica_una_cartella_non_preparata(tmp_path, capsys):
    qualsiasi = tmp_path / "qualsiasi"
    qualsiasi.mkdir()
    (qualsiasi / "index.html").write_text("ciao", encoding="utf-8")
    assert pub.main([str(qualsiasi), "--dry"]) == 2
    assert "RELEASE.json" in capsys.readouterr().err


def test_senza_vercel_dice_come_installarlo(scena, monkeypatch, capsys):
    _, _, release = scena
    assert prepara(scena) == 0
    monkeypatch.setattr(pub.shutil, "which", lambda _: None)
    assert pub.main([str(release), "--dry"]) == 2
    assert "npm" in capsys.readouterr().err


def test_comando_windows_passa_da_cmd(monkeypatch):
    """Su Windows un .cmd non si avvia da solo: senza cmd.exe fallirebbe lì e non qui."""
    monkeypatch.setattr(pub.os, "name", "nt")
    assert pub.comando(r"C:\npm\vercel.cmd", ["deploy"])[:2] == ["cmd.exe", "/c"]
    monkeypatch.setattr(pub.os, "name", "posix")
    assert pub.comando("/usr/bin/vercel", ["deploy"]) == ["/usr/bin/vercel", "deploy"]


# --------------------------------------------- la consegna vera non è sparita

def test_la_consegna_dichiarata_esiste_davvero():
    """Se qualcuno rinomina un file in sito-claudio/, si scopre qui e non
    mentre si prepara una release."""
    consegna = RADICE / "sito-claudio"
    for origine, _ in pr.COPIE:
        assert (consegna / origine).is_file(), f"manca {origine}"
    for patch in pr.PATCH:
        assert (consegna / patch).is_file(), f"manca {patch}"
