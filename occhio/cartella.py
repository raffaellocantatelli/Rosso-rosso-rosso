#!/usr/bin/env python3
"""occhio.cartella — il modo a fotografie, e la mappa che ne esce.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Perche' e' meglio del video dal vivo, per tre motivi che non sono opinioni:

1. **Costa la meta' o meno.** Il video spende una chiamata ogni 2,5 secondi
   qualunque cosa inquadri, muro compreso. Con le fotografie spendi una
   chiamata per fotografia scelta da te, e le scegli bene.
2. **Le foto sono migliori.** Ferme, a fuoco, con la luce giusta. Un dorso
   letto male e' un titolo sbagliato nel registro per sempre.
3. **Non serve `https`.** Era l'ostacolo vero: `getUserMedia` fuori da
   `localhost` non parte, e quel fastidio impediva di provarlo. Con una
   cartella di foto il problema sparisce del tutto.

Il luogo si dichiara con le cartelle, che e' la cosa piu' vicina a nessuna
interfaccia:

    foto/salotto/libreria-grande/ripiano-3/IMG_0021.jpg

**Il GPS non decide mai una stanza.** Viene letto e conservato accanto al suo
errore, e serve fuori — magazzini, cantine, sopralluoghi. Dentro casa
l'errore e' piu' grande della casa: lo misura `falsificatori/h7_gps_stanze.py`
sulle tue foto, non io a memoria.

Rieseguire la stessa cartella non ripaga le stesse letture: ogni fotografia
gia' letta e' riconosciuta dalla sua impronta sha256 e saltata. E' la stessa
regola del ripasso con la telecamera (H6), applicata al portafoglio.
"""

from __future__ import annotations

import base64
import hashlib
import html
import sys
from pathlib import Path

from . import inventario as inv
from . import luogo as lg
from . import visione as vis

ESTENSIONI = {".jpg", ".jpeg", ".png", ".webp"}
MIME = {".png": "image/png", ".webp": "image/webp"}


def sha256(percorso: Path) -> str:
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        for blocco in iter(lambda: f.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def foto(radice: Path):
    for p in sorted(Path(radice).rglob("*")):
        if p.is_file() and p.suffix.lower() in ESTENSIONI:
            yield p


def percorri(radice, registro=None, cascata=vis.CASCATA, soglia=0.75,
             scrivi=True, limite=None, verboso=True):
    """Legge una cartella di fotografie e deposita cio' che riconosce."""
    radice = Path(radice).expanduser()
    if not radice.is_dir():
        raise NotADirectoryError(radice)
    registro = registro or inv.Inventario()

    elenco = list(foto(radice))
    if limite:
        elenco = elenco[:limite]
    conti = {"foto": 0, "saltate": 0, "letti": 0, "nuovi": 0,
             "gia_noti": 0, "incerti": 0, "errori": 0}

    for p in elenco:
        impronta_file = sha256(p)
        if impronta_file in registro.foto_lette:
            conti["saltate"] += 1
            if verboso:
                print(f"  · {p.name:<28} già letta, salto (nessuna spesa)")
            continue

        posto = lg.dal_percorso(p, radice)
        dati = lg.exif(p)
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        try:
            esito = vis.leggi(b64, MIME.get(p.suffix.lower(), "image/jpeg"), cascata)
        except vis.VisioneNonDisponibile:
            raise
        except Exception as e:
            conti["errori"] += 1
            print(f"  ! {p.name:<28} {vis.oscura_segreti(e)}", file=sys.stderr)
            continue

        conti["foto"] += 1
        nuovi_qui = []
        for o in esito["oggetti"]:
            conti["letti"] += 1
            stato, _ = registro.riconosci(o["tipo"], o["titolo"])
            if stato == "INCERTO":
                conti["incerti"] += 1
                continue
            if stato != "NUOVO":
                conti["gia_noti"] += 1
                continue
            if not scrivi or esito["stub"] or o["confidenza"] < soglia:
                continue
            registro.registra(o["tipo"], o["titolo"], testo_letto=o["testo_letto"],
                              confidenza=o["confidenza"], fonte="foto",
                              luogo=posto, foto_sha=impronta_file)
            conti["nuovi"] += 1
            nuovi_qui.append(o["titolo"])

        if verboso:
            gps = ""
            if dati.get("gps"):
                e = dati.get("errore_gps_m")
                gps = f"  gps ±{e:g} m" if e else "  gps (errore non dichiarato)"
            print(f"  ✓ {p.name:<28} {lg.etichetta(posto):<34}"
                  f" {len(esito['oggetti'])} letti, {len(nuovi_qui)} nuovi{gps}")

    return conti, registro


# --------------------------------------------------------------------------
# la mappa
# --------------------------------------------------------------------------

def mappa_testo(registro) -> str:
    """La mappa che serve davvero: dove sta cosa, in ordine, leggibile."""
    righe = []
    for posto, oggetti in registro.per_luogo().items():
        righe.append(f"\n{posto}  ({len(oggetti)})")
        for v in sorted(oggetti, key=lambda x: (x.get("tipo", ""), x.get("titolo", ""))):
            righe.append(f"    {v.get('tipo','altro'):<9} {v.get('titolo','')[:60]}")
    return "\n".join(righe) or "(nessun oggetto)"


def mappa_html(registro) -> str:
    """Una pagina sola, senza dipendenze, apribile con due clic.

    Non e' una pianta della casa: e' un albero. Una pianta la darebbe il LiDAR
    (RoomPlan), che pero' misura la GEOMETRIA e non legge nessun titolo — e
    per averla serve un'app nativa. Questo albero risponde alla domanda vera,
    «dov'e' quel disco», che una pianta 3D non risponde meglio.
    """
    per_luogo = registro.per_luogo()
    totale = len(registro.voci)
    corpo = []
    for posto, oggetti in per_luogo.items():
        tipi = {}
        for v in oggetti:
            tipi[v.get("tipo", "altro")] = tipi.get(v.get("tipo", "altro"), 0) + 1
        sommario = " · ".join(f"{n} {t}" for t, n in
                              sorted(tipi.items(), key=lambda kv: -kv[1]))
        voci = "".join(
            f'<li><span class=t>{html.escape(v.get("tipo","altro"))}</span>'
            f'{html.escape(v.get("titolo",""))}'
            + (f'<span class=v>{v["avvistamenti"]}×</span>'
               if v.get("avvistamenti", 1) > 1 else "")
            + "</li>"
            for v in sorted(oggetti, key=lambda x: (x.get("tipo", ""), x.get("titolo", ""))))
        corpo.append(
            f'<section><h2>{html.escape(posto)}<b>{len(oggetti)}</b></h2>'
            f'<p class=s>{html.escape(sommario)}</p><ul>{voci}</ul></section>')

    return f"""<!DOCTYPE html><html lang=it><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>occhio — mappa</title><style>
:root{{--f:#0c0e12;--p:#141821;--b:#232a38;--t:#e8ecf4;--m:#8b96ab;--g:#2ee06a}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--f);color:var(--t);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:28px}}
h1{{margin:0 0 4px;font-size:30px;letter-spacing:-.5px}}
.cap{{color:var(--m);margin:0 0 26px;max-width:70ch;font-size:13.5px}}
main{{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(310px,1fr))}}
section{{background:var(--p);border:1px solid var(--b);border-radius:13px;padding:15px 17px}}
h2{{margin:0;font-size:16px;display:flex;justify-content:space-between;align-items:baseline;gap:10px}}
h2 b{{color:var(--g);font-size:13px}}
.s{{color:var(--m);font-size:12px;margin:3px 0 11px}}
ul{{list-style:none;margin:0;padding:0}}
li{{padding:5px 0;border-top:1px solid var(--b);display:flex;gap:9px;align-items:baseline}}
.t{{color:var(--m);font-size:10px;text-transform:uppercase;letter-spacing:.6px;flex:0 0 56px}}
.v{{color:var(--m);font-size:11px;margin-left:auto}}
footer{{color:var(--m);font-size:12px;margin-top:30px;max-width:80ch;border-top:1px solid var(--b);padding-top:14px}}
</style></head><body>
<h1>occhio — mappa</h1>
<p class=cap>{totale} oggetti in {len(per_luogo)} luoghi. Il luogo è
<b>dichiarato</b> dalla cartella in cui sta la fotografia, non dedotto dal GPS:
dentro casa l'errore della posizione è più grande della casa, e una mappa
costruita su quelle coordinate mostrerebbe rumore con l'aria di un dato.
Puoi misurarlo sulle tue foto con <code>falsificatori/h7_gps_stanze.py</code>.</p>
<main>{"".join(corpo) or "<p class=cap>Nessun oggetto nel registro.</p>"}</main>
<footer>Generato da <code>python -m occhio --mappa</code>. Origine protetta:
Claudio Terzi [CT-LGAI-001]. Ogni riga è verificabile aprendo il mobile che la porta.</footer>
</body></html>"""
