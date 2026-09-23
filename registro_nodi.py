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

I LIMITI (dal 23/09/2026). Un nodo che dichiara «qui non si puo' fare X»
deposita una rinuncia che ogni nodo successivo eredita senza controllarla: e'
l'eco di §4 applicata non ai dati ma alle rese. Percio' un limite si registra
solo insieme al comando che lo dimostra, e il registro quel comando lo ESEGUE:

    python registro_nodi.py --nodo X --limite "..." --provato-con "docker info"
    python registro_nodi.py --limiti         # i limiti dichiarati, col comando
    python registro_nodi.py --ritenta        # riesegue: quali sono caduti

Se il comando riesce, il limite viene RIFIUTATO: non era un limite.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import argparse
import json
import os
import subprocess
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


def _esegui(comando, secondi=120):
    """Esegue e restituisce (uscita, prima riga utile). Il registro esegue, non
    crede: un limite senza un comando che lo dimostri non e' un limite."""
    try:
        r = subprocess.run(comando, shell=True, capture_output=True,
                           text=True, timeout=secondi)
    except subprocess.TimeoutExpired:
        return 124, "scaduto dopo %ds" % secondi
    except OSError as e:
        return 127, str(e)
    testo = (r.stderr or "") + (r.stdout or "")
    riga = next((l.strip() for l in testo.splitlines() if l.strip()), "")
    return r.returncode, riga[:300]


#: Un comando che cerca dentro il testo del progetto puo' trovare se stesso:
#: il registro e la documentazione contengono il comando, quindi il giorno in
#: cui qualcuno lo scrive da qualche parte il limite "cade" senza che sia
#: cambiato niente nel mondo. E' il loopback di CLAUDE.md §4 dentro lo
#: strumento costruito per impedirlo — successo davvero il 23/09/2026.
CERCA_NEL_PROGETTO = ("grep -r", "grep -R", "git grep", "rg ", "ack ")


def limite(nodo, descrizione, comando):
    """Registra un limite SOLO se il comando che dovrebbe dimostrarlo fallisce."""
    for spia in CERCA_NEL_PROGETTO:
        if spia in comando:
            print("RIFIUTATO — `%s` cerca dentro il testo del progetto." % spia.strip())
            print("Il registro e la documentazione contengono il comando stesso: prima o")
            print("poi si troverebbe da solo e il limite cadrebbe senza che sia cambiato")
            print("niente. Prova una condizione del mondo: un file, una variabile, una")
            print("connessione — non una parola scritta qui dentro.")
            return 2
    uscita, riga = _esegui(comando)
    if uscita == 0:
        print("RIFIUTATO — `%s` riesce (uscita 0)." % comando)
        print("Non e' un limite: e' una cosa che non era stata provata.")
        if riga:
            print("  prima riga: %s" % riga)
        return 1
    os.makedirs(os.path.dirname(REGISTRO), exist_ok=True)
    voce = {
        "data_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "nodo": nodo,
        "tipo": "limite",
        "azione": "limite dichiarato: " + descrizione,
        "comando": comando,
        "uscita": uscita,
        "prima_riga": riga,
        "file": [],
        "note": "",
    }
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(json.dumps(voce, ensure_ascii=False) + "\n")
    print("Limite registrato: %s" % descrizione)
    print("  `%s` -> uscita %d%s" % (comando, uscita, (": " + riga) if riga else ""))
    print("  Resta valido finche' qualcuno non lo fa cadere: --ritenta")
    return 0


def _limiti_dichiarati():
    """I limiti in vigore. Append-only vuol dire che non si cancella niente —
    ma due dichiarazioni della stessa cosa non possono valere entrambe
    (§6 regola 2). Vince l'ultima: le precedenti restano nella storia."""
    per_descrizione = {}
    for v in _voci():
        if v.get("tipo") == "limite" and v.get("comando"):
            per_descrizione[v.get("azione", "")] = v
    return list(per_descrizione.values())


def limiti():
    voci = _limiti_dichiarati()
    if not voci:
        print("Nessun limite dichiarato. Nessuna resa ereditata.")
        return 0
    print("=== Limiti dichiarati (ognuno col comando che lo dimostra) ===\n")
    for v in voci:
        print("%s  [%s]" % (v["data_iso"], v["nodo"]))
        print("      %s" % v["azione"])
        print("      $ %s   -> uscita %s" % (v["comando"], v.get("uscita")))
        if v.get("prima_riga"):
            print("      %s" % v["prima_riga"])
    print("\n%d limiti. Non sono fatti del mondo: sono misure di un momento." % len(voci))
    return 0


def ritenta():
    """Riesegue i comandi dei limiti dichiarati. Un limite caduto e' la cosa
    piu' utile che un nodo possa trovare nel lavoro di un altro."""
    voci = _limiti_dichiarati()
    if not voci:
        print("Nessun limite da ritentare.")
        return 0
    caduti = 0
    print("=== Ritento %d limiti ===\n" % len(voci))
    for v in voci:
        uscita, riga = _esegui(v["comando"])
        if uscita == 0:
            caduti += 1
            print("CADUTO   %s" % v["azione"])
            print("         `%s` adesso riesce. Dichiarato da %s il %s."
                  % (v["comando"], v["nodo"], v["data_iso"][:10]))
        else:
            print("regge    %s  (uscita %d)" % (v["azione"], uscita))
    print()
    if caduti:
        print("%d limiti sono caduti. Annotalo: e' entrato qualcosa di nuovo." % caduti)
        return 0
    print("Nessun limite caduto. Non vuol dire che siano veri: vuol dire che")
    print("nessuno li ha ancora fatti cadere.")
    return 1


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
    p.add_argument("--limite", help="Dichiara un limite: richiede --provato-con")
    p.add_argument("--provato-con", dest="provato_con",
                   help="Il comando che dimostra il limite. Viene ESEGUITO")
    p.add_argument("--limiti", action="store_true", help="Elenca i limiti dichiarati")
    p.add_argument("--ritenta", action="store_true",
                   help="Riesegue i comandi dei limiti: quali sono caduti")
    args = p.parse_args()

    if args.conflitti:
        sys.exit(conflitti())
    if args.limiti:
        sys.exit(limiti())
    if args.ritenta:
        sys.exit(ritenta())
    if args.limite:
        if not args.provato_con:
            print("Serve --provato-con: un limite senza il comando che lo dimostra e'")
            print("una rinuncia che ogni nodo dopo di te eredita senza controllarla.")
            sys.exit(2)
        if not args.nodo:
            print("Serve --nodo: chi dichiara il limite.")
            sys.exit(2)
        sys.exit(limite(args.nodo, args.limite, args.provato_con))
    if args.leggi is not None:
        sys.exit(leggi(args.leggi))
    if args.nodo and args.azione:
        sys.exit(annota(args.nodo, args.azione, args.file, args.note))

    p.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
