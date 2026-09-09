#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Il video dell'effetto: l'opera vista da chi cammina davanti.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Un'immagine ferma di quest'opera e' una bugia per omissione: l'opera non ha
uno stato, ha una traiettoria. Qui la traiettoria viene resa fotogramma per
fotogramma con la stessa ottica di `ottica.py`.

DUE RENDERER, E PERCHE'

1. `campo_cella` - vista da lontano (oltre 5,2 m), dove i punti fondono.
   Non e' una sfocatura: e' la copertura MEDIA di ogni cella del reticolo,
   calcolata in forma chiusa come unione di due dischi. Ne segue che la
   risoluzione intrinseca della vista da lontano e' UNA CELLA, cioe' 100x133
   valori su tutta l'opera - tutto il resto e' interpolazione. E' per questo
   che gira in millisecondi invece che in secondi.

2. `render_vicino` - vista ravvicinata su un ritaglio, dove i punti si
   vedono uno per uno e si guarda il meccanismo invece dell'effetto.

`--verifica` confronta il renderer veloce con quello gia' falsificato in
`verifica_ottica.py`. Un renderer nuovo che nessuno ha controllato contro
quello vecchio e' esattamente il difetto di §4: il sistema che si ascolta.

    python3 video.py                      # il video completo
    python3 video.py --verifica           # solo il controllo incrociato
    python3 video.py --foto ritratto.jpg  # con l'immagine definitiva
"""
import argparse
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ottica import Progetto
import genera_layer as gl
import viso as viso_mod

QUI = os.path.dirname(os.path.abspath(__file__))
USCITA = os.path.join(QUI, "uscita")
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


# --------------------------------------------------------------- geometria
def _rot(x, y, cx, cy, a):
    c, s = math.cos(a), math.sin(a)
    dx, dy = x - cx, y - cy
    return cx + c * dx - s * dy, cy + s * dx + c * dy


def _lente(d, r1, r2):
    """Area d'intersezione di due dischi. Vettoriale."""
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


class Opera:
    """Il retino del viso, calcolato una volta sola."""

    def __init__(self, prog, densita_fn=None, margine=None, dissolvenza=True):
        self.prog = prog
        margine = gl.MARGINE if margine is None else margine
        self.margine = margine
        _, _, self.diam = gl.retino_viso(prog, margine=margine,
                                         densita_fn=densita_fn,
                                         dissolvenza=dissolvenza)
        self.ny, self.nx = self.diam.shape

    def _raggio(self, x_lastra, y_lastra):
        """Raggio del punto della cella che contiene un punto della lastra."""
        p = self.prog.passo
        i = np.clip(((x_lastra + self.margine) / p - 0.5).round().astype(int),
                    0, self.nx - 1)
        j = np.clip(((y_lastra + self.margine) / p - 0.5).round().astype(int),
                    0, self.ny - 1)
        return self.diam[j, i] / 2.0

    # ---------------------------------------------------- vista da lontano
    def campo_cella(self, s):
        """Luminanza media per cella del reticolo del vetro. (ny_c, nx_c)."""
        p = self.prog
        cx, cy = p.larghezza / 2.0, p.altezza / 2.0
        r1 = p.diam_griglia / 2.0
        nxc = int(math.ceil(p.larghezza / p.passo))
        nyc = int(math.ceil(p.altezza / p.passo))
        ix, iy = np.meshgrid(np.arange(nxc), np.arange(nyc))
        FX = (ix + 0.5) * p.passo
        FY = (iy + 0.5) * p.passo

        # cella della lastra dietro che contiene il punto davanti
        qx, qy = _rot(FX + s, FY, cx, cy, -p.alpha)
        qx = (qx - cx) / (1 + p.eps) + cx
        qy = (qy - cy) / (1 + p.eps) + cy
        # ATTENZIONE AL MARGINE. Il reticolo della lastra dietro sta a
        # (i+0.5)*passo - margine in coordinate del pannello (vedi `centri`),
        # non a (i+0.5)*passo. Con margine 15 mm e passo 6 mm lo scarto vale
        # esattamente mezza cella, e mezza cella INVERTE il moire': dove
        # dovrebbe esserci allineamento c'e' disallineamento. E' l'errore che
        # dava correlazione -0.96 contro il renderer gia' falsificato: stessa
        # ampiezza, stessa periodicita', fase opposta. Un'ampiezza giusta non
        # dimostra niente.
        m = self.margine
        bx0 = np.floor((qx + m) / p.passo) * p.passo + p.passo / 2 - m
        by0 = np.floor((qy + m) / p.passo) * p.passo + p.passo / 2 - m

        sovr = np.zeros_like(FX)
        r2c = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                bx = bx0 + di * p.passo
                by = by0 + dj * p.passo
                r2 = self._raggio(bx, by)
                wx, wy = _rot(cx + (bx - cx) * (1 + p.eps),
                              cy + (by - cy) * (1 + p.eps), cx, cy, p.alpha)
                d = np.hypot(FX - (wx - s), FY - wy)
                sovr += _lente(d, r1, r2)
                if di == 0 and dj == 0:
                    r2c = r2
        nero = (math.pi * r1 ** 2 + math.pi * r2c ** 2 - sovr) / p.passo ** 2
        nero = np.clip(nero, 0.0, 1.0)
        return (1.0 - nero) * (1.0 - math.pi * r1 ** 2 / p.passo ** 2)

    def lontano(self, s, dim, regione=None):
        """Vista da lontano, ingrandita a `dim`.

        `regione` = (x0, y0, larghezza, altezza) in mm sul pannello. Serve a
        confrontarsi con un renderer che ritaglia i bordi: sovrapporre un
        campo intero a un campo ritagliato non e' un confronto, e la
        correlazione negativa che ne esce non e' un errore di fisica.
        """
        c = self.campo_cella(s)
        if regione is not None:
            x0, y0, w, h = regione
            pp = self.prog.passo
            i0 = int(round(x0 / pp)); j0 = int(round(y0 / pp))
            i1 = max(i0 + 1, int(round((x0 + w) / pp)))
            j1 = max(j0 + 1, int(round((y0 + h) / pp)))
            c = c[j0:j1, i0:i1]
        im = Image.fromarray(np.clip(c * 255 / 0.62, 0, 255).astype(np.uint8))
        return np.asarray(im.resize(dim, Image.BICUBIC), dtype=np.float64) / 255.0 * 0.62

    # ---------------------------------------------------- vista ravvicinata
    def render_vicino(self, s, x0, y0, w_mm, h_mm, res):
        """Ritaglio a piena risoluzione: i punti si vedono uno per uno."""
        p = self.prog
        cx, cy = p.larghezza / 2.0, p.altezza / 2.0
        r1 = p.diam_griglia / 2.0
        W, H = int(w_mm * res), int(h_mm * res)
        y, x = np.mgrid[0:H, 0:W].astype(np.float64)
        X = x0 + x / res
        Y = y0 + y / res
        bordo = 0.5 / res

        # reticolo del vetro
        u = np.mod(X, p.passo) - p.passo / 2
        v = np.mod(Y, p.passo) - p.passo / 2
        cov_f = np.clip((r1 + bordo - np.hypot(u, v)) / (2 * bordo), 0, 1)

        # reticolo del viso, sulla lastra ruotata e scorsa di s
        qx, qy = _rot(X + s, Y, cx, cy, -p.alpha)
        qx = (qx - cx) / (1 + p.eps) + cx
        qy = (qy - cy) / (1 + p.eps) + cy
        m = self.margine
        bx = np.floor((qx + m) / p.passo) * p.passo + p.passo / 2 - m
        by = np.floor((qy + m) / p.passo) * p.passo + p.passo / 2 - m
        r2 = self._raggio(bx, by)
        cov_b = np.clip((r2 + bordo - np.hypot(qx - bx, qy - by)) / (2 * bordo), 0, 1)

        return (1 - cov_f) * (1 - cov_b) * (1.0 - math.pi * r1 ** 2 / p.passo ** 2)


# ------------------------------------------------------------- verifica
def verifica(prog, res=4.0, fondo=0.3848):
    """Il renderer veloce contro quello gia' falsificato.

    Non basta che il nuovo renderer produca qualcosa di plausibile: deve dare
    lo stesso campo di quello che ha superato `verifica_ottica.py`. Altrimenti
    ho scritto due sistemi che si danno ragione a vicenda.
    """
    import verifica_ottica as vo
    op = Opera(prog, densita_fn=vo._campo_piatto(fondo), dissolvenza=False)
    sc = gl.Scena(prog, res=res, dissolvenza=False,
                  densita_fn=vo._campo_piatto(fondo))
    print(f"  {'s (mm)':>7} {'lento':>10} {'veloce':>10} {'scarto':>9}   corr")
    ok = True
    for gradi in (0.0, 1.5, 3.0, 4.5):
        th = math.radians(gradi)
        s = prog.parallasse(th)
        lento, _ = vo._campo_moire(sc, prog, th, res, riduzione=4)
        b_mm = int(prog.passo * res * 3) / res      # il bordo tolto dal lento
        veloce = op.lontano(s, (lento.shape[1], lento.shape[0]),
                            regione=(b_mm, b_mm,
                                     prog.larghezza - 2 * b_mm,
                                     prog.altezza - 2 * b_mm))
        a = (lento - lento.mean()).ravel()
        b = (veloce - veloce.mean()).ravel()
        corr = float(a @ b / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-12))
        amp_l = float(np.percentile(lento, 98) - np.percentile(lento, 2))
        amp_v = float(np.percentile(veloce, 98) - np.percentile(veloce, 2))
        scarto = abs(amp_v - amp_l) / max(amp_l, 1e-9)
        buono = corr >= 0.90 and scarto <= 0.25
        ok = ok and buono
        print(f"  {s:7.2f} {amp_l:10.4f} {amp_v:10.4f} {scarto*100:8.1f}% "
              f"  {corr:.4f}  [{'ok' if buono else 'NO'}]")
    print(f"  ESITO: {'RETTO' if ok else 'FALSIFICATO'}"
          "   (atteso: correlazione >= 0.90, scarto d'ampiezza <= 25%)")
    return ok


# ------------------------------------------------------------- montaggio
def _testo(dr, xy, t, dim=22, grassetto=False, colore=(28, 30, 30), ancora="la"):
    f = ImageFont.truetype(MONO_B if grassetto else MONO, dim)
    dr.text(xy, t, font=f, fill=colore, anchor=ancora)


def fotogramma(op, prog, dx, modo, larghezza=1080, altezza=1560):
    """Un fotogramma completo: opera + righello + lettura."""
    th = math.atan2(dx, prog.distanza)
    s = prog.parallasse(th)
    banda = prog.magnificazione * s

    tela = Image.new("RGB", (larghezza, altezza), (238, 240, 238))
    AW, AH = larghezza - 60, int((larghezza - 60) * prog.altezza / prog.larghezza)

    if modo == "lontano":
        img = op.lontano(s, (AW, AH))
        etichetta = "VISTA A 6 m   i punti fondono, resta la macchia che attraversa"
    else:
        # ritaglio centrato sull'occhio illuminato, non sul campo vuoto:
        # da vicino si guarda il MECCANISMO, e il meccanismo si legge dove
        # il retino porta un tono, non dove porta solo il fondo
        w_mm, h_mm = 210.0, 210.0 * AH / AW
        x0 = 246.0 - w_mm / 2
        y0 = 330.0 - h_mm / 2
        img = op.render_vicino(s, x0, y0, w_mm, h_mm, res=AW / w_mm)
        img = np.asarray(Image.fromarray(
            np.clip(img * 255 / 0.62, 0, 255).astype(np.uint8)).resize((AW, AH),
            Image.LANCZOS), dtype=np.float64) / 255.0 * 0.62
        etichetta = f"VISTA A 1,2 m   ritaglio {w_mm:.0f} x {h_mm:.0f} mm   i punti, uno per uno"

    g = np.clip(img / 0.62, 0, 1) ** (1 / 1.35)
    tela.paste(Image.fromarray((g * 255).astype(np.uint8)).convert("RGB"), (30, 30))

    dr = ImageDraw.Draw(tela)
    dr.rectangle([30, 30, 30 + AW, 30 + AH], outline=(196, 202, 199))
    y = 30 + AH + 30
    _testo(dr, (30, y), etichetta, 19, colore=(120, 128, 125))

    # righello della posizione della testa
    y += 44
    x_da, x_a = 30, larghezza - 30
    dr.line([x_da, y, x_a, y], fill=(196, 202, 199))
    for mm in range(-900, 901, 150):
        px = x_da + (mm + 900) / 1800 * (x_a - x_da)
        h = 11 if mm == 0 else 6
        dr.line([px, y, px, y + h], fill=(140, 148, 145) if mm == 0 else (200, 206, 203))
        if mm % 450 == 0:
            _testo(dr, (px, y + 16), f"{mm:+d}" if mm else "0", 16,
                   colore=(140, 148, 145), ancora="ma")
    pc = x_da + (dx + 900) / 1800 * (x_a - x_da)
    dr.line([pc, y - 13, pc, y + 13], fill=(168, 42, 30), width=3)
    dr.ellipse([pc - 6, y - 22, pc + 6, y - 10], fill=(168, 42, 30))

    # lettura strumentale
    y += 52
    _testo(dr, (30, y), "testa", 16, colore=(140, 148, 145))
    _testo(dr, (30, y + 20), f"{dx:+.0f} mm", 24, True)
    _testo(dr, (275, y), "scorrimento s", 16, colore=(140, 148, 145))
    _testo(dr, (275, y + 20), f"{s:+.2f} mm", 24, True)
    _testo(dr, (520, y), "macchia spostata di", 16, colore=(140, 148, 145))
    _testo(dr, (520, y + 20), f"{banda:+.0f} mm", 24, True, (168, 42, 30))
    _testo(dr, (larghezza - 30, y - 2), "R3 - Claudio Terzi [CT-LGAI-001]", 14,
           colore=(170, 178, 175), ancora="ra")
    _testo(dr, (larghezza - 30, y + 20),
           f"p {prog.passo:.2f}   alpha {math.degrees(prog.alpha):.2f} deg"
           f"   aria {prog.gap:.0f} mm", 14, colore=(170, 178, 175), ancora="ra")
    return tela


def monta(op, prog, path, fps=25, sec_lontano=15, sec_vicino=8, ampiezza=900):
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    n_l, n_v = int(fps * sec_lontano), int(fps * sec_vicino)
    prova = fotogramma(op, prog, 0, "lontano")
    cmd = [exe, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{prova.width}x{prova.height}", "-r", str(fps), "-i", "-",
           "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)
    for modo, n in (("lontano", n_l), ("vicino", n_v)):
        for k in range(n):
            # andata e ritorno con partenza e arrivo fermi (coseno)
            dx = -ampiezza * math.cos(2 * math.pi * k / n)
            pr.stdin.write(fotogramma(op, prog, dx, modo).tobytes())
        print(f"  {modo}: {n} fotogrammi")
    pr.stdin.close()
    pr.wait()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--passo", type=float, default=6.0)
    ap.add_argument("--alpha", type=float, default=0.86)
    ap.add_argument("--gap", type=float, default=50.0)
    ap.add_argument("--foto")
    ap.add_argument("--ampiezza", type=float, default=0.38,
                    help="con --foto: la taratura determinata da collaudo.py")
    ap.add_argument("--verifica", action="store_true")
    ap.add_argument("--dissolvenza", action="store_true",
                    help="con --foto: applica anche la dissolvenza del retino. "
                         "Spenta di default: su un'immagine fatta bene la "
                         "dissolvenza e' gia' dentro l'immagine")
    ap.add_argument("--out", default=os.path.join(USCITA, "effetto.mp4"))
    a = ap.parse_args()
    prog = Progetto(passo=a.passo, alpha_gradi=a.alpha, gap=a.gap)

    if a.verifica:
        print("VERIFICA INCROCIATA - renderer veloce contro renderer falsificato")
        raise SystemExit(0 if verifica(prog) else 2)

    fn = ((lambda w, h: viso_mod.da_foto(a.foto, w, h, ampiezza=a.ampiezza,
                                         dissolvenza=a.dissolvenza))
          if a.foto else None)
    op = Opera(prog, densita_fn=fn, dissolvenza=not a.foto)
    print(monta(op, prog, a.out))


if __name__ == "__main__":
    main()
