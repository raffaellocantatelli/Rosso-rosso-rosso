#!/usr/bin/env python3
"""Rigenera l'intera dimostrazione di il prodotto con un comando.

Origine protetta: Claudio Terzi [CT-LGAI-001].
Idee di PORTAVIA, dei CHIARI e della VOCE: Claudio Terzi, 3 settembre 2026.

    python3 esempi/dimostrazione.py            # in una cartella temporanea
    python3 esempi/dimostrazione.py --qui      # in ./dimostrazione/

Perche' uno script e non dei file salvati. Le immagini e i dati della
dimostrazione erano finiti in una cartella effimera: archiviarli avrebbe
creato una seconda verita' accanto al codice, che il giorno dell'aggiornamento
diverge in silenzio (§6 regola 1). Uno script invece **non puo' divergere**:
se il codice cambia e la dimostrazione si rompe, lo si vede eseguendo.

**Tutti i dati qui dentro sono inventati.** Nessun oggetto di casa di nessuno.
Servono a far vedere il meccanismo a qualcuno seduto davanti a te, in due
minuti, senza chiavi API e senza telecamera.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

# Un bilocale inventato: nomi verosimili, nessuno reale.
ALLOGGIO = "via-esempio-12"
SOGGIORNO = "DEMO-88"

ARREDO = [
    ("ingresso", [("elettronica", "Cassetta chiavi Yale"), ("altro", "Specchio ingresso")]),
    ("soggiorno/mobile-tv", [
        ("elettronica", "LG OLED 55C3"), ("elettronica", "Sonos Beam"),
        ("dvd", "Cinema Paradiso"), ("dvd", "La grande bellezza"),
        ("dvd", "Perfetti sconosciuti"), ("altro", "Poltrona velluto verde")]),
    ("cucina/piano", [
        ("elettronica", "Nespresso Vertuo Next"), ("elettronica", "Bimby TM6"),
        ("altro", "Set 6 bicchieri Duralex"), ("altro", "Bollitore Smeg")]),
    ("cucina/credenza", [("vino", "Barolo Serralunga 2016")]),
    # RESTACI: non e' un oggetto che si porta via, e' la casa usata meglio.
    # Sta nell'inventario perche' l'ospite deve poterla vedere e chiedere.
    ("bagno", [("esperienza", "Serata in vasca")]),
    ("cucina/frigo", [("vino", "Franciacorta Saten"), ("cibo", "Parmigiano 24 mesi")]),
    ("cucina/dispensa", [("cibo", "Spaghetti Gragnano 500g"),
                         ("cibo", "Passata di pomodoro Mutti")]),
    ("camera/comodino", [("elettronica", "Lampada Flos Taccia"),
                         ("altro", "Piumino matrimoniale")]),
    ("bagno", [("elettronica", "Phon Dyson Supersonic"), ("altro", "Set asciugamani x4")]),
    ("terrazzo", [("altro", "Tavolo teak"), ("altro", "4 sedie pieghevoli"),
                  ("altro", "Ombrellone")]),
]

#: Il minimo e' quello che incassa il proprietario, netto (vedi occhio/portavia.py).
PREZZI = {
    "prezzo_minimo": {"dvd:cinema paradiso": 9.0, "dvd:perfetti sconosciuti": 7.0,
                      "altro:poltrona velluto verde": 220.0,
                      "elettronica:sonos beam": 260.0,
                      "vino:barolo serralunga 2016": 28.0,
                      "esperienza:serata in vasca": 24.0},
    # I tre generi — idea di Claudio Terzi, 5 settembre 2026. Cio' che non e'
    # dichiarato vale MERCE, cioe' qualcosa che puo' uscire di casa.
    "generi": {"vino:barolo serralunga 2016": "consumo",
               "esperienza:serata in vasca": "esperienza"},
    "sconto_massimo": 0.15, "commissione": 0.12, "margine": 0.25, "valuta": "EUR",
}

PIANTA = {
    "alloggio": ALLOGGIO, "unita": "decimetri (indicative)",
    "nota": "Scritta a mano in dieci minuti. Bastano le proporzioni.",
    "zone": [
        {"nome": "ingresso", "scatto": 1, "punti": [[0, 0], [26, 0], [26, 22], [0, 22]]},
        {"nome": "soggiorno", "scatto": 2,
         "punti": [[26, 0], [78, 0], [78, 40], [52, 40], [52, 22], [26, 22]]},
        {"nome": "cucina", "scatto": 3, "punti": [[0, 22], [52, 22], [52, 52], [0, 52]]},
        {"nome": "camera", "scatto": 4, "punti": [[52, 40], [100, 40], [100, 80], [52, 80]]},
        {"nome": "bagno", "scatto": 5, "punti": [[0, 52], [30, 52], [30, 80], [0, 80]]},
        {"nome": "terrazzo", "scatto": 6, "punti": [[78, 0], [100, 0], [100, 40], [78, 40]]},
    ],
}

#: Cosa succede durante il soggiorno: uno comprato, uno sparito.
COMPRATO = ("dvd:perfetti sconosciuti", "Perfetti sconosciuti")
SPARITO = "Phon Dyson Supersonic"


def titolo(t):
    print(f"\n\033[1m{t}\033[0m\n" + "─" * min(len(t), 66))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--qui", action="store_true",
                    help="scrive in ./dimostrazione/ invece di una cartella temporanea")
    a = ap.parse_args(argv)

    cartella = Path("dimostrazione").resolve() if a.qui else Path(tempfile.mkdtemp())
    if a.qui and cartella.exists():
        shutil.rmtree(cartella)
    cartella.mkdir(parents=True, exist_ok=True)

    os.environ["OCCHIO_INVENTARIO"] = str(cartella / "inventario.jsonl")
    os.environ["OCCHIO_CONSEGNE"] = str(cartella / "consegne.jsonl")
    os.environ["OCCHIO_PORTAVIA"] = str(cartella / "portavia.jsonl")
    os.environ["OCCHIO_CREDITI"] = str(cartella / "crediti.jsonl")

    from occhio.cartella import mappa_html
    from occhio.consegna import Consegne, differenza, stampa_differenza
    from occhio.crediti import Crediti
    from occhio.inventario import Inventario
    from occhio.luogo import dal_percorso
    from occhio.portavia import Portavia, Regole, spiega_mancanti, vendita_in_chiari
    from occhio.voce import rispondi

    (cartella / "pianta.json").write_text(
        json.dumps(PIANTA, ensure_ascii=False, indent=2), encoding="utf-8")
    (cartella / "prezzi.json").write_text(
        json.dumps(PREZZI, ensure_ascii=False, indent=2), encoding="utf-8")

    # 1. l'inventario, come se le fotografie fossero state lette
    titolo("1. L'inventario — come se le fotografie fossero state lette")
    reg = Inventario(cartella / "inventario.jsonl")
    for percorso, oggetti in ARREDO:
        posto = dal_percorso(f"/f/{percorso}/x.jpg", "/f")
        for tipo, t in oggetti:
            reg.registra(tipo, t, fonte="foto", confidenza=0.92,
                         luogo=posto, foto_sha="0" * 64)
    print(f"  {len(reg.voci)} oggetti in {len(reg.per_luogo())} luoghi")

    # 2. la consegna, controfirmata
    titolo("2. TALLY — la consegna, controfirmata dall'ospite")
    c = Consegne(cartella / "consegne.jsonl")
    prima = c.deposita(ALLOGGIO, "consegna", reg.voci, SOGGIORNO)
    c.controfirma(prima["impronta"], SOGGIORNO)
    print(f"  impronta {prima['impronta'][:16]}… — controfirmata")

    # 3. PORTAVIA: durante il soggiorno l'ospite compra
    titolo("3. I TRE BANCHI — l'ospite compra invece di portare via")
    regole = Regole(prezzo_minimo=PREZZI["prezzo_minimo"],
                    sconto_massimo=PREZZI["sconto_massimo"],
                    commissione=PREZZI["commissione"], margine=PREZZI["margine"],
                    generi=PREZZI["generi"])
    pv = Portavia(cartella / "portavia.jsonl", regole)
    cr = Crediti(cartella / "crediti.jsonl")
    cr.emetti("ospite", 40, "soggiorno", riferimento=f"soggiorno:{SOGGIORNO}")
    v = vendita_in_chiari(pv, cr, COMPRATO[0], COMPRATO[1],
                          regole.esposto(COMPRATO[0]), "ospite", "proprietario",
                          SOGGIORNO, ALLOGGIO)
    print(f"  «{COMPRATO[1]}» venduto a {v['prezzo']} chiari "
          f"(commissione {v['commissione']}, al proprietario {v['al_proprietario']})")
    print(f"  saldo ospite: {cr.saldo('ospite')} — proprietario: {cr.saldo('proprietario')}")

    # APRILA: la bottiglia si beve, e a fine soggiorno manchera' per davvero
    b = pv.vendita("vino:barolo serralunga 2016", "Barolo Serralunga 2016",
                   regole.esposto("vino:barolo serralunga 2016"),
                   soggiorno=SOGGIORNO, alloggio=ALLOGGIO)
    print(f"  APRILA   «{b['titolo']}» {b['prezzo']:.2f} {b['valuta']} — "
          f"si consuma: a fine soggiorno mancherà, e sarà spiegato")

    # RESTACI: la vasca resta dov'e'. Incassa e non spiega nessuna assenza.
    e = pv.vendita("esperienza:serata in vasca", "Serata in vasca",
                   regole.esposto("esperienza:serata in vasca"),
                   soggiorno=SOGGIORNO, alloggio=ALLOGGIO,
                   quando="giovedì 21:00")
    print(f"  RESTACI  «{e['titolo']}» {e['prezzo']:.2f} {e['valuta']} — "
          f"resta in casa: non spiegherà nessuna assenza")

    # 4. la riconsegna: manca il phon, e il DVD non manca — e' stato comprato
    titolo("4. La differenza — ciò che manca, e ciò che è stato comprato")
    # la bottiglia bevuta manca quanto il phon rubato: la differenza le vede
    # uguali, ed e' il genere della vendita a separarle
    restanti = [x for x in reg.voci
                if x["titolo"] not in (COMPRATO[1], SPARITO,
                                       "Barolo Serralunga 2016")]
    dopo = c.deposita(ALLOGGIO, "riconsegna", restanti, SOGGIORNO)
    c.controfirma(dopo["impronta"], SOGGIORNO)
    d = differenza(prima, dopo)
    print(stampa_differenza(d))
    s = spiega_mancanti(d, pv, SOGGIORNO)
    print(f"\n  COMPRATI: {[o['titolo'] for o in s['comprati']]}")
    print(f"  NON SPIEGATI: {[o['titolo'] for o in s['non_spiegati']]}")

    # 5. la mappa con la pianta
    titolo("5. La mappa e la pianta")
    pagina = cartella / "mappa.html"
    pagina.write_text(
        mappa_html(reg, PIANTA, s, fatte={"ingresso", "soggiorno", "cucina", "terrazzo"}),
        encoding="utf-8")
    print(f"  {pagina}")

    # 6. la voce
    titolo("6. LA VOCE")
    for frase in ("che vini ho in cucina", "dov'è il phon",
                  "quanti dvd ho", "cosa posso cucinare stasera"):
        e = rispondi(reg, frase, regole=regole)
        print(f"  » {frase}\n    {e['testo_risposta'][:110]}")

    titolo("Dove sono i file")
    for f in sorted(cartella.iterdir()):
        print(f"  {f}")
    print(f"\n  Apri la mappa:  {pagina}")
    print("  Tutti i dati sono inventati. Nessun oggetto di casa di nessuno.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
