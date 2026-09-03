#!/usr/bin/env python3
"""occhio.planimetria — la pianta stilizzata come lista delle cose da fare.

Origine protetta: Claudio Terzi [CT-LGAI-001].

L'obiezione che ha fatto nascere questo modulo e' giusta: dichiarare la
stanza scrivendola e' attrito, e l'attrito uccide il vincolo dei tre minuti.
Chi pulisce non digita niente.

Ma dentro «pianta con le zone che si accendono» ci sono **due cose di costo
diversissimo**, e vanno separate:

1. **Il disegno come interfaccia** — vedere le zone e toccarne una invece di
   scrivere. Costa niente: la pianta di un bilocale sono otto rettangoli, si
   scrivono in dieci minuti in un file di testo. **Non serve il LiDAR per
   disegnare una pianta.** Questo modulo fa questo.
2. **Il posizionamento automatico** — «mi avvicino alla zona e lui ci va da
   solo». Costa moltissimo (app nativa, ARKit, rilocalizzazione) e in questo
   preciso prodotto **e' controindicato**: la rilocalizzazione ARKit e'
   probabilistica e viene ingannata dai cambiamenti dell'ambiente. In un
   alloggio in affitto l'ambiente cambia a ogni ospite: cio' che vuoi
   rilevare — oggetti spostati o spariti — e' esattamente cio' che rompe la
   localizzazione. Il meccanismo fallisce dove il prodotto ne ha bisogno.

Percio' qui: **il disegno si', il posizionamento no.** La zona si seleziona
toccandola, o non si seleziona affatto perche' gli scatti sono in ordine
fisso — «scatto 3 di 8: piano cucina». Zero tecnologia, zero errore.

Il verde e' lo stesso di sempre, salito di scala: prima erano gli oggetti
catalogati, adesso sono le zone verificate. La pianta **e'** la lista delle
cose da fare.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

# Stati di una zona. L'ordine e' quello di gravita': chi guarda cerca il rosso.
MANCA, DA_FARE, FATTA = "manca", "da_fare", "fatta"
COLORI = {FATTA: "#2ee06a", DA_FARE: "#ffb020", MANCA: "#ff4d4d"}


def carica(percorso) -> dict:
    """Legge una pianta. Formato deliberatamente scrivibile a mano."""
    return json.loads(Path(percorso).read_text(encoding="utf-8"))


def modello_da_inventario(registro, alloggio="alloggio") -> dict:
    """Una pianta di partenza dalle stanze gia' presenti nell'inventario.

    Non e' la tua casa: e' una griglia di rettangoli con i nomi giusti, da
    trascinare a mano nel file. Serve a non partire dal foglio bianco — che
    e' il vero motivo per cui una pianta non viene mai fatta.
    """
    stanze = []
    for posto in registro.per_luogo():
        prima = posto.split(" › ")[0]
        if prima not in stanze and prima != "(luogo non dichiarato)":
            stanze.append(prima)
    zone, x, y = [], 0, 0
    for i, s in enumerate(stanze):
        zone.append({"nome": s, "scatto": i + 1,
                     "punti": [[x, y], [x + 40, y], [x + 40, y + 30], [x, y + 30]]})
        x += 42
        if x > 84:
            x, y = 0, y + 32
    return {"alloggio": alloggio, "unita": "decimetri (indicative)",
            "nota": "Coordinate da correggere a mano: bastano le proporzioni, "
                    "non serve la misura vera. Non serve il LiDAR.",
            "zone": zone}


def stato_zone(registro, differenza=None, fatte=()) -> dict:
    """Colore di ogni zona: verde fatta, ambra da fare, rosso manca qualcosa.

    `differenza` e' l'esito di `consegna.differenza`: se un oggetto mancante
    apparteneva a una zona, quella zona diventa rossa. E' il momento in cui
    la pianta smette di essere una decorazione.
    """
    stati, mancanti = {}, {}
    if differenza:
        from .inventario import _etichetta
        for o in differenza.get("mancanti", []):
            zona = _etichetta(o.get("luogo")).split(" › ")[0]
            mancanti.setdefault(zona, []).append(o.get("titolo", ""))
    for posto in registro.per_luogo():
        zona = posto.split(" › ")[0]
        if zona in mancanti:
            stati[zona] = MANCA
        elif zona in fatte:
            stati[zona] = FATTA
        else:
            stati[zona] = stati.get(zona, DA_FARE)
    for zona in mancanti:
        stati[zona] = MANCA
    return {"zone": stati, "mancanti": mancanti}


# --------------------------------------------------------------------------
# il disegno
# --------------------------------------------------------------------------

def _dentro(punto, poligono) -> bool:
    """Punto dentro poligono, con il conteggio dei raggi."""
    x, y = punto
    dentro = False
    n = len(poligono)
    for i in range(n):
        x0, y0 = poligono[i]
        x1, y1 = poligono[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xi = (x1 - x0) * (y - y0) / (y1 - y0) + x0
            if x < xi:
                dentro = not dentro
    return dentro


def _distanza_dal_bordo(punto, poligono) -> float:
    x, y = punto
    minima = float("inf")
    n = len(poligono)
    for i in range(n):
        x0, y0 = poligono[i]
        x1, y1 = poligono[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        lung = dx * dx + dy * dy
        t = 0.0 if lung == 0 else max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / lung))
        px, py = x0 + t * dx, y0 + t * dy
        minima = min(minima, ((x - px) ** 2 + (y - py) ** 2) ** 0.5)
    return minima


def _punto_etichetta(punti):
    """Il punto piu' interno della stanza: dove l'etichetta sta comoda.

    Il centro del riquadro di una stanza a L cade fuori dalla stanza, e
    l'etichetta finirebbe dentro la stanza accanto: il disegno direbbe una
    cosa falsa. **Anche il baricentro dell'area puo' cadere fuori** — su una L
    marcata ci cade, e l'ho scoperto perche' il test e' passato dalla parte
    sbagliata, non perche' l'avessi previsto. Quindi non si sceglie una
    formula: si cerca. Griglia di punti, si tengono quelli dentro, vince
    quello piu' lontano da ogni muro. Su sei stanze costa niente.
    """
    ax, ay, bx, by = _riquadro(punti)
    passi = 24
    migliore, punteggio = None, -1.0
    for i in range(1, passi):
        for j in range(1, passi):
            p = (ax + (bx - ax) * i / passi, ay + (by - ay) * j / passi)
            if not _dentro(p, punti):
                continue
            d = _distanza_dal_bordo(p, punti)
            if d > punteggio:
                migliore, punteggio = p, d
    return migliore or _baricentro(punti)


def _baricentro(punti):
    """Centro dell'area. Usato solo come ripiego per poligoni degeneri."""
    a = cx = cy = 0.0
    n = len(punti)
    for i in range(n):
        x0, y0 = punti[i]
        x1, y1 = punti[(i + 1) % n]
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    if abs(a) < 1e-9:
        xs = [p[0] for p in punti]
        ys = [p[1] for p in punti]
        return sum(xs) / n, sum(ys) / n
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


def _riquadro(punti):
    xs = [p[0] for p in punti]
    ys = [p[1] for p in punti]
    return min(xs), min(ys), max(xs), max(ys)


def svg(pianta: dict, stati: dict | None = None, conteggi: dict | None = None,
        larghezza=760) -> str:
    """Una pianta stilizzata, in SVG puro. Nessuna libreria, nessun carattere
    esterno: deve aprirsi su un telefono in una casa senza rete."""
    stati = (stati or {}).get("zone", stati or {})
    conteggi = conteggi or {}
    zone = pianta.get("zone", [])
    if not zone:
        return "<p>La pianta non ha zone.</p>"

    x0 = min(_riquadro(z["punti"])[0] for z in zone)
    y0 = min(_riquadro(z["punti"])[1] for z in zone)
    x1 = max(_riquadro(z["punti"])[2] for z in zone)
    y1 = max(_riquadro(z["punti"])[3] for z in zone)
    m = 8
    vb = f"{x0 - m} {y0 - m} {x1 - x0 + 2 * m} {y1 - y0 + 2 * m}"
    scala = (x1 - x0 + 2 * m) / larghezza

    pezzi = []
    for z in zone:
        nome = z.get("nome", "")
        stato = stati.get(nome, DA_FARE)
        col = COLORI.get(stato, COLORI[DA_FARE])
        punti = " ".join(f"{p[0]},{p[1]}" for p in z["punti"])
        ax, ay, bx, by = _riquadro(z["punti"])
        cx, cy = _punto_etichetta(z["punti"])
        n = conteggi.get(nome, 0)
        scatto = z.get("scatto")
        # Il nome deve stare DENTRO la zona: una stanza stretta con
        # l'etichetta che sborda fa sembrare sbagliato un disegno giusto.
        corpo = max(2.2, min(4.6, (bx - ax) * 1.35 / max(len(nome), 1)))
        pezzi.append(
            f'<g class="zona" data-zona="{html.escape(nome)}" data-stato="{stato}">'
            f'<polygon points="{punti}" fill="{col}" fill-opacity="{0.20 if stato != DA_FARE else 0.07}"'
            f' stroke="{col}" stroke-width="{0.9 * scala:.2f}" stroke-linejoin="round"/>'
            + (f'<circle cx="{ax + 5}" cy="{ay + 5}" r="{3.2}" fill="{col}"/>'
               f'<text x="{ax + 5}" y="{ay + 5}" font-size="{4.2}" fill="#0a0d12"'
               f' text-anchor="middle" dominant-baseline="central"'
               f' font-family="ui-monospace,monospace" font-weight="700">{scatto}</text>'
               if scatto else "")
            + f'<text x="{cx}" y="{cy - 1}" font-size="{corpo:.2f}" fill="#e8ecf4"'
              f' text-anchor="middle" font-family="ui-monospace,SFMono-Regular,monospace">'
              f'{html.escape(nome)}</text>'
            + (f'<text x="{cx}" y="{cy + corpo * 1.25:.2f}" font-size="{corpo * 0.78:.2f}"'
               f' fill="{col}" text-anchor="middle" font-family="ui-monospace,monospace">'
               f'{n} oggetti</text>' if n else "")
            + "</g>")

    passo = 10
    griglia = "".join(
        f'<line x1="{gx}" y1="{y0 - m}" x2="{gx}" y2="{y1 + m}"/>'
        for gx in range(int(x0 - m), int(x1 + m) + 1, passo)) + "".join(
        f'<line x1="{x0 - m}" y1="{gy}" x2="{x1 + m}" y2="{gy}"/>'
        for gy in range(int(y0 - m), int(y1 + m) + 1, passo))

    return (f'<svg viewBox="{vb}" width="100%" style="max-width:{larghezza}px" '
            f'role="img" aria-label="pianta stilizzata delle zone">'
            f'<g stroke="#2a3span" stroke-width="{0.18 * scala:.3f}" '
            f'stroke-opacity="0.5" stroke-linecap="square">'
            .replace("#2a3span", "#334055")
            + griglia + "</g>" + "".join(pezzi) + "</svg>")


def legenda_html() -> str:
    return ('<p class=leg>'
            '<span><i style="background:#2ee06a"></i> zona verificata</span>'
            '<span><i style="background:#ffb020"></i> ancora da fare</span>'
            '<span><i style="background:#ff4d4d"></i> qui manca qualcosa</span>'
            '</p>')
