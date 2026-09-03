# -*- coding: utf-8 -*-
"""Le sorgenti pubbliche di Sentinella, e l'inviluppo che le confeziona.

Il contratto delle risposte e' quello di UmbraTheater, ripreso deliberatamente:
fuori da `ok` i conteggi sono `null` e mai `0`, perche' «nessun dato» e
«nessun evento» sono cose diverse. Su una mappa di allerta la differenza non e'
un dettaglio di stile: uno zero al posto di un trattino significa «il cielo e'
tranquillo» quando la verita' e' «non lo sappiamo».

Solo libreria standard: nessun pip, nessuna chiave, nessun account.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
from __future__ import annotations

import json
import os
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

AGENTE = "Sentinella/1.0 (dashboard OSINT self-hosted; solo feed pubblici)"

OK = "ok"
ERRORE = "errore"

# Tetti di trasporto. Ogni tetto e' dichiarato nella risposta: un conteggio
# tagliato non deve mai sembrare una misura.
TETTO_SISMI = 250
TETTO_BOLIDI = 50
TETTO_PASSAGGI = 60
TETTO_METEO = 40

UNITA_ASTRONOMICA_KM = 149_597_870.7
DISTANZA_LUNARE_AU = 0.002569555  # 1 LD in unita' astronomiche

SORGENTI = {
    "sismi": {
        "name": "USGS Earthquake Hazards Program",
        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
        "coverage": "magnitudo >= 2.5, ultime 24 h, mondiale",
    },
    "passaggi": {
        "name": "NASA/JPL CNEOS — Close Approach Data",
        "url": "https://ssd-api.jpl.nasa.gov/cad.api",
        "coverage": "oggetti noti entro 20 distanze lunari, prossimi 365 giorni",
    },
    "bolidi": {
        "name": "NASA/JPL CNEOS — Fireballs",
        "url": "https://ssd-api.jpl.nasa.gov/fireball.api",
        "coverage": "bolidi rilevati da sensori governativi, con posizione nota",
    },
    "meteo_spaziale": {
        "name": "NOAA SWPC — Space Weather Alerts",
        "url": "https://services.swpc.noaa.gov/products/alerts.json",
        "coverage": "allerte, avvisi e watch emessi dal centro NOAA, ultimi giorni",
    },
    "geomagnetismo": {
        "name": "NOAA SWPC — Planetary K-index",
        "url": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
        "coverage": "indice Kp planetario stimato, cadenza tre ore",
    },
}


def adesso_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def inviluppo(chiave, *, items=None, total=None, cap=None, status=OK, error=None, **extra):
    """Il contratto unico, applicato in un posto solo.

    Quando `status` non e' `ok`, `total` e `returned` sono **null**, mai 0.
    """
    fonte = SORGENTI[chiave]
    lista = items if items is not None else []
    if status == OK:
        returned = len(lista)
        totale = total if total is not None else returned
        troncato = totale is not None and returned < totale
    else:
        returned = None
        totale = None
        troncato = False
    return {
        "updated": adesso_iso(),
        "source": dict(fonte),
        "status": status,
        "total": totale,
        "returned": returned,
        "cap": cap,
        "truncated": troncato,
        "error": error,
        "items": lista,
        **extra,
    }


class Cache:
    """Cache a scadenza, con memoria dell'ultimo buon risultato.

    Se la sorgente cade, la voce scaduta resta disponibile come `raffreddata`:
    un dato vecchio dichiarato tale e' utile, un dato vecchio spacciato per
    fresco no. Chi legge riceve sempre l'eta' del dato.
    """

    def __init__(self):
        self._dati = {}
        self._lucchetto = threading.Lock()

    def leggi(self, chiave):
        with self._lucchetto:
            voce = self._dati.get(chiave)
        if not voce:
            return None, None
        scade, valore, nato = voce
        return (valore if scade > time.time() else None), nato

    def ultimo(self, chiave):
        with self._lucchetto:
            voce = self._dati.get(chiave)
        return (voce[1], voce[2]) if voce else (None, None)

    def scrivi(self, chiave, valore, ttl):
        with self._lucchetto:
            self._dati[chiave] = (time.time() + ttl, valore, time.time())


cache = Cache()


def _contesto_ssl():
    ca = os.environ.get("SENTINELLA_CA") or os.environ.get("SSL_CERT_FILE")
    if ca and os.path.exists(ca):
        return ssl.create_default_context(cafile=ca)
    return ssl.create_default_context()


def scarica(url, parametri=None, timeout=30):
    if parametri:
        url = url + "?" + urllib.parse.urlencode(parametri)
    richiesta = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": "application/json"})
    with urllib.request.urlopen(richiesta, timeout=timeout, context=_contesto_ssl()) as risposta:
        return json.loads(risposta.read().decode("utf-8", "replace"))


def _tabella(payload):
    """Le API CNEOS rispondono a colonne: nomi in `fields`, righe in `data`."""
    campi = payload.get("fields") or []
    righe = payload.get("data") or []
    return [dict(zip(campi, riga)) for riga in righe]


def _numero(valore):
    try:
        return float(valore)
    except (TypeError, ValueError):
        return None


# ── le quattro finestre sul cielo, piu' il suolo ────────────────────────────

def sismi(ttl=60):
    chiave = "sismi"
    valido, _ = cache.leggi(chiave)
    if valido:
        return valido
    try:
        grezzo = scarica(SORGENTI[chiave]["url"])
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return _caduta(chiave, exc, ttl=20)
    tutte = grezzo.get("features") or []
    items = []
    for f in tutte[:TETTO_SISMI]:
        p = f.get("properties") or {}
        c = (f.get("geometry") or {}).get("coordinates") or [None, None, None]
        items.append({
            "id": f.get("id"),
            "mag": p.get("mag"),
            "place": p.get("place"),
            "time": p.get("time"),
            "url": p.get("url"),
            "alert": p.get("alert"),      # livello PAGER dichiarato da USGS, quando c'e'
            "tsunami": p.get("tsunami"),
            "sig": p.get("sig"),
            "lon": c[0], "lat": c[1], "depth_km": c[2],
        })
    esito = inviluppo(chiave, items=items, total=len(tutte), cap=TETTO_SISMI)
    cache.scrivi(chiave, esito, ttl)
    return esito


def passaggi(ttl=1800):
    """Passaggi ravvicinati di oggetti noti. Sono effemeridi pubblicate, non previsioni nostre."""
    chiave = "passaggi"
    valido, _ = cache.leggi(chiave)
    if valido:
        return valido
    try:
        grezzo = scarica(SORGENTI[chiave]["url"], {
            "dist-max": "20LD", "date-min": "now", "date-max": "+365", "sort": "dist",
        })
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return _caduta(chiave, exc, ttl=60)
    righe = _tabella(grezzo)
    items = []
    for r in righe[:TETTO_PASSAGGI]:
        dist = _numero(r.get("dist"))
        items.append({
            "designazione": r.get("des"),
            "quando_utc": r.get("cd"),
            "dist_au": dist,
            "dist_ld": round(dist / DISTANZA_LUNARE_AU, 3) if dist is not None else None,
            "dist_km": round(dist * UNITA_ASTRONOMICA_KM) if dist is not None else None,
            "dist_min_au": _numero(r.get("dist_min")),
            "dist_max_au": _numero(r.get("dist_max")),
            "v_rel_kms": _numero(r.get("v_rel")),
            "h": _numero(r.get("h")),                 # magnitudine assoluta
            "sigma_tempo": r.get("t_sigma_f"),        # incertezza sull'istante del passaggio
        })
    esito = inviluppo(chiave, items=items, total=int(grezzo.get("count") or len(righe)), cap=TETTO_PASSAGGI)
    cache.scrivi(chiave, esito, ttl)
    return esito


def bolidi(ttl=1800):
    """Bolidi gia' avvenuti. Non anticipano niente: misurano quanto spesso accade."""
    chiave = "bolidi"
    valido, _ = cache.leggi(chiave)
    if valido:
        return valido
    try:
        grezzo = scarica(SORGENTI[chiave]["url"], {
            "limit": str(TETTO_BOLIDI), "sort": "-date", "req-loc": "true",
        })
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return _caduta(chiave, exc, ttl=60)
    items = []
    for r in _tabella(grezzo):
        lat, lon = _numero(r.get("lat")), _numero(r.get("lon"))
        if lat is None or lon is None:
            continue
        if (r.get("lat-dir") or "N").upper() == "S":
            lat = -lat
        if (r.get("lon-dir") or "E").upper() == "W":
            lon = -lon
        items.append({
            "quando_utc": r.get("date"),
            "lat": lat, "lon": lon,
            "energia_kt": _numero(r.get("impact-e")),      # energia d'impatto, kilotoni di TNT
            "radiata_j": _numero(r.get("energy")),
            "quota_km": _numero(r.get("alt")),
            "velocita_kms": _numero(r.get("vel")),
        })
    esito = inviluppo(chiave, items=items, total=int(grezzo.get("count") or len(items)), cap=TETTO_BOLIDI)
    cache.scrivi(chiave, esito, ttl)
    return esito


def meteo_spaziale(ttl=600):
    chiave = "meteo_spaziale"
    valido, _ = cache.leggi(chiave)
    if valido:
        return valido
    try:
        grezzo = scarica(SORGENTI[chiave]["url"])
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return _caduta(chiave, exc, ttl=60)
    voci = grezzo if isinstance(grezzo, list) else []
    items = [{
        "product_id": v.get("product_id"),
        "emesso_utc": v.get("issue_datetime"),
        "messaggio": v.get("message") or "",
    } for v in voci[:TETTO_METEO]]
    esito = inviluppo(chiave, items=items, total=len(voci), cap=TETTO_METEO)
    cache.scrivi(chiave, esito, ttl)
    return esito


def geomagnetismo(ttl=600):
    chiave = "geomagnetismo"
    valido, _ = cache.leggi(chiave)
    if valido:
        return valido
    try:
        grezzo = scarica(SORGENTI[chiave]["url"])
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return _caduta(chiave, exc, ttl=60)
    serie = []
    for v in (grezzo if isinstance(grezzo, list) else []):
        if isinstance(v, dict):
            kp = _numero(v.get("Kp") if "Kp" in v else v.get("kp_index"))
            quando = v.get("time_tag")
        elif isinstance(v, list) and len(v) >= 2:
            kp, quando = _numero(v[1]), v[0]
        else:
            continue
        if kp is None or not quando:
            continue
        serie.append({"quando_utc": quando, "kp": kp})
    esito = inviluppo(chiave, items=serie, total=len(serie), cap=None)
    cache.scrivi(chiave, esito, ttl)
    return esito


def _caduta(chiave, exc, ttl):
    """Una sorgente caduta. Se ne abbiamo una copia vecchia la restituiamo, dichiarandone l'eta'."""
    motivo = f"{SORGENTI[chiave]['name']} non raggiungibile: {exc.__class__.__name__}"
    vecchio, nato = cache.ultimo(chiave)
    if vecchio and vecchio.get("status") == OK:
        raffreddato = dict(vecchio)
        raffreddato["raffreddata"] = True
        raffreddato["eta_secondi"] = int(time.time() - nato) if nato else None
        raffreddato["error"] = motivo + " — mostro l'ultima lettura riuscita"
        return raffreddato
    return inviluppo(chiave, status=ERRORE, error=motivo)
