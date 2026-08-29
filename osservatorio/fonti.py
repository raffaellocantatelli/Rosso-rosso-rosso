#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Registro dichiarativo delle sorgenti — una riga per fonte, niente magia.

Il difetto che questo file esiste per non ripetere: in una dashboard OSINT
il numero e' la cosa piu' facile da mostrare e la piu' facile da falsificare.
Un layer scollegato produce 0. Una query con un tetto produce il tetto. In
entrambi i casi lo schermo mostra una cifra che sembra una misura e non lo e'.

Quindi qui ogni fonte dichiara, prima di essere interrogata:

  - se ha bisogno di una chiave, e quale variabile d'ambiente la porta;
  - ogni quanto si aggiorna DAVVERO a monte (cadenza_monte_s), che non e'
    ogni quanto la interroghiamo noi;
  - che pezzo di mondo copre (una fonte "solo USA" non puo' dire niente
    sul resto del pianeta, e non deve sembrare che lo faccia);
  - se e' implementata o solo dichiarata.

Il collettore non inventa mai uno zero: una fonte senza chiave vale None e
si presenta come SENZA_CHIAVE, mai come "nessun evento".

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import csv
import io
import json
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class Risultato:
    """Cio' che una fonte restituisce dopo essere stata letta."""
    conteggio: Optional[int] = None
    punti: List[dict] = field(default_factory=list)
    troncato: bool = False        # abbiamo toccato il tetto della query
    dettaglio: str = ""


@dataclass
class Fonte:
    id: str
    nome: str
    dominio: str
    url: str
    parser: Optional[Callable[[bytes], Risultato]]
    cadenza_s: int            # ogni quanto la interroghiamo noi
    cadenza_monte_s: int      # ogni quanto si aggiorna la sorgente
    copertura: str
    chiave_env: Optional[str] = None
    intestazioni: dict = field(default_factory=dict)
    nota: str = ""

    @property
    def implementata(self) -> bool:
        return self.parser is not None


# ---------------------------------------------------------------- parser

def _p_usgs(raw: bytes) -> Risultato:
    d = json.loads(raw)
    punti = []
    for f in d.get("features", []):
        c = (f.get("geometry") or {}).get("coordinates") or []
        p = f.get("properties") or {}
        if len(c) >= 2:
            punti.append({"lat": c[1], "lon": c[0], "peso": p.get("mag") or 0,
                          "etichetta": p.get("place") or "sisma"})
    return Risultato(conteggio=len(d.get("features", [])), punti=punti,
                     dettaglio="magnitudo qualsiasi, ultima ora")


def _p_emsc(raw: bytes) -> Risultato:
    d = json.loads(raw)
    feats = d.get("features", [])
    punti = []
    for f in feats:
        p = f.get("properties") or {}
        lat, lon = p.get("lat"), p.get("lon")
        if lat is None:
            c = (f.get("geometry") or {}).get("coordinates") or []
            if len(c) >= 2:
                lat, lon = c[1], c[0]
        if lat is not None:
            punti.append({"lat": lat, "lon": lon, "peso": p.get("mag") or 0,
                          "etichetta": p.get("flynn_region") or "sisma"})
    return Risultato(conteggio=len(feats), punti=punti, troncato=len(feats) >= 300,
                     dettaglio="rete europea, indipendente da USGS")


def _p_nws(raw: bytes) -> Risultato:
    d = json.loads(raw)
    return Risultato(conteggio=d.get("total"),
                     dettaglio="allerte in vigore: %s a terra, %s marittime"
                               % (d.get("land"), d.get("marine")))


def _p_gdacs(raw: bytes) -> Risultato:
    ns = {"geo": "http://www.w3.org/2003/01/geo/wgs84_pos#"}
    root = ET.fromstring(raw)
    punti, n = [], 0
    for item in root.iter("item"):
        n += 1
        lat = item.find("geo:lat", ns)
        lon = item.find("geo:long", ns)
        titolo = item.findtext("title") or "evento"
        if lat is not None and lon is not None:
            try:
                punti.append({"lat": float(lat.text), "lon": float(lon.text),
                              "peso": 3, "etichetta": titolo.strip()})
            except (TypeError, ValueError):
                pass
    return Risultato(conteggio=n, punti=punti, dettaglio="disastri in corso, Commissione UE")


def _p_swpc(raw: bytes) -> Risultato:
    d = json.loads(raw)
    return Risultato(conteggio=len(d), dettaglio="avvisi meteo spaziale NOAA")


def _p_ioda(raw: bytes) -> Risultato:
    d = json.loads(raw)
    voci = d.get("data", d if isinstance(d, list) else [])
    return Risultato(conteggio=len(voci), troncato=len(voci) >= 500,
                     dettaglio="segnalazioni di blackout di rete; il tetto della "
                               "query e' 500")


def _p_celestrak(raw: bytes) -> Risultato:
    d = json.loads(raw)
    return Risultato(conteggio=len(d), dettaglio="elementi orbitali, gruppo stazioni")


def _p_gdelt(raw: bytes) -> Risultato:
    d = json.loads(raw)
    art = d.get("articles", [])
    return Risultato(conteggio=len(art), troncato=len(art) >= 75,
                     dettaglio="articoli nell'ultima ora sulla query geopolitica")


def _p_firms(raw: bytes) -> Risultato:
    testo = raw.decode("utf-8", "replace")
    righe = list(csv.DictReader(io.StringIO(testo)))
    punti = []
    for r in righe[:400]:
        try:
            punti.append({"lat": float(r["latitude"]), "lon": float(r["longitude"]),
                          "peso": 2, "etichetta": "hotspot termico"})
        except (KeyError, TypeError, ValueError):
            pass
    return Risultato(conteggio=len(righe), punti=punti,
                     dettaglio="hotspot VIIRS ultime 24h; sulla mappa i primi 400")


def _p_opensky(raw: bytes) -> Risultato:
    d = json.loads(raw)
    stati = d.get("states") or []
    punti = []
    for s in stati[:600]:
        try:
            if s[5] is not None and s[6] is not None:
                punti.append({"lat": s[6], "lon": s[5], "peso": 1,
                              "etichetta": (s[1] or "").strip() or "aeromobile"})
        except (IndexError, TypeError):
            pass
    return Risultato(conteggio=len(stati), punti=punti,
                     dettaglio="stati ADS-B; sulla mappa i primi 600")


# ---------------------------------------------------------------- registro

_ORA = int(time.time())

FONTI: List[Fonte] = [
    Fonte(id="usgs", nome="Terremoti — USGS", dominio="sismico",
          url="https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
          parser=_p_usgs, cadenza_s=60, cadenza_monte_s=60, copertura="mondiale",
          nota="rete statunitense; e' una delle due sorgenti sismiche, non la sola"),

    Fonte(id="emsc", nome="Terremoti — EMSC", dominio="sismico",
          url="https://www.seismicportal.eu/fdsnws/event/1/query?format=json&limit=300&orderby=time",
          parser=_p_emsc, cadenza_s=120, cadenza_monte_s=60, copertura="mondiale",
          nota="rete europea, indipendente da USGS: due reti che vedono lo stesso "
               "sisma valgono come conferma incrociata, una sola no"),

    Fonte(id="nws", nome="Allerte meteo — NWS", dominio="meteo",
          url="https://api.weather.gov/alerts/active/count",
          parser=_p_nws, cadenza_s=120, cadenza_monte_s=60, copertura="SOLO USA",
          intestazioni={"Accept": "application/geo+json"},
          nota="copre solo gli Stati Uniti: non dice nulla sul resto del mondo"),

    Fonte(id="gdacs", nome="Disastri in corso — GDACS", dominio="disastri",
          url="https://www.gdacs.org/xml/rss.xml",
          parser=_p_gdacs, cadenza_s=300, cadenza_monte_s=900, copertura="mondiale",
          nota="Commissione Europea + UN OCHA"),

    Fonte(id="swpc", nome="Meteo spaziale — NOAA SWPC", dominio="spazio",
          url="https://services.swpc.noaa.gov/products/alerts.json",
          parser=_p_swpc, cadenza_s=300, cadenza_monte_s=300, copertura="mondiale"),

    Fonte(id="ioda", nome="Blackout di rete — IODA", dominio="rete",
          url="https://api.ioda.inetintel.cc.gatech.edu/v2/outages/alerts"
              "?from=%d&until=%d" % (_ORA - 86400, _ORA),
          parser=_p_ioda, cadenza_s=300, cadenza_monte_s=300, copertura="mondiale",
          nota="Georgia Tech; la finestra e' fissata all'avvio del programma"),

    Fonte(id="celestrak", nome="Oggetti in orbita — Celestrak", dominio="spazio",
          url="https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json",
          parser=_p_celestrak, cadenza_s=3600, cadenza_monte_s=43200, copertura="orbitale",
          nota="gruppo ristretto: contare 'tutti gli oggetti attivi' qui sarebbe "
               "un numero grande e inutile"),

    Fonte(id="gdelt", nome="Notizie geopolitiche — GDELT", dominio="geopolitico",
          url="https://api.gdeltproject.org/api/v2/doc/doc?query=(conflict%20OR%20ceasefire%20"
              "OR%20sanctions%20OR%20airstrike)&mode=artlist&maxrecords=75&format=json&timespan=1h",
          parser=_p_gdelt, cadenza_s=300, cadenza_monte_s=900, copertura="mondiale",
          nota="il tetto e' 75: se il conteggio arriva a 75 il dato e' troncato, "
               "non e' 'settantacinque notizie'"),

    # --- sorgenti che richiedono una chiave: senza, restano dichiaratamente spente
    Fonte(id="firms", nome="Incendi — NASA FIRMS", dominio="fuoco",
          url="https://firms.modaps.eosdis.nasa.gov/api/area/csv/{CHIAVE}/VIIRS_SNPP_NRT/world/1",
          parser=_p_firms, cadenza_s=900, cadenza_monte_s=10800, copertura="mondiale",
          chiave_env="FIRMS_MAP_KEY",
          nota="chiave gratuita su firms.modaps.eosdis.nasa.gov/api/area — "
               "e' la fonte che nel reel mostrava 5000 'al cap'"),

    Fonte(id="opensky", nome="Traffico aereo — OpenSky", dominio="aria",
          url="https://opensky-network.org/api/states/all",
          parser=_p_opensky, cadenza_s=120, cadenza_monte_s=10, copertura="mondiale",
          chiave_env="OPENSKY_TOKEN",
          nota="serve un token OAuth: l'accesso anonimo e' stretto a poche "
               "richieste e non regge una dashboard"),

    # --- dichiarate e NON implementate: compaiono per non fingere di coprirle
    Fonte(id="ais", nome="Traffico marittimo — AIS", dominio="mare",
          url="wss://stream.aisstream.io/v0/stream", parser=None,
          cadenza_s=0, cadenza_monte_s=1, copertura="mondiale",
          chiave_env="AISSTREAM_KEY",
          nota="richiede un websocket persistente: dichiarata, non implementata"),

    Fonte(id="cfradar", nome="Salute della rete — Cloudflare Radar", dominio="rete",
          url="https://api.cloudflare.com/client/v4/radar/annotations/outages", parser=None,
          cadenza_s=0, cadenza_monte_s=3600, copertura="mondiale",
          chiave_env="CF_API_TOKEN",
          nota="dichiarata, non implementata"),
]

PER_ID = {f.id: f for f in FONTI}
