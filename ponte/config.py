#!/usr/bin/env python3
"""Configurazione del ponte verso il NAS. Nessuna credenziale vive qui dentro.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Questo repository e' PUBBLICO (CLAUDE.md §2.5). Una password letta da un file
versionato sarebbe pubblicata alla prima `git push`, e non e' un errore che si
ripara cancellandola dopo: git conserva. Quindi:

  - le credenziali si leggono SOLO dall'ambiente, o da un file fuori dal
    repository (~/.r3/webdav.env, permessi 600);
  - la riga di comando non accetta nessuna opzione `--password`, apposta:
    finirebbe nella cronologia della shell e nella lista dei processi.

Variabili lette:

    R3_WEBDAV_URL        https://host:5006          endpoint WebDAV del NAS
    R3_WEBDAV_UTENTE     account dedicato, non l'amministratore
    R3_WEBDAV_PASSWORD   password di quell'account
    R3_WEBDAV_RADICE     /R3                        cartella condivisa
    R3_NAS_QUICKCONNECT  id QuickConnect            solo per --cerca
    R3_WEBDAV_PORTA      5006                       porta WebDAV HTTPS
    R3_WEBDAV_CA         /percorso/ca.pem           certificato del NAS
    R3_WEBDAV_INSICURO   1                          disattiva la verifica TLS
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_URL = "R3_WEBDAV_URL"
ENV_UTENTE = "R3_WEBDAV_UTENTE"
ENV_PASSWORD = "R3_WEBDAV_PASSWORD"
ENV_RADICE = "R3_WEBDAV_RADICE"
ENV_QUICKCONNECT = "R3_NAS_QUICKCONNECT"
ENV_PORTA = "R3_WEBDAV_PORTA"
ENV_CA = "R3_WEBDAV_CA"
ENV_INSICURO = "R3_WEBDAV_INSICURO"

PORTA_PREDEFINITA = 5006
RADICE_PREDEFINITA = "/R3"

# Fuori dal repository, di proposito.
FILE_FUORI_REPO = Path.home() / ".r3" / "webdav.env"


def carica_env(percorso: Path | None = None) -> list[str]:
    """Legge le credenziali da ~/.r3/webdav.env senza sovrascrivere l'ambiente.

    Ritorna l'elenco dei file letti — serve a `--check` per dire da dove
    arriva la configurazione invece di lasciarlo indovinare.
    """
    letti: list[str] = []
    candidati = [percorso] if percorso else [FILE_FUORI_REPO]
    for f in candidati:
        if f is None or not f.exists():
            continue
        for riga in f.read_text(encoding="utf-8").splitlines():
            riga = riga.strip()
            if not riga or riga.startswith("#") or "=" not in riga:
                continue
            chiave, _, valore = riga.partition("=")
            os.environ.setdefault(chiave.strip(), valore.strip().strip('"').strip("'"))
        letti.append(str(f))
    return letti


def _permessi_larghi(f: Path) -> bool:
    """Vero se il file delle credenziali e' leggibile da altri utenti."""
    try:
        return bool(f.stat().st_mode & 0o077)
    except OSError:
        return False


@dataclass
class Config:
    url: str | None = None
    utente: str | None = None
    password: str | None = None
    radice: str = RADICE_PREDEFINITA
    quickconnect: str | None = None
    porta: int = PORTA_PREDEFINITA
    ca: str | None = None
    insicuro: bool = False

    @classmethod
    def da_ambiente(cls) -> "Config":
        porta = os.environ.get(ENV_PORTA, "").strip()
        return cls(
            url=os.environ.get(ENV_URL) or None,
            utente=os.environ.get(ENV_UTENTE) or None,
            password=os.environ.get(ENV_PASSWORD) or None,
            radice=os.environ.get(ENV_RADICE) or RADICE_PREDEFINITA,
            quickconnect=os.environ.get(ENV_QUICKCONNECT) or None,
            porta=int(porta) if porta.isdigit() else PORTA_PREDEFINITA,
            ca=os.environ.get(ENV_CA) or None,
            insicuro=os.environ.get(ENV_INSICURO, "").strip() in ("1", "si", "true", "vero"),
        )

    def mancanti(self) -> list[str]:
        """Cosa manca per aprire il ponte. Lista vuota = si puo' provare."""
        mancano = []
        if not self.url:
            mancano.append(ENV_URL)
        if not self.utente:
            mancano.append(ENV_UTENTE)
        if not self.password:
            mancano.append(ENV_PASSWORD)
        return mancano

    def avvertenze(self) -> list[str]:
        """Cose vere e spiacevoli da dire prima di collegarsi, non dopo."""
        note = []
        if self.url and self.url.startswith("http://"):
            note.append(
                "l'URL e' http:// e non https://: utente e password viaggiano in chiaro"
            )
        if self.insicuro:
            note.append(
                f"{ENV_INSICURO}=1: il certificato del NAS non viene verificato. "
                f"Regge contro un errore, non contro qualcuno in mezzo. "
                f"La cura vera e' {ENV_CA} con il certificato del NAS"
            )
        if FILE_FUORI_REPO.exists() and _permessi_larghi(FILE_FUORI_REPO):
            note.append(f"{FILE_FUORI_REPO} e' leggibile da altri utenti: chmod 600")
        return note
