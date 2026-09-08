#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ottica dell'opera a due strati: vetro stampato + 5 cm d'aria + plexiglas stampato.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Non descrive l'effetto: lo calcola. Ogni numero che esce da qui deriva da una
formula scritta qui sotto, e `verifica_ottica.py` la mette alla prova rendendo
davvero i due strati e misurando lo spostamento delle frange.

GEOMETRIA (dal davanti al muro)

    occhio -- D --> [ vetro: faccia1 | faccia2 = STAMPA GRIGLIA ]
                          |
                          |  g = intercapedine d'aria (50 mm)
                          v
                    [ plexi: faccia3 | faccia4 = STAMPA VISO + bianco coprente ]

Perche' la griglia va stampata sulla FACCIA 2 (interna) del vetro:
il raggio che parte dal viso attraversa l'aria e arriva alla faccia 2; la
griglia e' li'. La lastra di vetro che viene dopo sposta lateralmente tutto
allo stesso modo, quindi non entra nell'allineamento. La matematica resta
pulita e l'inchiostro resta protetto. Se invece si stampa sulla faccia 1
(esterna), il vetro entra nel conto: vedi `parallasse()`.

1. PARALLASSE
   Angolo di vista theta (0 = frontale). Fra le due stampe:

       s(theta) = g*tan(theta) + t_plexi*tan(asin(sin(theta)/n_plexi))

   Il secondo termine c'e' perche' la stampa sul plexi e' in seconda
   superficie: la luce esce attraversando 5 mm di PMMA e viene rifratta.
   Per theta piccolo:  s ~= theta * (g + t_plexi/n_plexi) = theta * d_eff.

   Movimento della testa dx a distanza D:  tan(theta) = dx/D, quindi

       s = d_eff * dx / D          (un ciclo di allineamento ogni dx = p*D/d_eff)

2. MOIRE'
   Reticolo davanti passo p. Reticolo dietro passo p*(1+eps), ruotato di alpha.

       K = k1 - k2 ~= (2*pi/p) * (eps, -alpha)
       P = p / sqrt(eps^2 + alpha^2)        periodo della banda di moire'
       M = 1 / sqrt(eps^2 + alpha^2)        magnificazione
       direzione della banda: versore (eps, -alpha)/sqrt(eps^2+alpha^2)

   Quando lo strato dietro scorre di s in orizzontale, la banda si sposta di
   M*s LUNGO QUELLA DIREZIONE. Conseguenza non ovvia e voluta:

       eps = 0 (solo rotazione)  -> ti muovi in ORIZZONTALE, la banda scorre
                                    in VERTICALE. E' l'effetto perturbante.
       alpha = 0 (solo scala)    -> la banda segue la testa, effetto naturale.

   La rotazione si regola in fase di montaggio (alpha = 0.86 gradi su 600 mm
   sono 9.0 mm di sfalsamento a un angolo: si mette a spessori e si guarda).
   La differenza di scala invece va chiesta allo stampatore e non si corregge
   piu'. Per questo il progetto usa lo STESSO passo su entrambi gli strati e
   affida tutto ad alpha.

3. RIFLESSI
   Fresnel non polarizzato su ogni interfaccia aria/materiale. Quattro
   superfici nello stack. Il velo speculare totale e' la somma, e cresce in
   fretta oltre i 60 gradi: e' questo, non il moire', a decidere dove si puo'
   stare.

4. CANCELLAZIONE DEI TONI (il motivo per cui il viso "cerca l'identita'")
   Il punto nero davanti ha diametro a1 fisso. Il punto dietro ha diametro
   a2(x,y) che porta il tono del viso.
     - dove i due reticoli sono ALLINEATI il punto davanti copre quello
       dietro: tutti i toni con a2 < a1 spariscono. Del viso restano solo le
       ombre piu' profonde -> una maschera, non una persona.
     - dove sono ANTI-ALLINEATI le aree nere si sommano: il viso c'e' tutto,
       su un fondo piu' scuro.
   Il confine fra le due condizioni e' la banda di moire' del punto 2, e
   scorre quando ti muovi. Il viso non appare e scompare: viene ATTRAVERSATO
   da una soglia di riconoscibilita'.
"""
import argparse
import math

# ----------------------------------------------------------------- materiali
N_VETRO = 1.52       # vetro sodico-calcico, luce visibile media
N_PLEXI = 1.49       # PMMA colato
N_ARIA = 1.0003


# ------------------------------------------------------------------ progetto
class Progetto:
    """Tutti i parametri fisici dell'opera in un solo posto."""

    def __init__(self,
                 larghezza=600.0,        # mm, area visibile
                 altezza=800.0,          # mm
                 gap=50.0,               # mm d'aria fra faccia2 vetro e faccia3 plexi
                 t_vetro=6.0,            # mm
                 t_plexi=5.0,            # mm
                 stampa_su_faccia2=True, # griglia sulla faccia interna del vetro
                 plexi_prima_superficie=True,  # viso stampato sulla faccia rivolta
                                               # all'intercapedine, non dietro
                 passo=6.0,              # mm, passo del reticolo (uguale sui due strati)
                 diam_griglia=4.2,       # mm, diametro del punto nero sul vetro
                 alpha_gradi=0.86,       # rotazione del vetro rispetto al plexi
                 eps=0.0,                # differenza relativa di passo fra gli strati
                 distanza=2500.0):       # mm, distanza nominale di osservazione
        self.larghezza = larghezza
        self.altezza = altezza
        self.gap = gap
        self.t_vetro = t_vetro
        self.t_plexi = t_plexi
        self.stampa_su_faccia2 = stampa_su_faccia2
        self.plexi_prima_superficie = plexi_prima_superficie
        self.passo = passo
        self.diam_griglia = diam_griglia
        self.alpha = math.radians(alpha_gradi)
        self.eps = eps
        self.distanza = distanza

    # -- parallasse ---------------------------------------------------------
    def parallasse(self, theta):
        """Scorrimento laterale s (mm) dello strato dietro rispetto a quello
        davanti, visto sotto l'angolo theta (radianti)."""
        s = self.gap * math.tan(theta)
        if not self.plexi_prima_superficie:
            # stampa in seconda superficie: la luce esce attraverso il PMMA
            s += self.t_plexi * math.tan(math.asin(math.sin(theta) / N_PLEXI))
        if not self.stampa_su_faccia2:
            # griglia sulla faccia esterna: si aggiunge lo spessore del vetro
            s += self.t_vetro * math.tan(math.asin(math.sin(theta) / N_VETRO))
        return s

    @property
    def d_eff(self):
        """Distanza efficace fra i piani di stampa (mm), per angoli piccoli."""
        d = self.gap + (0.0 if self.plexi_prima_superficie
                        else self.t_plexi / N_PLEXI)
        if not self.stampa_su_faccia2:
            d += self.t_vetro / N_VETRO
        return d

    def parallasse_da_spostamento(self, dx, D=None):
        """s (mm) quando la testa si sposta di dx (mm) a distanza D."""
        D = D or self.distanza
        return self.parallasse(math.atan2(dx, D))

    def spostamento_per_ciclo(self, D=None):
        """Quanti mm di testa servono per un ciclo completo di allineamento."""
        D = D or self.distanza
        return self.passo * D / self.d_eff

    # -- moire' -------------------------------------------------------------
    # Formule ESATTE, non a piccoli angoli. Con alpha < 1 grado le due
    # coincidono a meno del per mille, ma la versione approssimata sbaglia il
    # caso di sola scala (da' p/eps invece di p(1+eps)/eps) e nasconde il
    # fatto che P e M dipendono da eps e alpha in modo diverso.
    #     k1 = (2pi/p)(1, 0)                 reticolo davanti
    #     k2 = (2pi/p2)(cos a, sin a)        reticolo dietro, p2 = p(1+eps)
    #     K  = k1 - k2      P = 2pi/|K|      M = P*cos(a)/p2
    @property
    def passo_dietro(self):
        return self.passo * (1.0 + self.eps)

    @property
    def _K(self):
        p2 = self.passo_dietro
        kx = 1.0 / self.passo - math.cos(self.alpha) / p2
        ky = -math.sin(self.alpha) / p2
        return kx, ky

    @property
    def mismatch(self):
        kx, ky = self._K
        return math.hypot(kx, ky) * self.passo

    @property
    def periodo_moire(self):
        """Distanza fra due bande di moire' (mm)."""
        kx, ky = self._K
        m = math.hypot(kx, ky)
        return float("inf") if m == 0 else 1.0 / m

    @property
    def magnificazione(self):
        """Di quante volte la banda amplifica lo scorrimento s."""
        P = self.periodo_moire
        return float("inf") if P == float("inf") else P * math.cos(self.alpha) / self.passo_dietro

    @property
    def direzione_moire_gradi(self):
        """Direzione in cui scorre la banda, 0 = destra, -90 = verso il basso."""
        kx, ky = self._K
        return math.degrees(math.atan2(ky, kx)) if self.mismatch else 0.0

    def scorrimento_banda(self, dx, D=None):
        """Di quanti mm si sposta la banda di moire' per dx mm di testa."""
        return self.magnificazione * self.parallasse_da_spostamento(dx, D)

    @property
    def guadagno(self):
        """Rapporto fra velocita' della banda e velocita' della testa."""
        return self.magnificazione * self.d_eff / self.distanza

    # -- resa del punto -----------------------------------------------------
    @property
    def copertura_griglia(self):
        return math.pi * self.diam_griglia ** 2 / (4 * self.passo ** 2)

    def tono_soglia(self):
        """Sotto questa densita' (0 = bianco, 1 = nero pieno) il tono del viso
        viene cancellato nelle bande allineate. E' la soglia di identita'."""
        return self.copertura_griglia

    # -- leggibilita' -------------------------------------------------------
    def angolo_punto_arcmin(self, D=None):
        D = D or self.distanza
        return math.degrees(math.atan2(self.passo, D)) * 60.0

    def distanza_fusione(self, arcmin=4.0):
        """Distanza (mm) oltre la quale i punti fondono e il viso si compone."""
        return self.passo / math.tan(math.radians(arcmin / 60.0))


# ----------------------------------------------------------------- riflessi
def fresnel(theta, n1=1.0, n2=N_VETRO):
    """Riflettanza non polarizzata su un'interfaccia liscia."""
    st = math.sin(theta)
    sin_t = n1 * st / n2
    if abs(sin_t) >= 1.0:
        return 1.0
    tt = math.asin(sin_t)
    if theta == 0.0:
        return ((n2 - n1) / (n2 + n1)) ** 2
    rs = (n1 * math.cos(theta) - n2 * math.cos(tt)) / (n1 * math.cos(theta) + n2 * math.cos(tt))
    rp = (n1 * math.cos(tt) - n2 * math.cos(theta)) / (n1 * math.cos(tt) + n2 * math.cos(theta))
    return (rs * rs + rp * rp) / 2.0


def velo_speculare(theta, ar_faccia1=False):  # noqa: D401
    """Frazione di luce ambientale (proveniente dalla direzione speculare)
    rimandata verso l'occhio dalle interfacce aria/materiale dello stack.

    Le interfacce sono TRE, non quattro: faccia1 e faccia2 del vetro, faccia3
    del plexi. La faccia4 e' l'inchiostro con il bianco coprente: non e'
    un'interfaccia con l'aria, e' l'immagine.

    Cascata, non somma: la luce riflessa dalla prima superficie non arriva
    alla seconda. Sommandole si supera il 100% agli angoli radenti, che e'
    la firma di un modello sbagliato.
    """
    r_v = fresnel(theta, 1.0, N_VETRO)
    r_p = fresnel(theta, 1.0, N_PLEXI)
    r1 = r_v * (0.01 / 0.0426) if ar_faccia1 else r_v   # coating AR ~1% a 0 gradi
    riflesso = 0.0
    residuo = 1.0
    for r in (r1, r_v, r_p):
        riflesso += residuo * r
        residuo *= (1.0 - r)
    return riflesso


def fantasma(prog):
    """Immagine fantasma da doppia riflessione plexi->vetro->occhio.
    Restituisce (profondita' apparente in mm, intensita' relativa)."""
    r_v = fresnel(0.0, 1.0, N_VETRO)
    r_p = fresnel(0.0, 1.0, N_PLEXI)
    return 2.0 * prog.gap, r_v * r_p


# -------------------------------------------------------------------- tabella
def tabella(prog):
    L = []
    a = L.append
    a("=" * 68)
    a("  R3 / OPERA A DUE STRATI - tavola ottica")
    a("  Origine protetta: Claudio Terzi [CT-LGAI-001]")
    a("=" * 68)
    a("")
    a("GEOMETRIA")
    a(f"  area visibile             {prog.larghezza:.0f} x {prog.altezza:.0f} mm")
    a(f"  vetro                     {prog.t_vetro:.1f} mm, stampa su faccia "
      f"{'2 (interna)' if prog.stampa_su_faccia2 else '1 (esterna)'}")
    a(f"  intercapedine d'aria      {prog.gap:.1f} mm")
    a(f"  plexiglas                 {prog.t_plexi:.1f} mm, stampa "
      + ("in prima superficie (verso l'intercapedine)"
         if prog.plexi_prima_superficie else "in seconda superficie"))
    a(f"  distanza efficace d_eff   {prog.d_eff:.2f} mm"
      + ("" if prog.plexi_prima_superficie
         else "   <- non 50: il PMMA rifrange"))
    a("")
    a("RETICOLO")
    a(f"  passo p                   {prog.passo:.2f} mm  (identico sui due strati)")
    a(f"  punto griglia (vetro)     diam {prog.diam_griglia:.2f} mm, "
      f"copertura {prog.copertura_griglia*100:.1f}%")
    a(f"  colonne x righe           {prog.larghezza/prog.passo:.0f} x {prog.altezza/prog.passo:.0f}")
    a(f"  rotazione alpha           {math.degrees(prog.alpha):.3f} gradi  "
      f"= {math.tan(prog.alpha)*prog.larghezza:.1f} mm di sfalsamento su {prog.larghezza:.0f} mm")
    a(f"  scarto di scala eps       {prog.eps*100:.3f}%")
    a("")
    a("MOIRE'")
    a(f"  periodo banda P           {prog.periodo_moire:.0f} mm  "
      f"({prog.altezza/prog.periodo_moire:.2f} bande sull'altezza)")
    a(f"  magnificazione M          {prog.magnificazione:.1f} x")
    a(f"  direzione di scorrimento  {prog.direzione_moire_gradi:.1f} gradi "
      f"(0 = orizzontale, -90 = verso il basso)")
    a(f"  guadagno banda/testa      {prog.guadagno:.2f} x   "
      f"(30 cm di testa -> {prog.scorrimento_banda(300):.0f} mm di banda)")
    a("")
    a("MOVIMENTO")
    a(f"  distanza nominale D       {prog.distanza:.0f} mm")
    a(f"  un ciclo di allineamento  ogni {prog.spostamento_per_ciclo():.0f} mm di spostamento laterale")
    for g in (5, 10, 15, 20, 25, 30, 40):
        th = math.radians(g)
        dx = prog.distanza * math.tan(th)
        a(f"    theta {g:2d} gradi | testa {dx:6.0f} mm | s {prog.parallasse(th):6.2f} mm"
          f" | banda {prog.magnificazione*prog.parallasse(th):7.0f} mm"
          f" | velo {velo_speculare(th)*100:5.1f}%")
    a("")
    a("LEGGIBILITA'")
    a(f"  punto visto a D           {prog.angolo_punto_arcmin():.1f} arcmin (acuita' ~1 arcmin)")
    a(f"  i punti fondono oltre     {prog.distanza_fusione()/1000:.1f} m")
    a(f"  -> a {prog.distanza/1000:.1f} m il viso e' sulla soglia: si riconosce e non si legge.")
    a("")
    a("SOGLIA DI IDENTITA'")
    a(f"  nelle bande allineate spariscono tutti i toni sotto "
      f"{prog.tono_soglia()*100:.0f}% di densita';")
    a("  restano solo occhi, narici, taglio della bocca. La maschera.")
    a("")
    a("RIFLESSI")
    for g in (0, 15, 30, 45, 60, 70, 75, 80):
        th = math.radians(g)
        a(f"  theta {g:2d} gradi | 3 superfici {velo_speculare(th)*100:5.1f}%"
          f" | con AR su faccia1 {velo_speculare(th, True)*100:5.1f}%")
    d, i = fantasma(prog)
    a(f"  fantasma della griglia    {d:.0f} mm dietro il piano, intensita' {i*100:.2f}%")
    a("  zona specchio: chi guarda a theta vede riflesso cio' che sta a -theta.")
    a("  la parete di fronte va scura e le luci fuori dal cono +/- 30 gradi.")
    a("=" * 68)
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Tavola ottica dell'opera a due strati.")
    ap.add_argument("--passo", type=float, default=6.0)
    ap.add_argument("--gap", type=float, default=50.0)
    ap.add_argument("--alpha", type=float, default=0.86, help="rotazione in gradi")
    ap.add_argument("--eps", type=float, default=0.0, help="scarto di scala, frazione")
    ap.add_argument("--distanza", type=float, default=2500.0)
    ap.add_argument("--diam", type=float, default=4.2)
    ap.add_argument("--faccia1", action="store_true", help="griglia sulla faccia esterna")
    args = ap.parse_args()
    prog = Progetto(passo=args.passo, gap=args.gap, alpha_gradi=args.alpha,
                    eps=args.eps, distanza=args.distanza, diam_griglia=args.diam,
                    stampa_su_faccia2=not args.faccia1)
    print(tabella(prog))


if __name__ == "__main__":
    main()
