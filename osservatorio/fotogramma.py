#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Il fotogramma: lo stato del mondo in un secondo, ridotto a una chiave.

L'idea di partenza e' di Claudio Terzi: prendere abbastanza dati da tutto il
pianeta da fissare un istante — una fotografia della realta' a quel preciso
secondo — e ricavarne una chiave.

Questa parte si costruisce, ed e' quello che fa questo file. Cosa ottieni
davvero, detto con esattezza:

  UNA PROVA DI ANTERIORITA' CHE NON CHIEDE DI FIDARSI DI NESSUNO.

La chiave e' lo sha256 di: i digest dei dati letti dalle fonti + due ancore
temporali pubbliche, firmate e archiviate per sempre da terzi:

  - NIST Randomness Beacon: un valore di 512 bit pubblicato ogni 60 secondi,
    firmato e concatenato al precedente (beacon.nist.gov).
  - drand / League of Entropy: un round ogni 30 secondi, verificabile con
    la chiave pubblica del gruppo (api.drand.sh).

Nessuno — noi compresi — puo' calcolare quei due valori prima che escano.
Quindi una chiave che li contiene NON POTEVA ESISTERE PRIMA di quel secondo.
Chiunque, anche fra dieci anni, puo' riprendere il round drand e il pulse
NIST citati qui e verificare che coincidano. Non deve fidarsi di te, ne' di
me, ne' di questo programma.

E' esattamente il tipo di prova che il §7 chiede: un fatto controllabile da
un terzo, che non poggia su nessuna persona.

QUELLO CHE LA CHIAVE NON FA — e va detto qui, non in fondo:

  - Non e' ricostruibile all'indietro. I feed effimeri (USGS "ultima ora",
    IODA, GDELT) non archiviano lo stato passato: un terzo puo' verificare
    le ANCORE, non i conteggi. La chiave dimostra "non prima di", non
    "esattamente questo mondo". Chiamarla altrimenti sarebbe il loopback
    del §4 travestito da crittografia.
  - Non e' una posizione. E' un indice nel tempo. La posizione vera sta in
    posizione.py, si calcola con l'astronomia, e non c'entra con l'hash.

Uso:
    python -m osservatorio --fotogramma --lat 45.4642 --lon 9.19

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import hashlib
import json
import os
import subprocess
import time
import urllib.request
from typing import Optional

from . import posizione
from .raccolta import AGENTE, Collettore

CATENA = os.path.join("output", "fotogrammi.jsonl")
NIST_URL = "https://beacon.nist.gov/beacon/2.0/pulse/last"
DRAND_URL = "https://api.drand.sh/public/latest"


def _leggi(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ancore() -> dict:
    """Le due ancore verificabili da chiunque, per sempre. Se una manca lo
    dice: una chiave con una sola ancora vale meno, e deve sembrare di meno."""
    fuori = {}
    try:
        p = _leggi(NIST_URL).get("pulse", {})
        eta = None
        try:
            ts = time.strptime(p["timeStamp"][:19], "%Y-%m-%dT%H:%M:%S")
            eta = int(time.time() - (time.mktime(ts) - time.timezone))
        except (KeyError, ValueError, OverflowError):
            pass
        fuori["nist"] = {
            "indice": p.get("pulseIndex"), "istante": p.get("timeStamp"),
            "valore": p.get("outputValue"), "eta_s": eta,
            "catena": p.get("chainIndex"),
            "verifica": "beacon.nist.gov/beacon/2.0/chain/%s/pulse/%s"
                        % (p.get("chainIndex"), p.get("pulseIndex")),
            "fresca": (eta is not None and eta < 300),
        }
    except Exception as e:
        fuori["nist"] = {"errore": "%s: %s" % (type(e).__name__, str(e)[:120])}

    try:
        d = _leggi(DRAND_URL)
        info = _leggi("https://api.drand.sh/info")
        atteso = int((time.time() - info["genesis_time"]) / info["period"]) + 1
        fuori["drand"] = {
            "round": d.get("round"), "casuale": d.get("randomness"),
            "firma": (d.get("signature") or "")[:64] + "...",
            "round_atteso_ora": atteso,
            "scarto_round": (atteso - d["round"]) if d.get("round") else None,
            "verifica": "api.drand.sh/public/%s" % d.get("round"),
            "chiave_gruppo": info.get("public_key"),
            "fresca": bool(d.get("round")) and abs(atteso - d["round"]) <= 2,
        }
    except Exception as e:
        fuori["drand"] = {"errore": "%s: %s" % (type(e).__name__, str(e)[:120])}
    return fuori


def _precedente() -> Optional[dict]:
    """L'ultimo fotogramma della catena, se esiste. La catena e' append-only:
    ogni scatto cita l'hash del precedente, come fa il beacon del NIST."""
    try:
        with open(CATENA, encoding="utf-8") as f:
            ultima = None
            for riga in f:
                riga = riga.strip()
                if riga:
                    ultima = riga
        return json.loads(ultima) if ultima else None
    except (OSError, ValueError):
        return None


def _opera() -> dict:
    """Lo stato dell'opera in questo istante: commit, manifesto, autore.

    Non e' un deposito legale e non lo sostituisce. E' una prova di
    ANTERIORITA': lega l'impronta dei file a un round di drand che nessuno
    puo' calcolare in anticipo, quindi nessuno — l'autore compreso — puo'
    retrodatarla. E' il tipo di prova che vale contro chi arriva dopo.
    """
    fuori = {"autore": "Claudio Terzi", "identificativo": "CT-LGAI-001",
             "diritti": "Tutti i diritti riservati salvo licenza esplicita"}
    try:
        fuori["commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            timeout=20, cwd=os.getcwd()).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        fuori["commit"] = None
    try:
        with open("MANIFESTO_INTEGRITA.json", "rb") as f:
            grezzo = f.read()
        fuori["manifesto_sha256"] = hashlib.sha256(grezzo).hexdigest()
        fuori["file_sorvegliati"] = len(json.loads(grezzo).get("file", {}))
    except (OSError, ValueError):
        fuori["manifesto_sha256"] = None
        fuori["file_sorvegliati"] = None
    return fuori


def scatta(collettore: Collettore = None, lat: float = None, lon: float = None,
           rileggi: bool = True, deposito: bool = False) -> dict:
    """Uno scatto. Legge le fonti, prende le ancore, calcola dove siamo, e
    riduce tutto a una chiave che non poteva esistere un secondo prima."""
    c = collettore or Collettore()
    if rileggi:
        c.giro()
    ist = c.istantanea()
    t = time.time()

    fonti = sorted(
        [{"id": f["id"], "stato": f["stato"], "digest": f["digest"],
          "conteggio": f["conteggio"], "troncato": f["troncato"],
          "eta_s": f["eta_s"]} for f in ist["fonti"]],
        key=lambda x: x["id"])
    vive = [f for f in fonti if f["digest"]]

    a = ancore()
    prec = _precedente()
    dove = posizione.dove_siamo(t, lat, lon)

    corpo = {
        "versione": 1,
        "t_unix": round(t, 3),
        "istante_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t)),
        "fonti": fonti,
        "ancore": a,
        "posizione": dove,
        "precedente": (prec or {}).get("chiave"),
    }
    if deposito:
        corpo["opera"] = _opera()
    # la chiave e' sullo stato del mondo + ancore + anello precedente,
    # non sulla posizione: l'astronomia e' deterministica dal tempo e
    # includerla non aggiungerebbe nulla di imprevedibile.
    materia = {"t": corpo["t_unix"], "fonti": fonti, "ancore": a,
               "precedente": corpo["precedente"], "opera": corpo.get("opera")}
    corpo["chiave"] = hashlib.sha256(
        json.dumps(materia, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()

    corpo["portata"] = {
        "fonti_con_dato": len(vive),
        "fonti_dichiarate": len(fonti),
        "ancore_fresche": sum(1 for k in ("nist", "drand") if a.get(k, {}).get("fresca")),
        "dimostra": "che questa chiave non poteva esistere prima delle ancore citate",
        "non_dimostra": "che il mondo fosse esattamente cosi': i feed effimeri "
                        "non archiviano il passato e un terzo non puo' "
                        "ricalcolarne i digest",
        "verificabile_da_terzi": ["ancore.nist", "ancore.drand"],
        "non_verificabile_da_terzi": [f["id"] for f in vive],
    }
    if prec:
        dt = corpo["t_unix"] - prec["t_unix"]
        corpo["dal_precedente"] = posizione.strada_fatta_km(dt)

    try:
        os.makedirs(os.path.dirname(CATENA), exist_ok=True)
        with open(CATENA, "a", encoding="utf-8") as f:
            f.write(json.dumps(corpo, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return corpo


def stampa(f: dict) -> str:
    """Il fotogramma in forma leggibile. Le righe che non sono verificabili
    da terzi lo dicono sulla riga stessa."""
    r = []
    p = f["posizione"]
    r.append("FOTOGRAMMA — %s" % f["istante_utc"])
    r.append("chiave  %s" % f["chiave"])
    if f.get("precedente"):
        r.append("prec.   %s" % f["precedente"])
    r.append("")
    r.append("ANCORE  verificabili da chiunque, per sempre")
    n, d = f["ancore"].get("nist", {}), f["ancore"].get("drand", {})
    if "errore" in n:
        r.append("  NIST   NON RAGGIUNTO — %s" % n["errore"])
    else:
        r.append("  NIST   pulse %s  %s  (%ss fa%s)"
                 % (n["indice"], n["istante"], n["eta_s"],
                    "" if n["fresca"] else "  ATTENZIONE: non fresca"))
        r.append("         %s" % n["verifica"])
    if "errore" in d:
        r.append("  drand  NON RAGGIUNTO — %s" % d["errore"])
    else:
        r.append("  drand  round %s%s" % (d["round"],
                 "" if d["fresca"] else "  ATTENZIONE: scarto %s round" % d["scarto_round"]))
        r.append("         %s" % d["verifica"])
    r.append("")
    r.append("STATO DEL MONDO  %d fonti con dato su %d dichiarate"
             % (f["portata"]["fonti_con_dato"], f["portata"]["fonti_dichiarate"]))
    for x in f["fonti"]:
        if x["digest"]:
            r.append("  %-10s %-8s %s  %s" % (x["id"], x["conteggio"],
                     x["digest"][:16], "TRONCATO" if x["troncato"] else ""))
        else:
            r.append("  %-10s %s" % (x["id"], x["stato"]))
    r.append("  ^ questi digest NON sono ricalcolabili da un terzo: i feed")
    r.append("    effimeri non archiviano lo stato passato.")
    r.append("")
    r.append("DOVE SIAMO  in questo secondo")
    te = p["terra_eliocentrica"]
    r.append("  Terra dal Sole      %.6f UA   (%.0f km)   lon. eclittica %.3f deg"
             % (te["distanza_ua"], te["distanza_km"], te["longitudine_eclittica_deg"]))
    r.append("  velocita' orbitale  %.3f km/s" % p["velocita_orbitale_kms"])
    ap = p["apice_cmb"]
    r.append("  moto rispetto al fondo cosmico   %.2f +/- %.2f km/s"
             % (ap["velocita_kms"], ap["errore_kms"]))
    r.append("  verso  AR %.3f  Dec %+.3f   (galattiche l=%.3f b=%.3f)"
             % (ap["equatoriali_ardec_deg"][0], ap["equatoriali_ardec_deg"][1],
                ap["galattiche_lb_deg"][0], ap["galattiche_lb_deg"][1]))
    if "visto_da_qui" in ap:
        v = ap["visto_da_qui"]
        r.append("  da dove sei: altezza %+.1f deg, azimut %.1f deg  (%s)"
                 % (v["altezza_deg"], v["azimut_deg"],
                    "sopra l'orizzonte" if v["sopra_orizzonte"] else "sotto l'orizzonte"))
    sg = p["sole_nella_galassia"]
    r.append("  Sole dal centro galattico  %.3f +/- %.3f kpc   [costante misurata da altri]"
             % (sg["distanza_centro_kpc"], sg["errore_kpc"]))
    if f.get("dal_precedente"):
        dp = f["dal_precedente"]
        r.append("")
        r.append("  dal fotogramma precedente (%.1f s): %.0f km percorsi rispetto al CMB"
                 % (dp["secondi"], dp["km"]))
    r.append("")
    if f.get("opera"):
        o = f["opera"]
        r.append("ANTERIORITA'  cosa viene datato da questo scatto")
        r.append("  autore   %s [%s]" % (o["autore"], o["identificativo"]))
        r.append("  diritti  %s" % o["diritti"])
        r.append("  commit   %s" % (o["commit"] or "(non in un repository git)"))
        r.append("  manifesto %s  (%s file)"
                 % ((o["manifesto_sha256"] or "assente")[:32], o["file_sorvegliati"]))
        r.append("  ^ questa chiave contiene l'impronta dell'opera E un round drand")
        r.append("    che nessuno puo' calcolare in anticipo: non e' retrodatabile,")
        r.append("    nemmeno dall'autore. Non e' un deposito legale.")
        r.append("")
    r.append("COSA DIMOSTRA   %s" % f["portata"]["dimostra"])
    r.append("COSA NON DIMOSTRA")
    r.append("   %s" % f["portata"]["non_dimostra"])
    return "\n".join(r)
