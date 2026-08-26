"""L'archivio come contesto: le fonti sì, la propria voce no.

«Dagli accesso ai dati, perché abbiamo memoria preesistente» — Claudio Terzi,
26/08/2026.

La memoria preesistente c'e' davvero, ed e' la cosa piu' preziosa del
progetto: il Protocollo, i documenti depositati, il racconto dell'archivio,
le decisioni. Finora nessun modello l'ha mai vista: gli si chiedeva di
ragionare su R³∞ senza dargliene una riga.

## La riga che divide, e perche' non e' negoziabile

**FONTI** — scritte da Claudio, o depositate come documento del progetto.
Sono la memoria. Entrano nel contesto.

**GENERATI** — prodotti dal sistema stesso: riflessioni giornaliere,
contraddittori, stato della memoria vettoriale. **Non entrano mai.**

Non e' prudenza eccessiva: e' il difetto ricorrente di questo progetto, che
si e' ripresentato cinque volte. Il daily che rilegge il proprio output e lo
trova «rilevante» ha alimentato 23 giorni di vuoto. Dare a un modello i
propri testi precedenti come «memoria» produce esattamente quella spirale,
con una differenza: sembra erudizione.

Un documento generato dal sistema puo' essere letto da una persona. Non puo'
essere dato in pasto al sistema come se fosse una fonte.

## Provenienza obbligatoria

Ogni frammento recuperato porta `file:riga`. Serve perche' un'etichetta
RECUPERATO sia verificabile: chi legge la risposta puo' aprire quel file a
quella riga. Un recupero la cui fonte non si puo' aprire e' un'inferenza
travestita.
"""
from __future__ import annotations

import math
import os
import re
from collections import Counter

RADICE = os.path.dirname(os.path.abspath(__file__))

#: Le fonti. Scritte da una persona, o depositate come documento del progetto.
FONTI = [
    ("testi", ".md"),
    ("memoria", ".md"),
]
FILE_SINGOLI = ["CLAUDE.md", "README.md", "R3_DECISIONI_E_PROTOCOLLO_2026-08-10.md"]

#: Mai indicizzati. Due categorie, e la seconda e' meno ovvia:
#:
#: 1. output del sistema — daily, contraddittori, memoria vettoriale: e' il
#:    sistema che parla di se' stesso;
#: 2. documenti scritti da un nodo IA (PROGETTO_CONTRADDITTORIO, i rapporti
#:    di contraddittorio). Sono depositi legittimi, si leggono, si citano —
#:    ma non sono memoria dell'autore. Darli in pasto al modello significa
#:    fargli leggere il ragionamento di un altro modello e chiamarlo fonte.
#:
#: La prima versione li escludeva per coincidenza, perche' il nome conteneva
#: "CONTRADDITTORIO_". La lezione di questa sessione e' che una protezione
#: che funziona per fortuna non e' una protezione: qui e' scritta apposta.
GENERATI = re.compile(
    r"CONTRADDITTORIO_"      # rapporti del contraddittorio e il suo progetto
    r"|^daily_"              # riflessioni giornaliere
    r"|store\.json|state\.json|verifiche\.jsonl"  # stato interno
)

#: Cartelle private da indicizzare senza committarle (es. una copia locale del
#: Drive). Elenco separato da ':' in R3_ARCHIVIO_EXTRA. Restano fuori da git:
#: l'indice si costruisce a ogni esecuzione, non e' un file da depositare.
EXTRA = [p for p in os.environ.get("R3_ARCHIVIO_EXTRA", "").split(":") if p.strip()]

TOKEN = re.compile(r"[a-zàèéìòùA-ZÀÈÉÌÒÙ]{4,}")
PAROLE_PER_FRAMMENTO = 120


def _tokenizza(testo):
    return Counter(t.lower() for t in TOKEN.findall(testo))


def _coseno(a, b):
    comuni = set(a) & set(b)
    if not comuni:
        return 0.0
    prodotto = sum(a[t] * b[t] for t in comuni)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return prodotto / (na * nb) if na and nb else 0.0


def _spezza(percorso, relativo):
    """Frammenti con il numero di riga da cui cominciano."""
    with open(percorso, "r", encoding="utf-8", errors="replace") as f:
        righe = f.readlines()

    frammenti, corrente, prima_riga, parole = [], [], 1, 0
    for numero, riga in enumerate(righe, start=1):
        if not corrente:
            prima_riga = numero
        corrente.append(riga)
        parole += len(riga.split())
        finito_blocco = riga.strip() == "" and parole >= PAROLE_PER_FRAMMENTO
        if finito_blocco or parole >= PAROLE_PER_FRAMMENTO * 2:
            testo = "".join(corrente).strip()
            if testo:
                frammenti.append({"file": relativo, "riga": prima_riga, "testo": testo})
            corrente, parole = [], 0
    testo = "".join(corrente).strip()
    if testo:
        frammenti.append({"file": relativo, "riga": prima_riga, "testo": testo})
    return frammenti


def _percorsi():
    for cartella, estensione in FONTI:
        piena = os.path.join(RADICE, cartella)
        if not os.path.isdir(piena):
            continue
        for nome in sorted(os.listdir(piena)):
            if nome.endswith(estensione) and not GENERATI.search(nome):
                yield os.path.join(piena, nome), os.path.join(cartella, nome)
    for nome in FILE_SINGOLI:
        piena = os.path.join(RADICE, nome)
        if os.path.isfile(piena):
            yield piena, nome
    for extra in EXTRA:
        if not os.path.isdir(extra):
            continue
        for radice, _dirs, files in os.walk(extra):
            for nome in sorted(files):
                if nome.endswith((".md", ".txt")) and not GENERATI.search(nome):
                    piena = os.path.join(radice, nome)
                    yield piena, os.path.relpath(piena, extra) + "  [privato]"


def costruisci_indice():
    indice = []
    for piena, relativo in _percorsi():
        for frammento in _spezza(piena, relativo):
            frammento["vettore"] = _tokenizza(frammento["testo"])
            indice.append(frammento)
    return indice


def recupera(domanda, quanti=6, indice=None, soglia=0.04):
    """I frammenti piu' vicini alla domanda, con la loro provenienza."""
    indice = costruisci_indice() if indice is None else indice
    vettore = _tokenizza(domanda)
    punteggiati = []
    for frammento in indice:
        punteggio = _coseno(vettore, frammento["vettore"])
        if punteggio >= soglia:
            punteggiati.append((punteggio, frammento))
    punteggiati.sort(key=lambda x: x[0], reverse=True)
    return [
        {"file": f["file"], "riga": f["riga"], "punteggio": round(p, 3),
         "testo": f["testo"][:900]}
        for p, f in punteggiati[:quanti]
    ]


def come_contesto(domanda, quanti=6, indice=None):
    """I frammenti formattati per un prompt, con la provenienza in chiaro."""
    frammenti = recupera(domanda, quanti, indice)
    if not frammenti:
        return "(nessun frammento dell'archivio supera la soglia di pertinenza)"
    pezzi = []
    for f in frammenti:
        pezzi.append(f"--- FONTE: {f['file']}:{f['riga']} (pertinenza {f['punteggio']})\n{f['testo']}")
    return "\n\n".join(pezzi)


def statistiche():
    indice = costruisci_indice()
    per_file = Counter(f["file"] for f in indice)
    return {"frammenti": len(indice), "file": len(per_file), "dettaglio": dict(per_file)}


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) > 1 and sys.argv[1] != "--stato":
        domanda = " ".join(sys.argv[1:])
        for f in recupera(domanda):
            print(f"[{f['punteggio']}] {f['file']}:{f['riga']}")
            print("   " + f["testo"][:200].replace("\n", " ") + "…\n")
    else:
        print(json.dumps(statistiche(), ensure_ascii=False, indent=2))
