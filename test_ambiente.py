"""Il primo comando del protocollo deve partire anche senza `python-dotenv`.

`CLAUDE.md` §3 ordina `python -m sdq1 --check` prima di qualunque conclusione
sul sistema. Fino al 17/09 quel comando moriva con ModuleNotFoundError dove la
dipendenza non era installata — e lo stesso import mancante faceva uscire
`falsificatori/h5_tracce.py` con 1, che in quel contratto vuol dire REGGE:
un'ipotesi confermata da una libreria assente.

Questi test eseguono i due rami in due processi veri, uno con `dotenv`
disponibile e uno con `dotenv` reso irraggiungibile. Interrogare
`ambiente.carica_env()` nel processo dei test direbbe solo com'e' fatto
l'ambiente dei test.

    python test_ambiente.py     # oppure: pytest
"""
import pathlib
import subprocess
import sys
import textwrap

RADICE = pathlib.Path(__file__).resolve().parent

# Rende `import dotenv` impossibile per il processo figlio, senza disinstallare
# niente: un blocco in `sys.meta_path` che solleva ImportError solo su quel nome.
BLOCCO = textwrap.dedent(
    """
    import sys
    class _Senza:
        def find_module(self, nome, percorso=None):
            return None
        def find_spec(self, nome, percorso=None, target=None):
            if nome == "dotenv" or nome.startswith("dotenv."):
                raise ImportError("dotenv reso irraggiungibile dal test")
            return None
    sys.meta_path.insert(0, _Senza())
    """
)


def _esegui(codice, con_dotenv):
    prologo = "" if con_dotenv else BLOCCO
    return subprocess.run(
        [sys.executable, "-c", prologo + textwrap.dedent(codice)],
        cwd=RADICE, capture_output=True, text=True,
    )


def _scrivi_env(tmp_path):
    f = tmp_path / ".env"
    f.write_text(
        '# commento\nR3_PROVA_CHIAVE=valore-dal-file\nR3_PROVA_VIRGOLETTE="con spazi"\n'
        "export R3_PROVA_EXPORT=terzo\n",
        encoding="utf-8",
    )
    return f


CODICE_LETTURA = """
    import os, sys
    sys.path.insert(0, {radice!r})
    import ambiente
    os.environ["R3_PROVA_CHIAVE"] = "gia-nell-ambiente"
    trovato = ambiente.carica_env({percorso!r})
    print(trovato,
          os.environ["R3_PROVA_CHIAVE"],
          os.environ.get("R3_PROVA_VIRGOLETTE"),
          os.environ.get("R3_PROVA_EXPORT"), sep="|")
"""


def _controlla_lettura(tmp_path, con_dotenv):
    percorso = _scrivi_env(tmp_path)
    r = _esegui(
        CODICE_LETTURA.format(radice=str(RADICE), percorso=str(percorso)),
        con_dotenv=con_dotenv,
    )
    assert r.returncode == 0, r.stderr
    trovato, chiave, virgolette, esportata = r.stdout.strip().split("|")
    assert trovato == "True"
    # os.environ vince sempre su .env: nella Action la chiave arriva dai secrets
    assert chiave == "gia-nell-ambiente"
    assert virgolette == "con spazi"
    assert esportata == "terzo"


def test_legge_env_con_dotenv(tmp_path):
    _controlla_lettura(tmp_path, con_dotenv=True)


def test_legge_env_senza_dotenv(tmp_path):
    """Il ramo di ripiego deve fare le stesse quattro cose, non tre."""
    _controlla_lettura(tmp_path, con_dotenv=False)


def test_env_assente_non_e_un_errore():
    for con_dotenv in (True, False):
        r = _esegui(
            """
            import sys
            sys.path.insert(0, {radice!r})
            import ambiente
            print(ambiente.carica_env("questo-file-non-esiste.env"))
            """.format(radice=str(RADICE)),
            con_dotenv=con_dotenv,
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "False"


def test_check_parte_senza_dotenv():
    """Il comando di §3 deve rispondere, non morire in un traceback.

    Qui non conta se il Core sia acceso — conta che la diagnosi venga
    stampata. Un nodo che non puo' misurare deduce, ed e' l'inizio di §4.
    """
    r = _esegui(
        """
        import runpy, sys
        sys.argv = ["sdq1", "--check"]
        try:
            runpy.run_module("sdq1", run_name="__main__")
        except SystemExit as e:
            print("uscita:", e.code)
        """,
        con_dotenv=False,
    )
    assert "ModuleNotFoundError" not in r.stderr, r.stderr
    assert "Il Core è acceso?" in r.stdout, r.stdout + r.stderr


def test_ogni_punto_d_ingresso_passa_da_ambiente():
    """Un modulo nuovo che importa dotenv da solo rifa' il buco."""
    consentiti = {
        pathlib.Path("ambiente.py"),          # l'implementazione canonica
        pathlib.Path("test_ambiente.py"),     # questo file
    }
    colpevoli = []
    for f in RADICE.rglob("*.py"):
        rel = f.relative_to(RADICE)
        if rel in consentiti or rel.parts[0] in {"protocollo-rosso-bot", "sito-claudio", ".git"}:
            continue
        if "from dotenv import" in f.read_text(encoding="utf-8"):
            colpevoli.append(str(rel))
    assert not colpevoli, (
        "questi file importano dotenv direttamente invece di usare "
        f"ambiente.carica_env(): {colpevoli}"
    )


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
