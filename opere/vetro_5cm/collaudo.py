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

LA TARATURA
`ampiezza` e' l'escursione tonale concessa al viso intorno al fondo. Alzarla
rende il viso piu' leggibile e il movimento piu' debole; abbassarla il
contrario. Non e' una preferenza: e' IL compromesso dell'opera. Per ogni
immagine qui si cerca la piu' alta che sta ancora sopra soglia, e si riporta
quella.
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
SOGLIA_RESA = 0.55
SOGLIA_CELLE_VIVE = 0.80
RESA_MINIMA_CELLA = 0.30
AMPIEZZA_MINIMA = 0.30         # sotto, il viso e' troppo piatto per leggersi
ESCURSIONE_MINIMA = 0.12       # sotto, nell'immagine non c'e' un viso


def _motivo(r):
    if r["escursione_sorgente"] < ESCURSIONE_MINIMA:
        return ("l'immagine non ha toni: escursione "
                f"{r['escursione_sorgente']:.3f} < {ESCURSIONE_MINIMA}. "
                "Generazione fallita, o fondo piatto")
    if r["ampiezza"] < AMPIEZZA_MINIMA:
        return (f"passa solo ad ampiezza {r['ampiezza']:.2f} < {AMPIEZZA_MINIMA}: "
                "troppo contrastata. Va rifatta piu' piatta all'origine")
    if r["resa_media"] < SOGLIA_RESA:
        return f"resa {r['resa_media']:.3f} < {SOGLIA_RESA}"
    if r["frazione_celle_vive"] < SOGLIA_CELLE_VIVE:
        return (f"solo il {r['frazione_celle_vive']*100:.0f}% delle celle si "
                "muove abbastanza")
    return "idonea"

# Soglie tarate su tre casi costruiti apposta - campo piatto ideale,
# il segnaposto procedurale, e una versione di quest'ultimo volutamente
# contrastata - non su ritratti veri. Sono un filtro, non un giudizio:
# servono a scartare cio' che di sicuro non funziona, non a scegliere
# l'opera. Quella scelta resta dell'autore, fra le immagini che passano.


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
def griglia(passo, larghezza=600.0, altezza=800.0):
    return int(round(larghezza / passo)), int(round(altezza / passo))


def esamina(percorso, passo, r1, ampiezza, larghezza=600.0, altezza=800.0):
    """Un'immagine, una taratura. Tutti i numeri di quella combinazione."""
    nx, ny = griglia(passo, larghezza, altezza)
    d = viso_mod.da_foto(percorso, nx, ny, fondo=FONDO, ampiezza=ampiezza)
    r = resa(d, passo, r1)
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
        "ampiezza": round(ampiezza, 3),
        "resa_media": float(r.mean()),
        "frazione_celle_vive": float(np.mean(r >= RESA_MINIMA_CELLA)),
        "densita": {"min": float(d.min()), "media": float(d.mean()),
                    "max": float(d.max()),
                    "mediana": float(np.median(d))},
        "frazione_sotto_il_fondo": float(np.mean(d < FONDO)),
        "celle": [nx, ny],
        "_densita": d,
        "_resa": r,
    }


def tara(percorso, passo, r1, ampiezze=None, **kw):
    """La piu' alta ampiezza che sta ancora sopra soglia."""
    ampiezze = ampiezze if ampiezze is not None else np.arange(0.46, 0.17, -0.01)
    prove = [esamina(percorso, passo, r1, float(a), **kw) for a in ampiezze]
    buone = [p for p in prove
             if p["resa_media"] >= SOGLIA_RESA
             and p["frazione_celle_vive"] >= SOGLIA_CELLE_VIVE]
    scelta = buone[0] if buone else max(prove, key=lambda p: p["resa_media"])
    # Il punteggio vero NON e' la resa: e' l'AMPIEZZA a cui l'immagine passa.
    # Abbassando l'ampiezza qualunque immagine finisce per superare la soglia,
    # perche' un viso schiacciato sul fondo muove tantissimo e non si vede.
    # Un'immagine e' buona quando regge il movimento SENZA farsi appiattire.
    scelta["idonea"] = bool(
        buone and scelta["ampiezza"] >= AMPIEZZA_MINIMA
        and scelta["escursione_sorgente"] >= ESCURSIONE_MINIMA)
    scelta["motivo"] = _motivo(scelta)
    scelta["prove"] = [{k: v for k, v in p.items() if not k.startswith("_")}
                       for p in prove]
    return scelta


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
                f"resa {r['resa_media']:.3f}   celle vive "
                f"{r['frazione_celle_vive']*100:.0f}%   ampiezza {r['ampiezza']:.2f}"
                "     allineato / disallineato",
                font=f, fill=(120, 130, 127))
        if not r["idonea"]:
            dr.text((0, y + alto + 48), r.get("motivo", "")[:96], font=f, fill=colore)
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
    ap.add_argument("--ampiezza", type=float, default=None,
                    help="taratura fissa invece della ricerca automatica")
    ap.add_argument("--json", default="collaudo.json")
    ap.add_argument("--contatto", default="collaudo_contatto.png")
    ap.add_argument("--stampa", action="store_true",
                    help="genera i file di stampa dall'immagine migliore")
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

    print(f"COLLAUDO  passo {a.passo:.2f} mm   punto sul vetro {diam:.2f} mm   "
          f"griglia {griglia(a.passo)[0]} x {griglia(a.passo)[1]} celle")
    print(f"  soglie: resa media >= {SOGLIA_RESA:.2f}, celle vive "
          f">= {SOGLIA_CELLE_VIVE*100:.0f}%, e tutto questo a un'ampiezza "
          f"tonale >= {AMPIEZZA_MINIMA:.2f}")
    print("  (l'ampiezza e' il punteggio vero: abbassandola passerebbe "
          "qualunque immagine,\n   al prezzo di un viso troppo piatto per "
          "essere visto)\n")

    ris = []
    for p in file:
        try:
            r = (esamina(p, a.passo, r1, a.ampiezza) if a.ampiezza
                 else tara(p, a.passo, r1))
        except Exception as e:                       # noqa: BLE001
            print(f"  {os.path.basename(p):34s} ERRORE: {e}")
            continue
        if a.ampiezza:
            r["idonea"] = bool(r["resa_media"] >= SOGLIA_RESA
                               and r["frazione_celle_vive"] >= SOGLIA_CELLE_VIVE
                               and r["ampiezza"] >= AMPIEZZA_MINIMA
                               and r["escursione_sorgente"] >= ESCURSIONE_MINIMA)
            r["motivo"] = _motivo(r)
            r["prove"] = []
        r["file"] = p
        ris.append(r)

    ris.sort(key=lambda r: (r["idonea"], r["resa_media"]), reverse=True)
    for r in ris:
        stato = "IDONEA " if r["idonea"] else "SCARTATA"
        print(f"  {stato}  {os.path.basename(r['file']):34s} "
              f"resa {r['resa_media']:.3f}   vive {r['frazione_celle_vive']*100:5.1f}%"
              f"   ampiezza {r['ampiezza']:.2f}"
              f"   sotto il fondo {r['frazione_sotto_il_fondo']*100:3.0f}%"
              + ("" if r["idonea"] else f"\n            -> {r['motivo']}"))

    idonee = [r for r in ris if r["idonea"]]
    print()
    if idonee:
        m = idonee[0]
        print(f"  MIGLIORE: {os.path.basename(m['file'])} con ampiezza "
              f"{m['ampiezza']:.2f}")
        print(f"  {len(idonee)} idonee su {len(ris)}.")
    else:
        peggio = max(ris, key=lambda r: r["resa_media"]) if ris else None
        print("  NESSUNA IDONEA.")
        if peggio:
            sotto = peggio["frazione_sotto_il_fondo"]
            print(f"  La migliore ({os.path.basename(peggio['file'])}) si ferma a "
                  f"resa {peggio['resa_media']:.3f}.")
            print(f"  Passa solo scendendo ad ampiezza {peggio['ampiezza']:.2f}, "
                  f"sotto il minimo di {AMPIEZZA_MINIMA:.2f}: a quel punto il "
                  "viso si muove ma non si legge.")
            print("  Rimedio: rifarle PIU' PIATTE all'origine. Non comprimerle "
                  "in post - la compressione lascia bande che il retino amplifica.")
            if sotto < 0.45:
                print(f"  Inoltre solo il {sotto*100:.0f}% dell'immagine sta sotto "
                      "il fondo: le ombre rendono il triplo delle luci, quindi "
                      "chiedile un mezzo stop piu' scure.")

    if ris:
        print("\n  scritto " + contatto(ris, a.contatto, a.passo, r1))
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({
                "passo_mm": a.passo, "diametro_punto_vetro_mm": round(diam, 3),
                "fondo": FONDO,
                "soglie": {"resa_media": SOGLIA_RESA,
                           "frazione_celle_vive": SOGLIA_CELLE_VIVE,
                           "resa_minima_cella": RESA_MINIMA_CELLA},
                "risultati": [{k: v for k, v in r.items() if not k.startswith("_")}
                              for r in ris],
            }, fh, indent=2, ensure_ascii=False)
        print("  scritto " + a.json)

    if a.stampa:
        if not idonee:
            print("\n  --stampa ignorato: nessuna immagine idonea."); return 2
        import subprocess
        alpha = math.degrees(2 * math.asin(a.passo / 800.0))
        # L'ampiezza va passata: e' il risultato del collaudo. Senza, i file
        # uscirebbero alla taratura di default e la misura appena fatta non
        # servirebbe a niente.
        cmd = [sys.executable, "genera_layer.py", "--foto", idonee[0]["file"],
               "--passo", str(a.passo), "--diam", f"{diam:.3f}",
               "--alpha", f"{alpha:.4f}",
               "--ampiezza", f"{idonee[0]['ampiezza']:.3f}", "--solo-svg",
               "--prefisso", f"p{int(a.passo*10)}_finale_"]
        print("\n  " + " ".join(cmd))
        subprocess.run(cmd, check=False)

    return 0 if idonee else 2


if __name__ == "__main__":
    sys.exit(main())
