#!/usr/bin/env python3
"""occhio.crediti — il CHIARO: pagare senza denaro, dentro il circuito.

Origine protetta: Claudio Terzi [CT-LGAI-001].
Idea dei crediti interni e dello scambio fra utenti: Claudio Terzi,
3 settembre 2026.

L'idea, con le sue parole: «non vendo a 15 euro, lo vendo a 15 crediti — e
chi viaggia può cambiarli in prodotti, o scontarci un soggiorno».

E' buona per una ragione che va detta: **toglie l'attrito del pagamento nel
momento in cui il desiderio e' vivo.** Un ospite che deve tirare fuori la
carta di credito per un DVD da nove euro non lo compra; con un saldo gia'
in tasca, lo prende. E per il proprietario il credito guadagnato torna nel
circuito invece di uscirne.

---

## Il muro, che decide la forma di questo modulo

C'e' una differenza enorme, e non e' di sfumatura, fra:

* **un buono di circuito chiuso** — si ottiene e si spende dentro il servizio,
  non si riscatta in denaro, non passa di mano fra le persone. Resta un
  meccanismo commerciale;
* **una moneta** — trasferibile fra utenti e riconvertibile in denaro. In
  Europa questo e' terreno di **moneta elettronica e servizi di pagamento**:
  autorizzazione, capitale, antiriciclaggio, vigilanza. Non e' un dettaglio
  che si sistema dopo: e' un'azienda diversa.

L'idea nella sua forma piena — «scambio fra tutti gli utenti», «può cambiare
i soldi» — cade dalla seconda parte. Percio' qui il CHIARO nasce con tre
vincoli **imposti dal codice**, non dalle buone intenzioni:

1. **Non si converte in denaro. Mai.** `converti_in_denaro()` solleva sempre,
   ed esiste apposta per essere citata da un test.
2. **Non si trasferisce fra persone**, salvo che qualcuno lo accenda
   esplicitamente — e in quel momento il modulo dichiara che si e' passato
   dall'altra parte del muro.
3. **Non si crea dal nulla.** Ogni chiaro emesso ha una causale che punta a un
   fatto avvenuto: una vendita, un soggiorno, un oggetto lasciato. Un saldo
   che cresce senza che nulla sia entrato dall'esterno e' il difetto di
   CLAUDE.md §4 con un simbolo di valuta davanti.

**UNKNOWN, e per davvero:** dove passi esattamente il confine nel tuo caso lo
dice un avvocato che si occupa di servizi di pagamento, non questo file. Cio'
che questo file fa e' impedirti di attraversarlo per sbaglio.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

LIBRO = Path(os.environ.get("OCCHIO_CREDITI", "output/crediti.jsonl"))

#: Nome dell'unita'. Un credito che si chiama «credito» somiglia a denaro;
#: uno che ha un nome proprio si ricorda ed e' un marchio.
UNITA = "chiaro"
UNITA_PLURALE = "chiari"

#: Valore interno dichiarato, solo per fare i conti dentro il circuito.
#: Non e' un tasso di cambio: **non esiste alcun cambio.**
VALORE_INTERNO_EUR = 1.0

#: Perche' un chiaro puo' nascere. Ognuna punta a un fatto verificabile.
CAUSALI_EMISSIONE = {
    "vendita": "hai venduto un oggetto e hai scelto i chiari invece dei soldi",
    "soggiorno": "hai ospitato o soggiornato nel circuito",
    "lasciato": "hai lasciato in casa un oggetto che qualcun altro ha usato",
    "rimborso": "annullamento di una spesa gia' fatta",
}
CAUSALI_SPESA = {
    "acquisto": "hai comprato un oggetto in una casa del circuito",
    "soggiorno": "hai scontato un soggiorno",
}


class SaldoInsufficiente(Exception):
    """Non ci sono abbastanza chiari. Il saldo non va mai sotto zero."""


class FuoriDalCircuito(Exception):
    """Qualcuno ha chiesto al chiaro di comportarsi come denaro."""


def _ora() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------------
# il libro
# --------------------------------------------------------------------------

class Crediti:
    """Libro append-only dei movimenti. Il saldo si ricalcola, non si conserva.

    Conservare il saldo a parte significa avere due verita' che prima o poi
    divergono, e quando divergono nessuno sa quale sia quella giusta. Qui il
    saldo e' una somma: se il libro e' integro, il saldo e' corretto per
    costruzione.
    """

    def __init__(self, percorso: Path | str = LIBRO,
                 trasferibile: bool = False):
        self.percorso = Path(percorso)
        #: Accenderlo porta il circuito dall'altra parte del muro (vedi in
        #: testa al modulo). Il modulo lo dice ogni volta che viene usato.
        self.trasferibile = bool(trasferibile)
        self.movimenti: list[dict] = []
        self.carica()

    def carica(self) -> int:
        self.movimenti = []
        self.righe_illeggibili = 0
        if not self.percorso.exists():
            return 0
        with open(self.percorso, "r", encoding="utf-8") as f:
            for riga in f:
                riga = riga.strip()
                if not riga:
                    continue
                try:
                    self.movimenti.append(json.loads(riga))
                except json.JSONDecodeError:
                    self.righe_illeggibili += 1
        return len(self.movimenti)

    def _scrivi(self, voce: dict) -> dict:
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        with open(self.percorso, "a", encoding="utf-8") as f:
            f.write(json.dumps(voce, ensure_ascii=False) + "\n")
        self.movimenti.append(voce)
        return voce

    # -- lettura ----------------------------------------------------------

    def saldo(self, conto: str) -> int:
        """Chiari disponibili. Interi: mezzo chiaro non esiste, e i decimali
        sono il modo piu' rapido per far divergere due somme."""
        return sum(m["quanti"] if m["a"] == conto else -m["quanti"]
                   for m in self.movimenti
                   if conto in (m.get("a"), m.get("da")))

    def estratto(self, conto: str) -> list[dict]:
        return [m for m in self.movimenti if conto in (m.get("a"), m.get("da"))]

    def emessi(self) -> int:
        return sum(m["quanti"] for m in self.movimenti if m.get("da") is None)

    def spesi(self) -> int:
        return sum(m["quanti"] for m in self.movimenti if m.get("a") is None)

    def in_circolo(self) -> int:
        return self.emessi() - self.spesi()

    # -- scrittura --------------------------------------------------------

    def emetti(self, conto: str, quanti: int, causale: str,
               riferimento: str = "") -> dict:
        """Crea chiari. Solo contro un fatto avvenuto, mai a piacere.

        `riferimento` deve puntare a qualcosa di controllabile — l'identita'
        di una vendita, di un soggiorno. Un'emissione senza riferimento e'
        rifiutata: e' il modo in cui un saldo cresce senza che nulla sia
        entrato dall'esterno, cioe' §4 con un simbolo di valuta davanti.
        """
        quanti = self._intero(quanti)
        if causale not in CAUSALI_EMISSIONE:
            raise ValueError(f"causale sconosciuta: {causale!r}. "
                             f"Attese: {', '.join(CAUSALI_EMISSIONE)}")
        if not str(riferimento).strip():
            raise ValueError(
                "emissione senza riferimento a un fatto avvenuto: rifiutata. "
                "Ogni chiaro deve poter essere ricondotto a una vendita, a un "
                "soggiorno o a un oggetto lasciato.")
        return self._scrivi({"tipo": "emissione", "da": None, "a": conto,
                             "quanti": quanti, "causale": causale,
                             "riferimento": str(riferimento),
                             "momento": _ora()})

    def spendi(self, conto: str, quanti: int, causale: str,
               riferimento: str = "") -> dict:
        quanti = self._intero(quanti)
        if causale not in CAUSALI_SPESA:
            raise ValueError(f"causale sconosciuta: {causale!r}. "
                             f"Attese: {', '.join(CAUSALI_SPESA)}")
        disponibili = self.saldo(conto)
        if quanti > disponibili:
            raise SaldoInsufficiente(
                f"servono {quanti} {UNITA_PLURALE}, ce ne sono {disponibili}")
        return self._scrivi({"tipo": "spesa", "da": conto, "a": None,
                             "quanti": quanti, "causale": causale,
                             "riferimento": str(riferimento),
                             "momento": _ora()})

    def trasferisci(self, da: str, a: str, quanti: int) -> dict:
        """Passare chiari da una persona a un'altra.

        **Spento di default, e non per prudenza generica:** e' esattamente il
        passo che porta un buono di circuito chiuso dentro il perimetro dei
        servizi di pagamento. Accenderlo e' una decisione d'impresa, non una
        funzione da chiamare.
        """
        if not self.trasferibile:
            raise FuoriDalCircuito(
                "il trasferimento fra persone e' spento. Accenderlo porta il "
                "circuito dentro il perimetro di moneta elettronica e servizi "
                "di pagamento: autorizzazione, capitale, antiriciclaggio. "
                "Non e' un interruttore tecnico, e' un'azienda diversa — "
                "parlane con un avvocato prima di usare "
                "Crediti(trasferibile=True).")
        quanti = self._intero(quanti)
        if quanti > self.saldo(da):
            raise SaldoInsufficiente(f"{da} non ha {quanti} {UNITA_PLURALE}")
        return self._scrivi({"tipo": "trasferimento", "da": da, "a": a,
                             "quanti": quanti, "causale": "trasferimento",
                             "riferimento": "", "momento": _ora(),
                             "fuori_dal_circuito_chiuso": True})

    @staticmethod
    def _intero(quanti) -> int:
        """Interi, e nient'altro.

        `int(1.5)` da' 1 senza dire niente: mezzo chiaro sparirebbe in
        silenzio, e un troncamento silenzioso in un libro contabile e'
        esattamente il modo in cui due somme cominciano a divergere.
        Trovato da un test, non da una rilettura.
        """
        if isinstance(quanti, bool):
            raise ValueError(f"quantita' non valida: {quanti!r}")
        if isinstance(quanti, float):
            if not quanti.is_integer():
                raise ValueError(
                    f"mezzo chiaro non esiste: {quanti!r}. Arrotonda tu, "
                    "esplicitamente, invece di lasciarlo fare al troncamento.")
            quanti = int(quanti)
        if not isinstance(quanti, int):
            raise ValueError(f"quantita' non valida: {quanti!r}")
        if quanti <= 0:
            raise ValueError("la quantita' dev'essere positiva")
        return quanti

    # -- coerenza ---------------------------------------------------------

    def verifica(self) -> dict:
        """I chiari si conservano: emessi = spesi + in circolo, e nessun
        saldo e' negativo. Se una delle due cade, il libro e' rotto."""
        conti = {c for m in self.movimenti for c in (m.get("a"), m.get("da")) if c}
        saldi = {c: self.saldo(c) for c in conti}
        negativi = {c: s for c, s in saldi.items() if s < 0}
        somma = sum(saldi.values())
        return {
            "conti": len(conti), "saldi": saldi,
            "emessi": self.emessi(), "spesi": self.spesi(),
            "in_circolo": self.in_circolo(),
            "conservati": somma == self.in_circolo(),
            "saldi_negativi": negativi,
            "righe_illeggibili": self.righe_illeggibili,
            "trasferibile": self.trasferibile,
        }


# --------------------------------------------------------------------------
# il muro, in una funzione sola
# --------------------------------------------------------------------------

def converti_in_denaro(*_a, **_k):
    """Non esiste, e non e' una svista.

    Nel momento in cui un chiaro torna euro, il buono diventa moneta e il
    prodotto cambia mestiere. Questa funzione c'e' per essere citata da un
    test e per rendere rumoroso il giorno in cui qualcuno provera' a
    scriverla.
    """
    raise FuoriDalCircuito(
        "un chiaro non si converte in denaro: e' cio' che lo tiene un buono di "
        "circuito chiuso invece che moneta elettronica. Se serve il rimborso in "
        "euro, serve prima un'autorizzazione — e allora questo modulo non e' "
        "piu' quello giusto.")


# --------------------------------------------------------------------------
# il prezzo in chiari
# --------------------------------------------------------------------------

def prezzo_in_chiari(prezzo_eur: float, valore=VALORE_INTERNO_EUR) -> int:
    """Quanti chiari costa una cosa che in euro costerebbe tanto.

    Si arrotonda **per eccesso**: chi paga in chiari non deve costare al
    proprietario meno del suo minimo. Mezzo chiaro non esiste, e la meta'
    mancante non la puo' mettere il venditore senza accorgersene.
    """
    import math
    if valore <= 0:
        raise ValueError("il valore interno dev'essere positivo")
    return max(1, math.ceil(float(prezzo_eur) / valore - 1e-9))
