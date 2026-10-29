#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Layer 4 del Guardian Layer — manifesto di integrità.

Il Guardian Layer prevede quattro layer di memoria. I primi tre (Drive, repo,
copia offline) conservano. Il quarto verifica che ciò che è conservato non sia
cambiato di nascosto — ed è l'unico che non era mai stato implementato.

Senza di lui la ridondanza copia anche le corruzioni, senza accorgersene.

    python manifesto_integrita.py             # genera/aggiorna il manifesto
    python manifesto_integrita.py --verifica  # confronta e segnala le divergenze

Falsificabile per costruzione (P6): se un file del repository cambia, nasce o
sparisce senza che il manifesto venga rigenerato, `--verifica` esce con codice
1 e nomina il file.

**La copertura e' per difetto, dal 17/09.** Prima era un elenco scritto a mano
piu' sei alberi, filtrati per estensione: 434 file nel repository, 308
sorvegliati. I 126 fuori non erano scelti — erano quelli a cui nessuno aveva
pensato, e **ogni file nuovo nasceva fuori**. `occhio/`, cioe' il prodotto
intero, non era coperto; nemmeno `contraddittore.py`, `archivio.py`,
`rassegna.py`, `esperimenti/`.

Un Layer 4 che non vede i file nuovi non protegge il repository: protegge la
fotografia che qualcuno ne ha scattato una volta. Adesso il confine del
manifesto e' il confine del repository — lo decide `.gitignore`, che e'
dell'autore — e le uniche cose fuori sono elencate in `ESCLUSI`, ciascuna con
il motivo accanto.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

RADICE = os.path.dirname(os.path.abspath(__file__))
MANIFESTO = os.path.join(RADICE, "MANIFESTO_INTEGRITA.json")

# Cio' che il manifesto NON copre, con il motivo accanto. Un'esclusione senza
# motivo dichiarato e' un buco con una scusa.
#
# Le tre esclusioni di runtime sono esattamente i percorsi che la Action
# giornaliera committa a ogni giro (`git add` in `.github/workflows/daily.yml`).
# Coprirli significherebbe un avviso rosso ogni notte, per costruzione: e un
# avviso che si accende sempre e' una lettura che non obbliga a niente — il
# difetto che `latenza.py` esiste per misurare. Un test lega le due cose: se
# qualcuno aggiunge un percorso a quel `git add`, deve dichiararlo anche qui.
ESCLUSI = {
    "MANIFESTO_INTEGRITA.json": "non puo' contenere il proprio hash",
    "output": "cio' che il sistema produce: la run giornaliera lo riscrive",
    "sdq1/memory/store.json": "memoria vettoriale, riscritta a ogni daily",
    "sdq1/sar/state.json": "stato SAR, riscritto a ogni daily",
}

# Il nucleo: non e' un elenco di cio' che si copre — si copre tutto — ma di
# cio' che non puo' restare scoperto. Se un domani qualcuno restringe la
# copertura, il test su questi file glielo dice. I motivi, in breve: senza
# `registro_ipotesi.*` il registro puo' dire RETTA senza prova; senza i test
# delle guardie, P5 e P6 restano nel codice ma smettono di essere verificati;
# senza `verificatore.py` e i falsificatori, eseguire torna a essere leggere.
NUCLEO = (
    "CLAUDE.md",
    "registro_ipotesi.py",
    "registro_ipotesi.json",
    "registro_osservazioni.py",
    "test_registro_ipotesi.py",
    "test_registro_osservazioni.py",
    "verificatore.py",
    "manifesto_integrita.py",
    "ambiente.py",
    "test_ambiente.py",
    "latenza.py",
    "trasmissione_ciclica.py",
    ".github/workflows/daily.yml",
)


class RepositoryAssente(RuntimeError):
    """Senza git non si sa dove finisce il repository, e non si indovina."""


def _file_del_repository():
    """Ogni file che appartiene al repository, **i nuovi compresi**.

    Tracciati piu' non tracciati e non ignorati: e' la definizione di git di
    «dentro il repository», e il confine lo disegna `.gitignore`, che e' una
    decisione dell'autore — i registri di `occhio` stanno fuori apposta,
    perche' contengono le firme di un ospite e questo repository e' pubblico.

    Se git non c'e', questa funzione **solleva** invece di ripiegare su una
    camminata del disco: due definizioni diverse di «dentro» darebbero due
    manifesti diversi a seconda dell'ambiente, ed e' il difetto che il Layer 4
    dovrebbe scoprire, non commettere.
    """
    try:
        esito = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=RADICE, capture_output=True,
        )
    except OSError as e:
        raise RepositoryAssente(f"git non eseguibile: {e}") from e
    if esito.returncode != 0:
        raise RepositoryAssente(
            "git non riesce a elencare i file "
            f"({esito.stderr.decode('utf-8', 'replace').strip()})"
        )
    return [p for p in esito.stdout.decode("utf-8").split("\0") if p]


def escluso(percorso):
    """True se `percorso` e' fuori dal manifesto per una regola dichiarata."""
    for voce in ESCLUSI:
        if percorso == voce or percorso.startswith(voce + "/"):
            return True
    return False


def file_da_sorvegliare():
    return sorted(
        p for p in _file_del_repository()
        if not escluso(p) and os.path.isfile(os.path.join(RADICE, p))
    )


def sha256(percorso):
    h = hashlib.sha256()
    with open(os.path.join(RADICE, percorso), "rb") as f:
        for blocco in iter(lambda: f.read(65536), b""):
            h.update(blocco)
    return h.hexdigest()


def istantanea():
    return {
        percorso: {
            "sha256": sha256(percorso),
            "byte": os.path.getsize(os.path.join(RADICE, percorso)),
        }
        for percorso in file_da_sorvegliare()
    }


def genera():
    voci = istantanea()
    manifesto = {
        "generato": datetime.now(timezone.utc).isoformat(),
        "origine": "Claudio Terzi [CT-LGAI-001]",
        "algoritmo": "sha256",
        "file": voci,
    }
    with open(MANIFESTO, "w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"Manifesto scritto: {os.path.basename(MANIFESTO)} "
          f"({len(voci)} file sorvegliati)")
    return 0


def verifica():
    if not os.path.exists(MANIFESTO):
        print(f"Nessun manifesto trovato ({os.path.basename(MANIFESTO)}). "
              "Generalo con:", file=sys.stderr)
        print("  python manifesto_integrita.py", file=sys.stderr)
        return 2

    with open(MANIFESTO, "r", encoding="utf-8") as f:
        atteso = json.load(f)["file"]
    corrente = istantanea()

    mancanti = sorted(set(atteso) - set(corrente))
    nuovi = sorted(set(corrente) - set(atteso))
    modificati = sorted(
        p for p in set(atteso) & set(corrente)
        if atteso[p]["sha256"] != corrente[p]["sha256"]
    )

    for percorso in mancanti:
        print(f"MANCANTE   {percorso}")
    for percorso in modificati:
        print(f"MODIFICATO {percorso}")
        print(f"           atteso   {atteso[percorso]['sha256']}")
        print(f"           trovato  {corrente[percorso]['sha256']}")
    for percorso in nuovi:
        print(f"NUOVO      {percorso}")

    if mancanti or modificati or nuovi:
        print(
            f"\nINTEGRITÀ VIOLATA — {len(mancanti)} mancanti, "
            f"{len(modificati)} modificati, {len(nuovi)} non nel manifesto."
        )
        print("Se le modifiche sono volute, rigenera il manifesto e committalo.")
        return 1

    print(f"INTEGRITÀ OK — {len(corrente)} file, nessuna divergenza.")
    print(f"Manifesto generato il {json.load(open(MANIFESTO, encoding='utf-8'))['generato']}")
    return 0


def main():
    p = argparse.ArgumentParser(description="Layer 4 — manifesto di integrità R³∞")
    p.add_argument("--verifica", action="store_true", help="Confronta invece di generare")
    args = p.parse_args()
    sys.exit(verifica() if args.verifica else genera())


if __name__ == "__main__":
    main()
