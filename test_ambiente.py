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


def _esegui_script(percorso, con_dotenv):
    """Lancia un `.py` vero. `python -c` e' interattivo: dotenv usa la cwd
    e i due rami coincidono per incidente, che e' esattamente il modo in
    cui il test precedente restava verde."""
    if con_dotenv:
        return subprocess.run(
            [sys.executable, str(percorso)],
            cwd=RADICE, capture_output=True, text=True,
        )
    codice = BLOCCO + f"\nimport runpy\nrunpy.run_path({str(percorso)!r})\n"
    return subprocess.run(
        [sys.executable, "-c", codice],
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


CODICE_RISALITA = """
    import os, sys
    sys.path.insert(0, {radice!r})
    os.chdir({dentro!r})
    import ambiente
    print(ambiente.carica_env(), os.environ.get("R3_PROVA_RISALITA"), sep="|")
"""


def test_senza_argomenti_i_due_rami_risalgono_uguale(tmp_path):
    """Senza `.env` in radice, entrambi i rami risalgono dalla cwd.

    Se i due rami divergono qui, il programma si comporta in un modo o
    nell'altro a seconda di quale libreria sia installata — che e' il difetto
    che `ambiente.py` esiste per chiudere, riaperto un piano piu' sotto.
    """
    (tmp_path / ".env").write_text("R3_PROVA_RISALITA=dal-genitore\n", encoding="utf-8")
    dentro = tmp_path / "una" / "due"
    dentro.mkdir(parents=True)

    esiti = []
    for con_dotenv in (True, False):
        r = _esegui(
            CODICE_RISALITA.format(radice=str(RADICE), dentro=str(dentro)),
            con_dotenv=con_dotenv,
        )
        assert r.returncode == 0, r.stderr
        esiti.append(r.stdout.strip())

    assert esiti[0] == esiti[1] == "True|dal-genitore", esiti


def test_da_un_file_py_i_due_rami_caricano_lo_stesso_env(tmp_path):
    """Il test che il difetto del 19/09 avrebbe fatto fallire.

    `load_dotenv()` chiamato da `ambiente.py` (un `.py`, non un REPL) parte
    dalla cartella di `ambiente.py`, non dalla cwd. Il ripiego, se cammina
    dalla cwd, trova un altro file. Due processi, lo stesso chiamante `.py`,
    cwd diversa dalla radice: gli esiti devono coincidere. Provato rimettendo
    `load_dotenv()` senza percorso: fallisce.
    """
    altrove = tmp_path / "altrove"
    altrove.mkdir()
    (altrove / ".env").write_text("R3_PROVA_PY=dalla-cwd\n", encoding="utf-8")

    chiamante = tmp_path / "chiamante.py"
    chiamante.write_text(
        textwrap.dedent(
            f"""
            import os, sys
            sys.path.insert(0, {str(RADICE)!r})
            os.chdir({str(altrove)!r})
            import ambiente
            print(ambiente.carica_env(), os.environ.get("R3_PROVA_PY"), sep="|")
            """
        ),
        encoding="utf-8",
    )

    esiti = []
    for con_dotenv in (True, False):
        r = _esegui_script(chiamante, con_dotenv=con_dotenv)
        assert r.returncode == 0, r.stderr
        esiti.append(r.stdout.strip())

    assert esiti[0] == esiti[1], esiti


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
    """Il comando di §3 deve rispondere, non morire per `dotenv`.

    Qui non conta se il Core sia acceso — conta che la diagnosi venga
    stampata. Un nodo che non puo' misurare deduce, ed e' l'inizio di §4.
    Se manca un'altra dipendenza, non e' questo il test che lo copre: la
    proprieta' e' che `dotenv` assente non e' un traceback.
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
    assert "No module named 'dotenv'" not in r.stderr, r.stderr
    if "Il Core è acceso?" in r.stdout:
        return
    # Altre dipendenze assenti: il test non deve spacciarsi per prova su dotenv.
    assert "dotenv" not in r.stderr, r.stderr


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
