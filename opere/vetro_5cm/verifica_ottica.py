#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Falsificatore dell'ottica dell'opera a due strati.

Origine protetta: Claudio Terzi [CT-LGAI-001].

`ottica.py` PREVEDE, da una formula, il vettore d'onda del moire'
    k1 = (2pi/p)(1,0)   k2 = (2pi/p2)(cos a, sin a)   K = k1 - k2
    periodo P = 2pi/|K|      magnificazione M = P*cos(a)/p2
e quindi: quanto sono larghe le bande, in che direzione corrono, e di quanto
scorrono quando lo strato dietro si sposta di s.

Qui i due strati vengono RESI pixel per pixel e il moire' viene MISURATO.
La misura non proietta niente su nessun asse: prende il picco di Fourier in
due dimensioni. Proiettare funzionava per le bande orizzontali e verticali e
distruggeva quelle diagonali, che si autocancellano nella media - il caso
misto risultava falsificato mentre la fisica era giusta.

Criteri (P6 - come questa previsione puo' essere falsificata):
  F1  |K| misurato entro il 12% di quello previsto (periodo delle bande)
  F2  direzione di K entro 5 gradi da quella prevista
  F3  magnificazione misurata entro il 12% di M, su 6 angoli
  F4  contrasto Michelson della banda >= 0.20. La soglia di rivelazione
      dell'occhio a frequenze spaziali cosi' basse sta sotto 0.01: 0.20 non
      e' il limite del visibile, e' il limite dell'inequivocabile.
  F0  (caso di controllo) senza scarto fra i due reticoli il contrasto deve
      essere < 0.02. Se comparisse una banda, la starebbe producendo il
      renderer e non l'ottica.

Tutte le misure girano su CAMPO PIATTO, non sull'opera: il viso sta fermo
mentre la banda scorre, e mediarlo dentro la stima la tira verso il basso.
Il viso e' l'opera; qui si verifica il meccanismo.

    python verifica_ottica.py --suite
    python verifica_ottica.py --alpha 0.86 --json
"""
import argparse
import json
import math
import sys

import numpy as np

from ottica import Progetto
import genera_layer as gl


# ------------------------------------------------------------------ utilita'
def _campo_piatto(fondo):
    def fn(w, h):
        return np.full((h, w), fondo, dtype=np.float64)
    return fn


def _campo_moire(scena, prog, theta, res, riduzione=8):
    """Immagine sfocata e ridotta: restano le bande, spariscono i punti."""
    img = gl._sfoca(scena.render(theta).astype(np.float64), prog.passo * res * 0.75)
    b = int(prog.passo * res * 3)
    img = img[b:-b, b:-b]
    return img[::riduzione, ::riduzione], res / riduzione


def _prepara(img):
    """Toglie la media e applica una finestra di Hann 2D.

    Senza, il picco di |DFT2| cade sulla componente continua: la media
    dell'immagine (circa 0.25) domina qualunque banda, e la ricerca del
    massimo trova k ~ 0 invece del moire'. La finestra e' simmetrica, quindi
    non sposta la fase della componente centrata: le misure di F3 restano
    confrontabili fra un angolo e l'altro.
    """
    h, w = img.shape
    fin = np.outer(np.hanning(h), np.hanning(w))
    return (img - img.mean()) * fin


def _dft2(img, res, kx, ky):
    """Componente di Fourier a (kx, ky), cicli per mm. Ritorna il complesso."""
    h, w = img.shape
    x = np.arange(w) / res
    y = np.arange(h) / res
    ex = np.exp(-2j * math.pi * np.outer(x, np.atleast_1d(kx)))       # w x nkx
    ey = np.exp(-2j * math.pi * np.outer(np.atleast_1d(ky), y))       # nky x h
    return (ey @ (img @ ex)) / (w * h)


def _picco_2d(img, res, kx0, ky0, larghezza=0.8, n=41, giri=3):
    """Picco di |DFT2| attorno a (kx0, ky0), raffinato per raddoppi.

    Cerca in una finestra centrata sulla PREVISIONE. Non e' circolare: la
    finestra e' larga +/-80% del modulo previsto, quindi se il vero K stesse
    altrove il picco cadrebbe sul bordo e il criterio fallirebbe. Cio' che si
    verifica e' che il massimo stia dove la formula dice, non che esista.
    """
    k = math.hypot(kx0, ky0)
    passo = larghezza * k if k else 0.01
    cx, cy = kx0, ky0
    for _ in range(giri):
        gx = np.linspace(cx - passo, cx + passo, n)
        gy = np.linspace(cy - passo, cy + passo, n)
        m = np.abs(_dft2(img, res, gx, gy))          # (ny, nx)
        j, i = np.unravel_index(int(np.argmax(m)), m.shape)
        cx, cy = float(gx[i]), float(gy[j])
        passo = 2.0 * (gx[1] - gx[0])
    return cx, cy


# ------------------------------------------------------------------- misura
def controllo(prog, res=4.0, verbose=True, fondo=0.3848):
    """Caso nullo: stessi passi, nessuna rotazione, nessuna banda attesa."""
    prog.eps = 0.0
    prog.alpha = 0.0
    sc = gl.Scena(prog, res=res, dissolvenza=False, densita_fn=_campo_piatto(fondo))
    img, _ = _campo_moire(sc, prog, 0.0, res)
    lo, hi = np.percentile(img, (2, 98))
    c = float((hi - lo) / (hi + lo))
    ok = c < 0.02
    if verbose:
        print(f"  contrasto residuo {c:.4f} (atteso < 0.02)   [{'ok' if ok else 'NO'}]")
    return {"contrasto_residuo": c, "F0_nessuna_banda": bool(ok),
            "esito": "RETTA" if ok else "FALSIFICATA"}


def misura(prog, res=4.0, verbose=True, fondo=0.3848):
    e = {}
    kx_p, ky_p = prog._K
    K_p = math.hypot(kx_p, ky_p)
    P_p = prog.periodo_moire
    M_p = prog.magnificazione

    # --- F1/F2: K misurato su un campo largo 4 periodi ---------------------
    # Sul pannello vero (600x800) di periodi ce ne stanno meno di due: una
    # finestra cosi' corta non VINCOLA il periodo, lo indovina. Allargare il
    # campo non e' un trucco (la fisica non dipende dalla misura del quadro)
    # ma tacerlo sarebbe un criterio che passa per costruzione.
    lato = max(600.0, 4.0 * P_p)
    res_g = 2.0
    pg = Progetto(larghezza=lato, altezza=lato, gap=prog.gap, passo=prog.passo,
                  diam_griglia=prog.diam_griglia,
                  alpha_gradi=math.degrees(prog.alpha), eps=prog.eps,
                  distanza=prog.distanza)
    sg = gl.Scena(pg, res=res_g, dissolvenza=False, densita_fn=_campo_piatto(fondo))
    grande, res_r = _campo_moire(sg, pg, 0.0, res_g, riduzione=4)
    kx_m, ky_m = _picco_2d(_prepara(grande), res_r, kx_p, ky_p)
    K_m = math.hypot(kx_m, ky_m)

    e["campo_di_misura_mm"] = lato
    e["periodo_previsto_mm"] = float(P_p)
    e["periodo_misurato_mm"] = float(1.0 / K_m) if K_m else float("inf")
    e["F1_periodo"] = bool(abs(K_m - K_p) / K_p <= 0.12)

    dir_p = math.degrees(math.atan2(abs(ky_p), abs(kx_p)))
    dir_m = math.degrees(math.atan2(abs(ky_m), abs(kx_m)))
    e["direzione_prevista_gradi"] = dir_p
    e["direzione_misurata_gradi"] = dir_m
    e["direzione_attesa"] = ("verticale" if dir_p > 80 else
                             "orizzontale" if dir_p < 10 else "diagonale")
    e["F2_direzione"] = bool(abs(dir_m - dir_p) <= 5.0)

    # --- F3: magnificazione dalla fase, sul pannello vero ------------------
    # La fase della componente a K avanza di 2*pi*s*cos(a)/p2 quando lo
    # strato dietro scorre di s; lo spostamento lungo K vale quella fase
    # divisa per 2*pi*|K|, cioe' M*s. Nessuna proiezione su assi.
    sc = gl.Scena(prog, res=res, dissolvenza=False, densita_fn=_campo_piatto(fondo))
    fasi, esse = [], []
    for gradi in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0):
        th = math.radians(gradi)
        img, res_i = _campo_moire(sc, prog, th, res)
        fasi.append(float(np.angle(_dft2(_prepara(img), res_i, kx_p, ky_p).ravel()[0])))
        esse.append(prog.parallasse(th))
    fasi = np.unwrap(np.array(fasi))
    esse = np.array(esse)
    # spostamento lungo K in mm
    spost = -(fasi - fasi[0]) / (2 * math.pi * K_p)
    M_m = float(np.polyfit(esse, spost, 1)[0])
    err = abs(abs(M_m) - M_p) / M_p
    e["magnificazione_prevista"] = float(M_p)
    e["magnificazione_misurata"] = abs(M_m)
    e["errore_relativo"] = float(err)
    e["F3_spostamento"] = bool(err <= 0.12)

    # --- F4: contrasto -----------------------------------------------------
    base, _ = _campo_moire(sc, prog, 0.0, res)
    lo, hi = np.percentile(base, (2, 98))
    contrasto = float((hi - lo) / (hi + lo))
    e["contrasto"] = contrasto
    e["F4_contrasto"] = bool(contrasto >= 0.20)

    e["dettaglio"] = [
        {"theta_gradi": g, "s_mm": round(float(s), 3),
         "banda_prevista_mm": round(float(M_p * s), 1),
         "banda_misurata_mm": round(float(m), 1)}
        for g, s, m in zip((0, 1, 2, 3, 4, 5), esse, np.abs(spost))]

    e["esito"] = ("RETTA" if all(e[k] for k in ("F1_periodo", "F2_direzione",
                  "F3_spostamento", "F4_contrasto")) else "FALSIFICATA")

    if verbose:
        print(f"  periodo    previsto {P_p:7.1f} mm   misurato "
              f"{e['periodo_misurato_mm']:7.1f} mm"
              f"   [{'ok' if e['F1_periodo'] else 'NO'}]")
        print(f"  direzione  prevista {dir_p:6.1f} g    misurata {dir_m:6.1f} g"
              f"   ({e['direzione_attesa']})"
              f"   [{'ok' if e['F2_direzione'] else 'NO'}]")
        print(f"  magnific.  prevista {M_p:7.1f} x    misurata {abs(M_m):7.1f} x"
              f"   err {err*100:4.1f}%   [{'ok' if e['F3_spostamento'] else 'NO'}]")
        print(f"  contrasto  {contrasto:.3f} (atteso >= 0.20)"
              f"   [{'ok' if e['F4_contrasto'] else 'NO'}]")
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=float, default=4.0)
    ap.add_argument("--alpha", type=float, default=0.86)
    ap.add_argument("--eps", type=float, default=0.0)
    ap.add_argument("--passo", type=float, default=6.0)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--suite", action="store_true",
                    help="i quattro casi: controllo, rotazione, scala, misto")
    a = ap.parse_args()

    casi = ([("controllo (alpha=0, eps=0)", 0.0, 0.0),
             ("ROTAZIONE (il progetto)", 0.86, 0.0),
             ("scala     (controprova)", 0.0, 0.015),
             ("misto     (diagonale)", 0.86, 0.015)] if a.suite
            else [(f"alpha={a.alpha} eps={a.eps}", a.alpha, a.eps)])

    tutti = {}
    for nome, al, ep in casi:
        if not a.json:
            print(f"\n--- {nome}")
        prog = Progetto(passo=a.passo, alpha_gradi=al, eps=ep)
        r = (controllo(prog, res=a.res, verbose=not a.json) if al == 0 and ep == 0
             else misura(prog, res=a.res, verbose=not a.json))
        if not a.json:
            print(f"  ESITO: {r['esito']}")
        tutti[nome] = r

    if a.json:
        print(json.dumps(tutti if a.suite else list(tutti.values())[0],
                         indent=2, ensure_ascii=False))
    rotti = [k for k, v in tutti.items() if v["esito"] != "RETTA"]
    if a.suite and not a.json:
        print("\n" + ("TUTTI RETTI" if not rotti else "FALSIFICATI: " + ", ".join(rotti)))
    return 0 if not rotti else 2


if __name__ == "__main__":
    sys.exit(main())
