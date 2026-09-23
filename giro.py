#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""giro.py — il giro che si fa da solo quando l'autore non c'e'.

Origine protetta: Claudio Terzi [CT-LGAI-001].
Chiesto da Claudio Terzi il 23/09/2026: «ci sono momenti in cui non posso
risponderti perche' sto andando in viaggio con la valigia».

Il problema non e' fare girare dei comandi: e' **non disturbarlo per niente.**
Un automatismo che ogni giorno dice «tutto ok» e' rumore, e dopo tre giorni
non lo legge piu' nessuno — compreso il giorno in cui qualcosa era successo.

Percio' questo giro non riferisce cosa ha fatto. Riferisce **cosa e'
cambiato** rispetto al giro precedente, e se non e' cambiato niente esce in
silenzio con codice 0. Chi lo chiama (una Routine, un'Action, un cron) si
regola su quello:

    0   niente di nuovo — non chiamarlo
    1   qualcosa e' cambiato — c'e' qualcosa da leggere
    2   qualcosa si e' rotto — quello si dice sempre, anche in viaggio

Lo stato di ogni giro finisce in `output/giro.jsonl`, append-only: confrontare
col passato e' l'unico modo per sapere se e' entrato qualcosa dall'esterno,
che e' la sola domanda che conta (CLAUDE.md §4).

    python3 giro.py              # esegue e confronta
    python3 giro.py --prova      # esegue senza scrivere
    python3 giro.py --storia     # gli ultimi giri
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

STORICO = Path(os.environ.get("R3_GIRO", "output/giro.jsonl"))

#: Ogni voce e' un comando che PUO' FALLIRE, con cosa significa la sua uscita.
#: Niente che non possa fallire: cio' che non puo' fallire non dice niente.
CONTROLLI = [
    ("limiti", "python3 registro_nodi.py --ritenta",
     "0 = un limite e' CADUTO (la notizia piu' utile che ci sia), 1 = reggono"),
    ("integrita", "python3 manifesto_integrita.py --verifica",
     "0 = nessuna divergenza; altro = un file sorvegliato e' cambiato"),
    ("test", "python3 -m pytest tests/ -q",
     "0 = la suite regge; altro = qualcosa si e' rotto e va detto subito"),
    ("core", "python3 -m sdq1 --check",
     "0 = il Core ha un provider reale; altro = gira a vuoto"),
]

#: File il cui NUMERO DI RIGHE e' la misura. Una riga in piu' in contatti.jsonl
#: e' l'evento che il progetto aspetta da mesi (H2 ramo b).
CONTATORI = {
    "contatti": "output/contatti.jsonl",
    "risposte_nodi": "output/rassegna_nodi.jsonl",
    "verifiche": "output/verifiche.jsonl",
}


def _esegui(comando, secondi=600):
    try:
        r = subprocess.run(comando, shell=True, capture_output=True,
                           text=True, timeout=secondi)
    except subprocess.TimeoutExpired:
        return 124, "scaduto dopo %ds" % secondi
    except OSError as e:
        return 127, str(e)
    testo = (r.stdout or "") + (r.stderr or "")
    righe = [l.strip() for l in testo.splitlines() if l.strip()]
    return r.returncode, (righe[-1][:200] if righe else "")


def _righe(percorso):
    p = Path(percorso)
    if not p.exists():
        return 0
    return sum(1 for r in p.read_text(encoding="utf-8").splitlines() if r.strip())


def _giri():
    if not STORICO.exists():
        return []
    fuori = []
    for riga in STORICO.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga:
            continue
        try:
            fuori.append(json.loads(riga))
        except json.JSONDecodeError:
            continue
    return fuori


def misura():
    """Esegue tutto e restituisce lo stato di adesso. Non giudica."""
    stato = {
        "data_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "controlli": {},
        "contatori": {n: _righe(p) for n, p in CONTATORI.items()},
    }
    for nome, comando, _ in CONTROLLI:
        uscita, riga = _esegui(comando)
        stato["controlli"][nome] = {"uscita": uscita, "riga": riga}
    return stato


def confronta(adesso, prima):
    """Cosa e' cambiato. Restituisce (notizie, rotture)."""
    notizie, rotture = [], []

    for nome, dati in adesso["controlli"].items():
        u = dati["uscita"]
        vecchia = (prima or {}).get("controlli", {}).get(nome, {}).get("uscita")
        if nome == "limiti" and u == 0:
            notizie.append("UN LIMITE E' CADUTO — %s" % dati["riga"])
        elif nome in ("integrita", "test") and u != 0:
            rotture.append("%s: uscita %d — %s" % (nome, u, dati["riga"]))
        elif vecchia is not None and u != vecchia:
            notizie.append("%s: uscita %s -> %s (%s)" % (nome, vecchia, u, dati["riga"]))

    for nome, quante in adesso["contatori"].items():
        prima_quante = (prima or {}).get("contatori", {}).get(nome)
        if prima_quante is None:
            continue
        if quante > prima_quante:
            notizie.append("%s: %d -> %d — e' entrato qualcosa dall'esterno"
                           % (nome, prima_quante, quante))
        elif quante < prima_quante:
            rotture.append("%s: %d -> %d — sono SPARITE delle righe"
                           % (nome, prima_quante, quante))

    return notizie, rotture


def giro(prova=False):
    giri = _giri()
    prima = giri[-1] if giri else None
    adesso = misura()
    notizie, rotture = confronta(adesso, prima)

    if not prova:
        STORICO.parent.mkdir(parents=True, exist_ok=True)
        with STORICO.open("a", encoding="utf-8") as f:
            f.write(json.dumps(adesso, ensure_ascii=False) + "\n")

    if prima is None:
        print("Primo giro: non c'e' niente con cui confrontare. Stato depositato.")
        for nome, dati in adesso["controlli"].items():
            print("  %-12s uscita %s" % (nome, dati["uscita"]))
        for nome, quante in adesso["contatori"].items():
            print("  %-12s %d righe" % (nome, quante))
        return 1

    for r in rotture:
        print("ROTTO    %s" % r)
    for n in notizie:
        print("NUOVO    %s" % n)

    if rotture:
        return 2
    if notizie:
        return 1
    return 0


def storia(quanti=10):
    giri = _giri()
    if not giri:
        print("Nessun giro ancora.")
        return 0
    for g in giri[-quanti:]:
        uscite = " ".join("%s=%s" % (n, d["uscita"]) for n, d in g["controlli"].items())
        contatori = " ".join("%s=%d" % (n, q) for n, q in g["contatori"].items())
        print("%s  %s | %s" % (g["data_iso"], uscite, contatori))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python3 giro.py",
        description="Il giro che riferisce solo cosa e' cambiato. "
                    "Origine protetta: Claudio Terzi [CT-LGAI-001].")
    p.add_argument("--prova", action="store_true", help="esegue senza scrivere")
    p.add_argument("--storia", nargs="?", type=int, const=10, help="gli ultimi N giri")
    a = p.parse_args(argv)
    if a.storia is not None:
        return storia(a.storia)
    return giro(a.prova)


if __name__ == "__main__":
    sys.exit(main())
