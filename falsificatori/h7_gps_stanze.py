#!/usr/bin/env python3
"""H7 — «La geolocalizzazione delle foto distingue le stanze di una casa».

Origine protetta: Claudio Terzi [CT-LGAI-001].

Questa ipotesi esiste perché è quella che vorrei fosse vera: se lo fosse,
una mappa degli oggetti si costruirebbe da sola, senza chiedere niente a
nessuno. È esattamente per questo che va messa alla prova prima di scriverci
sopra del codice — CLAUDE.md §4: quando una metrica migliora senza che nulla
sia entrato dall'esterno, sospetta l'eco. Una mappa fatta di coordinate
rumorose *sembra* un dato misurato, e nessuno la rimette più in dubbio.

**Non ti chiedo di credermi sull'errore del GPS in casa.** Le fotografie
dell'iPhone scrivono un campo apposta, `GPSHPositioningError` (tag 0x001F),
in cui il telefono dichiara da solo di quanto può sbagliare. Questo script
legge quel campo dalle TUE foto e lo confronta con la distanza fra le stanze.
Il numero è tuo.

Come si esegue — servono almeno due stanze, tre foto per stanza:

    mkdir -p ~/prova-gps/{salotto,cucina,camera}
    # scatta 3 foto in ogni stanza, mettile nella cartella giusta
    python3 falsificatori/h7_gps_stanze.py ~/prova-gps

H7 CADE se la distanza fra le stanze è più piccola dell'errore che il
telefono stesso dichiara: in quel caso le coordinate non separano niente e
la mappa GPS va buttata, non migliorata.

Esce 0 se H7 CADE, 1 se REGGE, 2 se non conclusa (convenzione dei
falsificatori di questo repository).
"""

import os
import statistics
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

from occhio.luogo import distanza_m, exif  # noqa: E402

ESTENSIONI = {".jpg", ".jpeg"}

#: Quando il telefono non dichiara il proprio errore, non se ne inventa uno:
#: il confronto si sposta sulla dispersione DENTRO una stanza, che è misurata
#: e non assunta. Due foto scattate a un metro l'una dall'altra dovrebbero
#: distare un metro: quanto distano davvero è la risposta.
MINIME_PER_STANZA = 2


def raccogli(cartella):
    """Una cartella per stanza. Restituisce {stanza: [scheda, ...]}."""
    stanze = {}
    for nome in sorted(os.listdir(cartella)):
        sotto = os.path.join(cartella, nome)
        if not os.path.isdir(sotto):
            continue
        schede = []
        for f in sorted(os.listdir(sotto)):
            if os.path.splitext(f)[1].lower() not in ESTENSIONI:
                continue
            d = exif(os.path.join(sotto, f))
            d["file"] = f
            schede.append(d)
        if schede:
            stanze[nome] = schede
    return stanze


def centro(schede):
    punti = [s["gps"] for s in schede if s.get("gps")]
    if not punti:
        return None
    return {"lat": statistics.fmean(p["lat"] for p in punti),
            "lon": statistics.fmean(p["lon"] for p in punti)}


def dispersione(schede):
    """Quanto si sparpagliano fra loro foto scattate nella STESSA stanza."""
    c = centro(schede)
    punti = [s["gps"] for s in schede if s.get("gps")]
    if not c or len(punti) < 2:
        return None
    return statistics.fmean(distanza_m(c, p) for p in punti)


def main():
    if len(sys.argv) < 2:
        print(__doc__.split("Come si esegue")[1].split("H7 CADE")[0].strip(),
              file=sys.stderr)
        print("\nnessuna cartella indicata: verifica non conclusa", file=sys.stderr)
        return 2
    cartella = os.path.expanduser(sys.argv[1])
    if not os.path.isdir(cartella):
        print(f"non è una cartella: {cartella}", file=sys.stderr)
        return 2

    stanze = raccogli(cartella)
    if len(stanze) < 2:
        print(f"servono almeno 2 sottocartelle con foto, trovate {len(stanze)}: "
              "verifica non conclusa", file=sys.stderr)
        return 2

    tutte = [s for schede in stanze.values() for s in schede]
    con_gps = [s for s in tutte if s.get("gps")]
    errori = [s["errore_gps_m"] for s in tutte if s.get("errore_gps_m")]

    print(f"cartella: {cartella}")
    print(f"stanze: {len(stanze)} — foto: {len(tutte)} — con GPS: {len(con_gps)}\n")
    for nome, schede in stanze.items():
        d = dispersione(schede)
        c = centro(schede)
        print(f"  {nome:<16} {len(schede)} foto"
              f"  centro {'%.6f, %.6f' % (c['lat'], c['lon']) if c else 'UNKNOWN'}"
              f"  dispersione interna {('%.1f m' % d) if d is not None else 'UNKNOWN'}")

    if not con_gps:
        print("\nNessuna foto porta una posizione GPS.")
        print("Questo NON è un fallimento del test: è una risposta, e la più")
        print("comune in casa. Se il telefono non scrive la posizione, la mappa")
        print("GPS non è «da tarare», non esiste proprio. Verifica non conclusa")
        print("come ipotesi; conclusa come decisione: dichiara le stanze a mano.")
        return 2

    if errori:
        errore_tipico = statistics.median(errori)
        fonte_errore = f"dichiarato dal telefono su {len(errori)} foto"
    else:
        interne = [d for d in (dispersione(s) for s in stanze.values()) if d]
        if not interne:
            print("\ntroppe poche foto con GPS per misurare: verifica non conclusa",
                  file=sys.stderr)
            return 2
        errore_tipico = statistics.median(interne)
        fonte_errore = "misurato come dispersione dentro le stanze (il telefono non lo dichiara)"

    centri = {n: centro(s) for n, s in stanze.items() if centro(s)}
    nomi = list(centri)
    distanze = [(a, b, distanza_m(centri[a], centri[b]))
                for i, a in enumerate(nomi) for b in nomi[i + 1:]]
    if not distanze:
        print("\nuna sola stanza ha coordinate: verifica non conclusa", file=sys.stderr)
        return 2

    print(f"\nerrore tipico: {errore_tipico:.1f} m  ({fonte_errore})")
    print("distanze fra i centri delle stanze:")
    for a, b, d in sorted(distanze, key=lambda x: x[2]):
        segno = "<" if d < errore_tipico else ">="
        print(f"  {a} ↔ {b}: {d:.1f} m  {segno} errore")

    separazione = statistics.median(d for _, _, d in distanze)
    print(f"\nseparazione tipica fra stanze: {separazione:.1f} m")

    if separazione < errore_tipico:
        print("\nH7 CADUTA — le stanze distano meno dell'errore della misura.")
        print("Le coordinate delle foto non separano le stanze di questa casa:")
        print("una mappa costruita su di esse mostrerebbe rumore con l'aria di")
        print("un dato. La posizione va dichiarata, non deradotta dal GPS.")
        print("Il GPS resta utile FUORI: magazzini, cantine, sopralluoghi.")
        return 0

    print("\nH7 REGGE su questa esecuzione: le stanze sono più lontane fra loro")
    print(f"dell'errore dichiarato ({separazione:.1f} m contro {errore_tipico:.1f} m).")
    print("Reggere non è confermare. Rifallo in un altro momento della giornata:")
    print("la posizione fusa Wi-Fi/celle cambia con la rete, non con la casa.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
