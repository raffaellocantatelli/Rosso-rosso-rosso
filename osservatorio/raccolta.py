#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collettore: interroga le fonti, e soprattutto ammette quando non lo fa.

Regole dure, applicate qui e non lasciate alla buona volonta' di chi legge
la dashboard:

  1. UNO ZERO NON SI INVENTA. Se una fonte non ha chiave, non e' implementata
     o ha fallito, il conteggio resta None. Sullo schermo diventa un trattino
     e uno stato esplicito, mai la cifra 0. La differenza fra "nessun evento"
     e "nessun dato" e' l'intera differenza fra una misura e un'illusione.
  2. OGNI NUMERO PORTA LA SUA ETA'. Un conteggio senza il momento in cui e'
     stato letto non e' verificabile. Lo stato VECCHIO scatta da solo quando
     la lettura invecchia oltre il doppio della cadenza dichiarata a monte.
  3. IL TETTO SI DICHIARA. Se una risposta arriva al limite della query, il
     risultato e' marcato troncato: il valore vero e' >= a quello mostrato
     ed e' ignoto.
  4. LA TRACCIA E' APPEND-ONLY. Ogni lettura riuscita o fallita finisce in
     output/osservatorio.jsonl. Nessuna riga viene mai riscritta, come nel
     registro dei nodi: chi arriva dopo puo' ricostruire cosa si vedeva e
     quando, senza fidarsi di questo processo.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from .fonti import FONTI, Fonte, Risultato

AGENTE = "R3-osservatorio/1.0 (+https://github.com/raffaellocantatelli/Rosso-rosso-rosso)"
TIMEOUT_S = 20
TRACCIA = os.path.join("output", "osservatorio.jsonl")

# stati possibili di una fonte
LIVE = "LIVE"
VECCHIO = "VECCHIO"
ERRORE = "ERRORE"
SENZA_CHIAVE = "SENZA_CHIAVE"
NON_IMPLEMENTATA = "NON_IMPLEMENTATA"
MAI_LETTA = "MAI_LETTA"


class StatoFonte:
    """Cio' che sappiamo di una fonte in questo istante. Niente di piu'."""

    def __init__(self, fonte: Fonte):
        self.fonte = fonte
        self.conteggio: Optional[int] = None
        self.digest: Optional[str] = None      # sha256 dei byte grezzi ricevuti
        self.punti: List[dict] = []
        self.troncato = False
        self.dettaglio = ""
        self.ultimo_ok: Optional[float] = None
        self.ultimo_tentativo: Optional[float] = None
        self.errore: Optional[str] = None
        self.latenza_ms: Optional[int] = None

    @property
    def chiave(self) -> Optional[str]:
        if not self.fonte.chiave_env:
            return None
        return os.environ.get(self.fonte.chiave_env) or None

    def stato(self) -> str:
        if not self.fonte.implementata:
            return NON_IMPLEMENTATA
        if self.fonte.chiave_env and not self.chiave:
            return SENZA_CHIAVE
        if self.ultimo_ok is None:
            return ERRORE if self.errore else MAI_LETTA
        eta = time.time() - self.ultimo_ok
        if eta > max(2 * self.fonte.cadenza_monte_s, 3 * self.fonte.cadenza_s):
            return VECCHIO
        if self.errore:
            return VECCHIO
        return LIVE

    def eta_s(self) -> Optional[int]:
        if self.ultimo_ok is None:
            return None
        return int(time.time() - self.ultimo_ok)

    def come_json(self) -> dict:
        f = self.fonte
        return {
            "id": f.id, "nome": f.nome, "dominio": f.dominio,
            "copertura": f.copertura, "nota": f.nota,
            "url": f.url.replace("{CHIAVE}", "***"),
            "chiave_env": f.chiave_env,
            "cadenza_monte_s": f.cadenza_monte_s,
            "cadenza_s": f.cadenza_s,
            "stato": self.stato(),
            "conteggio": self.conteggio,       # None, mai 0 di comodo
            "troncato": self.troncato,
            "dettaglio": self.dettaglio,
            "eta_s": self.eta_s(),
            "ultimo_ok": self.ultimo_ok,
            "ultimo_tentativo": self.ultimo_tentativo,
            "errore": self.errore,
            "latenza_ms": self.latenza_ms,
            "digest": self.digest,
            "punti": len(self.punti),
        }


class Collettore:
    """Un thread, un ciclo, nessuna promessa di lavorare quando e' spento."""

    def __init__(self, fonti: Optional[List[Fonte]] = None):
        self.stati: Dict[str, StatoFonte] = {
            f.id: StatoFonte(f) for f in (fonti if fonti is not None else FONTI)
        }
        self.avviato = time.time()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    # ---------------------------------------------------------- lettura

    def _scarica(self, s: StatoFonte) -> None:
        f = s.fonte
        url = f.url
        intestazioni = dict(f.intestazioni)
        intestazioni.setdefault("User-Agent", AGENTE)

        chiave = s.chiave
        if chiave:
            if "{CHIAVE}" in url:
                url = url.replace("{CHIAVE}", chiave)
            else:
                intestazioni["Authorization"] = "Bearer %s" % chiave

        t0 = time.time()
        s.ultimo_tentativo = t0
        try:
            req = urllib.request.Request(url, headers=intestazioni)
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                raw = r.read()
            ris: Risultato = f.parser(raw)
            with self._lock:
                s.digest = hashlib.sha256(raw).hexdigest()
                s.conteggio = ris.conteggio
                s.punti = ris.punti
                s.troncato = ris.troncato
                s.dettaglio = ris.dettaglio
                s.ultimo_ok = time.time()
                s.errore = None
                s.latenza_ms = int((time.time() - t0) * 1000)
            self._traccia(s, "ok")
        except Exception as e:                      # rete, parsing, formato cambiato
            with self._lock:
                s.errore = "%s: %s" % (type(e).__name__, str(e)[:200])
                s.latenza_ms = int((time.time() - t0) * 1000)
                # il conteggio precedente resta, ma invecchia: non viene azzerato
            self._traccia(s, "errore")

    def _traccia(self, s: StatoFonte, esito: str) -> None:
        try:
            os.makedirs(os.path.dirname(TRACCIA), exist_ok=True)
            riga = {"ts": round(time.time(), 3), "fonte": s.fonte.id, "esito": esito,
                    "conteggio": s.conteggio, "troncato": s.troncato,
                    "latenza_ms": s.latenza_ms, "errore": s.errore}
            with open(TRACCIA, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(riga, ensure_ascii=False) + "\n")
        except OSError:
            pass    # la traccia e' un di piu': se non si scrive, la dashboard vive

    def _da_leggere(self, s: StatoFonte) -> bool:
        f = s.fonte
        if not f.implementata or (f.chiave_env and not s.chiave):
            return False
        if s.ultimo_tentativo is None:
            return True
        return (time.time() - s.ultimo_tentativo) >= f.cadenza_s

    # ---------------------------------------------------------- ciclo

    def giro(self) -> None:
        for s in list(self.stati.values()):
            if self._stop.is_set():
                return
            if self._da_leggere(s):
                self._scarica(s)

    def _ciclo(self) -> None:
        while not self._stop.is_set():
            self.giro()
            self._stop.wait(5)

    def avvia(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._ciclo, name="collettore", daemon=True)
        self._thread.start()

    def ferma(self) -> None:
        """Il collettore vive quanto il processo. Chiuso il processo, non
        resta nulla in esecuzione: nessun lavoro in background, nessuna
        continuita' oltre la sessione."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    # ---------------------------------------------------------- lettura stato

    def istantanea(self) -> dict:
        with self._lock:
            fonti = [s.come_json() for s in self.stati.values()]
            punti = []
            for s in self.stati.values():
                if s.stato() in (LIVE, VECCHIO):
                    for p in s.punti:
                        q = dict(p)
                        q["fonte"] = s.fonte.id
                        punti.append(q)
        conta = {}
        for f in fonti:
            conta[f["stato"]] = conta.get(f["stato"], 0) + 1
        return {
            "adesso": time.time(),
            "avviato": self.avviato,
            "fonti": fonti,
            "punti": punti,
            "riepilogo": conta,
            "totale_fonti": len(fonti),
        }
