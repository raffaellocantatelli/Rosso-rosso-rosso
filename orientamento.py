#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOVE SONO — orientamento rapido per un nodo che si sveglia.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Il primo comando di ogni sessione. Risponde a una sola domanda: **quanto è
cambiato il mondo da quando qualcuno ha guardato l'ultima volta?**

REGOLA CHE QUESTO FILE ESISTE PER IMPORRE
------------------------------------------
«Adesso» viene dall'orologio di sistema. **Mai** dal file più recente.

Il 2026-08-28 un nodo ha datato tutto il proprio lavoro 26/08 perché l'ultimo
daily del repository era quello, e ha depositato due file sbagliati sul Drive
prima di accorgersene. È il difetto di CLAUDE.md §4 applicato al tempo: il
sistema ha letto il proprio output e l'ha scambiato per il mondo.

Qui ogni numero è uno **scarto contro l'orologio**, mai un valore assoluto
copiato da un file. Un file vecchio di due giorni lo dice.

Uso:
    python orientamento.py            # veloce, solo stato locale
    python orientamento.py --fetch    # aggiorna prima i rami remoti (rete)

Esce con 1 se c'è qualcosa di scaduto o imminente, 0 se tutto è nei tempi.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ADESSO = datetime.now(timezone.utc)
OGGI = ADESSO.date()

ROSSO = "\033[31m"; GIALLO = "\033[33m"; VERDE = "\033[32m"; GRIGIO = "\033[90m"; FINE = "\033[0m"
if not sys.stdout.isatty() or os.getenv("NO_COLOR"):
    ROSSO = GIALLO = VERDE = GRIGIO = FINE = ""

allarmi: list = []


def giorni_fa(quando) -> int:
    if isinstance(quando, str):
        quando = datetime.fromisoformat(quando.replace("Z", "+00:00")).date()
    elif isinstance(quando, datetime):
        quando = quando.date()
    return (OGGI - quando).days


def etichetta(giorni: int, soglia_gialla: int = 1, soglia_rossa: int = 3) -> str:
    if giorni >= soglia_rossa:
        return f"{ROSSO}{giorni}g fa{FINE}"
    if giorni >= soglia_gialla:
        return f"{GIALLO}{giorni}g fa{FINE}"
    return f"{VERDE}{giorni}g fa{FINE}" if giorni else f"{VERDE}oggi{FINE}"


def git(*args) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# ------------------------------------------------------------------
def sezione(titolo: str) -> None:
    print(f"\n{titolo}")
    print("─" * len(titolo))


def battito() -> None:
    sezione("BATTITO — il sistema produce ancora?")

    daily = sorted(glob.glob(os.path.join("output", "daily_*.txt")))
    if not daily:
        print(f"  {ROSSO}nessun daily{FINE}")
        allarmi.append("nessun daily in output/")
        return
    ultimo = os.path.basename(daily[-1])
    data = re.search(r"(\d{4}-\d{2}-\d{2})", ultimo).group(1)
    g = giorni_fa(data)
    print(f"  ultimo daily     {ultimo}  {etichetta(g, 2, 3)}")
    if g >= 3:
        allarmi.append(f"battito: {g} giorni senza daily — la Action gira ancora?")

    health = os.path.join("output", "health_log.jsonl")
    if os.path.exists(health):
        righe = [json.loads(r) for r in open(health, encoding="utf-8") if r.strip()]
        if righe:
            ult = righe[-1]
            reali = [v for v in righe
                     if any(p["disponibile"] for n, p in v["providers"].items() if n != "stub")]
            g = giorni_fa(ult["data_iso"])
            attivi = [n for n, p in ult["providers"].items() if p["disponibile"] and n != "stub"]
            stato = f"{VERDE}{', '.join(attivi)}{FINE}" if attivi else f"{ROSSO}nessun provider reale{FINE}"
            print(f"  ultimo health    {ult['data_iso']}  {etichetta(g, 2, 3)}  →  {stato}")
            print(f"  {GRIGIO}rilevazioni con provider reale: {len(reali)}/{len(righe)}{FINE}")


def contatti() -> None:
    sezione("CONTATTO — il sistema tocca il mondo?")
    p = os.path.join("output", "contatti.jsonl")
    n = sum(1 for r in open(p, encoding="utf-8") if r.strip()) if os.path.exists(p) else 0
    if n:
        print(f"  {VERDE}{n} contatti registrati{FINE}")
    else:
        print(f"  {ROSSO}0 contatti{FINE} — H2 cade sul ramo (b): vivo, ma non tocca niente")
        print(f"  {GRIGIO}python -m sdq1 --contatto --tipo … --nota … --verifica …{FINE}")


def scadenze() -> None:
    """Le scadenze contano i giorni contro l'orologio, non contro i file."""
    sezione("SCADENZE — quanto manca, contato adesso")

    trovate = []
    if os.path.exists("registro_ipotesi.json"):
        for h in json.load(open("registro_ipotesi.json", encoding="utf-8")):
            if h.get("scadenza"):
                trovate.append((h["id"], h["stato"], h["scadenza"]))

    # Gli esperimenti intermedi vivono nell'ultimo STATO_SESSIONE depositato.
    stati = sorted(glob.glob(os.path.join("memoria", "STATO_SESSIONE_*.json")))
    if stati:
        try:
            d = json.load(open(stati[-1], encoding="utf-8"))
            for chiave, valore in d.items():
                if isinstance(valore, dict) and valore.get("scadenza"):
                    trovate.append((chiave, valore.get("azione", "")[:52], valore["scadenza"]))
        except (json.JSONDecodeError, OSError):
            pass

    if not trovate:
        print(f"  {GRIGIO}nessuna scadenza dichiarata{FINE}")
        return

    for nome, nota, scadenza in sorted(trovate, key=lambda t: t[2]):
        mancano = (datetime.fromisoformat(scadenza).date() - OGGI).days
        if mancano < 0:
            testo = f"{ROSSO}SCADUTA da {-mancano}g{FINE}"
            allarmi.append(f"{nome}: scaduta da {-mancano} giorni")
        elif mancano <= 3:
            testo = f"{ROSSO}fra {mancano} giorni{FINE}"
            allarmi.append(f"{nome}: scade fra {mancano} giorni ({scadenza})")
        elif mancano <= 14:
            testo = f"{GIALLO}fra {mancano} giorni{FINE}"
        else:
            testo = f"{GRIGIO}fra {mancano} giorni{FINE}"
        print(f"  {nome:22.22s} {scadenza}  {testo}")
        if nota:
            print(f"  {GRIGIO}{'':22s} {nota}{FINE}")


def rami(fetch: bool) -> None:
    sezione("RAMI — sto lavorando dove lavora il progetto?")
    if not git("rev-parse", "--git-dir"):
        print(f"  {GRIGIO}non è un repository git{FINE}")
        return
    if fetch:
        subprocess.run(["git", "fetch", "origin", "--prune", "--quiet"], timeout=120)

    corrente = git("rev-parse", "--abbrev-ref", "HEAD")
    print(f"  ramo corrente    {corrente}")

    sporco = git("status", "--porcelain")
    if sporco:
        print(f"  {GIALLO}modifiche non committate: {len(sporco.splitlines())} file{FINE}")

    remoti = [r for r in git("for-each-ref", "--format=%(refname:short)",
                             "refs/remotes/origin").splitlines() if not r.endswith("/HEAD")]
    dietro = []
    for ramo in remoti:
        if ramo.endswith(corrente):
            continue
        n = git("rev-list", "--count", f"HEAD..{ramo}")
        if n and n.isdigit() and int(n) > 0:
            ultimo = git("log", "-1", "--format=%cs", ramo)
            dietro.append((ramo, int(n), ultimo))

    if not dietro:
        print(f"  {VERDE}nessun ramo remoto ha commit che questo non ha{FINE}")
        return

    print(f"  {ROSSO}commit che questo ramo NON ha:{FINE}")
    for ramo, n, ultimo in sorted(dietro, key=lambda t: -t[1]):
        g = giorni_fa(ultimo) if ultimo else 999
        print(f"    {ramo:52.52s} +{n:3d}  ultimo {ultimo} ({g}g fa)")
        if n >= 5:
            allarmi.append(f"{ramo} ha {n} commit che questo ramo non ha")
    if not fetch:
        print(f"  {GRIGIO}(riferimenti locali — riesegui con --fetch per essere sicuro){FINE}")


def deposito() -> None:
    sezione("DEPOSITO — quando qualcuno ha guardato l'ultima volta")
    stati = sorted(glob.glob(os.path.join("memoria", "STATO_SESSIONE_*.json")))
    if not stati:
        print(f"  {GRIGIO}nessuno STATO_SESSIONE depositato{FINE}")
        return
    ultimo = stati[-1]
    data = re.search(r"(\d{4}-\d{2}-\d{2})", ultimo).group(1)
    g = giorni_fa(data)
    print(f"  ultimo stato     {os.path.basename(ultimo)}  {etichetta(g, 2, 4)}")
    if g >= 2:
        print(f"  {GIALLO}Il Drive può essere cambiato da allora: elenca la cartella,{FINE}")
        print(f"  {GIALLO}non fidarti di questo file per sapere cosa c'è adesso.{FINE}")


def main() -> int:
    p = argparse.ArgumentParser(description="Orientamento rapido: quanto è cambiato il mondo.")
    p.add_argument("--fetch", action="store_true", help="Aggiorna i rami remoti prima di confrontare (rete).")
    args = p.parse_args()

    print(f"\n{VERDE}ADESSO: {ADESSO:%Y-%m-%d %H:%M UTC}{FINE}  "
          f"{GRIGIO}(orologio di sistema — non dedurre la data dai file){FINE}")

    battito()
    contatti()
    scadenze()
    rami(args.fetch)
    deposito()

    sezione("COSA GUARDARE PRIMA DI TOCCARE QUALSIASI COSA")
    if allarmi:
        for a in allarmi:
            print(f"  {ROSSO}▸{FINE} {a}")
        print()
        return 1
    print(f"  {VERDE}niente di scaduto o divergente.{FINE}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
