#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Il viso: campo di densita' 0..1 (0 = bianco, 1 = nero pieno).

Origine protetta: Claudio Terzi [CT-LGAI-001].

Non e' un disegno: e' una SUPERFICIE. Si definisce una profondita' z(x,y) fatta
di primitive (ellissoide del cranio, cresta nasale, arcate sopraccigliari,
zigomi, labbra, orbite, bulbi), se ne prende la normale e la si illumina.
Un viso dipinto a macchie non sopravvive alla retinatura a 6 mm; un viso
illuminato si', perche' i toni restano coerenti quando la risoluzione crolla.

"Cerca l'identita'" e' una scelta costruttiva, non un titolo:
  - la meta' destra si dissolve nel fondo con una rampa (`dissolvenza`);
  - l'occhio destro perde definizione prima del resto;
  - lo sguardo non converge: le due pupille puntano a due punti diversi.
Chi guarda cerca di chiudere la figura, e la figura non si chiude.

Con `--foto` si usa una fotografia vera al posto della superficie: la pipeline
a valle non cambia. Il procedurale e' il segnaposto verificabile, non il fine.
"""
import argparse
import math
import numpy as np


def _g(x, y, cx, cy, sx, sy, rot=0.0):
    """Gaussiana anisotropa ruotata, normalizzata a 1 al centro."""
    c, s = math.cos(rot), math.sin(rot)
    dx, dy = x - cx, y - cy
    u, v = c * dx + s * dy, -s * dx + c * dy
    return np.exp(-((u / sx) ** 2 + (v / sy) ** 2))


def superficie(u, v):
    """Profondita' z(u,v) di una testa.

    COORDINATE ISOTROPE: 1 unita' = meta' dell'altezza del quadro, sui DUE
    assi. Su 600x800 mm questo significa u in [-0.75, 0.75] e v in [-1, 1],
    e un cerchio resta un cerchio. Normalizzare u e v entrambi a [-1,1]
    schiaccia la testa di un fattore 0.75: il primo tentativo dava un moai.

    Proporzioni canoniche, riferite al semiasse verticale B della testa e
    all'asse degli occhi (v = VC):
        corona  +B      arcate +0.11B     occhi 0      zigomi -0.06B
        punta del naso -0.29B     bocca -0.44B     mento -B
    Larghezza della testa = 0.64 dell'altezza, mascella rastremata.

    Vincolo di illuminazione: per ogni primitiva la pendenza massima vale
    circa 0.86*A/sigma. Oltre ~0.7 la normale supera il terminatore e la
    primitiva diventa una sbarra nera. E' l'errore che rendeva il naso una
    striscia di catrame.
    """
    B = 0.62                      # semiasse verticale della testa
    A = 0.72 * B                  # semiasse orizzontale (0.446)
    VC = 0.20                     # asse degli occhi: 0.40 dell'altezza dall'alto
    w = v - VC

    # silhouette: cranio pieno, mascella rastremata verso il mento
    giu = np.clip(-w / B, 0.0, 1.0)
    a_v = A * (1.0 - 0.22 * giu ** 2)
    # superellisse: esponente 2.2 sull'asse verticale = cranio pieno e mento
    # piatto. Con l'esponente 2 il mento esce a punta, e la testa e' una mandorla.
    q = 1.0 - np.abs(u / a_v) ** 2.0 - np.abs(w / B) ** 2.2
    dentro = q > 0
    z = np.where(dentro, 0.46 * B * np.clip(q, 0, None) ** 0.55, 0.0)

    ue = 0.159                    # semidistanza fra le pupille (una larghezza d'occhio)

    # arcate sopraccigliari
    z += 0.030 * (_g(u, v, -ue - 0.02, VC + 0.11 * B, 0.135, 0.045, 0.16)
                  + _g(u, v, ue + 0.02, VC + 0.11 * B, 0.135, 0.045, -0.16))
    # orbite
    z -= 0.036 * (_g(u, v, -ue, VC + 0.005, 0.115, 0.062)
                  + _g(u, v, ue, VC + 0.005, 0.115, 0.062))
    # bulbi: quello di destra meno definito
    z += 0.026 * _g(u, v, -ue, VC, 0.070, 0.048)
    z += 0.018 * _g(u, v, ue + 0.012, VC, 0.082, 0.058)

    # naso: cresta, punta, ali, base. A 6 mm di retino il naso sopravvive
    # solo come MASSA d'ombra, non come profilo: conta l'ampiezza, non il dettaglio.
    z += 0.042 * _g(u, v, 0.0, VC - 0.10 * B, 0.042, 0.150)
    z += 0.038 * _g(u, v, 0.0, VC - 0.29 * B, 0.052, 0.050)
    z += 0.020 * (_g(u, v, -0.068, VC - 0.285 * B, 0.036, 0.038)
                  + _g(u, v, 0.068, VC - 0.285 * B, 0.036, 0.038))
    z -= 0.012 * _g(u, v, 0.0, VC - 0.340 * B, 0.100, 0.034)      # base, ombra portata

    # zigomi
    z += 0.020 * (_g(u, v, -0.245, VC - 0.06 * B, 0.115, 0.100)
                  + _g(u, v, 0.245, VC - 0.06 * B, 0.115, 0.100))

    # bocca
    z -= 0.011 * _g(u, v, 0.0, VC - 0.375 * B, 0.065, 0.038)     # filtro
    z += 0.016 * _g(u, v, 0.0, VC - 0.415 * B, 0.130, 0.030)     # labbro superiore
    z += 0.019 * _g(u, v, 0.0, VC - 0.472 * B, 0.125, 0.034)     # labbro inferiore
    z -= 0.016 * _g(u, v, 0.0, VC - 0.443 * B, 0.140, 0.011)     # taglio

    # mandibola: senza, la testa resta un uovo anche con tutto il resto giusto
    z += 0.014 * (_g(u, v, -0.255, VC - 0.50 * B, 0.140, 0.075, -0.55)
                  + _g(u, v, 0.255, VC - 0.50 * B, 0.140, 0.075, 0.55))

    # mento
    z -= 0.010 * _g(u, v, 0.0, VC - 0.56 * B, 0.085, 0.030)
    z += 0.017 * _g(u, v, 0.0, VC - 0.72 * B, 0.130, 0.075)

    return z, dentro


def campo(w, h, luce=(-0.60, 0.46, 0.55), ambiente=0.26, dissolvenza=True,
          contrasto=1.30, seed=7, fondo=0.3848, ampiezza=0.38):
    """Densita' 0..1 su una griglia w x h. 0 = bianco, 1 = nero pieno.

    IL FONDO NON E' BIANCO, ED E' UNA DECISIONE OTTICA, NON ESTETICA.
    Il moire' nasce dal punto davanti che copre il punto dietro. Dove dietro
    non c'e' niente (bianco) non c'e' niente da coprire, e dove c'e' nero
    pieno il punto davanti sparisce dentro: in entrambi i casi l'effetto si
    spegne. E' massimo dove il punto dietro ha lo STESSO diametro di quello
    davanti.

    Quindi: `fondo` = copertura del reticolo del vetro (0.3848 con p=6, d=4.2),
    e il viso modula intorno a quel valore con semiampiezza `ampiezza`.
    Conseguenza voluta: nelle bande allineate il viso si abbassa fino al
    fondo e SI CONFONDE CON ESSO. Non svanisce in un vuoto: rientra nel
    campo. E' letteralmente la perdita di identita', non una metafora.
    """
    ar = w / h                                   # 0.75 su 600x800
    us = np.linspace(-ar, ar, w)
    vs = np.linspace(1.0, -1.0, h)               # v verso l'alto
    u, v = np.meshgrid(us, vs)

    z, dentro = superficie(u, v)

    # normale per differenze finite, con il passo REALE della griglia isotropa
    hu = 2.0 * ar / (w - 1)
    hv = 2.0 / (h - 1)
    zv, zu = np.gradient(z, hv, hu)
    nx, ny, nz = -zu, zv, np.ones_like(z)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / n, ny / n, nz / n

    lx, ly, lz = luce
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ln, ly / ln, lz / ln

    lam = np.clip(nx * lx + ny * ly + nz * lz, 0.0, None)
    luminanza = ambiente + (1.0 - ambiente) * lam

    # occlusione al bordo del cranio: la testa si stacca dal fondo senza
    # diventare un contorno nero (il bordo tocca 0.55, non 0)
    B, A, VC = 0.62, 0.72 * 0.62, 0.20
    ww = v - VC
    giu = np.clip(-ww / B, 0.0, 1.0)
    a_v = A * (1.0 - 0.22 * giu ** 2)
    r = (np.abs(u / a_v) ** 2.0 + np.abs(ww / B) ** 2.2) ** 0.5
    bordo = np.clip((1.0 - r) / 0.20, 0.0, 1.0)
    bordo = bordo * bordo * (3 - 2 * bordo)
    luminanza *= 0.62 + 0.38 * bordo

    # attaccatura dei capelli: senza, la fronte e' una cupola e il viso
    # sembra piu' basso di dove sta davvero
    luminanza *= 1.0 - 0.30 * np.clip((ww - 0.40 * B) / (0.22 * B), 0.0, 1.0)

    # pupille: due sguardi che non convergono. Non e' un dettaglio grafico,
    # e' la ragione per cui il viso non si chiude.
    luminanza -= 0.62 * _g(u, v, -0.159, VC + 0.004, 0.028, 0.030)
    luminanza -= 0.40 * _g(u, v, 0.185, VC - 0.008, 0.032, 0.034)
    # rima palpebrale superiore: senza, gli occhi sembrano due fori
    luminanza -= 0.22 * _g(u, v, -0.159, VC + 0.040, 0.082, 0.010)
    luminanza -= 0.14 * _g(u, v, 0.171, VC + 0.038, 0.086, 0.011)
    # narici e angoli della bocca
    luminanza -= 0.22 * (_g(u, v, -0.052, VC - 0.302 * B, 0.022, 0.012)
                         + _g(u, v, 0.052, VC - 0.302 * B, 0.022, 0.012))
    luminanza -= 0.20 * (_g(u, v, -0.128, VC - 0.443 * B, 0.028, 0.018)
                         + _g(u, v, 0.128, VC - 0.443 * B, 0.028, 0.018))

    grezza = 1.0 - np.clip(luminanza, 0.0, 1.0)
    grezza = np.clip((grezza - 0.5) * contrasto + 0.5, 0.0, 1.0)

    # normalizzazione sui percentili DENTRO la testa: cosi' l'escursione
    # tonale del viso e' sempre quella voluta, anche cambiando luce o posa
    testa = r < 1.0
    lo, hi = np.percentile(grezza[testa], (2.0, 98.0))
    n = np.clip((grezza - lo) / max(hi - lo, 1e-6), 0.0, 1.0)

    maschera = np.clip((1.0 - r) / 0.012, 0.0, 1.0)   # bordo antialiasato
    densita = fondo + ampiezza * (2.0 * n - 1.0) * maschera

    if dissolvenza:
        # la meta' destra si attenua: l'identita' e' disponibile solo per meta'.
        # Qui c'e' SOLO la rampa continua. La grana no: a passo 6 mm il retino
        # media su ~14 pixel e una grana per pixel sparirebbe. La dissolvenza
        # granulare vive nel retino, dove i punti si perdono uno a uno
        # (`rampa_identita` + il sorteggio in genera_layer.py).
        # si attenua VERSO IL FONDO, non verso il bianco: il viso rientra
        # nel campo invece di bucarlo
        densita = fondo + (densita - fondo) * (0.28 + 0.72 * rampa_identita(w, h))

    return np.clip(densita, 0.0, 0.95)


def rampa_identita(w, h, inizio=0.42, larghezza=0.60):
    """Probabilita' che un punto del retino sopravviva, 1 a sinistra e 0 a
    destra. Il retino la usa per far perdere l'identita' un punto alla volta:
    e' l'unica scala a cui la dissolvenza e' visibile sull'opera vera."""
    ar = w / h
    u = np.linspace(-ar, ar, w)[None, :]
    r = np.clip((inizio - u) / larghezza, 0.0, 1.0)
    return np.repeat(r * r * (3 - 2 * r), h, axis=0)


def da_foto(percorso, w, h, contrasto=1.15, dissolvenza=False):
    """Alternativa al procedurale: una fotografia vera."""
    from PIL import Image, ImageOps
    im = Image.open(percorso).convert("L")
    im = ImageOps.fit(im, (w, h), Image.LANCZOS)
    d = 1.0 - np.asarray(im, dtype=np.float64) / 255.0
    d = np.clip((d - 0.5) * contrasto + 0.5, 0.0, 1.0)
    if dissolvenza:
        xs = np.linspace(-1.0, 1.0, w)
        rampa = np.clip((0.58 - xs) / 0.78, 0.0, 1.0)
        rampa = (rampa * rampa * (3 - 2 * rampa))[None, :]
        d = d * (0.20 + 0.80 * rampa)
    return d


def main():
    ap = argparse.ArgumentParser(description="Anteprima del campo del viso.")
    ap.add_argument("--out", default="opere/vetro_5cm/uscita/viso_continuo.png")
    ap.add_argument("--w", type=int, default=600)
    ap.add_argument("--h", type=int, default=800)
    ap.add_argument("--foto")
    ap.add_argument("--senza-dissolvenza", action="store_true")
    a = ap.parse_args()
    from PIL import Image
    d = (da_foto(a.foto, a.w, a.h) if a.foto
         else campo(a.w, a.h, dissolvenza=not a.senza_dissolvenza))
    Image.fromarray(((1 - d) * 255).astype(np.uint8)).save(a.out)
    print(f"scritto {a.out}  densita' media {d.mean():.3f}  max {d.max():.3f}")


if __name__ == "__main__":
    main()
