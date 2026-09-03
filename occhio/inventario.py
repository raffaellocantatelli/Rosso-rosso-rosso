#!/usr/bin/env python3
"""occhio.inventario — il registro degli oggetti, append-only e deterministico.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Un inventario e' utile solo se sa dire **no**: se ripassando con la telecamera
sullo stesso scaffale il conteggio cresce, il numero non misura gli oggetti,
misura le passate. E' il difetto di CLAUDE.md §4 applicato a un armadio.

Percio' l'identita' di un oggetto qui non e' mai una impressione: e' una
funzione pura di cio' che si e' letto, e si puo' rieseguire su un registro
gia' scritto ottenendo lo stesso risultato.

Tre livelli di identita', in ordine di forza:

1. **chiave testuale** — `tipo:titolo` normalizzato. Vale quando il titolo e'
   stato letto davvero. E' la piu' forte perche' sopravvive a inquadratura,
   luce e distanza: lo stesso DVD ripreso da due metri o da venti centimetri
   da' la stessa chiave.
2. **impronta percettiva (dHash a 64 bit)** del ritaglio. Vale quando il
   titolo non e' leggibile ma l'oggetto e' visibilmente lo stesso. Distanza
   di Hamming <= SOGLIA_IMPRONTA -> stesso oggetto fisico.
3. **niente dei due** -> stato INCERTO. Non entra nel registro da solo.
   Il colore in sovrimpressione sara' ambra, non verde: il verde significa
   «e' scritto nel registro», e deve restare una promessa mantenuta.

Il file e' `output/inventario.jsonl`, una riga JSON per evento. Append-only
per la ragione di §6 regola 3: due passate non possono sovrascriversi.
Lo stato corrente si ricostruisce rileggendo il file, non si conserva a parte.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path

# Distanza di Hamming sotto la quale due impronte a 64 bit sono considerate
# lo stesso oggetto. 10/64 e' prudente: sotto questa soglia due dorsi di DVD
# diversi dello stesso cofanetto restano distinti (verificabile con
# `python -m occhio --prova-impronte`), sopra i 14 iniziano a fondersi.
SOGLIA_IMPRONTA = 10

ARCHIVIO = Path(os.environ.get("OCCHIO_INVENTARIO", "output/inventario.jsonl"))

TIPI_NOTI = (
    "dvd", "blu-ray", "vhs", "cd", "vinile", "libro", "rivista",
    "scatola", "elettronica", "documento", "quadro", "altro",
)

# Articoli e rumore che l'OCR di un dorso porta con se': "THE MATRIX" e
# "MATRIX, THE" sono lo stesso disco, e devono dare la stessa chiave.
_ARTICOLI = {"il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
             "the", "a", "an", "der", "die", "das", "le", "les", "el"}


# --------------------------------------------------------------------------
# normalizzazione e identita'
# --------------------------------------------------------------------------

def normalizza(testo: str) -> str:
    """Riduce un titolo alla sua forma confrontabile.

    Toglie accenti, punteggiatura, doppi spazi, maiuscole e articoli iniziali
    o finali. Non tocca i numeri: «Rocky 2» e «Rocky 3» devono restare diversi.
    """
    if not testo:
        return ""
    t = unicodedata.normalize("NFKD", str(testo))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    if not t:
        return ""
    parole = t.split()
    # articolo in testa, o in coda dopo virgola all'italiana/inglese
    while parole and parole[0] in _ARTICOLI:
        parole.pop(0)
    while parole and parole[-1] in _ARTICOLI:
        parole.pop()
    return " ".join(parole)


def chiave(tipo: str, titolo: str) -> str | None:
    """Chiave canonica di un oggetto, o None se il titolo non e' utilizzabile.

    Un titolo di una sola lettera o di sole cifre non identifica niente: e'
    meglio dichiarare l'assenza di chiave che fabbricarne una debole, perche'
    una chiave debole fonde due oggetti diversi e il registro perde una voce
    senza dirlo.
    """
    n = normalizza(titolo)
    if len(n.replace(" ", "")) < 3:
        return None
    t = normalizza(tipo) or "altro"
    return f"{t}:{n}"


def distanza_impronta(a: str, b: str) -> int:
    """Distanza di Hamming fra due impronte esadecimali a 64 bit.

    Restituisce 64 (massima distanza) se una delle due manca o e' malformata:
    nessuna impronta non deve mai somigliare a tutto.
    """
    if not a or not b:
        return 64
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 64


# --------------------------------------------------------------------------
# il registro
# --------------------------------------------------------------------------

class Inventario:
    """Vista in memoria di un file append-only. Si ricostruisce rileggendolo."""

    def __init__(self, percorso: Path | str = ARCHIVIO):
        self.percorso = Path(percorso)
        self.voci: list[dict] = []
        self._per_chiave: dict[str, dict] = {}
        self.carica()

    # -- lettura ----------------------------------------------------------

    def carica(self) -> int:
        """Rilegge il file da zero. Righe illeggibili contate, non silenziate."""
        self.voci = []
        self._per_chiave = {}
        self.righe_illeggibili = 0
        if not self.percorso.exists():
            return 0
        with open(self.percorso, "r", encoding="utf-8") as f:
            for riga in f:
                riga = riga.strip()
                if not riga:
                    continue
                try:
                    voce = json.loads(riga)
                except json.JSONDecodeError:
                    self.righe_illeggibili += 1
                    continue
                self._assorbi(voce)
        return len(self.voci)

    def _assorbi(self, voce: dict) -> None:
        """Applica un evento allo stato corrente.

        Un evento `avvistamento` su una voce gia' presente non aggiunge una
        voce: incrementa il contatore. E' qui che il ripasso smette di gonfiare
        il totale.
        """
        k = voce.get("chiave")
        if k and k in self._per_chiave:
            esistente = self._per_chiave[k]
            esistente["avvistamenti"] = esistente.get("avvistamenti", 1) + 1
            esistente["visto_ultimo"] = voce.get("visto_ultimo", esistente.get("visto_ultimo"))
            if voce.get("impronta") and voce["impronta"] not in esistente.setdefault("impronte", []):
                esistente["impronte"].append(voce["impronta"])
            return
        voce.setdefault("avvistamenti", 1)
        voce.setdefault("impronte", [voce["impronta"]] if voce.get("impronta") else [])
        self.voci.append(voce)
        if k:
            self._per_chiave[k] = voce

    # -- riconoscimento ---------------------------------------------------

    def riconosci(self, tipo: str, titolo: str, impronta: str | None = None) -> tuple[str, dict | None]:
        """Dice se un oggetto letto adesso e' gia' nel registro.

        Ritorna `(stato, voce)` dove stato e':
          - `CATALOGATO`  la chiave testuale coincide  -> verde
          - `RIVISTO`     l'impronta coincide, il titolo no -> verde chiaro
          - `NUOVO`       ha una chiave e non e' nel registro -> da scrivere
          - `INCERTO`     nessuna chiave utilizzabile -> ambra, mai automatico

        Nessuno di questi stati dipende da cosa e' successo nella sessione
        corrente: dipende solo dal contenuto del file. Riavviando il server
        gli stessi oggetti danno gli stessi stati — questa e' la differenza
        fra un registro e una impressione.
        """
        k = chiave(tipo, titolo)
        if k and k in self._per_chiave:
            return "CATALOGATO", self._per_chiave[k]
        if impronta:
            for voce in self.voci:
                for imp in voce.get("impronte", []):
                    if distanza_impronta(impronta, imp) <= SOGLIA_IMPRONTA:
                        return ("CATALOGATO" if k and voce.get("chiave") == k else "RIVISTO"), voce
        if k:
            return "NUOVO", None
        return "INCERTO", None

    # -- scrittura --------------------------------------------------------

    def registra(self, tipo: str, titolo: str, impronta: str | None = None,
                 testo_letto: str = "", confidenza: float | None = None,
                 fonte: str = "telecamera", note: str = "") -> dict:
        """Scrive un evento in coda al file e aggiorna la vista.

        Un oggetto senza chiave utilizzabile non viene scritto: solleva
        ValueError. Serve perche' il chiamante sia costretto a decidere —
        chiedere all'umano o lasciar perdere — invece di depositare una voce
        che nessuno potra' piu' ritrovare.
        """
        k = chiave(tipo, titolo)
        if not k:
            raise ValueError(
                f"titolo non identificante: {titolo!r}. "
                "Serve una conferma umana (--conferma) o una lettura migliore."
            )
        stato, esistente = self.riconosci(tipo, titolo, impronta)
        ora = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        voce = {
            "chiave": k,
            "tipo": normalizza(tipo) or "altro",
            "titolo": str(titolo).strip(),
            "testo_letto": str(testo_letto or "").strip()[:500],
            "impronta": impronta,
            "confidenza": confidenza,
            "fonte": fonte,
            "note": note,
            "visto_primo": ora if stato == "NUOVO" else (esistente or {}).get("visto_primo", ora),
            "visto_ultimo": ora,
            "evento": "nuovo" if stato == "NUOVO" else "avvistamento",
        }
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        with open(self.percorso, "a", encoding="utf-8") as f:
            f.write(json.dumps(voce, ensure_ascii=False) + "\n")
        self._assorbi(dict(voce))
        voce["stato"] = stato
        return voce

    # -- resoconto --------------------------------------------------------

    def per_tipo(self) -> dict[str, int]:
        conteggio: dict[str, int] = {}
        for v in self.voci:
            conteggio[v.get("tipo", "altro")] = conteggio.get(v.get("tipo", "altro"), 0) + 1
        return dict(sorted(conteggio.items(), key=lambda kv: -kv[1]))

    def csv(self) -> str:
        import csv as _csv
        import io
        buf = io.StringIO()
        w = _csv.writer(buf)
        w.writerow(["tipo", "titolo", "avvistamenti", "visto_primo", "visto_ultimo",
                    "confidenza", "testo_letto"])
        for v in sorted(self.voci, key=lambda x: (x.get("tipo", ""), x.get("titolo", ""))):
            w.writerow([v.get("tipo", ""), v.get("titolo", ""), v.get("avvistamenti", 1),
                        v.get("visto_primo", ""), v.get("visto_ultimo", ""),
                        v.get("confidenza", ""), v.get("testo_letto", "")])
        return buf.getvalue()
