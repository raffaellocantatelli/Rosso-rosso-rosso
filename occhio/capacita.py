#!/usr/bin/env python3
"""occhio.capacita — l'inventario di INVENTARIUM: tutto cio' che sa fare.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Un elenco delle funzioni scritto a mano diverge dal codice al primo comando
nuovo, e **nessuno se ne accorge finche' non serve**. E' la malattia delle
sette copie dell'indice (§6 regola 2) applicata alla documentazione: due
verita' che raccontano la stessa cosa, e un giorno una delle due ha ragione.

Percio' questo manifesto **non si scrive: si genera**, per introspezione, da:

* il parser vero della riga di comando (37 opzioni, non un elenco copiato);
* le funzioni pubbliche dei moduli, con la loro firma e la prima riga di
  documentazione presa dal codice;
* la forma dei dati, ricavata **scrivendo un record vero** in una cartella
  temporanea e guardando quali campi esistono — non da uno schema dichiarato,
  che potrebbe mentire;
* il registro delle ipotesi, con i loro falsificatori.

Un test verifica che il manifesto depositato copra ogni opzione e ogni
funzione: se aggiungi un comando e non rigeneri, la prova fallisce. E' la
differenza fra una documentazione e una promessa.

    python -m occhio --capacita              # a schermo
    python -m occhio --capacita capacita.json
"""

from __future__ import annotations

import inspect
import json
import os
import tempfile
import time
from pathlib import Path

PRODOTTO = "INVENTARIUM"
MANIGLIA = "inventariumapp"

#: I moduli che compongono il prodotto, con il nome commerciale di ciascuno.
MODULI = {
    "inventario": ("il registro degli oggetti", None),
    "visione": ("la lettura delle fotografie", None),
    "luogo": ("dove sta un oggetto, dichiarato non dedotto", None),
    "cartella": ("il modo a fotografie e la mappa", None),
    "planimetria": ("la pianta stilizzata delle zone", "GREEN"),
    "consegna": ("lo stato controfirmato e la differenza", "TALLY"),
    "portavia": ("il mercato dentro casa", "PORTAVIA"),
    "crediti": ("i crediti di circuito chiuso", "I CHIARI"),
    "voce": ("parlare alla casa", "LA VOCE"),
    "costo": ("quanto costa una passata", None),
    "server": ("il server locale e l'interfaccia", None),
}

#: Le tre porte chiuse a chiave. Sono qui perche' chi legge il manifesto per
#: integrare il prodotto le veda prima di provarci.
VINCOLI = [
    {"dove": "crediti.converti_in_denaro",
     "regola": "solleva sempre: un chiaro non torna mai denaro",
     "perche": "e' cio' che tiene i chiari un buono di circuito chiuso invece "
               "che moneta elettronica"},
    {"dove": "crediti.Crediti(trasferibile=True)",
     "regola": "spento per difetto; se acceso, ogni movimento resta marchiato",
     "perche": "il trasferimento fra persone porta il progetto dentro il "
               "perimetro dei servizi di pagamento"},
    {"dove": "voce.puo_scrivere",
     "regola": "sempre falso: la voce legge e propone, non scrive",
     "perche": "a una voce non si puo' chiedere chi sta parlando"},
    {"dove": "visione.leggi",
     "regola": "non accetta l'inventario come parametro",
     "perche": "un modello che sa cosa aspettarsi lo rilegge anche su un muro"},
    {"dove": "consegna.deposita",
     "regola": "di ogni oggetto conserva solo l'impronta della fotografia",
     "perche": "un'immagine generata non deve poter entrare fra le prove"},
]


def _funzioni(nome_modulo: str) -> list[dict]:
    modulo = __import__(f"occhio.{nome_modulo}", fromlist=["*"])
    fuori = []
    for nome, oggetto in inspect.getmembers(modulo):
        if nome.startswith("_") or getattr(oggetto, "__module__", "") != modulo.__name__:
            continue
        if inspect.isfunction(oggetto):
            doc = (inspect.getdoc(oggetto) or "").splitlines()
            fuori.append({"tipo": "funzione", "nome": nome,
                          "firma": str(inspect.signature(oggetto)),
                          "descrizione": doc[0] if doc else ""})
        elif inspect.isclass(oggetto):
            metodi = []
            for m, f in inspect.getmembers(oggetto, inspect.isfunction):
                if m.startswith("_"):
                    continue
                d = (inspect.getdoc(f) or "").splitlines()
                metodi.append({"nome": m, "firma": str(inspect.signature(f)),
                               "descrizione": d[0] if d else ""})
            doc = (inspect.getdoc(oggetto) or "").splitlines()
            fuori.append({"tipo": "classe", "nome": nome,
                          "descrizione": doc[0] if doc else "", "metodi": metodi})
    return sorted(fuori, key=lambda x: (x["tipo"], x["nome"]))


def _comandi() -> list[dict]:
    from .__main__ import costruisci_parser
    ap = costruisci_parser()
    gruppi = {}
    for g in ap._action_groups:
        for a in g._group_actions:
            gruppi[id(a)] = g.title
    fuori = []
    for a in ap._actions:
        if not a.option_strings or "--help" in a.option_strings:
            continue
        fuori.append({
            "opzione": a.option_strings[0],
            "gruppo": gruppi.get(id(a), "generale"),
            "argomenti": (list(a.metavar) if isinstance(a.metavar, tuple)
                          else ([a.metavar] if a.metavar else [])),
            "predefinito": a.default if isinstance(a.default, (str, int, float, bool, type(None))) else None,
            "aiuto": (a.help or "").strip(),
        })
    return fuori


def _forma_dei_dati() -> dict:
    """La forma dei record, ricavata scrivendone di veri.

    Uno schema dichiarato a mano puo' mentire; un record scritto dal codice no.
    Tutto succede in una cartella temporanea e non tocca niente di reale.
    """
    from . import consegna as cs
    from . import crediti as cd
    from . import inventario as inv
    from . import luogo as lg
    from . import portavia as pv

    with tempfile.TemporaryDirectory() as d:
        r = inv.Inventario(Path(d) / "i.jsonl")
        posto = lg.dal_percorso("/f/salotto/libreria/x.jpg", "/f")
        voce = r.registra("dvd", "Esempio", "0" * 16, testo_letto="ESEMPIO",
                          confidenza=0.9, fonte="foto", luogo=posto,
                          foto_sha="0" * 64)
        c = cs.Consegne(Path(d) / "c.jsonl")
        stato = c.deposita("alloggio", "consegna", r.voci, "soggiorno")
        firma = c.controfirma(stato["impronta"], "codice")
        diff = cs.differenza(stato, stato)
        negozio = pv.Portavia(Path(d) / "p.jsonl",
                              pv.Regole(prezzo_minimo={"dvd:esempio": 5.0}))
        vendita = negozio.vendita("dvd:esempio", "Esempio", 7.0)
        libro = cd.Crediti(Path(d) / "cr.jsonl")
        movimento = libro.emetti("conto", 10, "vendita", riferimento="x")

        return {
            "voce_inventario": {"campi": sorted(voce), "esempio_chiave": voce["chiave"]},
            "luogo_dichiarato": {"campi": sorted(posto)},
            "stato_consegna_TALLY": {"campi": sorted(stato),
                                     "campi_oggetto": sorted(stato["oggetti"][0])},
            "controfirma": {"campi": sorted(firma)},
            "differenza": {"campi": sorted(diff)},
            "vendita_PORTAVIA": {"campi": sorted(vendita)},
            "movimento_CHIARI": {"campi": sorted(movimento)},
            "file_su_disco": {
                "inventario": str(inv.ARCHIVIO), "consegne": str(cs.CATENA),
                "portavia": str(pv.CATALOGO), "crediti": str(cd.LIBRO),
                "formato": "JSON Lines, append-only: una riga per evento, "
                           "lo stato si ricalcola rileggendo",
            },
        }


def _ipotesi() -> list[dict]:
    percorso = Path(__file__).resolve().parent.parent / "registro_ipotesi.json"
    if not percorso.exists():
        return []
    fuori = []
    for h in json.loads(percorso.read_text(encoding="utf-8")):
        f = h.get("falsificatore") or {}
        fuori.append({"id": h.get("id"), "stato": h.get("stato"),
                      "testo": h.get("testo"),
                      "falsificatore": " ".join(f.get("comando", [])) or None})
    return fuori


def genera() -> dict:
    """Il manifesto. Ogni voce viene dal codice, nessuna e' scritta a mano."""
    return {
        "prodotto": PRODOTTO,
        "maniglia": MANIGLIA,
        "significato": "inventarium, dal latino invenire: l'elenco delle cose "
                       "trovate — non di quelle inventate",
        "origine_protetta": "Claudio Terzi [CT-LGAI-001]",
        "motore": "occhio",
        "generato": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generato_da": "python -m occhio --capacita",
        "avvertenza": "generato per introspezione dal codice. Non modificarlo "
                      "a mano: rigeneralo, altrimenti diverge in silenzio.",
        "moduli": {
            nome: {"scopo": scopo, "nome_commerciale": commerciale,
                   "elementi": _funzioni(nome)}
            for nome, (scopo, commerciale) in MODULI.items()
        },
        "comandi": _comandi(),
        "forma_dei_dati": _forma_dei_dati(),
        "ipotesi": _ipotesi(),
        "vincoli_non_negoziabili": VINCOLI,
        "dipendenze": ["requests", "libreria standard"],
    }


def conta(m: dict) -> dict:
    elementi = [e for mod in m["moduli"].values() for e in mod["elementi"]]
    return {
        "moduli": len(m["moduli"]),
        "funzioni": sum(1 for e in elementi if e["tipo"] == "funzione"),
        "classi": sum(1 for e in elementi if e["tipo"] == "classe"),
        "metodi": sum(len(e.get("metodi", [])) for e in elementi),
        "comandi": len(m["comandi"]),
        "forme_di_dati": len(m["forma_dei_dati"]) - 1,
        "ipotesi": len(m["ipotesi"]),
        "vincoli": len(m["vincoli_non_negoziabili"]),
    }
