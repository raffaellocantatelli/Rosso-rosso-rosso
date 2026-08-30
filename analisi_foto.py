#!/usr/bin/env python3
"""analisi_foto.py — analisi locale di una fotografia e preparazione della ricerca inversa.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Questo modulo esiste perche' l'archivio del progetto contiene fotografie su carta,
fotografate con il telefono. Su un'immagine cosi' ci sono due oggetti diversi:
la STAMPA (l'oggetto fisico, con il suo bordo e la sua epoca) e la RIPRESA
(lo scatto del telefono, con i suoi metadati). Vanno misurati separatamente.

Cosa fa davvero, tutto rieseguibile e verificabile:
  - legge i metadati EXIF reali (data, fotocamera, GPS) e dichiara UNKNOWN
    quando mancano, senza inventarli;
  - calcola impronte: sha256 (identita' del file) e dhash/ahash percettivi
    (identita' dell'immagine, sopravvive a ricompressione e ridimensionamento);
  - misura nitidezza, esposizione e dominante di colore;
  - individua il rettangolo della stampa dentro la foto del telefono e lo
    ritaglia raddrizzato, se glielo chiedi;
  - costruisce un indice dell'archivio e trova doppioni e quasi-doppioni;
  - prepara la ricerca inversa: esegue la chiamata SOLO se trova una chiave API
    nell'ambiente, altrimenti lo scrive a chiare lettere e ti da' i link da
    aprire a mano.

Cosa NON fa, per scelta:
  - non riconosce volti e non tenta di identificare persone;
  - non dichiara di aver cercato online se non ha cercato. Se manca la chiave,
    il campo eseguita resta False. Un risultato assente non diventa mai un
    risultato negativo.

Dipendenza: Pillow (pip install Pillow). requests solo per la ricerca inversa.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
from pathlib import Path

try:
    from PIL import Image, ImageFilter, ImageOps, ImageStat
    from PIL.ExifTags import GPSTAGS, TAGS
except ImportError:  # pragma: no cover - dipendenza esterna
    sys.stderr.write("Serve Pillow: pip install Pillow\n")
    raise

ESTENSIONI = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp", ".bmp"}


# --------------------------------------------------------------------------
# impronte
# --------------------------------------------------------------------------

def sha256(percorso: Path) -> str:
    """Identita' del file: cambia se cambia anche un solo byte."""
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        for blocco in iter(lambda: f.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def _griglia(img: Image.Image, larghezza: int, altezza: int) -> list[int]:
    piccola = img.convert("L").resize((larghezza, altezza), Image.Resampling.LANCZOS)
    return list(piccola.tobytes())


def dhash(img: Image.Image, lato: int = 8) -> str:
    """Impronta percettiva su gradienti orizzontali (64 bit).

    Sopravvive a ricompressione, ridimensionamento e piccoli ritocchi: due file
    diversi con la stessa immagine danno impronte a distanza piccola.
    """
    px = _griglia(img, lato + 1, lato)
    bit = 0
    for r in range(lato):
        for c in range(lato):
            i = r * (lato + 1) + c
            bit = (bit << 1) | int(px[i] > px[i + 1])
    return f"{bit:0{lato * lato // 4}x}"


def ahash(img: Image.Image, lato: int = 8) -> str:
    """Impronta percettiva sulla media: piu' grossolana di dhash, sbaglia diverso."""
    px = _griglia(img, lato, lato)
    media = sum(px) / len(px)
    bit = 0
    for v in px:
        bit = (bit << 1) | int(v > media)
    return f"{bit:0{lato * lato // 4}x}"


def distanza(a: str, b: str) -> int:
    """Distanza di Hamming fra due impronte esadecimali."""
    return bin(int(a, 16) ^ int(b, 16)).count("1")


# --------------------------------------------------------------------------
# metadati
# --------------------------------------------------------------------------

def _pulisci(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace").strip("\x00").strip() or None
    if isinstance(v, tuple) and len(v) == 2 and all(isinstance(x, int) for x in v):
        return v[0] / v[1] if v[1] else None
    return v


def _creator_tool(xmp) -> str | None:
    """Legge xmp:CreatorTool, il programma che ha scritto il file per ultimo."""
    if not xmp:
        return None
    testo = xmp.decode("utf-8", "replace") if isinstance(xmp, bytes) else xmp
    marcatore = 'xmp:CreatorTool="'
    i = testo.find(marcatore)
    if i < 0:
        return None
    fine = testo.find('"', i + len(marcatore))
    return testo[i + len(marcatore):fine] if fine > 0 else None


def _gradi(valore, riferimento) -> float | None:
    try:
        g, m, s = (float(x) for x in valore)
    except (TypeError, ValueError):
        return None
    dec = g + m / 60 + s / 3600
    return -dec if riferimento in ("S", "W") else dec


def metadati(percorso: Path) -> dict:
    """EXIF realmente presenti. Le chiavi assenti restano assenti: non si inventano."""
    with Image.open(percorso) as img:
        exif = img.getexif()
        larghezza, altezza = img.size
        formato = img.format
        xmp = img.info.get("xmp") or b""

    campi: dict = {}
    for tag, valore in exif.items():
        campi[TAGS.get(tag, str(tag))] = _pulisci(valore)
    for tag, valore in exif.get_ifd(0x8769).items():
        campi[TAGS.get(tag, str(tag))] = _pulisci(valore)

    gps_raw = exif.get_ifd(0x8825)
    gps = {}
    if gps_raw:
        letto = {GPSTAGS.get(t, str(t)): v for t, v in gps_raw.items()}
        lat = _gradi(letto.get("GPSLatitude"), letto.get("GPSLatitudeRef"))
        lon = _gradi(letto.get("GPSLongitude"), letto.get("GPSLongitudeRef"))
        if lat is not None and lon is not None:
            gps = {"lat": round(lat, 6), "lon": round(lon, 6),
                   "mappa": f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map=17"}

    out = {
        "formato": formato,
        "pixel": [larghezza, altezza],
        "megapixel": round(larghezza * altezza / 1e6, 1),
        "orientamento_exif": exif.get(274),
        "fotocamera": " ".join(x for x in (campi.get("Make"), campi.get("Model")) if x) or None,
        "software": campi.get("Software"),
        "data_scatto": campi.get("DateTimeOriginal") or campi.get("DateTime"),
        "gps": gps or None,
        # Identificativo scritto dalla fotocamera o dal programma di gestione:
        # sopravvive al riesporto e lega fra loro copie diverse dello stesso
        # scatto anche quando le impronte percettive non bastano piu'.
        "id_immagine": campi.get("ImageUniqueID"),
        "programma_xmp": _creator_tool(xmp),
    }
    out["mancanti"] = [k for k in ("fotocamera", "data_scatto", "gps") if not out[k]]
    out["exif_completo"] = {k: v for k, v in sorted(campi.items()) if v is not None}
    return out


def miniatura_exif(percorso: Path, immagine: Image.Image) -> dict | None:
    """Estrae la miniatura nascosta nell'EXIF e la confronta con l'immagine vera.

    Quasi ogni fotocamera scrive nell'EXIF una miniatura dello scatto. Molti
    programmi che ritagliano o ritoccano l'immagine NON la riscrivono: resta
    li' la versione precedente. Se miniatura e immagine non combaciano, il
    file e' stato modificato dopo lo scatto, e la miniatura mostra il prima.

    Un riscontro positivo (miniatura diversa) e' una prova. Un riscontro
    negativo non lo e': significa solo che chi ha modificato il file ha
    riscritto anche la miniatura, o che non c'e' stata modifica.
    """
    blob = immagine.info.get("exif")
    if not blob:
        return None
    inizio = blob.find(b"\xff\xd8\xff", 100)
    if inizio < 0:
        return None
    fine = blob.find(b"\xff\xd9", inizio)
    if fine < 0:
        return None

    import io
    try:
        with Image.open(io.BytesIO(blob[inizio:fine + 2])) as mini:
            mini.load()
            lati_m = mini.size
            impronta = dhash(mini)
    except Exception:
        return None

    lati_i = immagine.size
    scarto = distanza(impronta, dhash(immagine))
    return {
        "presente": True,
        "pixel": list(lati_m),
        "byte": fine + 2 - inizio,
        "proporzioni": round(max(lati_m) / min(lati_m), 3),
        "proporzioni_immagine": round(max(lati_i) / min(lati_i), 3),
        "dhash": impronta,
        "distanza_dall_immagine": scarto,
        # soglia larga: la miniatura e' minuscola e molto compressa, quindi
        # anche una miniatura fedele non da' mai distanza zero.
        "coerente": scarto <= 16 and abs(max(lati_m) / min(lati_m) - max(lati_i) / min(lati_i)) < 0.05,
    }


# --------------------------------------------------------------------------
# misure sull'immagine
# --------------------------------------------------------------------------

def misure(img: Image.Image) -> dict:
    """Nitidezza, esposizione e dominante. Numeri, non aggettivi."""
    lavoro = img.copy()
    lavoro.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

    grigio = lavoro.convert("L")
    bordi = ImageStat.Stat(grigio.filter(ImageFilter.FIND_EDGES))
    isto = grigio.histogram()
    totale = sum(isto) or 1

    r, g, b = ImageStat.Stat(lavoro.convert("RGB")).mean
    grigio_medio = (r + g + b) / 3 or 1

    return {
        "nitidezza": round(bordi.stddev[0], 2),
        "ombre_pct": round(100 * sum(isto[:40]) / totale, 1),
        "medi_pct": round(100 * sum(isto[40:180]) / totale, 1),
        "alte_pct": round(100 * sum(isto[180:]) / totale, 1),
        "rgb_medio": [round(r, 1), round(g, 1), round(b, 1)],
        "dominante": {
            "rosso": round(r / grigio_medio, 3),
            "verde": round(g / grigio_medio, 3),
            "blu": round(b / grigio_medio, 3),
        },
    }


def rileva_stampa(img: Image.Image, soglia: int = 90, copertura: float = 0.5) -> dict | None:
    """Trova il rettangolo dell'area stampata dentro la foto di una foto.

    Metodo: proiezioni per righe e colonne dei pixel scuri. L'area stampata di
    una fotografia su carta e' quasi sempre piu' scura del margine bianco e del
    piano d'appoggio; le righe con molti pixel scuri delimitano la stampa.

    Il rettangolo restituito e' INFERITO, non misurato: e' la regione scura
    dominante, che coincide con la stampa solo se la stampa e' scura. Su una
    stampa chiara (cielo, neve, fondo bianco) il metodo restituisce None
    invece di tirare a indovinare, e su una stampa a contrasto misto puo'
    restituire solo la parte scura. Guarda sempre il ritaglio prima di fidarti.
    """
    piccola = img.convert("L")
    piccola.thumbnail((800, 800), Image.Resampling.LANCZOS)
    w, h = piccola.size
    px = piccola.tobytes()

    righe = [sum(1 for c in range(w) if px[r * w + c] < soglia) / w for r in range(h)]
    colonne = [sum(1 for r in range(h) if px[r * w + c] < soglia) / h for c in range(w)]

    def banda(proiezione: list[float]) -> tuple[int, int] | None:
        # Soglia relativa al picco: una stampa che occupa meta' inquadratura
        # non raggiungerebbe mai una soglia assoluta alta, e verrebbe persa.
        limite = max(0.15, copertura * max(proiezione))
        migliore = attuale = None
        for i, v in enumerate(proiezione):
            if v >= limite:
                attuale = (i, i) if attuale is None else (attuale[0], i)
            else:
                if attuale and (migliore is None or attuale[1] - attuale[0] > migliore[1] - migliore[0]):
                    migliore = attuale
                attuale = None
        if attuale and (migliore is None or attuale[1] - attuale[0] > migliore[1] - migliore[0]):
            migliore = attuale
        return migliore

    v = banda(righe)
    o = banda(colonne)
    if not v or not o:
        return None

    sx = img.size[0] / w
    sy = img.size[1] / h
    box = [int(o[0] * sx), int(v[0] * sy), int((o[1] + 1) * sx), int((v[1] + 1) * sy)]
    area = (box[2] - box[0]) * (box[3] - box[1])
    if area < 0.12 * img.size[0] * img.size[1]:
        return None

    lati = (box[2] - box[0], box[3] - box[1])
    return {
        "box": box,
        "frazione_inquadratura": round(area / (img.size[0] * img.size[1]), 3),
        "proporzioni": round(max(lati) / min(lati), 3),
    }


# --------------------------------------------------------------------------
# formato della stampa istantanea
# --------------------------------------------------------------------------

# I millimetri qui sotto vengono dalla mia memoria, non da una fonte letta in
# questa sessione: sono IPOTESI, e vanno controllati una volta su una scheda
# tecnica Polaroid prima di fidarsene. Il CODICE invece non si fonda su di
# essi: classifica sulla GEOMETRIA DEI BORDI, che e' misurata sui pixel e non
# richiede di conoscere le dimensioni in millimetri.
FORMATI = {
    "integrale_quadrata": {
        "descrizione": "Polaroid integrale a immagine quadrata (famiglia SX-70 / 600 / i-Type)",
        "mm_da_verificare": "stampa 88x107, immagine 79x79",
        "epoca": "SX-70 dal 1972, 600 dal 1981, i-Type dal 2017. "
                 "La geometria e' identica fra le tre: da sola NON distingue il decennio.",
    },
    "integrale_rettangolare": {
        "descrizione": "Polaroid integrale a immagine rettangolare (famiglia Spectra / Image)",
        "mm_da_verificare": "stampa 101x108, immagine 91x73",
        "epoca": "dal 1986.",
    },
    "bordi_uniformi": {
        "descrizione": "quattro bordi simili: pellicola a strappo (Type 100/660) "
                       "oppure una normale stampa da laboratorio con bordo",
        "mm_da_verificare": "Type 100: immagine circa 73x95",
        "epoca": "Type 100 dal 1963, fuori produzione dal 2016. "
                 "Una stampa da laboratorio con bordo non e' databile dalla forma.",
    },
}


def _maschera_carta(img: Image.Image, lato: int = 700):
    """Maschera booleana della carta: chiara e poco satura."""
    piccola = img.convert("RGB")
    piccola.thumbnail((lato, lato), Image.Resampling.LANCZOS)
    w, h = piccola.size
    hsv = piccola.convert("HSV")
    sat = hsv.getchannel("S").tobytes()
    val = hsv.getchannel("V").tobytes()
    soglia_v = max(140, int(0.72 * max(val)))
    carta = [val[i] >= soglia_v and sat[i] <= 70 for i in range(w * h)]
    return carta, w, h


def formato_stampa(img: Image.Image) -> dict | None:
    """Classifica una stampa istantanea dalla geometria dei suoi bordi.

    Serve una fotografia della stampa INTERA, dritta, su un piano che non sia
    bianco. Il metodo:
      1. isola la carta (chiara e desaturata) e ne prende il rettangolo esterno;
      2. dentro quel rettangolo cerca la finestra dell'immagine, cioe' le righe
         e colonne che non sono tutte carta;
      3. misura i quattro bordi come frazione del lato della stampa.

    La discriminante non richiede millimetri: una Polaroid integrale ha UN
    bordo largo (la linguetta con la sacca di reagente) e tre stretti; una
    pellicola a strappo, e una normale stampa con bordo, hanno quattro bordi
    simili. Le proporzioni della finestra separano poi la famiglia quadrata
    da quella rettangolare.

    Restituisce None se non trova una cornice di carta su tutti e quattro i
    lati: senza quella non c'e' niente da misurare, e tirare a indovinare
    sarebbe peggio che tacere.
    """
    carta, w, h = _maschera_carta(img)

    righe_carta = [sum(carta[r * w:(r + 1) * w]) / w for r in range(h)]
    col_carta = [sum(carta[r * w + c] for r in range(h)) / h for c in range(w)]
    if max(righe_carta) < 0.5 or max(col_carta) < 0.5:
        return None

    # rettangolo esterno della stampa: dove c'e' carta in quantita'
    def estremi(proiezione, limite):
        indici = [i for i, v in enumerate(proiezione) if v >= limite]
        return (indici[0], indici[-1]) if indici else None

    vert = estremi(righe_carta, 0.15)
    oriz = estremi(col_carta, 0.15)
    if not vert or not oriz:
        return None
    y0, y1 = vert
    x0, x1 = oriz
    larghezza, altezza = x1 - x0 + 1, y1 - y0 + 1
    if larghezza < 40 or altezza < 40:
        return None

    # Le proiezioni di prima erano rapportate all'intera inquadratura: dentro
    # il rettangolo della stampa vanno rifatte sul lato della stampa, altrimenti
    # una stampa che occupa meta' fotografia non raggiunge mai la soglia.
    righe_interne = [sum(carta[r * w + c] for c in range(x0, x1 + 1)) / larghezza
                     for r in range(y0, y1 + 1)]
    col_interne = [sum(carta[r * w + c] for r in range(y0, y1 + 1)) / altezza
                   for c in range(x0, x1 + 1)]

    # finestra dell'immagine: righe/colonne interne che NON sono tutte carta
    def finestra(proiezione, origine, limite=0.75):
        interne = [i for i, v in enumerate(proiezione) if v < limite]
        return (origine + interne[0], origine + interne[-1]) if interne else None

    fin_v = finestra(righe_interne, y0)
    fin_o = finestra(col_interne, x0)
    if not fin_v or not fin_o:
        return None

    bordi = {
        "alto": (fin_v[0] - y0) / altezza,
        "basso": (y1 - fin_v[1]) / altezza,
        "sinistro": (fin_o[0] - x0) / larghezza,
        "destro": (x1 - fin_o[1]) / larghezza,
    }
    if min(bordi.values()) <= 0.005:
        # la cornice non si chiude su tutti i lati: la stampa e' tagliata fuori
        # inquadratura, oppure il piano d'appoggio e' chiaro quanto la carta.
        return None

    largo = max(bordi, key=bordi.get)
    stretti = sorted(v for k, v in bordi.items() if k != largo)
    asimmetria = bordi[largo] / max(stretti[-1], 1e-6)
    lati_finestra = (fin_o[1] - fin_o[0] + 1, fin_v[1] - fin_v[0] + 1)
    proporzioni = max(lati_finestra) / min(lati_finestra)

    if asimmetria >= 2.5:
        chiave = "integrale_quadrata" if proporzioni <= 1.12 else "integrale_rettangolare"
    else:
        chiave = "bordi_uniformi"

    return {
        "bordi_frazione_del_lato": {k: round(v, 4) for k, v in bordi.items()},
        "bordo_largo": largo,
        "asimmetria": round(asimmetria, 2),
        "proporzioni_finestra": round(proporzioni, 3),
        "formato": chiave,
        **FORMATI[chiave],
    }


# --------------------------------------------------------------------------
# ricerca inversa
# --------------------------------------------------------------------------

MOTORI_MANUALI = {
    "google_lens": "https://lens.google.com/upload",
    "tineye": "https://tineye.com/",
    "yandex": "https://yandex.com/images/search?rpt=imageview",
    "bing": "https://www.bing.com/images/search?view=detailv2&iss=sbi",
}


def ricerca_inversa(percorso: Path, url_pubblico: str | None = None, timeout: int = 30) -> dict:
    """Ricerca inversa vera, ma solo se ha con cosa farla.

    Serve una chiave API nell'ambiente: TINEYE_API_KEY oppure SAUCENAO_API_KEY.
    Senza chiave la funzione NON cerca e lo dichiara: eseguita = False. Non
    esiste un percorso in cui questa funzione restituisca un esito inventato.

    Nessun motore serio espone una ricerca inversa senza chiave: le pagine web
    di Google Lens e Yandex vanno usate a mano, e i link sono qui sotto.
    """
    esito = {
        "eseguita": False,
        "motivo": None,
        "risultati": [],
        "da_aprire_a_mano": dict(MOTORI_MANUALI),
        "avvertenza": (
            "Caricare una foto su un servizio esterno la consegna a terzi: "
            "puo' restare in cache o essere indicizzata. Decisione dell'autore, "
            "non del nodo."
        ),
    }
    if url_pubblico:
        q = urllib.parse.quote(url_pubblico, safe="")
        esito["da_aprire_a_mano"] = {
            "google_lens": f"https://lens.google.com/uploadbyurl?url={q}",
            "tineye": f"https://tineye.com/search?url={q}",
            "yandex": f"https://yandex.com/images/search?rpt=imageview&url={q}",
            "bing": f"https://www.bing.com/images/search?q=imgurl:{q}&view=detailv2&iss=sbi",
        }

    chiave_tineye = os.environ.get("TINEYE_API_KEY")
    chiave_sauce = os.environ.get("SAUCENAO_API_KEY")
    if not (chiave_tineye or chiave_sauce):
        esito["motivo"] = (
            "NON ESEGUITA: nessuna chiave API nell'ambiente "
            "(TINEYE_API_KEY o SAUCENAO_API_KEY). Assenza di ricerca non e' "
            "assenza di riscontri."
        )
        return esito

    try:
        import requests
    except ImportError:
        esito["motivo"] = "NON ESEGUITA: manca requests (pip install requests)."
        return esito

    try:
        with open(percorso, "rb") as f:
            dati = f.read()
        if chiave_tineye:
            r = requests.post(
                "https://api.tineye.com/rest/search/",
                files={"image_upload": (percorso.name, dati)},
                headers={"X-API-Key": chiave_tineye},
                timeout=timeout,
            )
            r.raise_for_status()
            corpo = r.json()
            esito["motore"] = "tineye"
            esito["risultati"] = corpo.get("results", {}).get("matches", [])
        else:
            r = requests.post(
                "https://saucenao.com/search.php",
                files={"file": (percorso.name, dati)},
                data={"output_type": 2, "api_key": chiave_sauce, "db": 999},
                timeout=timeout,
            )
            r.raise_for_status()
            corpo = r.json()
            esito["motore"] = "saucenao"
            esito["risultati"] = corpo.get("results", [])
        esito["eseguita"] = True
        esito["conteggio"] = len(esito["risultati"])
    except Exception as errore:  # rete, quota, chiave scaduta
        esito["motivo"] = f"NON ESEGUITA: chiamata fallita ({type(errore).__name__}: {errore})"
    return esito


# --------------------------------------------------------------------------
# analisi di un file / indice di una cartella
# --------------------------------------------------------------------------

def analizza(percorso: Path, ritaglia_in: Path | None = None, cerca: bool = False,
             url_pubblico: str | None = None, riquadro: tuple[int, int, int, int] | None = None) -> dict:
    with Image.open(percorso) as originale:
        img = ImageOps.exif_transpose(originale)
        # Con la stampa tenuta in mano su uno sfondo affollato, la maschera
        # della carta cattura anche altri oggetti chiari. Il riquadro limita
        # la misura del formato alla zona in cui la stampa si trova davvero.
        area_formato = img.crop(riquadro) if riquadro else img
        scheda = {
            "file": str(percorso),
            "byte": percorso.stat().st_size,
            "sha256": sha256(percorso),
            "dhash": dhash(img),
            "ahash": ahash(img),
            "metadati": metadati(percorso),
            "misure": misure(img),
            "miniatura_exif": miniatura_exif(percorso, originale),
            "formato_stampa": formato_stampa(area_formato),
            "riquadro_formato": list(riquadro) if riquadro else None,
        }
        stampa = rileva_stampa(img)
        scheda["stampa_rilevata"] = stampa
        if stampa and ritaglia_in is not None:
            ritaglia_in.mkdir(parents=True, exist_ok=True)
            uscita = ritaglia_in / f"{percorso.stem}_stampa.jpg"
            img.crop(tuple(stampa["box"])).save(uscita, quality=95)
            scheda["ritaglio"] = str(uscita)

    if cerca:
        scheda["ricerca_inversa"] = ricerca_inversa(percorso, url_pubblico)
    return scheda


def indicizza(cartella: Path, uscita: Path) -> dict:
    """Indice dell'archivio: impronte di ogni immagine, poi doppioni e quasi-doppioni."""
    schede = []
    for percorso in sorted(cartella.rglob("*")):
        if percorso.is_file() and percorso.suffix.lower() in ESTENSIONI:
            try:
                with Image.open(percorso) as originale:
                    img = ImageOps.exif_transpose(originale)
                    schede.append({
                        "file": str(percorso),
                        "sha256": sha256(percorso),
                        "dhash": dhash(img),
                        "pixel": list(img.size),
                        "id_immagine": metadati(percorso).get("id_immagine"),
                    })
            except Exception as errore:
                schede.append({"file": str(percorso), "errore": str(errore)})

    validi = [s for s in schede if "dhash" in s]
    identici, simili = [], []
    for i in range(len(validi)):
        for j in range(i + 1, len(validi)):
            a, b = validi[i], validi[j]
            if a["sha256"] == b["sha256"]:
                identici.append([a["file"], b["file"]])
            else:
                d = distanza(a["dhash"], b["dhash"])
                if d <= 6:
                    simili.append({"a": a["file"], "b": b["file"], "distanza": d})

    # Stesso ImageUniqueID = stesso scatto d'origine, anche se una copia e'
    # stata riscalata al punto che le impronte percettive non si riconoscono.
    per_id: dict[str, list[str]] = {}
    for scheda in validi:
        identificativo = scheda.get("id_immagine")
        if identificativo:
            per_id.setdefault(identificativo, []).append(scheda["file"])
    stesso_scatto = [{"id_immagine": k, "file": v} for k, v in sorted(per_id.items()) if len(v) > 1]

    uscita.parent.mkdir(parents=True, exist_ok=True)
    with open(uscita, "w", encoding="utf-8") as f:
        for scheda in schede:
            f.write(json.dumps(scheda, ensure_ascii=False) + "\n")

    return {"immagini": len(schede), "leggibili": len(validi),
            "file_identici": identici, "quasi_doppioni": simili,
            "stesso_id_immagine": stesso_scatto, "indice": str(uscita)}


def stampa_leggibile(scheda: dict) -> None:
    m, mis = scheda["metadati"], scheda["misure"]
    print(f"\nFILE      {scheda['file']}")
    print(f"          {scheda['byte'] / 1e6:.1f} MB  {m['pixel'][0]}x{m['pixel'][1]} ({m['megapixel']} MP)  {m['formato']}")
    print(f"  sha256  {scheda['sha256']}")
    print(f"  dhash   {scheda['dhash']}   ahash {scheda['ahash']}")

    print("\nMETADATI (RECUPERATO = letto nel file)")
    for etichetta, chiave in (("fotocamera", "fotocamera"), ("data scatto", "data_scatto"),
                              ("software", "software"), ("programma xmp", "programma_xmp"),
                              ("id immagine", "id_immagine")):
        valore = m.get(chiave)
        print(f"  {etichetta:12} {'RECUPERATO ' + str(valore) if valore else 'UNKNOWN (assente nel file)'}")
    if m.get("gps"):
        print(f"  {'gps':12} RECUPERATO {m['gps']['lat']}, {m['gps']['lon']}  {m['gps']['mappa']}")
    else:
        print(f"  {'gps':12} UNKNOWN (assente nel file)")
    if m["mancanti"]:
        print("  nota: campi assenti. Non significa che lo scatto non li avesse:")
        print("        molte piattaforme rimuovono l'EXIF quando l'immagine viene caricata.")

    print("\nMISURE (RECUPERATO = calcolato sui pixel)")
    print(f"  nitidezza (dev.std. bordi)  {mis['nitidezza']}")
    print(f"  distribuzione toni          ombre {mis['ombre_pct']}%  medi {mis['medi_pct']}%  alte {mis['alte_pct']}%")
    d = mis["dominante"]
    print(f"  dominante R/G/B             {d['rosso']} / {d['verde']} / {d['blu']}")

    mini = scheda.get("miniatura_exif")
    print("\nMINIATURA NASCOSTA NELL'EXIF")
    if not mini:
        print("  assente: nessuna miniatura incorporata da confrontare")
    elif mini["coerente"]:
        print(f"  RECUPERATO  {mini['pixel'][0]}x{mini['pixel'][1]}, distanza {mini['distanza_dall_immagine']}/64 dall'immagine")
        print("  coerente: nessuna traccia di ritaglio o sostituzione successiva allo scatto.")
        print("  Attenzione: coerente NON prova che il file non sia stato modificato.")
    else:
        print(f"  ATTENZIONE  {mini['pixel'][0]}x{mini['pixel'][1]}, distanza {mini['distanza_dall_immagine']}/64,")
        print(f"  proporzioni {mini['proporzioni']} contro {mini['proporzioni_immagine']} dell'immagine.")
        print("  La miniatura non combacia: il file e' stato ritagliato o modificato")
        print("  dopo lo scatto, e la miniatura conserva la versione precedente.")

    fmt = scheda.get("formato_stampa")
    print("\nFORMATO DELLA STAMPA (dalla geometria dei bordi)")
    if not fmt:
        print("  UNKNOWN: non trovo una cornice di carta chiusa su tutti e quattro i lati.")
        print("  Serve la stampa INTERA nell'inquadratura, dritta, su un piano scuro.")
    else:
        b = fmt["bordi_frazione_del_lato"]
        print(f"  bordi (frazione del lato): alto {b['alto']:.3f}  basso {b['basso']:.3f}  "
              f"sinistro {b['sinistro']:.3f}  destro {b['destro']:.3f}")
        print(f"  bordo piu' largo: {fmt['bordo_largo']}, asimmetria {fmt['asimmetria']}x, "
              f"finestra {fmt['proporzioni_finestra']}")
        print(f"  INFERITO  {fmt['descrizione']}")
        print(f"  epoca: {fmt['epoca']}")
        print(f"  IPOTESI da verificare su scheda tecnica: {fmt['mm_da_verificare']}")

    stampa = scheda.get("stampa_rilevata")
    print("\nAREA STAMPATA (INFERITO: regione scura dominante, da verificare a occhio)")
    if stampa:
        print(f"  rettangolo {stampa['box']}, {stampa['frazione_inquadratura']:.0%} dell'inquadratura, proporzioni {stampa['proporzioni']}")
        if scheda.get("ritaglio"):
            print(f"  ritaglio salvato in {scheda['ritaglio']}")
    else:
        print("  UNKNOWN: nessun rettangolo stampato riconosciuto (o l'immagine e' chiara)")

    ric = scheda.get("ricerca_inversa")
    if ric:
        print("\nRICERCA INVERSA")
        if ric["eseguita"]:
            print(f"  ESEGUITA su {ric.get('motore')}: {ric.get('conteggio', 0)} riscontri")
        else:
            print(f"  {ric['motivo']}")
            for nome, url in ric["da_aprire_a_mano"].items():
                print(f"    {nome:12} {url}")
            print(f"  {ric['avvertenza']}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Analisi locale di una fotografia (R3).")
    p.add_argument("percorso", type=Path, help="file immagine, o cartella con --indice")
    p.add_argument("--json", action="store_true", help="stampa la scheda in JSON")
    p.add_argument("--ritaglia", type=Path, metavar="DIR",
                   help="salva in DIR la stampa ritagliata e raddrizzata")
    p.add_argument("--ricerca-inversa", action="store_true",
                   help="cerca online: esegue solo con TINEYE_API_KEY o SAUCENAO_API_KEY")
    p.add_argument("--riquadro", metavar="x0,y0,x1,y1",
                   help="limita la misura del formato a questa zona dell'immagine")
    p.add_argument("--url-pubblico", metavar="URL",
                   help="URL gia' pubblico dell'immagine, per i link ai motori")
    p.add_argument("--indice", type=Path, metavar="FILE.jsonl",
                   help="indicizza una cartella e cerca doppioni")
    a = p.parse_args(argv)

    if not a.percorso.exists():
        sys.stderr.write(f"non trovato: {a.percorso}\n")
        return 2

    if a.indice:
        esito = indicizza(a.percorso, a.indice)
        print(json.dumps(esito, ensure_ascii=False, indent=2))
        return 0

    riquadro = None
    if a.riquadro:
        try:
            valori = tuple(int(v) for v in a.riquadro.split(","))
        except ValueError:
            valori = ()
        if len(valori) != 4 or valori[2] <= valori[0] or valori[3] <= valori[1]:
            sys.stderr.write("--riquadro vuole x0,y0,x1,y1 con x1>x0 e y1>y0\n")
            return 2
        riquadro = valori

    scheda = analizza(a.percorso, a.ritaglia, a.ricerca_inversa, a.url_pubblico, riquadro)
    if a.json:
        print(json.dumps(scheda, ensure_ascii=False, indent=2, default=str))
    else:
        stampa_leggibile(scheda)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
