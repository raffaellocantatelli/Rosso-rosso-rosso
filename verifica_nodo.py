#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica di un nodo — ricontrolla le affermazioni invece di leggerle.

Il problema che risolve. `memoria/REGISTRO_NODI.jsonl` dice cosa un nodo
DICHIARA di aver fatto. Un nodo che arriva dopo, o un altro modello, non ha
modo di distinguere una dichiarazione vera da una scritta bene. E' lo stesso
difetto del §4 spostato di un piano: se l'unica prova che un nodo ha lavorato
e' il testo che quel nodo ha scritto, il sistema sta di nuovo ascoltando la
propria eco.

Questo file non e' un documento sul lavoro fatto. E' un programma che RIESEGUE
i controlli. Chi lo lancia non deve fidarsi di nessuno: legge l'esito.

  python verifica_nodo.py           # tutti i controlli, in italiano
  python verifica_nodo.py --json    # per un altro programma
  python verifica_nodo.py --rete    # include i controlli che escono su internet

Esce con codice 1 se anche un solo controllo fallisce.

La prova piu' forte e' `catena_fotogrammi_ancorata`: ogni fotogramma cita un
round di drand, e drand pubblica quei valori per sempre. Chiunque puo'
riscaricarli e confrontarli. Se coincidono, quel fotogramma non poteva essere
stato costruito prima di quel secondo — e questo non dipende ne' dall'autore
ne' dal nodo che l'ha scritto.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
AGENTE = "R3-verifica-nodo/1.0"


class Esito:
    def __init__(self, nome, ok, atteso, trovato, nota="", saltato=False):
        self.nome, self.ok, self.atteso = nome, ok, atteso
        self.trovato, self.nota, self.saltato = trovato, nota, saltato

    def json(self):
        return {"controllo": self.nome, "esito": "saltato" if self.saltato
                else ("ok" if self.ok else "fallito"), "atteso": self.atteso,
                "trovato": self.trovato, "nota": self.nota}


def _p(*parti):
    return os.path.join(QUI, *parti)


# --------------------------------------------------------------- controlli

def c_contatti_vuoto():
    """H2 ramo (b): zero voci indipendenti = ipotesi falsificata, oggi."""
    percorso = _p("output", "contatti.jsonl")
    voci = []
    if os.path.exists(percorso):
        with open(percorso, encoding="utf-8") as f:
            for riga in f:
                riga = riga.strip()
                if riga:
                    try:
                        voci.append(json.loads(riga))
                    except ValueError:
                        pass
    indipendenti = [v for v in voci if v.get("indipendente") is True]
    return Esito(
        "h2_ramo_b_stato",
        ok=True,   # e' una misura, non un test: riporta lo stato quale che sia
        atteso="conteggio delle voci indipendenti in output/contatti.jsonl",
        trovato={"voci_totali": len(voci), "indipendenti": len(indipendenti)},
        nota=("H2 ramo (b) e' FALSIFICATA allo stato attuale: nessuna voce "
              "indipendente" if not indipendenti else
              "H2 ramo (b) non e' piu' falsificata: %d voci indipendenti"
              % len(indipendenti)),
    )


def c_esperimento_23_08():
    """Il criterio dichiarato il 23/08 e' scaduto il 30/08: registrato l'esito?"""
    percorso = _p("memoria", "SAR_CONSERVARE_TRASMETTERE_2026-08-23.md")
    if not os.path.exists(percorso):
        return Esito("esito_esperimento_registrato", False,
                     "il file del collasso esiste", "assente")
    testo = open(percorso, encoding="utf-8").read()
    scaduto = time.time() > time.mktime(time.strptime("2026-08-30", "%Y-%m-%d"))
    registrato = "ESITO DELL'ESPERIMENTO" in testo
    return Esito(
        "esito_esperimento_registrato",
        ok=(registrato if scaduto else True),
        atteso="l'esito e' scritto nel file del collasso, se la scadenza e' passata",
        trovato={"scadenza_passata": scaduto, "esito_presente": registrato},
        nota="un criterio P6 che scatta e non viene registrato annulla P6",
    )


def c_catena_fotogrammi():
    """Ogni fotogramma cita l'hash del precedente: la catena non ha buchi."""
    percorso = _p("output", "fotogrammi.jsonl")
    if not os.path.exists(percorso):
        return Esito("catena_fotogrammi_intatta", False,
                     "output/fotogrammi.jsonl esiste", "assente")
    righe = [json.loads(r) for r in open(percorso, encoding="utf-8") if r.strip()]
    rotture = []
    for i in range(1, len(righe)):
        if righe[i].get("precedente") != righe[i - 1].get("chiave"):
            rotture.append(i)
    return Esito(
        "catena_fotogrammi_intatta",
        ok=not rotture,
        atteso="ogni anello cita la chiave del precedente",
        trovato={"fotogrammi": len(righe), "anelli_rotti": rotture},
    )


def c_ancore_drand(rete=False):
    """LA PROVA. Riscarica da drand i round citati e li confronta.

    drand pubblica un valore ogni 30 secondi, firmato dalla chiave del gruppo
    e conservato per sempre. Nessuno puo' calcolarlo in anticipo. Se il valore
    citato in un fotogramma coincide con quello che drand serve oggi, quel
    fotogramma non esisteva prima di quel round.
    """
    percorso = _p("output", "fotogrammi.jsonl")
    if not os.path.exists(percorso):
        return Esito("catena_fotogrammi_ancorata", False, "il file esiste", "assente")
    righe = [json.loads(r) for r in open(percorso, encoding="utf-8") if r.strip()]
    citati = [(r["istante_utc"], r["ancore"].get("drand", {}))
              for r in righe if r.get("ancore", {}).get("drand", {}).get("round")]
    if not rete:
        return Esito("catena_fotogrammi_ancorata", True,
                     "confronto con api.drand.sh", 
                     {"round_citati": [d.get("round") for _, d in citati]},
                     nota="saltato: serve --rete per uscire su internet", saltato=True)

    confronti = []
    for istante, d in citati:
        url = "https://api.drand.sh/public/%s" % d["round"]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
            with urllib.request.urlopen(req, timeout=25) as r:
                vero = json.loads(r.read())
            confronti.append({
                "istante": istante, "round": d["round"],
                "coincide": vero.get("randomness") == d.get("casuale"),
                "url": url,
            })
        except Exception as e:
            confronti.append({"istante": istante, "round": d["round"],
                              "coincide": None,
                              "errore": "%s: %s" % (type(e).__name__, str(e)[:80])})
    verificati = [c for c in confronti if c.get("coincide") is True]
    falsi = [c for c in confronti if c.get("coincide") is False]
    return Esito(
        "catena_fotogrammi_ancorata",
        ok=(not falsi) and bool(verificati),
        atteso="ogni round citato coincide con quello pubblicato da drand",
        trovato={"verificati": len(verificati), "discordanti": len(falsi),
                 "dettaglio": confronti},
        nota="e' l'unico controllo qui dentro che non dipende da questo repository",
    )


def c_manifesto():
    """Layer 4: il manifesto copre i file e nessuno e' divergente."""
    try:
        r = subprocess.run([sys.executable, _p("manifesto_integrita.py"), "--verifica"],
                           capture_output=True, text=True, timeout=180, cwd=QUI)
        uscita = (r.stdout + r.stderr).strip()
        return Esito("manifesto_integro", r.returncode == 0,
                     "verifica del manifesto senza divergenze",
                     uscita.splitlines()[0] if uscita else "(nessuna uscita)")
    except (OSError, subprocess.SubprocessError) as e:
        return Esito("manifesto_integro", False, "il manifesto si verifica",
                     "%s: %s" % (type(e).__name__, str(e)[:80]))


def c_manifesto_copre_tutto():
    """Un Layer 4 che non copre i file nuovi non protegge niente (§6.4)."""
    percorso = _p("MANIFESTO_INTEGRITA.json")
    if not os.path.exists(percorso):
        return Esito("manifesto_copre_i_pacchetti", False, "il manifesto esiste", "assente")
    testo = open(percorso, encoding="utf-8").read()
    attesi = ["osservatorio/fotogramma.py", "osservatorio/posizione.py",
              "osservatorio/quadro.html", "verifica_nodo.py"]
    mancanti = [a for a in attesi if a not in testo]
    return Esito("manifesto_copre_i_pacchetti", not mancanti,
                 "i file aggiunti dai nodi sono sorvegliati",
                 {"mancanti": mancanti})


def c_troncamento_si_accorge():
    """L'osservatorio marca da solo una lettura arrivata al tetto?"""
    try:
        sys.path.insert(0, QUI)
        from osservatorio.fonti import _p_emsc
        finto = json.dumps({"features": [{"properties": {"lat": 0, "lon": 0, "mag": 1}}] * 300})
        r = _p_emsc(finto.encode())
        return Esito("troncamento_rilevato", r.troncato is True,
                     "300 righe con tetto 300 -> troncato=True",
                     {"conteggio": r.conteggio, "troncato": r.troncato})
    except Exception as e:
        return Esito("troncamento_rilevato", False, "il parser si carica",
                     "%s: %s" % (type(e).__name__, str(e)[:80]))


def c_registro_nodi():
    """Il registro e' append-only e leggibile: ogni riga e' JSON valido."""
    percorso = _p("memoria", "REGISTRO_NODI.jsonl")
    if not os.path.exists(percorso):
        return Esito("registro_nodi_leggibile", False, "il registro esiste", "assente")
    rotte = []
    n = 0
    with open(percorso, encoding="utf-8") as f:
        for i, riga in enumerate(f, 1):
            if riga.strip():
                n += 1
                try:
                    json.loads(riga)
                except ValueError:
                    rotte.append(i)
    return Esito("registro_nodi_leggibile", not rotte,
                 "ogni riga del registro e' JSON valido",
                 {"voci": n, "righe_rotte": rotte})


CONTROLLI = [c_contatti_vuoto, c_esperimento_23_08, c_catena_fotogrammi,
             c_manifesto, c_manifesto_copre_tutto, c_troncamento_si_accorge,
             c_registro_nodi]


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="verifica_nodo",
        description="Riesegue i controlli che un nodo ha dichiarato di aver passato.")
    ap.add_argument("--json", action="store_true", help="uscita per un altro programma")
    ap.add_argument("--rete", action="store_true",
                    help="include il confronto con drand (esce su internet)")
    a = ap.parse_args(argv)

    esiti = [c() for c in CONTROLLI]
    esiti.append(c_ancore_drand(rete=a.rete))

    if a.json:
        print(json.dumps({"quando": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          "controlli": [e.json() for e in esiti]},
                         ensure_ascii=False, indent=1))
    else:
        print("VERIFICA NODO — %s" % time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()))
        print("Nessuna di queste righe chiede di fidarsi di chi ha scritto il codice.\n")
        for e in esiti:
            segno = "SALT" if e.saltato else ("OK  " if e.ok else "NO  ")
            print("  [%s] %s" % (segno, e.nome))
            print("        atteso:  %s" % e.atteso)
            print("        trovato: %s" % json.dumps(e.trovato, ensure_ascii=False))
            if e.nota:
                print("        nota:    %s" % e.nota)
        falliti = [e for e in esiti if not e.ok and not e.saltato]
        print("\n%d controlli, %d falliti" % (len(esiti), len(falliti)))
        if not a.rete:
            print("Per la prova che non dipende da questo repository: --rete")
    return 1 if any(not e.ok and not e.saltato for e in esiti) else 0


if __name__ == "__main__":
    sys.exit(main())
