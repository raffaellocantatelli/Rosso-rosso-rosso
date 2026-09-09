#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collaudo delle immagini candidate: quale regge il retino, e con che taratura.

Origine protetta: Claudio Terzi [CT-LGAI-001].

    python3 collaudo.py ritratti/                 # tutte le immagini della cartella
    python3 collaudo.py a.png b.png c.png
    python3 collaudo.py ritratti/ --stampa        # e genera i file dalla migliore
    python3 collaudo.py ritratti/ --passo 6.0 --diam 4.2

COSA MISURA, E PERCHE' NON E' PIU' LA "FRAZIONE UTILE"

Il primo criterio che avevo dato - la frazione di immagine entro +/-0,30 dal
fondo - era una soglia arbitraria messa a occhio. Questo si calcola.

Per ogni cella del reticolo si rendono i DUE stati estremi: punto davanti
esattamente sopra quello dietro (allineato) e punto davanti nel mezzo dei
quattro dietro (disallineato). La differenza fra le due luminanze e' quanta
luce quella cella muove quando chi guarda si sposta. Diviso per il massimo
ottenibile, da' la RESA: 1 = quella cella lavora al massimo, 0 = e' ferma.

La resa dell'immagine e' la media sulle celle. Non e' un'opinione sul viso:
e' quanta parte del movimento l'immagine consegna.

DUE COSE CHE SI SCOPRONO GUARDANDO LA CURVA

1. Il massimo cade esattamente sul fondo (0,3848), come deve.
2. **La curva NON e' simmetrica.** Densita' 0,65 rende il 74%, densita' 0,10
   rende il 26%. Le ombre lavorano molto piu' delle luci. Quindi un ritratto
   per quest'opera va tenuto un filo SOTTO il mezzo grigio, non sopra:
   e' meglio sbagliare scuro che sbagliare chiaro.

LA FINESTRA TONALE NON SI SCEGLIE: SI RICAVA
Fissato quanto deve muoversi la cella peggiore (`--resa-min`), i due estremi
di densita' fra cui mappare l'immagine sono determinati: sono i punti in cui
la curva della resa vale quel valore. E vengono fuori SQUILIBRATI, circa 1,9
volte piu' larghi verso le ombre.

Mappare simmetrici intorno al fondo - com'era la prima versione di questo
file - manda le luci in una zona dove il moire' non esiste. Su un ritratto
vero il 20% delle celle risultava ferma, TUTTE dal lato chiaro, e tutte sulla
guancia illuminata. Con la finestra derivata scendono a zero.
"""
import argparse
import glob
import json
import math
import os
import sys

import numpy as np

import viso as viso_mod

ESTENSIONI = (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp")
FONDO = 0.3848                 # copertura del reticolo del vetro
RESA_MIN_DEFAULT = 0.35        # quanto deve muoversi la cella PEGGIORE
RESA_MINIMA_CELLA = 0.30       # sotto, una cella si considera ferma
ESCURSIONE_MINIMA = 0.12       # sotto, nell'immagine non c'e' un viso

# La soglia sulla resa media non e' messa a occhio: sta fra due riferimenti
# calcolabili, dentro la finestra derivata da RESA_MIN_DEFAULT.
#
#   campo piatto, tutto sul fondo ........ 1.000   (degenere: nessun viso)
#   gaussiano centrato sul fondo ......... 0.768
#   istogramma UNIFORME sulla finestra ... 0.724   <- il riferimento naturale
#   -------- soglia 0.65 --------
#   bimodale, tutto agli estremi ......... 0.350   (il caso peggiore)
#
# Sopra 0,724 l'immagine usa la finestra meglio di una rampa lineare; sotto
# 0,65 sta accumulando toni agli estremi, dove il movimento e' minimo.
SOGLIA_RESA = 0.65

# Le soglie sono un filtro, non un giudizio: scartano cio' che di sicuro non
# funziona. Quale sia il volto giusto non e' una domanda decidibile da un
# filtro, e resta dell'autore fra le immagini che passano.


# --------------------------------------------------------------- ottica locale
def _lente(d, r1, r2):
    """Area d'intersezione di due dischi. Vettoriale.

    Duplicata da `video.py` di proposito: questo file deve poter girare con
    numpy e pillow soli, senza trascinarsi dietro il resto del progetto.
    Se la si cambia, va cambiata in tutti e due i posti - e la verifica
    incrociata di `video.py --verifica` se ne accorgerebbe.
    """
    d = np.asarray(d, dtype=np.float64)
    r1 = np.broadcast_to(np.asarray(r1, dtype=np.float64), d.shape)
    r2 = np.broadcast_to(np.asarray(r2, dtype=np.float64), d.shape)
    out = np.zeros_like(d)
    dentro = d <= np.abs(r1 - r2)
    out[dentro] = math.pi * np.minimum(r1, r2)[dentro] ** 2
    m = (~dentro) & (d < r1 + r2) & (d > 0)
    if np.any(m):
        dd, a, b = d[m], r1[m], r2[m]
        a1 = np.arccos(np.clip((dd * dd + a * a - b * b) / (2 * dd * a), -1, 1))
        a2 = np.arccos(np.clip((dd * dd + b * b - a * a) / (2 * dd * b), -1, 1))
        t = 0.5 * np.sqrt(np.maximum(0.0, (-dd + a + b) * (dd + a - b)
                                     * (dd - a + b) * (dd + a + b)))
        out[m] = a * a * a1 + b * b * a2 - t
    return out


def estremi(dens, passo, r1):
    """Luminanza della cella nei due stati estremi: allineato, disallineato."""
    r2 = passo * np.sqrt(np.clip(dens, 0.0, 0.95) / math.pi)

    def L(ox, oy):
        sovr = np.zeros_like(r2)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                d = np.hypot(ox + i * passo, oy + j * passo) * np.ones_like(r2)
                sovr += _lente(d, r1, r2)
        nero = (math.pi * r1 ** 2 + math.pi * r2 ** 2 - sovr) / passo ** 2
        return 1.0 - np.clip(nero, 0.0, 1.0)

    return L(0.0, 0.0), L(passo / 2, passo / 2)


def finestra_tonale(resa_min, passo, r1, campioni=4000):
    """I due estremi di densita' fra cui mappare l'immagine.

    NON e' una scelta di gusto: e' determinata. Fissato quanto deve muoversi
    la cella peggiore (`resa_min`), gli estremi sono i due punti in cui la
    curva della resa vale quel valore, uno per lato del fondo.

    E la finestra viene fuori SQUILIBRATA - circa 1,9 volte piu' larga verso
    le ombre che verso le luci - perche' la curva non e' simmetrica. Mappare
    simmetricamente intorno al fondo, come facevo prima, manda le luci in una
    zona dove il moire' non esiste: su un ritratto vero il 20% delle celle
    finiva ferma, TUTTE dal lato chiaro, e tutte sulla guancia illuminata.
    """
    d = np.linspace(0.0, 0.95, campioni)
    r = resa(d, passo, r1)
    basso, alto = d <= FONDO, d >= FONDO
    dl = float(d[basso][int(np.argmin(np.abs(r[basso] - resa_min)))])
    dh = float(d[alto][int(np.argmin(np.abs(r[alto] - resa_min)))])
    return dl, dh


def resa(dens, passo, r1):
    """Frazione dell'ampiezza massima che ogni cella consegna. In [0, 1]."""
    a, b = estremi(dens, passo, r1)
    dl = np.abs(a - b)
    # il massimo cade sul fondo: e' la cella che ha il punto dietro uguale a
    # quello davanti. Si calcola invece di scriverlo, cosi' resta vero anche
    # cambiando passo o diametro.
    ma, mb = estremi(np.array([FONDO]), passo, r1)
    return dl / max(float(abs(ma[0] - mb[0])), 1e-9)


# ------------------------------------------------------------------ collaudo
def _sfoca(a, sigma):
    n = max(1, int(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / sigma) ** 2)
    k /= k.sum()
    o = np.apply_along_axis(lambda m: np.convolve(m, k, "same"), 1, a)
    return np.apply_along_axis(lambda m: np.convolve(m, k, "same"), 0, o)


def sopravvivenza(dens, passo, r1):
    """Quanto del viso resta leggibile quando i due reticoli si allineano.

    Nello stato allineato il punto davanti copre quello dietro, quindi OGNI
    tono piu' chiaro del fondo rende esattamente lo stesso valore: quella
    parte del viso diventa una superficie unica. E' li' che l'identita' si
    perde, e `sparisce` la misura.

    `sopravvive` e' il contrasto locale che resta, in rapporto a quello dello
    stato disallineato. Locale, cioe' tolto il gradiente generale della luce:
    contano i tratti, non da che parte arriva la lampada. E RELATIVO al
    livello medio, perche' lo stato allineato e' molto piu' chiaro e in
    assoluto sembrerebbe piu' contrastato di quanto sia.
    """
    a, b = estremi(dens, passo, r1)
    ca = float((a - _sfoca(a, 3.0)).std() / max(a.mean(), 1e-9))
    cb = float((b - _sfoca(b, 3.0)).std() / max(b.mean(), 1e-9))
    return float(np.mean(dens < FONDO)), ca / max(cb, 1e-9)


def griglia(passo, larghezza=600.0, altezza=800.0):
    return int(round(larghezza / passo)), int(round(altezza / passo))


def esamina(percorso, passo, r1, resa_min, larghezza=600.0, altezza=800.0):
    """Un'immagine dentro la finestra tonale derivata da `resa_min`."""
    nx, ny = griglia(passo, larghezza, altezza)
    dl, dh = finestra_tonale(resa_min, passo, r1)
    d = viso_mod.da_foto(percorso, nx, ny, finestra=(dl, dh))
    r = resa(d, passo, r1)
    sparisce, sopravvive = sopravvivenza(d, passo, r1)
    # Escursione della SORGENTE, prima della rimappatura. Un'immagine senza
    # toni ha moire' perfetto e viso nullo: senza questo controllo una
    # generazione fallita, o un fondo piatto, vincerebbe la classifica.
    # Il filtro deve scartare cio' che non funziona, non premiare il vuoto.
    from PIL import Image, ImageOps
    src = np.asarray(ImageOps.fit(Image.open(percorso).convert("L"), (nx, ny),
                                  Image.LANCZOS), dtype=np.float64) / 255.0
    lo, hi = np.percentile(src, (2.0, 98.0))
    return {
        "escursione_sorgente": float(hi - lo),
        "resa_min_richiesta": round(resa_min, 3),
        "finestra": [round(dl, 4), round(dh, 4)],
        "escursione_tonale": round(dh - dl, 4),
        "squilibrio_verso_le_ombre": round((dh - FONDO) / max(FONDO - dl, 1e-9), 2),
        "resa_media": float(r.mean()),
        "resa_minima": float(r.min()),
        "sparisce_nell_allineato": sparisce,
        "sopravvive_nell_allineato": sopravvive,
        "frazione_celle_vive": float(np.mean(r >= RESA_MINIMA_CELLA)),
        "densita": {"min": float(d.min()), "media": float(d.mean()),
                    "max": float(d.max()),
                    "mediana": float(np.median(d))},
        "frazione_sotto_il_fondo": float(np.mean(d < FONDO)),
        "celle": [nx, ny],
        "_densita": d,
        "_resa": r,
    }


def _motivo(r):
    if r["escursione_sorgente"] < ESCURSIONE_MINIMA:
        return ("l'immagine non ha toni: escursione "
                f"{r['escursione_sorgente']:.3f} < {ESCURSIONE_MINIMA}. "
                "Generazione fallita, o fondo piatto")
    if r["resa_media"] < SOGLIA_RESA:
        return (f"resa media {r['resa_media']:.3f} < {SOGLIA_RESA}: i toni si "
                "accumulano agli estremi della finestra, dove il movimento e' "
                "minimo. Rifarla con meno contrasto")
    return "idonea"


# --------------------------------------------------------------- contatto
def contatto(risultati, path, passo, r1, alto=300):
    """Per ogni immagine, i due stati estremi affiancati.

    A sinistra la cella allineata (il punto davanti copre quello dietro: il
    viso rientra nel campo), a destra quella disallineata (il viso c'e'
    tutto). Quello che si vede fra le due e' esattamente cio' che il
    visitatore vede muovendosi.
    """
    from PIL import Image, ImageDraw, ImageFont
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 17)
    except OSError:
        f = fb = ImageFont.load_default()

    largo = int(alto * 600 / 800)
    riga_h = alto + 76
    W = max(2 * largo + 30, 780)
    tela = Image.new("RGB", (W, riga_h * len(risultati) + 8), (238, 240, 238))
    dr = ImageDraw.Draw(tela)
    for k, r in enumerate(risultati):
        a, b = estremi(r["_densita"], passo, r1)
        y = k * riga_h
        for i, campo in enumerate((a, b)):
            g = np.clip(campo / 0.62, 0, 1) ** (1 / 1.35)
            im = Image.fromarray((g * 255).astype(np.uint8)).resize((largo, alto),
                                                                    Image.LANCZOS)
            tela.paste(im.convert("RGB"), (i * (largo + 30), y))
        dr.text((0, y + alto + 4), os.path.basename(r["file"]), font=fb,
                fill=(24, 28, 27))
        verdetto = "IDONEA" if r["idonea"] else "SCARTATA"
        colore = (60, 90, 70) if r["idonea"] else (168, 42, 30)
        dr.text((W - 4, y + alto + 4), verdetto, font=fb, fill=colore, anchor="ra")
        dr.text((0, y + alto + 27),
                f"resa {r['resa_media']:.3f}   peggiore {r['resa_minima']:.3f}"
                f"   celle vive {r['frazione_celle_vive']*100:.0f}%"
                "     allineato / disallineato",
                font=f, fill=(120, 130, 127))
        if not r["idonea"]:
            dr.text((0, y + alto + 48), r.get("motivo", "")[:96], font=f, fill=colore)
    tela.save(path)
    return path


def confronto(risultati, path, passo, r1, alto=460):
    """Le candidate affiancate, nei due stati. E' il foglio su cui si sceglie.

    Quando il filtro le promuove tutte - ed e' il caso normale, se vengono
    dallo stesso prompt - i numeri non servono piu' a niente. Serve vederle
    nello stato in cui l'opera le mette.
    """
    from PIL import Image, ImageDraw, ImageFont
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 17)
        ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 20)
    except OSError:
        f = fb = ft = ImageFont.load_default()

    largo = int(alto * 600 / 800)
    sep, cima, mezzo, fondo_h = 12, 40, 52, 46
    W = len(risultati) * (largo + sep) + sep
    H = cima + alto + mezzo + alto + fondo_h
    tela = Image.new("RGB", (W, H), (238, 240, 238))
    dr = ImageDraw.Draw(tela)
    dr.text((sep, 12), "ALLINEATO — il viso rientra nel campo, resta la maschera",
            font=ft, fill=(24, 28, 27))
    dr.text((sep, cima + alto + 14),
            "DISALLINEATO — il viso c'e' tutto", font=ft, fill=(24, 28, 27))
    for k, r in enumerate(risultati):
        a, b = estremi(r["_densita"], passo, r1)
        x = sep + k * (largo + sep)
        for riga, campo in ((cima, a), (cima + alto + mezzo, b)):
            g = np.clip(campo / 0.62, 0, 1) ** (1 / 1.35)
            im = Image.fromarray((g * 255).astype(np.uint8)).resize((largo, alto),
                                                                    Image.LANCZOS)
            tela.paste(im.convert("RGB"), (x, riga))
            dr.rectangle([x, riga, x + largo - 1, riga + alto - 1],
                         outline=(200, 206, 203))
        y = cima + alto + mezzo + alto + 6
        dr.text((x, y), os.path.basename(r["file"]).replace(".png", ""), font=fb,
                fill=(24, 28, 27))
        dr.text((x, y + 22),
                f"resa {r['resa_media']:.3f}  sparisce "
                f"{r['sparisce_nell_allineato']*100:.0f}%", font=f,
                fill=(120, 130, 127))
    tela.save(path)
    return path


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description="Collaudo delle immagini candidate per l'opera a due strati.")
    ap.add_argument("percorsi", nargs="+", help="immagini o cartelle")
    ap.add_argument("--passo", type=float, default=4.5)
    ap.add_argument("--diam", type=float, default=None,
                    help="punto sul vetro; per difetto quello che da' "
                         "copertura 38,48%% al passo scelto")
    ap.add_argument("--resa-min", type=float, default=RESA_MIN_DEFAULT,
                    dest="resa_min",
                    help="quanto deve muoversi la cella peggiore, in frazione "
                         "del massimo. Da questo si RICAVA la finestra tonale: "
                         "piu' alto = movimento garantito ovunque ma meno "
                         "contrasto sul viso")
    ap.add_argument("--json", default="collaudo.json")
    ap.add_argument("--contatto", default="collaudo_contatto.png")
    ap.add_argument("--confronto", default="collaudo_confronto.png",
                    help="foglio con tutte le candidate affiancate nei due stati")
    ap.add_argument("--stampa", action="store_true",
                    help="genera i file di stampa. Senza --scelta usa la prima "
                         "in classifica, che quando le resa sono tutte uguali "
                         "NON vuol dire niente: meglio nominarla")
    ap.add_argument("--scelta", help="quale immagine stampare (nome o percorso). "
                                     "La classifica ordina, non sceglie")
    a = ap.parse_args()

    diam = a.diam if a.diam else a.passo * math.sqrt(4 * FONDO / math.pi)
    r1 = diam / 2.0

    file = []
    for p in a.percorsi:
        if os.path.isdir(p):
            for e in ESTENSIONI:
                file += sorted(glob.glob(os.path.join(p, "*" + e)))
                file += sorted(glob.glob(os.path.join(p, "*" + e.upper())))
        elif os.path.isfile(p):
            file.append(p)
    file = sorted(set(file))
    if not file:
        print("Nessuna immagine trovata."); return 2

    dl, dh = finestra_tonale(a.resa_min, a.passo, r1)
    print(f"COLLAUDO  passo {a.passo:.2f} mm   punto sul vetro {diam:.2f} mm   "
          f"griglia {griglia(a.passo)[0]} x {griglia(a.passo)[1]} celle")
    print(f"  finestra tonale derivata da resa minima {a.resa_min:.2f}: "
          f"{dl:.3f} .. {dh:.3f}")
    print(f"  squilibrata {((dh-FONDO)/(FONDO-dl)):.2f}x verso le ombre - "
          "non e' una scelta, e' la curva della resa")
    print(f"  soglia: resa media >= {SOGLIA_RESA:.2f}   "
          f"(uniforme 0.724, bimodale 0.350)\n")

    ris = []
    for p in file:
        try:
            r = esamina(p, a.passo, r1, a.resa_min)
        except Exception as e:                       # noqa: BLE001
            print(f"  {os.path.basename(p):34s} ERRORE: {e}")
            continue
        r["idonea"] = bool(r["resa_media"] >= SOGLIA_RESA
                           and r["escursione_sorgente"] >= ESCURSIONE_MINIMA)
        r["motivo"] = _motivo(r)
        r["file"] = p
        ris.append(r)

    ris.sort(key=lambda r: (r["idonea"], r["resa_media"]), reverse=True)
    for r in ris:
        stato = "IDONEA " if r["idonea"] else "SCARTATA"
        print(f"  {stato}  {os.path.basename(r['file']):34s} "
              f"resa {r['resa_media']:.3f}   peggiore {r['resa_minima']:.3f}"
              f"   vive {r['frazione_celle_vive']*100:5.1f}%"
              f"   sparisce {r['sparisce_nell_allineato']*100:3.0f}%"
              f"   sopravvive {r['sopravvive_nell_allineato']*100:3.0f}%"
              + ("" if r["idonea"] else f"\n            -> {r['motivo']}"))

    idonee = [r for r in ris if r["idonea"]]
    print()
    if idonee:
        m = idonee[0]
        print(f"  MIGLIORE: {os.path.basename(m['file'])}  "
              f"(resa {m['resa_media']:.3f})")
        print(f"  {len(idonee)} idonee su {len(ris)}.")
        if len(idonee) > 1:
            sp = [r["resa_media"] for r in idonee]
            if max(sp) - min(sp) < 0.05:
                print()
                print("  ATTENZIONE: le idonee stanno tutte entro il 5% di resa. "
                      "Il filtro NON le")
                print("  distingue - vengono dallo stesso prompt e hanno lo stesso "
                      "istogramma.")
                print("  Non c'e' una ragione tecnica per preferirne una. Si sceglie "
                      "sul foglio")
                print("  di confronto, e la ragione e' artistica.")
    else:
        peggio = max(ris, key=lambda r: r["resa_media"]) if ris else None
        print("  NESSUNA IDONEA.")
        if peggio:
            sotto = peggio["frazione_sotto_il_fondo"]
            print(f"  La migliore ({os.path.basename(peggio['file'])}) si ferma a "
                  f"resa {peggio['resa_media']:.3f}, sotto {SOGLIA_RESA:.2f}.")
            print("  Rimedio: rifarle con MENO CONTRASTO all'origine. Non "
                  "comprimerle in post - la compressione lascia bande che il "
                  "retino amplifica.")
            if sotto < 0.45:
                print(f"  Inoltre solo il {sotto*100:.0f}% sta sotto il fondo: "
                      "le ombre rendono quasi il triplo delle luci, quindi "
                      "chiedile mezzo stop piu' scure.")

    if ris:
        print("\n  scritto " + contatto(ris, a.contatto, a.passo, r1))
        if len(ris) > 1:
            print("  scritto " + confronto(ris, a.confronto, a.passo, r1))
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({
                "passo_mm": a.passo, "diametro_punto_vetro_mm": round(diam, 3),
                "fondo": FONDO, "resa_min": a.resa_min,
                "finestra_tonale": [round(dl, 4), round(dh, 4)],
                "riferimenti": {"campo_piatto": 1.0, "gaussiano_sul_fondo": 0.768,
                                "istogramma_uniforme": 0.724, "bimodale": 0.350},
                "soglie": {"resa_media": SOGLIA_RESA,
                           "escursione_sorgente": ESCURSIONE_MINIMA},
                "risultati": [{k: v for k, v in r.items() if not k.startswith("_")}
                              for r in ris],
            }, fh, indent=2, ensure_ascii=False)
        print("  scritto " + a.json)

    if a.stampa:
        if not idonee:
            print("\n  --stampa ignorato: nessuna immagine idonea."); return 2
        if a.scelta:
            trovate = [r for r in idonee
                       if os.path.basename(r["file"]) == os.path.basename(a.scelta)
                       or r["file"] == a.scelta]
            if not trovate:
                print(f"\n  --scelta '{a.scelta}' non e' fra le idonee."); return 2
            idonee = trovate
        elif len(idonee) > 1:
            print(f"\n  --stampa senza --scelta: uso "
                  f"{os.path.basename(idonee[0]['file'])}, la prima in classifica.")
        import subprocess
        alpha = math.degrees(2 * math.asin(a.passo / 800.0))
        # La resa minima va passata: da quella si ricava la finestra tonale.
        # Senza, i file uscirebbero con la mappatura simmetrica di default,
        # che spegne le luci.
        cmd = [sys.executable, "genera_layer.py", "--foto", idonee[0]["file"],
               "--passo", str(a.passo), "--diam", f"{diam:.3f}",
               "--alpha", f"{alpha:.4f}",
               "--resa-min", f"{a.resa_min:.3f}", "--solo-svg",
               "--prefisso", f"p{int(a.passo*10)}_finale_"]
        print("\n  " + " ".join(cmd))
        subprocess.run(cmd, check=False)

    return 0 if idonee else 2


if __name__ == "__main__":
    sys.exit(main())
