"""Persistenza SQLite.

Quattro tabelle: users, open_possibilities, actions, sanctuary_visits.
Il database viene creato al primo avvio (protocollo.db, o il percorso in
PROTOCOLLO_DB).

Due scelte di progetto che vengono dal Protocollo, non dalla comodita':

* le possibilita' nascono con etichetta IPOTESI e non esiste nessuna
  funzione che le chiuda o le promuova a fatto. Chi vorra' aggiungerne
  una dovra' scriverla apposta, e vedra' questa riga mentre lo fa;
* niente qui dentro conferma niente. Le funzioni scrivono e leggono; la
  verifica, se arriva, arriva da fuori (P5).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = "protocollo.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id   INTEGER PRIMARY KEY,
    nome          TEXT,
    primo_accesso TEXT NOT NULL,
    ultimo_accesso TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS open_possibilities (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id    INTEGER NOT NULL,
    testo          TEXT NOT NULL,
    falsificazione TEXT,
    etichetta      TEXT NOT NULL DEFAULT 'IPOTESI',
    creata_il      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS actions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    descrizione TEXT NOT NULL,
    verifica    TEXT,
    strato      TEXT NOT NULL DEFAULT 'tecnico',
    registrata_il TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sanctuary_visits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id   INTEGER NOT NULL,
    iniziata_il   TEXT NOT NULL,
    conclusa_il   TEXT,
    durata_gesto  REAL,
    gesto_lento   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_poss_user ON open_possibilities(telegram_id);
CREATE INDEX IF NOT EXISTS idx_azioni_user ON actions(telegram_id);
CREATE INDEX IF NOT EXISTS idx_visite_user ON sanctuary_visits(telegram_id);
"""


def db_path() -> Path:
    return Path(os.getenv("PROTOCOLLO_DB", DEFAULT_DB))


def connect(path: str | os.PathLike[str] | None = None) -> sqlite3.Connection:
    percorso = Path(path) if path is not None else db_path()
    if percorso.parent != Path("") and not percorso.parent.exists():
        percorso.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(percorso, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: str | os.PathLike[str] | None = None) -> None:
    """Crea lo schema se manca. Idempotente."""
    with connect(path) as conn:
        conn.executescript(SCHEMA)


def _adesso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- utenti -----------------------------------------------------------------

def registra_utente(telegram_id: int, nome: str | None = None,
                    path: Any = None) -> None:
    ora = _adesso()
    with connect(path) as conn:
        conn.execute(
            """INSERT INTO users (telegram_id, nome, primo_accesso, ultimo_accesso)
                    VALUES (?, ?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE SET
                    ultimo_accesso = excluded.ultimo_accesso,
                    nome = COALESCE(excluded.nome, users.nome)""",
            (telegram_id, nome, ora, ora),
        )


# --- possibilita' aperte ----------------------------------------------------

def aggiungi_possibilita(telegram_id: int, testo: str,
                         falsificazione: str | None,
                         path: Any = None) -> int:
    """Deposita una possibilita'. L'etichetta e' IPOTESI e non e' un parametro.

    falsificazione None significa UNKNOWN: nessun criterio dichiarato.
    """
    with connect(path) as conn:
        cur = conn.execute(
            """INSERT INTO open_possibilities
                   (telegram_id, testo, falsificazione, etichetta, creata_il)
               VALUES (?, ?, ?, 'IPOTESI', ?)""",
            (telegram_id, testo, falsificazione, _adesso()),
        )
        return int(cur.lastrowid)


def elenca_possibilita(telegram_id: int, path: Any = None) -> list[sqlite3.Row]:
    with connect(path) as conn:
        return conn.execute(
            """SELECT id, testo, falsificazione, etichetta, creata_il
                 FROM open_possibilities
                WHERE telegram_id = ?
             ORDER BY id""",
            (telegram_id,),
        ).fetchall()


# --- azioni -----------------------------------------------------------------

def registra_azione(telegram_id: int, descrizione: str, verifica: str | None,
                    path: Any = None) -> int:
    """Registra un dato dello strato tecnico.

    verifica None significa: nessuna verifica esterna dichiarata. Non viene
    riscritta in nessun modo piu' presentabile.
    """
    with connect(path) as conn:
        cur = conn.execute(
            """INSERT INTO actions
                   (telegram_id, descrizione, verifica, strato, registrata_il)
               VALUES (?, ?, ?, 'tecnico', ?)""",
            (telegram_id, descrizione, verifica, _adesso()),
        )
        return int(cur.lastrowid)


def elenca_azioni(telegram_id: int, path: Any = None) -> list[sqlite3.Row]:
    with connect(path) as conn:
        return conn.execute(
            """SELECT id, descrizione, verifica, registrata_il
                 FROM actions
                WHERE telegram_id = ?
             ORDER BY id""",
            (telegram_id,),
        ).fetchall()


def conta_azioni(telegram_id: int, path: Any = None) -> int:
    with connect(path) as conn:
        riga = conn.execute(
            "SELECT COUNT(*) AS n FROM actions WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
        return int(riga["n"])


def conta_azioni_verificabili(telegram_id: int, path: Any = None) -> int:
    """Quante azioni hanno una verifica esterna dichiarata.

    E' l'unico numero di questo database che dice qualcosa sul mondo fuori.
    """
    with connect(path) as conn:
        riga = conn.execute(
            """SELECT COUNT(*) AS n FROM actions
                WHERE telegram_id = ?
                  AND verifica IS NOT NULL AND TRIM(verifica) <> ''""",
            (telegram_id,),
        ).fetchone()
        return int(riga["n"])


# --- visite al Santuario ----------------------------------------------------

def inizia_visita(telegram_id: int, path: Any = None) -> int:
    with connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO sanctuary_visits (telegram_id, iniziata_il) VALUES (?, ?)",
            (telegram_id, _adesso()),
        )
        return int(cur.lastrowid)


def concludi_visita(visita_id: int, durata_gesto: float, gesto_lento: bool,
                    path: Any = None) -> None:
    """Chiude la visita con la durata reale del gesto, quale che sia."""
    with connect(path) as conn:
        conn.execute(
            """UPDATE sanctuary_visits
                  SET conclusa_il = ?, durata_gesto = ?, gesto_lento = ?
                WHERE id = ?""",
            (_adesso(), round(float(durata_gesto), 1), int(bool(gesto_lento)),
             visita_id),
        )


def elenca_visite(telegram_id: int, path: Any = None) -> list[sqlite3.Row]:
    with connect(path) as conn:
        return conn.execute(
            """SELECT id, iniziata_il, conclusa_il, durata_gesto, gesto_lento
                 FROM sanctuary_visits
                WHERE telegram_id = ?
             ORDER BY id""",
            (telegram_id,),
        ).fetchall()
