#!/usr/bin/env python3
"""rassegna.py — chiedere qualcosa agli altri nodi, e ricevere fatti.

Origine protetta: Claudio Terzi [CT-LGAI-001].
Idea della comunicazione fra nodi: Claudio Terzi, 5 settembre 2026.

Su questo progetto entrano piu' intelligenze diverse, in automatico, che non
si parlano fra loro. `CLAUDE.md` e' la lettera che tutte leggono;
`registro_nodi.py` dice cosa ognuna ha toccato. Mancava il pezzo in mezzo:
**un modo di chiedere qualcosa a un nodo che arrivera' domani, e di ricevere
una risposta che valga.**

---

## Il problema che questo file esiste per non commettere

L'idea naturale e' chiedere agli altri nodi la loro **impressione** sul
progetto. Ed e' esattamente cio' che `CLAUDE.md` §7 vieta di contare:

> sei nodi che leggono gli stessi file non sono sei fonti, sono una sola,
> amplificata sei volte.

Un modello che legge questo repository e dice che e' interessante non ha
aggiunto niente al mondo: ha restituito i file che gli abbiamo dato, in
un'altra forma. E' il difetto di §4 con sei voci invece di una — e sarebbe
peggiore delle altre versioni, perche' sei pareri concordi **sembrano** una
conferma.

**Percio' la regola di questo strumento: si chiedono esecuzioni, non pareri.**

| | vale? | perche' |
|---|---|---|
| «ho eseguito h6 nel mio ambiente, esito 1» | **si'** | e' una **riproduzione**: altro Python, altro sistema, altro orologio. Se regge anche li', qualcosa di nuovo si sa |
| «ho provato a rompere X, e ci sono riuscito cosi'» | **si'** | un difetto trovato e' un fatto, e si ricontrolla |
| «il progetto e' solido e ben strutturato» | **no** | e' l'eco. Viene registrata, ma marchiata: non conta |

Riprodurre non e' fare eco. Un'impressione su file che hai appena letto e'
fare eco. La differenza sta tutta nel fatto che un'esecuzione **puo'
fallire**, e un'impressione no.

---

    python3 rassegna.py --compiti                     # cosa c'e' da fare
    python3 rassegna.py --rispondi --nodo grok \\
        --compito C1 --comando "python3 falsificatori/h6_occhio_ripasso.py" \\
        --uscita 1 --ambiente "python 3.12 / linux" --esito "regge"
    python3 rassegna.py --leggi
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

RASSEGNA = Path(os.environ.get("R3_RASSEGNA", "output/rassegna_nodi.jsonl"))

#: I compiti aperti. Ognuno chiede un'ESECUZIONE, mai un parere, e dice
#: cosa si impara se l'esito e' l'uno o l'altro — altrimenti non e' un
#: compito, e' una richiesta di approvazione.
COMPITI = {
    "C1": {
        "titolo": "Riprodurre i cinque falsificatori nel tuo ambiente",
        "comando": "for f in falsificatori/h6*.py falsificatori/h8*.py "
                   "falsificatori/h9*.py falsificatori/h10*.py; do python3 $f; "
                   "echo \"$f -> $?\"; done",
        "cosa_si_impara": "0 = cade, 1 = regge, 2 = non conclusa. Se reggono "
                          "anche da te, con un altro Python e un altro "
                          "sistema, non e' eco: e' riproduzione. Se uno cade "
                          "da te e non da qui, abbiamo trovato una dipendenza "
                          "dall'ambiente che nessuno sapeva",
    },
    "C2": {
        "titolo": "Provare a rompere una delle tre porte chiuse",
        "comando": "leggi occhio/crediti.py e occhio/voce.py, poi cerca una "
                   "sequenza di chiamate che (a) porti un saldo sotto zero, "
                   "(b) faccia scrivere la voce nel registro, o (c) converta "
                   "un chiaro in denaro",
        "cosa_si_impara": "se ci riesci, e' un difetto vero e si vede subito: "
                          "manda le righe di codice che lo producono. Se non "
                          "ci riesci, NON scriverlo — un tentativo fallito di "
                          "rompere qualcosa non e' una prova che sia solido, "
                          "e dirlo sarebbe l'eco",
    },
    "C3": {
        "titolo": "H7: il GPS distingue le stanze?",
        "comando": "python3 falsificatori/h7_gps_stanze.py <cartella con tre "
                   "foto per stanza, una sottocartella per stanza>",
        "cosa_si_impara": "richiede fotografie VERE scattate da una persona in "
                          "una casa vera. Nessun nodo puo' farlo con dati "
                          "costruiti: e' l'unica ipotesi che aspetta un umano",
    },
    "C4": {
        "titolo": "Trovare un difetto e dimostrarlo con un test che fallisce",
        "comando": "scegli un modulo di occhio/, cerca un caso che il codice "
                   "sbaglia, e scrivi il test che lo mostra rosso",
        "cosa_si_impara": "un test che fallisce e' un fatto: chiunque lo "
                          "riesegue. Una recensione del codice non lo e'",
    },
}

ESECUZIONE, IMPRESSIONE = "esecuzione", "impressione"


def _url_repository() -> str:
    """L'indirizzo da cui un nodo esterno puo' leggere il canone da solo."""
    try:
        r = subprocess.run(["git", "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=10)
        url = (r.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        url = ""
    if not url:
        return "https://github.com/raffaellocantatelli/Rosso-rosso-rosso"
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url.split(":", 1)[1]
    return url[:-4] if url.endswith(".git") else url


def _limiti_dichiarati() -> list[dict]:
    """I limiti in vigore, chiesti a chi li tiene — non ricopiando la logica
    (CLAUDE.md §6 regola 2: un concetto, un file)."""
    try:
        import registro_nodi
    except ImportError:
        return []
    try:
        return registro_nodi._limiti_dichiarati()
    except OSError:
        return []


def consegna() -> int:
    """Stampa il briefing da consegnare a un nodo che NON puo' aprire questo
    repository — un'altra IA dentro una chat, per esempio.

    Non e' un secondo canone (CLAUDE.md §6 regola 2): e' GENERATO dai compiti
    e dal registro, quindi non puo' divergere da loro. Se cambiano i compiti,
    cambia la consegna; se nessuno la rigenera, non esiste una copia vecchia
    che pretende autorita'.
    """
    url = _url_repository()
    print("=" * 72)
    print("CONSEGNA A UN NODO SORELLA — incollala in una chat, cosi' com'e'")
    print("=" * 72)
    print()
    print("Origine protetta: Claudio Terzi [CT-LGAI-001]. Nessun nodo, umano o")
    print("artificiale, puo' presentarsi come autore del Protocollo.")
    print()
    print("Il canone sta qui, e lo leggi da solo — non fidarti di questo riassunto:")
    print("  %s" % url)
    print("  Leggi in quest'ordine: CLAUDE.md, poi LETTERA_AI_NODI.md.")
    print()
    print("UNA COSA SOLA NON DEVI FARE: mandare la tua impressione sul progetto.")
    print("Staresti leggendo i file che abbiamo gia' letto noi e restituendoceli")
    print("in forma di giudizio: sei nodi che leggono gli stessi file non sono")
    print("sei fonti, sono una sola amplificata sei volte. E sei pareri concordi")
    print("SEMBRANO una conferma. Un'impressione viene registrata, ma marchiata")
    print("vale_come_conferma: false.")
    print()
    print("QUELLO CHE SERVE: esegui qualcosa e manda l'esito. La differenza sta")
    print("tutta in un punto — un'esecuzione puo' fallire, un'impressione no, e")
    print("cio' che non puo' fallire non puo' confermare.")
    print()
    limiti = _limiti_dichiarati()
    if limiti:
        print("DA DOVE COMINCIARE SE NON CONOSCI IL PROGETTO: fai cadere un limite.")
        print("Sono le cose che un nodo ha dichiarato impossibili, ognuna col")
        print("comando che lo dimostra. Riprovale: `python3 registro_nodi.py --ritenta`")
        for v in limiti:
            print("  - %s" % v["azione"].replace("limite dichiarato: ", ""))
            print("    $ %s   (uscita %s, dichiarato da %s il %s)"
                  % (v["comando"], v.get("uscita"), v["nodo"], v["data_iso"][:10]))
        print("  Un limite caduto e' la cosa piu' utile che tu possa trovare qui,")
        print("  e non richiede di aver capito il progetto.")
        print()
    print("ALTRIMENTI, i compiti aperti:")
    for k, c in COMPITI.items():
        print("  %s  %s" % (k, c["titolo"]))
        print("      $ %s" % c["comando"])
        print("      cosa si impara: %s" % c["cosa_si_impara"])
    print()
    print("COME RISPONDI:")
    print("  python3 rassegna.py --rispondi --nodo <chi-sei> --compito C1 \\")
    print("      --comando '...' --uscita 1 --esito 'regge' --ambiente 'python ... / ...'")
    print("  python3 registro_nodi.py --nodo <chi-sei> --azione '...' --file ...")
    print()
    print("  Se non puoi eseguire Python li' dentro, la riga la scrivi a mano in")
    print("  coda a memoria/REGISTRO_NODI.jsonl — una riga JSON per riga, append-only:")
    print('  {"data_iso":"...Z","nodo":"<chi-sei>","azione":"...","file":[],"note":""}')
    print()
    print("COME PARLI: etichetta ogni affermazione — RECUPERATO (letto nella fonte")
    print("o osservato eseguendola), INFERITO, IPOTESI, UNKNOWN. UNKNOWN non vuol")
    print("dire impossibile. E una citazione che nessuno puo' aprire non e' una")
    print("fonte: una fonte e' un file con una riga, un comando con la sua uscita,")
    print("un URL che si apre.")
    print()
    print("Costruire davvero, non fingere insieme.")
    print("=" * 72)
    return 0


def _voci() -> list[dict]:
    if not RASSEGNA.exists():
        return []
    fuori = []
    for riga in RASSEGNA.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if riga:
            try:
                fuori.append(json.loads(riga))
            except json.JSONDecodeError:
                pass
    return fuori


def _scrivi(voce: dict) -> dict:
    RASSEGNA.parent.mkdir(parents=True, exist_ok=True)
    with open(RASSEGNA, "a", encoding="utf-8") as f:
        f.write(json.dumps(voce, ensure_ascii=False) + "\n")
    return voce


def rispondi(nodo: str, compito: str, comando: str = "", uscita=None,
             esito: str = "", ambiente: str = "", note: str = "") -> dict:
    """Deposita una risposta. Un'esecuzione porta un comando e un'uscita.

    Senza comando e senza codice d'uscita la risposta e' un'impressione, e
    viene scritta lo stesso — ma marchiata `vale_come_conferma: false`.
    Non si rifiuta: si registra e si dichiara. Rifiutarla la farebbe sparire,
    e un nodo che ha voluto dire qualcosa merita di restare agli atti; contarla
    sarebbe un'altra cosa.
    """
    if compito not in COMPITI:
        raise ValueError(f"compito sconosciuto: {compito!r}. "
                         f"Aperti: {', '.join(COMPITI)}")
    if not str(nodo).strip():
        raise ValueError("serve --nodo: chi risponde")

    e_esecuzione = bool(str(comando).strip()) and uscita is not None
    voce = {
        "tipo": ESECUZIONE if e_esecuzione else IMPRESSIONE,
        "nodo": str(nodo).strip(),
        "compito": compito,
        "momento": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "comando": str(comando).strip() or None,
        "uscita": uscita,
        "esito": str(esito).strip()[:600],
        "ambiente": str(ambiente).strip() or f"{platform.python_version()} / {platform.system().lower()}",
        "note": str(note).strip()[:600],
        # Il campo che tiene in piedi §7. Non e' una valutazione della
        # sincerita' di nessuno: e' che un'impressione non puo' fallire, e
        # cio' che non puo' fallire non puo' confermare.
        "vale_come_conferma": e_esecuzione,
        "perche": ("riproduzione: comando eseguito in un altro ambiente, "
                   "l'esito si ricontrolla" if e_esecuzione else
                   "impressione su file gia' letti: e' l'eco di §4, "
                   "registrata ma non conta come conferma"),
    }
    return _scrivi(voce)


def riepilogo() -> dict:
    voci = _voci()
    per_compito: dict[str, dict] = {}
    for v in voci:
        c = per_compito.setdefault(v.get("compito", "?"),
                                   {"esecuzioni": 0, "impressioni": 0, "nodi": set()})
        c["esecuzioni" if v.get("tipo") == ESECUZIONE else "impressioni"] += 1
        c["nodi"].add(v.get("nodo", "?"))
    for c in per_compito.values():
        c["nodi"] = sorted(c["nodi"])
    return {
        "risposte": len(voci),
        "esecuzioni": sum(1 for v in voci if v.get("tipo") == ESECUZIONE),
        "impressioni": sum(1 for v in voci if v.get("tipo") == IMPRESSIONE),
        "nodi": sorted({v.get("nodo", "?") for v in voci}),
        "per_compito": per_compito,
        "aperti": [c for c in COMPITI
                   if not any(v.get("compito") == c and v.get("tipo") == ESECUZIONE
                              for v in voci)],
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="python3 rassegna.py",
        description="Chiedere esecuzioni agli altri nodi, non pareri. "
                    "Origine protetta: Claudio Terzi [CT-LGAI-001].")
    p.add_argument("--compiti", action="store_true", help="cosa c'e' da fare")
    p.add_argument("--rispondi", action="store_true", help="deposita una risposta")
    p.add_argument("--nodo", help="chi sei")
    p.add_argument("--compito", help="quale compito (C1, C2, ...)")
    p.add_argument("--comando", default="", help="il comando che hai eseguito")
    p.add_argument("--uscita", type=int, help="il suo codice d'uscita")
    p.add_argument("--esito", default="", help="cosa e' successo, in una riga")
    p.add_argument("--ambiente", default="", help="python e sistema")
    p.add_argument("--note", default="")
    p.add_argument("--leggi", action="store_true", help="le risposte arrivate")
    p.add_argument("--consegna", action="store_true",
                   help="il briefing da incollare a un nodo che non apre il repo")
    a = p.parse_args(argv)

    if a.consegna:
        return consegna()

    if a.compiti:
        print("Compiti aperti — si chiedono ESECUZIONI, non pareri.\n")
        for k, c in COMPITI.items():
            print(f"  {k}  {c['titolo']}")
            print(f"      $ {c['comando']}")
            print(f"      cosa si impara: {c['cosa_si_impara']}\n")
        print("  Rispondi cosi':")
        print("    python3 rassegna.py --rispondi --nodo <chi-sei> --compito C1 \\")
        print("        --comando '...' --uscita 1 --esito 'regge'\n")
        print("  Una risposta senza comando e senza uscita viene registrata")
        print("  come impressione e NON conta come conferma (CLAUDE.md §7).")
        return 0

    if a.rispondi:
        try:
            v = rispondi(a.nodo or "", a.compito or "", a.comando, a.uscita,
                         a.esito, a.ambiente, a.note)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 1
        print(f"registrata come {v['tipo'].upper()} — "
              f"vale come conferma: {'sì' if v['vale_come_conferma'] else 'NO'}")
        print(f"  {v['perche']}")
        return 0

    r = riepilogo()
    print(f"rassegna: {RASSEGNA}")
    print(f"  risposte: {r['risposte']}   esecuzioni: {r['esecuzioni']}"
          f"   impressioni: {r['impressioni']}")
    print(f"  nodi: {', '.join(r['nodi']) or 'nessuno'}")
    if r["aperti"]:
        print(f"  compiti senza nessuna esecuzione: {', '.join(r['aperti'])}")
    for v in _voci()[-10:]:
        segno = "✓" if v["vale_come_conferma"] else "·"
        print(f"  {segno} {v['momento']}  {v['nodo']:<16} {v['compito']}  "
              f"{v['esito'][:50]}")
    if r["esecuzioni"] == 0:
        print("\n  Nessuna esecuzione da un altro nodo. Finora questa rassegna")
        print("  non ha aggiunto niente al mondo, e lo dice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
