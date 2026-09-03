#!/usr/bin/env python3
"""occhio.consegna — lo stato controfirmato di un alloggio, e la differenza.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Questo modulo nasce dall'uso vero: un alloggio in affitto breve, e fra un
ospite e l'altro la domanda «c'e' ancora tutto?». Cambia la natura del
prodotto, e con essa quella del problema tecnico.

**Perche' qui e' molto piu' facile che in una casa privata.** Inventariare
una casa e' difficile perche' il sistema deve SCOPRIRE cosa c'e': il modello
guarda uno scaffale ignoto e deve leggere titoli mai visti. Qui no. La lista
la dichiara il proprietario **una volta sola**, e da quel momento il modello
non deve piu' scoprire niente: deve **verificare** che una cosa nota sia
ancora al suo posto. Riconoscere «la macchina del caffe' che era su quel
ripiano c'e' ancora» e' un problema molto piu' piccolo di «che oggetti ci
sono in questa stanza», e sbaglia molto meno.

**Dove sta il valore, che non e' la lista.** Il valore e' lo *stato*: due
parti, un momento datato, e una differenza che nessuna delle due puo'
riscrivere da sola. La lista e' il meccanismo; il prodotto e' «chi ha ragione
quando manca la macchina del caffe'».

**Il punto piu' importante di tutto il modulo.** Una catena di impronte
controllata da una parte sola **non prova niente**: se il proprietario puo'
rigenerarla, dimostra solo che e' coerente con se stessa. Cio' che la rende
opponibile e' la **controfirma dell'ospite**: due parti in conflitto
d'interessi che dichiarano lo stesso stato nello stesso momento. Percio' qui
uno stato non controfirmato resta marcato come tale per sempre, e la
controfirma porta il proprio momento: non si puo' aggiungere a posteriori
fingendo che ci fosse dall'inizio.

Cosa questo modulo NON dichiara, ed e' UNKNOWN per davvero: **il valore
legale.** La controfirma prova che due parti che avevano lo stesso codice
hanno dichiarato lo stesso stato. Non prova l'identita' di nessuno, e se
opponibile in giudizio lo dice un avvocato, non un file Python.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path

CATENA = Path(os.environ.get("OCCHIO_CONSEGNE", "output/consegne.jsonl"))

GENESI = "0" * 64
TIPI = ("consegna", "riconsegna", "ricognizione")


def _ora() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def impronta_stato(stato: dict) -> str:
    """Impronta del contenuto, indipendente dall'ordine delle chiavi.

    `sort_keys` non e' un dettaglio estetico: senza, due serializzazioni dello
    stesso stato darebbero impronte diverse e la catena si romperebbe da sola
    al primo aggiornamento di libreria. E una catena che si rompe da sola
    insegna a ignorare le rotture.
    """
    copia = {k: v for k, v in stato.items() if k not in ("impronta", "controfirma")}
    grezzo = json.dumps(copia, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(grezzo.encode("utf-8")).hexdigest()


def firma(impronta: str, codice: str) -> str:
    """HMAC dello stato con il codice del soggiorno.

    Il codice lo conoscono in due: chi consegna e chi riceve. La firma prova
    che chi l'ha prodotta aveva il codice in quel momento — non chi fosse.
    E' poco, ed e' molto piu' di una catena di una parte sola.
    """
    return hmac.new(str(codice).encode("utf-8"), impronta.encode("utf-8"),
                    hashlib.sha256).hexdigest()


# --------------------------------------------------------------------------
# la catena
# --------------------------------------------------------------------------

class Consegne:
    """Catena append-only degli stati di un alloggio."""

    def __init__(self, percorso: Path | str = CATENA):
        self.percorso = Path(percorso)
        self.stati: list[dict] = []
        self.carica()

    def carica(self) -> int:
        self.stati = []
        self.righe_illeggibili = 0
        if not self.percorso.exists():
            return 0
        with open(self.percorso, "r", encoding="utf-8") as f:
            for riga in f:
                riga = riga.strip()
                if not riga:
                    continue
                try:
                    self.stati.append(json.loads(riga))
                except json.JSONDecodeError:
                    self.righe_illeggibili += 1
        return len(self.stati)

    def per_alloggio(self, alloggio: str, con_controfirme=False) -> list[dict]:
        """Gli stati di un alloggio.

        Le controfirme portano l'alloggio ma NON sono anelli della catena
        degli stati: pendono da uno stato. Confonderle con gli stati rompeva
        la verifica — trovato eseguendo, il 03/09, non rileggendo il codice.
        """
        return [s for s in self.stati
                if s.get("alloggio") == alloggio
                and (con_controfirme or s.get("tipo") != "controfirma")]

    def ultimo(self, alloggio: str, tipo: str | None = None) -> dict | None:
        for s in reversed(self.per_alloggio(alloggio)):
            if tipo is None or s.get("tipo") == tipo:
                return s
        return None

    # -- scrittura --------------------------------------------------------

    def deposita(self, alloggio: str, tipo: str, oggetti: list[dict],
                 soggiorno: str = "", codice: str | None = None,
                 note: str = "") -> dict:
        """Scrive uno stato in coda alla catena.

        `oggetti` sono voci dell'inventario: chiave, titolo, luogo, e
        l'impronta della fotografia ORIGINALE che li mostra.
        """
        if tipo not in TIPI:
            raise ValueError(f"tipo sconosciuto: {tipo!r}. Attesi: {', '.join(TIPI)}")
        precedente = self.per_alloggio(alloggio)
        stato = {
            "alloggio": alloggio,
            "soggiorno": soggiorno,
            "tipo": tipo,
            "momento": _ora(),
            "oggetti": [
                {"chiave": o.get("chiave"), "titolo": o.get("titolo"),
                 "luogo": o.get("luoghi", [o.get("luogo")])[0] if (o.get("luoghi") or o.get("luogo")) else None,
                 "foto_sha": o.get("foto_sha")}
                for o in oggetti
            ],
            "note": note,
            "precedente": precedente[-1]["impronta"] if precedente else GENESI,
            "deposto_da": "proprietario",
        }
        stato["impronta"] = impronta_stato(stato)
        # La controfirma e' un atto separato, con un momento suo: uno stato
        # nasce SEMPRE non controfirmato, anche quando il codice c'e' gia'.
        stato["controfirma"] = None
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        with open(self.percorso, "a", encoding="utf-8") as f:
            f.write(json.dumps(stato, ensure_ascii=False) + "\n")
        self.stati.append(stato)
        return stato

    def controfirma(self, impronta: str, codice: str, da: str = "ospite") -> dict:
        """L'altra parte dichiara di aver visto lo stesso stato.

        Depositata come riga a se' stante, con il proprio momento. Se arriva
        tre giorni dopo, nella catena si vede che e' arrivata tre giorni dopo:
        non c'e' modo di far sembrare che fosse li' dall'inizio.
        """
        bersaglio = next((s for s in self.stati if s.get("impronta") == impronta), None)
        if bersaglio is None:
            raise ValueError(f"nessuno stato con impronta {impronta[:12]}…")
        voce = {
            "tipo": "controfirma",
            "alloggio": bersaglio.get("alloggio"),
            "soggiorno": bersaglio.get("soggiorno"),
            "riferimento": impronta,
            "momento": _ora(),
            "da": da,
            "firma": firma(impronta, codice),
            "precedente": self.stati[-1].get("impronta") or GENESI,
        }
        voce["impronta"] = impronta_stato(voce)
        with open(self.percorso, "a", encoding="utf-8") as f:
            f.write(json.dumps(voce, ensure_ascii=False) + "\n")
        self.stati.append(voce)
        bersaglio["controfirma"] = voce
        return voce

    # -- verifica ---------------------------------------------------------

    def verifica(self, codice: str | None = None) -> dict:
        """Ricalcola tutto. Dice cosa e' rotto e cosa non e' controfirmato.

        Distingue due cose che vanno tenute distinte:
          - `catena_integra`: nessuno ha modificato una riga dopo averla scritta;
          - `controfirmati`: quanti stati hanno l'accordo dell'altra parte.
        Il primo senza il secondo prova soltanto che il proprietario e'
        coerente con se stesso, e in una lite non serve a niente.
        """
        rotture, senza_firma, firme_false = [], [], []
        atteso = {}
        controfirme = {}
        for s in self.stati:
            if s.get("tipo") == "controfirma":
                controfirme.setdefault(s.get("riferimento"), []).append(s)
        for s in self.stati:
            ricalcolata = impronta_stato(s)
            if ricalcolata != s.get("impronta"):
                rotture.append({"momento": s.get("momento"), "tipo": s.get("tipo"),
                                "scritta": s.get("impronta"), "ricalcolata": ricalcolata})
            if s.get("tipo") == "controfirma":
                if codice and s.get("firma") != firma(s["riferimento"], codice):
                    firme_false.append(s.get("momento"))
                continue
            a = s.get("alloggio")
            if atteso.get(a) is not None and s.get("precedente") != atteso[a]:
                rotture.append({"momento": s.get("momento"), "tipo": s.get("tipo"),
                                "anello": "il precedente non corrisponde"})
            atteso[a] = s.get("impronta")
            if not controfirme.get(s.get("impronta")):
                senza_firma.append({"momento": s.get("momento"), "tipo": s.get("tipo"),
                                    "alloggio": a})
        stati_veri = [s for s in self.stati if s.get("tipo") != "controfirma"]
        return {
            "stati": len(stati_veri),
            "controfirme": sum(len(v) for v in controfirme.values()),
            "catena_integra": not rotture,
            "rotture": rotture,
            "senza_controfirma": senza_firma,
            "firme_non_valide": firme_false,
            "righe_illeggibili": self.righe_illeggibili,
        }


# --------------------------------------------------------------------------
# la differenza: il prodotto
# --------------------------------------------------------------------------

def differenza(prima: dict, dopo: dict) -> dict:
    """Cosa manca, cosa e' comparso, cosa e' cambiato di posto.

    E' la sola cosa che qualcuno guardera' davvero. Tutto il resto — lettura,
    impronte, catena — esiste per rendere credibili queste tre liste.
    """
    a = {o["chiave"]: o for o in prima.get("oggetti", []) if o.get("chiave")}
    b = {o["chiave"]: o for o in dopo.get("oggetti", []) if o.get("chiave")}
    from .inventario import _etichetta
    spostati = []
    for k in a.keys() & b.keys():
        la, lb = _etichetta(a[k].get("luogo")), _etichetta(b[k].get("luogo"))
        if la != lb:
            spostati.append({"titolo": b[k].get("titolo"), "da": la, "a": lb})
    return {
        "alloggio": prima.get("alloggio"),
        "da": prima.get("momento"),
        "a": dopo.get("momento"),
        "mancanti": [a[k] for k in sorted(a.keys() - b.keys())],
        "comparsi": [b[k] for k in sorted(b.keys() - a.keys())],
        "spostati": spostati,
        "invariati": len(a.keys() & b.keys()) - len(spostati),
        # Il valore probatorio dipende da questo, non dal numero di oggetti.
        "prima_controfirmata": bool(prima.get("controfirma")),
        "dopo_controfirmata": bool(dopo.get("controfirma")),
    }


def stampa_differenza(d: dict) -> str:
    r = [f"alloggio {d['alloggio']}",
         f"da  {d['da']}   ({'controfirmato' if d['prima_controfirmata'] else 'NON controfirmato'})",
         f"a   {d['a']}   ({'controfirmato' if d['dopo_controfirmata'] else 'NON controfirmato'})", ""]
    if d["mancanti"]:
        r.append(f"MANCANTI ({len(d['mancanti'])}):")
        r += [f"    {o.get('titolo','')}" for o in d["mancanti"]]
    else:
        r.append("MANCANTI: nessuno.")
    if d["comparsi"]:
        r.append(f"\nCOMPARSI ({len(d['comparsi'])}):")
        r += [f"    {o.get('titolo','')}" for o in d["comparsi"]]
    if d["spostati"]:
        r.append(f"\nSPOSTATI ({len(d['spostati'])}):")
        r += [f"    {o['titolo']}: {o['da']} -> {o['a']}" for o in d["spostati"]]
    r.append(f"\ninvariati: {d['invariati']}")
    if not (d["prima_controfirmata"] and d["dopo_controfirmata"]):
        r.append("\nATTENZIONE: uno dei due stati non e' controfirmato dall'altra")
        r.append("parte. Una catena che una parte sola puo' rigenerare dimostra")
        r.append("solo di essere coerente con se stessa. In una lite non basta.")
    return "\n".join(r)
