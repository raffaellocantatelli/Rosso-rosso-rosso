#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Registro dei nodi concorrenti — append-only.

Il problema che risolve: piu' intelligenze lavorano sullo stesso repository
e sulla stessa cartella Drive, senza potersi coordinare. Ogni nodo, per non
perdere il proprio stato, ne salva una copia con la data nel nome. In tre
giorni sono nate 6 copie di R3_WORK_QUEUE e 5 report di sincronizzazione.

E' la stessa malattia delle 7 copie dell'indice, automatizzata.

La causa e' che ogni nodo CONSERVA invece di TRASMETTERE. La soluzione non
puo' essere chiedere ai nodi di essere educati: nessuno puo' garantirlo.
Deve essere un meccanismo che funziona senza cooperazione.

Questo file e' quel meccanismo:

  - APPEND-ONLY. Nessun nodo modifica mai una riga esistente, quindi due
    nodi non possono sovrascriversi. Al massimo git segnala un conflitto
    sull'ultima riga, e nessun contenuto viene perso.
  - UNA SOLA FONTE. Non esistono copie con la data nel nome, perche' git
    conserva gia' tutta la cronologia con gli hash. Una copia datata e' un
    secondo sistema di versionamento che gira in parallelo al primo: non
    aggiunge sicurezza, aggiunge ambiguita'.
  - DICHIARAZIONE OBBLIGATORIA. Ogni nodo dice chi e', cosa ha toccato e
    perche'. Chi arriva dopo legge il registro e sa cosa e' successo senza
    dover ricostruire dai diff.

    python registro_nodi.py --nodo claude --azione "..." --file a.py b.py
    python registro_nodi.py --leggi          # ultime 20 voci
    python registro_nodi.py --conflitti      # file toccati da piu' nodi

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict

REGISTRO = os.path.join("memoria", "REGISTRO_NODI.jsonl")


def _voci():
    if not os.path.exists(REGISTRO):
        return []
    voci = []
    with open(REGISTRO, "r", encoding="utf-8") as f:
        for riga in f:
            riga = riga.strip()
            if not riga:
                continue
            try:
                voci.append(json.loads(riga))
            except json.JSONDecodeError:
                # Una riga corrotta non deve impedire di leggere le altre:
                # e' il punto dell'append-only.
                continue
    return voci


def annota(nodo, azione, file_toccati, note=""):
    os.makedirs(os.path.dirname(REGISTRO), exist_ok=True)
    voce = {
        "data_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "nodo": nodo,
        "azione": azione,
        "file": sorted(file_toccati or []),
        "note": note,
    }
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(json.dumps(voce, ensure_ascii=False) + "\n")
    print(f"Annotato: {nodo} — {azione} ({len(voce['file'])} file)")
    return 0


def leggi(quante):
    voci = _voci()
    if not voci:
        print("Registro vuoto. Nessun nodo ha ancora dichiarato il proprio lavoro.")
        return 0
    print(f"=== Ultime {min(quante, len(voci))} voci di {len(voci)} ===\n")
    for v in voci[-quante:]:
        print(f"{v['data_iso']}  [{v['nodo']}]  {v['azione']}")
        for f in v["file"]:
            print(f"      {f}")
        if v.get("note"):
            print(f"      nota: {v['note']}")
    return 0


def conflitti():
    """File toccati da piu' nodi diversi: il punto dove nascono i conflitti."""
    per_file = defaultdict(set)
    for v in _voci():
        for f in v["file"]:
            per_file[f].add(v["nodo"])

    contesi = {f: n for f, n in per_file.items() if len(n) > 1}
    if not contesi:
        print("Nessun file risulta toccato da piu' nodi.")
        return 0

    print("=== File contesi (toccati da nodi diversi) ===\n")
    for f in sorted(contesi):
        print(f"  {f}")
        print(f"      nodi: {', '.join(sorted(contesi[f]))}")
    print(f"\n{len(contesi)} file contesi. Sono i candidati a rompersi per primi.")
    return 1


def main():
    p = argparse.ArgumentParser(description="Registro append-only dei nodi concorrenti")
    p.add_argument("--nodo", help="Chi sei (es. claude, gemini, grok)")
    p.add_argument("--azione", help="Cosa hai fatto, in una riga")
    p.add_argument("--file", nargs="*", default=[], help="File toccati")
    p.add_argument("--note", default="", help="Nota facoltativa")
    p.add_argument("--leggi", nargs="?", type=int, const=20, help="Mostra le ultime N voci")
    p.add_argument("--conflitti", action="store_true", help="File toccati da piu' nodi")
    args = p.parse_args()

    if args.conflitti:
        sys.exit(conflitti())
    if args.leggi is not None:
        sys.exit(leggi(args.leggi))
    if args.nodo and args.azione:
        sys.exit(annota(args.nodo, args.azione, args.file, args.note))

    p.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
