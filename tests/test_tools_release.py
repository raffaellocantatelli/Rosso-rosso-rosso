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


# ---------------------------------------------------- l'Oracolo sovrapposto

def pacchetto_finto(cartella: Path, rinomina_singoli=True) -> Path:
    """Un finto pacchetto Oracolo: manifesto di impronte e un prepare_release suo.

    Sta in piedi da solo — non contiene niente che venga dallo ZIP di Claudio.
    Serve a provare la delega e le guardie attorno, non il pacchetto vero: che
    il pacchetto vero funzioni è UNKNOWN da qui, e questa sessione il suo
    codice non l'ha eseguito.
    """
    import hashlib

    pacchetto = cartella / "PACCHETTO"
    (pacchetto / "tools").mkdir(parents=True)
    # Un prepare_release che fa ciò che fa quello vero: copia, tocca vercel.json,
    # ritira il vecchio mazzo, rinomina la voce di menu con gli APICI SINGOLI.
    apici = "'index.html', 'Tarocchi'" if rinomina_singoli else '"index.html", "Tarocchi"'
    (pacchetto / "tools" / "prepare_release.py").write_text(
        "import json, shutil, sys\n"
        "from pathlib import Path\n"
        "repo, dest = Path(sys.argv[1]), Path(sys.argv[2])\n"
        "shutil.copytree(repo, dest, ignore=shutil.ignore_patterns('.git', '.env'))\n"
        "(dest / 'public' / 'sovrano').mkdir(parents=True, exist_ok=True)\n"
        "(dest / 'public' / 'sovrano' / 'lame.v1.json').write_text('{\"id\": 74}')\n"
        "(dest / 'vercel.json').write_text('{\"builds\": [\"sovrano_entry.py\"]}')\n"
        "vecchio = dest / 'public' / 'cards'\n"
        "shutil.rmtree(vecchio) if vecchio.is_dir() else None\n"
        "nav = dest / 'public' / 'nav.js'\n"
        f"nav.write_text(nav.read_text().replace(\"[{apici}]\", \"['index.html', 'Oracolo del Sovrano']\"))\n"
        "print('report del pacchetto')\n",
        encoding="utf-8",
    )
    impronte = {}
    for f in pacchetto.rglob("*"):
        if f.is_file():
            impronte[str(f.relative_to(pacchetto)).replace(os.sep, "/")] = \
                hashlib.sha256(f.read_bytes()).hexdigest()
    (pacchetto / "MANIFEST_SHA256.json").write_text(
        json.dumps(impronte, indent=2), encoding="utf-8")
    return pacchetto


@pytest.fixture
def scena_oracolo(scena, tmp_path, monkeypatch):
    sito, consegna, release = scena
    (sito / "public" / "cards").mkdir()
    (sito / "public" / "cards" / "vecchia.json").write_text("{}", encoding="utf-8")
    (sito / "public" / "soglia.js").write_text("// la Soglia\n", encoding="utf-8")
    # Il nav.js del sito ha gli apici singoli, quello della consegna i doppi:
    # è la differenza da cui nasce la rinomina perduta.
    (sito / "public" / "nav.js").write_text(
        "var VOCI = [\n  ['index.html', 'Tarocchi'],\n];\n", encoding="utf-8")
    (consegna / "nuovi" / "nav.js").write_text(
        '// flex-wrap\nvar VOCI = [\n  ["index.html", "Tarocchi"],\n];\n', encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=sito, check=True)
    subprocess.run(["git", "-c", "user.email=p@p", "-c", "user.name=prova",
                    "commit", "-qm", "cards"], cwd=sito, check=True)
    monkeypatch.setattr(pr, "COPIE", [("nuovi/nav.js", "public/nav.js")])
    monkeypatch.setattr(pr, "PROVE", [])
    monkeypatch.setattr(pr, "PROVE_ORACOLO", [
        ("public/sovrano/lame.v1.json", '"id": 74', True, "le 74 Lame"),
        ("public/nav.js", "Oracolo del Sovrano", True, "il menu rinominato"),
    ])
    monkeypatch.setattr(pr, "PRESENTI", ["vercel.json"])
    monkeypatch.setattr(pr, "INTATTI", ["public/soglia.js"])
    monkeypatch.setattr(pr, "RITIRATI", ["public/cards"])
    return scena


def test_oracolo_delega_al_pacchetto(scena_oracolo, tmp_path):
    sito, consegna, release = scena_oracolo
    pacchetto = pacchetto_finto(tmp_path)
    assert prepara(scena_oracolo, ["--oracolo", str(pacchetto)]) == 0
    assert (release / "public" / "sovrano" / "lame.v1.json").is_file()
    assert not (release / "public" / "cards").exists()
    manifesto = json.loads((release / pr.MANIFESTO).read_text(encoding="utf-8"))
    assert manifesto["oracolo"] == str(pacchetto)


def test_il_menu_resta_rinominato_anche_col_nav_nuovo(scena_oracolo, tmp_path):
    """Il difetto vero: il pacchetto cerca gli apici singoli, il nav.js nuovo
    ha i doppi. Senza il recupero, la rinomina sparisce senza un errore."""
    sito, consegna, release = scena_oracolo
    (consegna / "nuovi" / "nav.js").write_text(
        '// flex-wrap\nvar VOCI = [\n  ["index.html", "Tarocchi"],\n];\n', encoding="utf-8")
    pacchetto = pacchetto_finto(tmp_path)
    assert prepara(scena_oracolo, ["--oracolo", str(pacchetto)]) == 0
    nav = (release / "public" / "nav.js").read_text(encoding="utf-8")
    assert "Oracolo del Sovrano" in nav
    assert "flex-wrap" in nav          # e la correzione del 04/09 è ancora lì


def test_alpha_resta_dell_oracolo(scena_oracolo, tmp_path):
    sito, consegna, release = scena_oracolo
    (consegna / "nuovi" / "alpha.html").write_text("<p>il vecchio Alpha</p>", encoding="utf-8")
    pr.COPIE.append(("nuovi/alpha.html", "public/alpha.html"))
    (sito / "public" / "alpha.html").write_text("<p>Lame del Sovrano</p>", encoding="utf-8")
    pacchetto = pacchetto_finto(tmp_path)
    assert prepara(scena_oracolo, ["--oracolo", str(pacchetto)]) == 0
    assert "Lame del Sovrano" in (release / "public" / "alpha.html").read_text(encoding="utf-8")


def test_pacchetto_manomesso_non_viene_eseguito(scena_oracolo, tmp_path):
    """Un file che non corrisponde alla propria impronta ferma tutto prima
    di eseguire qualunque cosa."""
    sito, consegna, release = scena_oracolo
    pacchetto = pacchetto_finto(tmp_path)
    strumento = pacchetto / "tools" / "prepare_release.py"
    strumento.write_text(strumento.read_text(encoding="utf-8") + "\nprint('cambiato')\n",
                         encoding="utf-8")
    assert prepara(scena_oracolo, ["--oracolo", str(pacchetto)]) == 2
    assert not release.exists()


def test_pacchetto_senza_manifesto_rifiutato(scena_oracolo, tmp_path):
    sito, consegna, release = scena_oracolo
    pacchetto = pacchetto_finto(tmp_path)
    (pacchetto / "MANIFEST_SHA256.json").unlink()
    assert prepara(scena_oracolo, ["--oracolo", str(pacchetto)]) == 2


def test_soglia_alterata_ferma_la_release(scena_oracolo, tmp_path, monkeypatch):
    """Se la Soglia cambia, la release non si dichiara pronta: è il file che
    protegge tutto il resto del sito."""
    sito, consegna, release = scena_oracolo
    pacchetto = pacchetto_finto(tmp_path)
    strumento = pacchetto / "tools" / "prepare_release.py"
    strumento.write_text(
        strumento.read_text(encoding="utf-8").replace(
            "print('report del pacchetto')",
            "(dest / 'public' / 'soglia.js').write_text('// manomessa')"),
        encoding="utf-8")
    # rigenero il manifesto: qui la manomissione è dichiarata, non nascosta
    import hashlib
    impronte = json.loads((pacchetto / "MANIFEST_SHA256.json").read_text(encoding="utf-8"))
    impronte["tools/prepare_release.py"] = hashlib.sha256(strumento.read_bytes()).hexdigest()
    (pacchetto / "MANIFEST_SHA256.json").write_text(json.dumps(impronte), encoding="utf-8")
    assert prepara(scena_oracolo, ["--oracolo", str(pacchetto)]) == 2
    assert not (release / pr.MANIFESTO).exists()


# --------------------------------------------- la consegna vera non è sparita

def test_la_consegna_dichiarata_esiste_davvero():
    """Se qualcuno rinomina un file in sito-claudio/, si scopre qui e non
    mentre si prepara una release."""
    consegna = RADICE / "sito-claudio"
    for origine, _ in pr.COPIE:
        assert (consegna / origine).is_file(), f"manca {origine}"
    for patch in pr.PATCH:
        assert (consegna / patch).is_file(), f"manca {patch}"
