#!/usr/bin/env python3
"""occhio.luogo — dove si trova un oggetto, e quanto vale davvero saperlo.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Ci sono due modi di rispondere a «dov'e' questo DVD», e uno dei due e' una
trappola.

**Il modo che sembra tecnologico e non funziona.** Prendere la posizione GPS
scritta nella fotografia. Dentro casa il telefono non vede i satelliti: fonde
Wi-Fi e celle, e restituisce una posizione con un errore che di solito e' piu'
grande della casa intera. Salotto e camera da letto cadono dentro lo stesso
cerchio. Una mappa costruita cosi' **sembra un dato misurato ed e' rumore**:
e' il difetto di CLAUDE.md §4 con un'interfaccia bellissima.

Non lo dico per averlo letto. Le fotografie dell'iPhone scrivono un campo
apposta — `GPSHPositioningError`, tag 0x001F — in cui **il telefono dichiara
da solo di quanto puo' sbagliare.** Questo modulo lo legge, e
`falsificatori/h7_gps_stanze.py` confronta quell'errore con la distanza fra
le stanze usando le TUE fotografie. Se l'errore e' piu' grande della distanza,
H7 cade e la mappa GPS va buttata. Il numero e' tuo, non mio.

**Il modo che funziona ed e' banale.** La stanza la dichiari tu, una volta,
e vale finche' non la cambi. Zero sensori, zero errore. L'informazione di
posizione che serve davvero — «salotto, libreria grande, terzo ripiano» — e'
un bit di input umano, non una misura.

Qui la gerarchia si legge dal percorso delle cartelle, che e' la cosa piu'
vicina a nessuna interfaccia:

    foto/salotto/libreria-grande/ripiano-3/IMG_0021.jpg
        -> stanza=salotto, mobile=libreria-grande, ripiano=ripiano-3

Il GPS resta letto e conservato, con il suo errore accanto, perche' per le
fotografie scattate FUORI (un magazzino, una cantina, un sopralluogo) e'
davvero utile. Non viene mai usato per dedurre una stanza.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

# --------------------------------------------------------------------------
# EXIF senza dipendenze
# --------------------------------------------------------------------------
# analisi_foto.py legge gli EXIF con Pillow, che qui non e' installato
# (verificato il 03/09). Invece di aggiungere una dipendenza per quattro campi,
# si legge il file: un JPEG e' una catena di segmenti, e l'EXIF sta in APP1.

_TIPI = {1: ("B", 1), 2: ("s", 1), 3: ("H", 2), 4: ("I", 4), 5: ("II", 8),
         7: ("B", 1), 9: ("i", 4), 10: ("ii", 8)}

TAG_MAKE, TAG_MODEL, TAG_DATETIME = 0x010F, 0x0110, 0x0132
TAG_EXIF_IFD, TAG_GPS_IFD = 0x8769, 0x8825
TAG_DATETIME_ORIGINAL = 0x9003
#: Il telefono dichiara qui, in metri, di quanto puo' sbagliare la posizione.
TAG_GPS_ERRORE = 0x001F


def _leggi_ifd(dati: bytes, base: int, offset: int, ordine: str) -> dict:
    """Legge una directory EXIF. Ogni voce e' 12 byte; oltre 4 byte si punta."""
    voci = {}
    if offset + 2 > len(dati):
        return voci
    (n,) = struct.unpack_from(ordine + "H", dati, offset)
    if n > 512:  # un IFD sano non ha centinaia di voci: file corrotto
        return voci
    for i in range(n):
        p = offset + 2 + i * 12
        if p + 12 > len(dati):
            break
        tag, tipo, conteggio = struct.unpack_from(ordine + "HHI", dati, p)
        if tipo not in _TIPI:
            continue
        fmt, dim = _TIPI[tipo]
        totale = dim * conteggio
        if totale > 4:
            (puntatore,) = struct.unpack_from(ordine + "I", dati, p + 8)
            inizio = base + puntatore
        else:
            inizio = p + 8
        if inizio < 0 or inizio + totale > len(dati):
            continue
        grezzo = dati[inizio:inizio + totale]
        if tipo == 2:
            voci[tag] = grezzo.split(b"\x00")[0].decode("utf-8", "replace")
        elif tipo in (5, 10):
            valori = []
            for k in range(conteggio):
                num, den = struct.unpack_from(ordine + ("II" if tipo == 5 else "ii"),
                                              grezzo, k * 8)
                valori.append(num / den if den else 0.0)
            voci[tag] = valori if conteggio > 1 else valori[0]
        elif tipo in (3, 4, 9, 1, 7):
            f = {3: "H", 4: "I", 9: "i", 1: "B", 7: "B"}[tipo]
            valori = list(struct.unpack_from(ordine + f * conteggio, grezzo, 0))
            voci[tag] = valori if conteggio > 1 else valori[0]
    return voci


def _gradi(valore, riferimento):
    """Da (gradi, primi, secondi) + N/S/E/W a un numero decimale."""
    if not isinstance(valore, list) or len(valore) < 3:
        return None
    g, m, s = valore[:3]
    d = g + m / 60 + s / 3600
    return -d if str(riferimento).upper() in ("S", "W") else d


def exif(percorso: Path | str) -> dict:
    """Cio' che la fotografia dichiara di se'. I campi assenti sono None.

    Un campo assente resta None e non viene mai riempito con una stima: una
    data inventata in un inventario e' peggio di una data mancante, perche'
    nessuno la mettera' piu' in dubbio.
    """
    vuoto = {"fotocamera": None, "scattata": None, "gps": None,
             "errore_gps_m": None, "exif_presente": False}
    try:
        dati = Path(percorso).read_bytes()
    except OSError:
        return vuoto
    if not dati.startswith(b"\xff\xd8"):
        return vuoto

    # cerca il segmento APP1 che comincia con "Exif\0\0"
    i, app1 = 2, None
    while i + 4 <= len(dati):
        if dati[i] != 0xFF:
            break
        marcatore = dati[i + 1]
        if marcatore in (0xD8, 0xD9) or 0xD0 <= marcatore <= 0xD7:
            i += 2
            continue
        (lunghezza,) = struct.unpack_from(">H", dati, i + 2)
        corpo = dati[i + 4: i + 2 + lunghezza]
        if marcatore == 0xE1 and corpo.startswith(b"Exif\x00\x00"):
            app1 = corpo[6:]
            break
        if marcatore == 0xDA:  # inizio dei dati compressi: l'EXIF non c'e'
            break
        i += 2 + lunghezza
    if not app1 or len(app1) < 8:
        return vuoto

    ordine = "<" if app1[:2] == b"II" else ">" if app1[:2] == b"MM" else None
    if ordine is None:
        return vuoto
    (offset0,) = struct.unpack_from(ordine + "I", app1, 4)
    ifd0 = _leggi_ifd(app1, 0, offset0, ordine)

    fuori = dict(vuoto, exif_presente=True)
    marca = str(ifd0.get(TAG_MAKE, "")).strip()
    modello = str(ifd0.get(TAG_MODEL, "")).strip()
    fuori["fotocamera"] = (marca + " " + modello).strip() or None
    fuori["scattata"] = ifd0.get(TAG_DATETIME) or None

    if TAG_EXIF_IFD in ifd0:
        sub = _leggi_ifd(app1, 0, ifd0[TAG_EXIF_IFD], ordine)
        fuori["scattata"] = sub.get(TAG_DATETIME_ORIGINAL) or fuori["scattata"]

    if TAG_GPS_IFD in ifd0:
        g = _leggi_ifd(app1, 0, ifd0[TAG_GPS_IFD], ordine)
        lat = _gradi(g.get(2), g.get(1))
        lon = _gradi(g.get(4), g.get(3))
        if lat is not None and lon is not None:
            fuori["gps"] = {"lat": round(lat, 7), "lon": round(lon, 7)}
        err = g.get(TAG_GPS_ERRORE)
        if isinstance(err, (int, float)):
            fuori["errore_gps_m"] = round(float(err), 1)
    return fuori


# --------------------------------------------------------------------------
# distanza fra due posizioni
# --------------------------------------------------------------------------

def distanza_m(a: dict, b: dict) -> float:
    """Metri fra due coordinate. Serve a confrontarli con l'errore dichiarato."""
    R = 6371000.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp = p2 - p1
    dl = math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


# --------------------------------------------------------------------------
# la gerarchia dichiarata, che e' la parte che funziona
# --------------------------------------------------------------------------

LIVELLI = ("stanza", "mobile", "ripiano")


def dal_percorso(percorso: Path | str, radice: Path | str) -> dict:
    """Legge stanza/mobile/ripiano dalle cartelle sopra la fotografia.

    Piu' di tre livelli: i primi tre contano, il resto finisce in `dettaglio`,
    perche' e' meglio conservare quello che qualcuno ha scritto che buttarlo
    via per far tornare uno schema.
    """
    p, r = Path(percorso).resolve(), Path(radice).resolve()
    try:
        parti = list(p.relative_to(r).parts[:-1])
    except ValueError:
        parti = []
    luogo = {n: (parti[i] if i < len(parti) else None) for i, n in enumerate(LIVELLI)}
    luogo["dettaglio"] = "/".join(parti[len(LIVELLI):]) or None
    luogo["percorso"] = "/".join(parti) or None
    return luogo


def etichetta(luogo: dict) -> str:
    """«salotto › libreria-grande › ripiano-3», o «(non dichiarato)»."""
    pezzi = [luogo.get(n) for n in LIVELLI if luogo.get(n)]
    if luogo.get("dettaglio"):
        pezzi.append(luogo["dettaglio"])
    return " › ".join(pezzi) if pezzi else "(non dichiarato)"
