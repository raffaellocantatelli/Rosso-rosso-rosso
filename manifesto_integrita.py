#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Layer 4 del Guardian Layer — manifesto di integrità.

Il Guardian Layer prevede quattro layer di memoria. I primi tre (Drive, repo,
copia offline) conservano. Il quarto verifica che ciò che è conservato non sia
cambiato di nascosto — ed è l'unico che non era mai stato implementato.

Senza di lui la ridondanza copia anche le corruzioni, senza accorgersene.

    python manifesto_integrita.py             # genera/aggiorna il manifesto
    python manifesto_integrita.py --verifica  # confronta e segnala le divergenze

Falsificabile per costruzione (P6): se un file chiave cambia senza che il
manifesto venga rigenerato, `--verifica` esce con codice 1 e nomina il file.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

MANIFESTO = "MANIFESTO_INTEGRITA.json"

# File chiave del nucleo di continuità. Il manifesto copre ciò che, se cambiasse
# in silenzio, cambierebbe il comportamento o l'identità del sistema.
SORVEGLIATI = [
    "CLAUDE.md",
    "README.md",
    "registro_ipotesi.py",
    "registro_ipotesi.json",
    "trasmissione_ciclica.py",
    "manifesto_integrita.py",
    "R3_DECISIONI_E_PROTOCOLLO_2026-08-10.md",
    ".github/workflows/daily.yml",
]

# Tutto il codice del sistema, ricorsivamente.
ALBERI = ["sdq1", "r3"]
ESTENSIONI = (".py", ".yml", ".yaml", ".md")


def file_da_sorvegliare():
    visti = set()
    for percorso in SORVEGLIATI:
        if os.path.isfile(percorso):
            visti.add(percorso)
    for albero in ALBERI:
        for radice, _dirs, files in os.walk(albero):
            if "__pycache__" in radice:
                continue
            for nome in sorted(files):
                if nome.endswith(ESTENSIONI):
                    visti.add(os.path.join(radice, nome))
    return sorted(visti)


def sha256(percorso):
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        for blocco in iter(lambda: f.read(65536), b""):
            h.update(blocco)
    return h.hexdigest()


def istantanea():
    return {
        percorso: {"sha256": sha256(percorso), "byte": os.path.getsize(percorso)}
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
    print(f"Manifesto scritto: {MANIFESTO} ({len(voci)} file sorvegliati)")
    return 0


def verifica():
    if not os.path.exists(MANIFESTO):
        print(f"Nessun manifesto trovato ({MANIFESTO}). Generalo con:", file=sys.stderr)
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
