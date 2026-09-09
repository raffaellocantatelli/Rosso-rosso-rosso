#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I due strati da stampare, e la simulazione fisica di cosa fanno insieme.

Origine protetta: Claudio Terzi [CT-LGAI-001].

USCITE
  uscita/vetro_griglia.svg   faccia 2 del vetro: reticolo regolare, nero pieno
  uscita/plexi_viso.svg      seconda superficie del plexi: il viso a retino AM
  uscita/*.png               anteprime e sequenza di movimento

DECISIONE DI MONTAGGIO (e' la piu' importante del progetto)
  Il plexi e' sovradimensionato di 18 mm per lato: TRE PASSI ESATTI, non un
  numero tondo in millimetri (vedi MARGINE piu' sotto).
  I due file hanno lo STESSO passo e nessuna rotazione impressa. L'angolo
  alpha si da' RUOTANDO LA LASTRA DI PLEXI dietro, non il vetro:
    - il vetro resta a squadro, e i suoi bordi restano paralleli al muro;
    - il plexi e' sovradimensionato di 15 mm per lato e sta dietro, quindi
      la sua rotazione non si vede;
    - alpha si regola a spessori guardando l'opera, invece di essere
      congelato in un file di stampa che non si puo' piu' correggere.
  Il viso sul plexi e' pre-ruotato di -alpha, cosi' dopo il montaggio torna
  dritto mentre il suo reticolo e' ruotato di alpha. Il moire' nasce dai
  punti, non dal viso.

TRE RETICOLI, NON DUE (e' la parte che di solito si dimentica)
  1. la griglia del vetro, come la vedi;
  2. la stessa griglia proiettata sul viso dalla direzione della LUCE:
     e' l'ombra dei punti, spostata di d_eff*tan(theta_luce);
  3. il retino del viso.
  L'ombra (2) genera un moire' proprio che NON si muove quando ti muovi tu:
  si muove se sposti la lampada. Con luce diffusa larga si spalma e resta
  solo un'attenuazione uniforme -> il movimento appartiene a chi guarda.
  Con un faretto puntiforme resta, e l'opera acquista un secondo moire' fermo.
  `render_composito(theta_luce=...)` mostra i due casi.
"""
import argparse
import math
import os

import numpy as np

from ottica import Progetto
import viso as viso_mod

# Margine del pannello di plexi, per lato. NON e' un numero tondo scelto a
# caso: e' 3 passi esatti (3 x 6,00 mm). Il reticolo della lastra dietro sta
# a (i+0.5)*passo - margine; se il margine non e' un multiplo intero del
# passo, quel reticolo cade sfasato rispetto a quello del vetro di
# (margine mod passo). Con 15 mm lo sfasamento vale mezza cella, e mezza
# cella INVERTE il moire'. Qui il margine e' commensurabile e il problema
# non esiste - ne' nei file, ne' al montaggio.
MARGINE = 18.0

QUI = os.path.dirname(os.path.abspath(__file__))
USCITA = os.path.join(QUI, "uscita")


# --------------------------------------------------------------- geometria
def _ruota(x, y, cx, cy, ang):
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = x - cx, y - cy
    return cx + c * dx - s * dy, cy + s * dx + c * dy


def centri(larghezza, altezza, passo, margine=0.0):
    """Centri del reticolo su un pannello, come due array (x, y)."""
    nx = int(math.ceil((larghezza + 2 * margine) / passo))
    ny = int(math.ceil((altezza + 2 * margine) / passo))
    ix = (np.arange(nx) + 0.5) * passo - margine
    iy = (np.arange(ny) + 0.5) * passo - margine
    return np.meshgrid(ix, iy)


# ------------------------------------------------------------- retino AM
def retino_viso(prog, densita_fn=None, margine=MARGINE, seed=11,
                dissolvenza=True, precompensa=True):
    """Retino AM del viso sulla lastra di plexi (che al montaggio sara'
    ruotata di alpha). Restituisce (X, Y, DIAM) come array 2D (ny, nx) nelle
    coordinate della LASTRA, margine compreso.

    Array 2D e non lista: il diametro deve restare indicizzato per CELLA del
    reticolo, perche' e' cosi' che il compositore lo rilegge. Appiattirlo in
    una lista di cerchi e poi ricostruire le celle dalle posizioni ruotate e'
    l'errore che aveva fatto sparire la rotazione, e con essa il moire'.
    """
    W, H = prog.larghezza, prog.altezza
    cx, cy = W / 2.0, H / 2.0
    X, Y = centri(W, H, prog.passo, margine)

    # dove campionare il viso: pre-compensazione della rotazione di montaggio
    SX, SY = (_ruota(X, Y, cx, cy, -prog.alpha) if precompensa else (X, Y))

    # campo continuo del viso a 4 px/mm, campionato ai centri dei punti
    res = 4
    w_px, h_px = int(W * res), int(H * res)
    campo = densita_fn(w_px, h_px) if densita_fn else viso_mod.campo(
        w_px, h_px, dissolvenza=dissolvenza)
    fondo = float(np.median(campo[:, :int(0.06 * w_px)]))   # il campo lontano dal viso
    ix = np.clip((SX * res).astype(int), 0, w_px - 1)
    iy = np.clip((SY * res).astype(int), 0, h_px - 1)
    dentro = (SX >= 0) & (SX < W) & (SY >= 0) & (SY < H)
    dens = np.where(dentro, campo[iy, ix], fondo)   # il margine continua il fondo

    # copertura -> diametro. cov = pi*d^2/(4*p^2)  =>  d = 2p*sqrt(cov/pi)
    diam = 2.0 * prog.passo * np.sqrt(np.clip(dens, 0.0, 0.95) / math.pi)

    if dissolvenza:
        # dissolvenza granulare: il punto non SPARISCE, torna alla misura del
        # fondo. Smette di portare il viso e ridiventa campo. E' la perdita
        # di identita' alla scala a cui la si vede davvero.
        rng = np.random.default_rng(seed)
        p_viva = viso_mod.rampa_identita(w_px, h_px)[0][ix]
        d_fondo = 2.0 * prog.passo * math.sqrt(fondo / math.pi)
        diam = np.where(rng.random(diam.shape) < (0.42 + 0.58 * p_viva),
                        diam, d_fondo)

    return X, Y, diam


# ------------------------------------------------------------------- SVG
def _svg(path, larghezza, altezza, corpo, titolo):
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1"\n'
            f'     width="{larghezza}mm" height="{altezza}mm"\n'
            f'     viewBox="0 0 {larghezza} {altezza}">\n'
            f'  <title>{titolo}</title>\n'
            f'  <desc>1:1 in millimetri. R3 - origine protetta: '
            f'Claudio Terzi [CT-LGAI-001].</desc>\n'
            f'  <rect width="{larghezza}" height="{altezza}" fill="none"/>\n'
            + corpo + "\n</svg>\n")
    return path


def _crocini(larghezza, altezza, margine, passo_tacche=None):
    """Crocini di registro nel margine coperto dalla cornice."""
    p = []
    m = margine / 2.0
    for x, y in ((m, m), (larghezza - m, m), (m, altezza - m),
                 (larghezza - m, altezza - m)):
        p.append(f'  <path d="M{x-4} {y}H{x+4}M{x} {y-4}V{y+4}" '
                 f'stroke="#000" stroke-width="0.15" fill="none"/>')
    return "\n".join(p)


def svg_vetro(prog, path=None, margine=MARGINE, prefisso=""):
    """Faccia 2 del vetro: reticolo regolare di punti neri opachi.
    Il pannello e' a misura esatta: e' il vetro a definire l'area visibile."""
    path = path or os.path.join(USCITA, f"{prefisso}vetro_griglia.svg")
    W, H = prog.larghezza, prog.altezza
    X, Y = centri(W, H, prog.passo)
    r = prog.diam_griglia / 2.0
    corpo = [f'  <g fill="#000">']
    for x, y in zip(X.ravel(), Y.ravel()):
        if -r <= x <= W + r and -r <= y <= H + r:
            corpo.append(f'    <circle cx="{x:.3f}" cy="{y:.3f}" r="{r:.3f}"/>')
    corpo.append("  </g>")
    corpo.append(_crocini(W, H, 12.0))
    return _svg(path, W, H, "\n".join(corpo),
                f"R3 vetro - reticolo p={prog.passo}mm d={prog.diam_griglia}mm")


def svg_plexi(prog, path=None, margine=MARGINE, prefisso="", **kw):
    """Seconda superficie del plexi: il viso a retino, su pannello
    sovradimensionato di `margine` per lato (serve alla rotazione)."""
    path = path or os.path.join(USCITA, f"{prefisso}plexi_viso.svg")
    W, H = prog.larghezza + 2 * margine, prog.altezza + 2 * margine
    X, Y, D = retino_viso(prog, margine=margine, **kw)
    corpo = [f'  <g fill="#000">']
    for x, y, d in zip(X.ravel(), Y.ravel(), D.ravel()):
        if d >= 0.30:                      # sotto 0.3 mm il getto UV non e' ripetibile
            corpo.append(f'    <circle cx="{x+margine:.3f}" cy="{y+margine:.3f}" '
                         f'r="{d/2:.3f}"/>')
    corpo.append("  </g>")
    # riferimento d'angolo: la retta che il montatore porta a alpha
    corpo.append(f'  <path d="M{margine/2} {margine/2}L{W-margine/2} {margine/2}" '
                 f'stroke="#000" stroke-width="0.15" fill="none"/>')
    corpo.append(_crocini(W, H, margine))
    return _svg(path, W, H, "\n".join(corpo),
                f"R3 plexi - viso a retino p={prog.passo}mm")


# ------------------------------------------------- simulazione del composito
def _copertura_reticolo(shape, res, passo, raggio, off_x=0.0, off_y=0.0,
                        ang=0.0, centro=None):
    """Campo 0..1 di copertura di un reticolo regolare di dischi.
    Antialiasing sul bordo del disco su circa un pixel: senza, la misura del
    moire' finisce dominata dall'aliasing del disco invece che dal moire'."""
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    x = x / res
    y = y / res
    if ang:
        cx, cy = centro if centro else (w / (2 * res), h / (2 * res))
        c, s = math.cos(-ang), math.sin(-ang)
        dx, dy = x - cx, y - cy
        x, y = cx + c * dx - s * dy, cy + s * dx + c * dy
    u = np.mod(x - off_x, passo) - passo / 2.0
    v = np.mod(y - off_y, passo) - passo / 2.0
    d = np.sqrt(u * u + v * v)
    bordo = 0.5 / res
    return np.clip((raggio + bordo - d) / (2 * bordo), 0.0, 1.0)


def _copertura_viso(shape, res, prog, diam, margine, off_x=0.0):
    """Campo di copertura del retino del viso (raggi variabili per cella).

    La lastra di plexi e' ruotata di alpha: si ruotano le COORDINATE DEI
    PIXEL dentro il riferimento della lastra e poi si cerca la cella, come
    per un reticolo qualsiasi. Ruotare i centri e reindicizzarli sul reticolo
    diritto fa collidere le celle e cancella la rotazione.
    """
    h, w = shape
    p = prog.passo
    ny, nx = diam.shape
    raggi = (diam / 2.0).astype(np.float32)

    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    x = x / res
    y = y / res
    # dal mondo alle coordinate della LASTRA: la lastra dietro e' ruotata di
    # alpha e stampata in scala (1+eps), quindi si applica l'inversa.
    cx, cy = prog.larghezza / 2.0, prog.altezza / 2.0
    c, s_ = math.cos(-prog.alpha), math.sin(-prog.alpha)
    dx, dy = x - cx - off_x, y - cy
    rx, ry = c * dx - s_ * dy, s_ * dx + c * dy
    k = 1.0 / (1.0 + prog.eps)
    x = cx + rx * k + margine
    y = cy + ry * k + margine

    i = np.clip((x / p - 0.5).round().astype(int), 0, nx - 1)
    j = np.clip((y / p - 0.5).round().astype(int), 0, ny - 1)
    d = np.sqrt((x - (i + 0.5) * p) ** 2 + (y - (j + 0.5) * p) ** 2)
    bordo = 0.5 / res
    return np.clip((raggi[j, i] + bordo - d) / (2 * bordo), 0.0, 1.0)


class Scena:
    """Il composito dei due strati, simulato in coordinate del piano dietro."""

    def __init__(self, prog, res=4.0, margine=MARGINE, **kw_retino):
        self.prog = prog
        self.res = res
        self.margine = margine
        W = int(prog.larghezza * res)
        H = int(prog.altezza * res)
        self.shape = (H, W)
        _, _, self.diam = retino_viso(prog, margine=margine, **kw_retino)
        self.diam_map = self.diam
        self.margine = margine

    def render(self, theta_vista, theta_luce=None):
        """Luminanza percepita 0..1. theta in radianti; theta_luce=None = diffusa.

        L = T_vista * T_luce * albedo_dietro
          T_vista: griglia del vetro proiettata dalla direzione di chi guarda
          T_luce : la stessa griglia proiettata dalla direzione della lampada
                   (l'OMBRA dei punti sul viso)
        """
        p = self.prog
        s_v = p.parallasse(theta_vista)
        r1 = p.diam_griglia / 2.0
        # lo scorrimento di parallasse si applica allo strato DIETRO
        viso = _copertura_viso(self.shape, self.res, p, self.diam_map,
                               self.margine, off_x=-s_v)
        t_vista = 1.0 - _copertura_reticolo(self.shape, self.res, p.passo, r1)
        if theta_luce is None:
            t_luce = np.float32(1.0 - p.copertura_griglia)   # luce diffusa larga
        else:
            s_l = p.parallasse(theta_luce)
            t_luce = 1.0 - _copertura_reticolo(self.shape, self.res, p.passo,
                                               r1, off_x=s_l - s_v)
        return t_vista * t_luce * (1.0 - viso)

    def occhio(self, immagine, distanza=None, arcmin=1.2):
        """Sfocatura dell'occhio a una data distanza: e' l'immagine che si
        vede davvero, non quella che c'e' sul vetro."""
        from scipy.ndimage import gaussian_filter  # opzionale
        d = distanza or self.prog.distanza
        sigma_mm = d * math.tan(math.radians(arcmin / 60.0))
        return gaussian_filter(immagine, sigma_mm * self.res)


def _sfoca(img, sigma_px):
    """Gaussiana separabile senza scipy."""
    n = max(1, int(3 * sigma_px))
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / sigma_px) ** 2)
    k /= k.sum()
    out = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 1, img)
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 0, out)


def salva(img, path):
    from PIL import Image
    a = np.clip(img, 0, 1)
    Image.fromarray((a * 255).astype(np.uint8)).save(path)
    return path


def passo_testa(prog, frazione=5):
    """Spostamento laterale della testa che muove la banda di 1/frazione di
    periodo. Campionare a passi di UN periodo intero produce fotogrammi
    identici: sembra che non succeda niente, e invece e' successo tutto."""
    s_bersaglio = prog.periodo_moire / (frazione * prog.magnificazione)
    return s_bersaglio * prog.distanza / prog.d_eff


def striscia(sc, prog, offsets, distanza_occhio, path, riduzione=2,
             normalizza=True):
    """Contatto orizzontale: la stessa opera vista da posizioni diverse.
    E' l'unico modo di far vedere in un file fermo una cosa che esiste solo
    nel movimento."""
    from PIL import Image
    sigma_mm = distanza_occhio * math.tan(math.radians(1.2 / 60.0))
    tel = []
    for dx in offsets:
        th = math.atan2(dx, prog.distanza)
        img = _sfoca(sc.render(th).astype(np.float64), sigma_mm * sc.res)
        tel.append(np.clip(img, 0, 1)[::riduzione, ::riduzione])
    if normalizza:
        # stessa mappatura per tutti i fotogrammi: l'occhio si adatta al
        # livello medio della sala, non ai valori assoluti. Stirare ogni
        # fotogramma per conto suo cancellerebbe proprio cio' che cambia.
        lo = min(float(np.percentile(t, 1)) for t in tel)
        hi = max(float(np.percentile(t, 99)) for t in tel)
        tel = [np.clip((t - lo) / max(hi - lo, 1e-6), 0, 1) for t in tel]
    h, w = tel[0].shape
    sep = 8
    tela = np.ones((h, len(tel) * w + (len(tel) - 1) * sep))
    for i, t in enumerate(tel):
        tela[:, i * (w + sep):i * (w + sep) + w] = t
    Image.fromarray((tela * 255).astype(np.uint8)).save(path)
    return path


# ------------------------------------------------------------------- main# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Genera i due strati e le anteprime.")
    ap.add_argument("--passo", type=float, default=6.0)
    ap.add_argument("--alpha", type=float, default=0.86)
    ap.add_argument("--gap", type=float, default=50.0)
    ap.add_argument("--diam", type=float, default=4.2)
    ap.add_argument("--distanza", type=float, default=2500.0)
    ap.add_argument("--foto", help="usa una fotografia al posto del viso procedurale")
    ap.add_argument("--res", type=float, default=4.0, help="px/mm della simulazione")
    ap.add_argument("--solo-svg", action="store_true")
    ap.add_argument("--prefisso", default="",
                    help="prefisso dei file di stampa, per tenere piu' "
                         "configurazioni affiancate (es. p45_)")
    a = ap.parse_args()

    os.makedirs(USCITA, exist_ok=True)
    prog = Progetto(passo=a.passo, alpha_gradi=a.alpha, gap=a.gap,
                    diam_griglia=a.diam, distanza=a.distanza)

    kw = {}
    if a.foto:
        kw["densita_fn"] = lambda w, h: viso_mod.da_foto(a.foto, w, h)

    print(svg_vetro(prog, prefisso=a.prefisso))
    print(svg_plexi(prog, prefisso=a.prefisso, **kw))
    if a.solo_svg:
        return

    sc = Scena(prog, res=a.res, **kw)
    pt = passo_testa(prog, 5)
    offsets = tuple(round(i * pt) for i in range(5))
    print(f"  passo di campionamento: {pt:.0f} mm di testa = 1/5 di periodo "
          f"({prog.periodo_moire/5:.0f} mm di banda)")

    # come la vede l'occhio a 2.5 m: i punti si vedono ancora
    print(striscia(sc, prog, offsets, 2500.0,
                   os.path.join(USCITA, "striscia_2500mm.png")))
    # a 6 m i punti fondono e resta il viso attraversato dalla banda
    print(striscia(sc, prog, offsets, 6000.0,
                   os.path.join(USCITA, "striscia_6000mm.png")))

    for dx in offsets:
        th = math.atan2(dx, prog.distanza)
        print(f"  dx={dx:+5d} mm  theta={math.degrees(th):5.2f} gradi  "
              f"s={prog.parallasse(th):6.2f} mm  "
              f"banda={prog.magnificazione*prog.parallasse(th):+7.0f} mm")

    # confronto luce diffusa / faretto: il secondo moire', quello fermo
    sig = 6000.0 * math.tan(math.radians(1.2 / 60.0)) * sc.res
    salva(_sfoca(sc.render(0.0).astype(np.float64), sig),
          os.path.join(USCITA, "luce_diffusa.png"))
    salva(_sfoca(sc.render(0.0, theta_luce=math.radians(35)).astype(np.float64), sig),
          os.path.join(USCITA, "luce_faretto35.png"))
    print("  scritto luce_diffusa.png / luce_faretto35.png")


if __name__ == "__main__":
    main()
