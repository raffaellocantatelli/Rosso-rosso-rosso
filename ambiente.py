"""Carica `.env` senza pretendere che `python-dotenv` sia installato.

Perche' esiste questo file. `CLAUDE.md` §3 dice a ogni nodo che apre il
repository di eseguire `python -m sdq1 --check` **prima** di qualunque
conclusione sul sistema. Fino al 17/09 quel comando moriva con
`ModuleNotFoundError: No module named 'dotenv'` in qualunque ambiente dove
la dipendenza non fosse installata: la prima istruzione del protocollo era
ineseguibile, e un nodo che non puo' misurare deduce.

Lo stesso difetto ha prodotto un errore peggiore, gia' documentato in
`PROSSIMO_PASSO.md`: `falsificatori/h5_tracce.py` usciva con 1 su un import
fallito, e 1 in quel contratto significa REGGE. Un'ipotesi «reggeva» perche'
mancava una libreria. E' il difetto di §4 — il sistema che legge la propria
assenza come un risultato.

Regola: `python-dotenv` resta in `requirements.txt` e resta il percorso
normale; quando non c'e', si legge il file a mano invece di fermarsi.
`os.environ` ha sempre la precedenza su `.env`, come in python-dotenv.

I due rami devono trovare **lo stesso file**. `load_dotenv()` senza argomenti
non parte dalla cwd quando e' chiamato da un `.py`: `find_dotenv` risale
dalla cartella del chiamante, che qui e' questo file. Il ripiego, se
camminasse dalla cwd, caricherebbe un altro `.env` (o nessuno) a seconda
di quale libreria e' installata — il difetto che questo file esiste per
chiudere, riaperto un piano piu' sotto. Per questo la ricerca e' una sola,
e dotenv, quando c'e', parsea il file gia' trovato.
"""
from __future__ import annotations

import os
from pathlib import Path


def _risali_cercando_env(partenza: Path) -> Path | None:
    """Il primo `.env` da `partenza` in su, come fa `find_dotenv` di dotenv."""
    for cartella in [partenza, *partenza.parents]:
        f = cartella / ".env"
        if f.is_file():
            return f
    return None


def _file_env(percorso: str | os.PathLike[str] | None) -> Path | None:
    """Stesso file per entrambi i rami. Non lasciare la ricerca a dotenv.

    Senza argomenti: prima il `.env` accanto a questo file (radice del
    repository), poi risalita dalla directory corrente. Cosi' `python -m
    sdq1 --check` trova il `.env` del progetto da qualunque cwd, e un test
    che scrive un `.env` in una cartella temporanea e ci entra lo trova
    lo stesso.
    """
    if percorso is not None:
        f = Path(percorso)
        return f if f.is_file() else None
    radice = Path(__file__).resolve().parent
    qui = radice / ".env"
    if qui.is_file():
        return qui
    return _risali_cercando_env(Path.cwd())


def _carica_a_mano(f: Path) -> None:
    for riga in f.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        chiave, _, valore = riga.partition("=")
        chiave = chiave.strip()
        if chiave.startswith("export "):
            chiave = chiave[len("export "):].strip()
        valore = valore.strip()
        if len(valore) >= 2 and valore[0] == valore[-1] and valore[0] in "\"'":
            valore = valore[1:-1]
        if chiave:
            os.environ.setdefault(chiave, valore)


def carica_env(percorso: str | os.PathLike[str] | None = None) -> bool:
    """Porta le variabili di `.env` nell'ambiente. True se il file c'era.

    Non sovrascrive mai una variabile gia' presente: nella Action le chiavi
    arrivano dai secrets, e un `.env` dimenticato nel checkout non deve
    poterle spegnere.
    """
    f = _file_env(percorso)

    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ImportError:
        pass
    else:
        if f is None:
            return False
        return bool(load_dotenv(f))

    if f is None:
        return False
    _carica_a_mano(f)
    return True
