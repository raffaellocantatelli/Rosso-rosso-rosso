#!/usr/bin/env python3
"""occhio.costo — quanto costa una passata, calcolato invece che ricordato.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Perche' un modulo e non una frase. In questo progetto una cifra scritta in un
documento non vale niente: vale il comando che la ricalcola. I prezzi qui sono
**dati in ingresso dichiarati con la loro data**, non conoscenza del modello —
un modello linguistico ricorda listini vecchi con grande sicurezza, ed e' uno
dei modi piu' facili per far sembrare RECUPERATO qualcosa che e' IPOTESI.

    python -m occhio --costo
    python -m occhio --costo --ritmo 5 --minuti 30 --modello haiku

Prima di prendere una decisione su questi numeri, riapri il listino e
correggi PREZZI: la riga PREZZI_VERIFICATI_IL dice quanto sono vecchi.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# dati in ingresso — ognuno con la sua provenienza
# --------------------------------------------------------------------------

#: RECUPERATO da una tabella di listino datata, non dalla memoria del modello.
#: Dollari per milione di token, (ingresso, uscita).
PREZZI_VERIFICATI_IL = "2026-06-24"
PREZZI = {
    "haiku-4.5": (1.00, 5.00),
    "sonnet-5": (2.00, 10.00),
    "opus-5": (5.00, 25.00),
}

#: RECUPERATO: le immagini sono contate a circa un token per riquadro di
#: 28x28 pixel. Il costo cresce con i PIXEL, non con l'informazione: una foto
#: piu' grande dello stesso scaffale costa di piu' e non legge di piu'.
LATO_RIQUADRO = 28

#: RECUPERATO da occhio/web/app.js:126 — il fotogramma spedito ha 1024 px sul
#: lato lungo. E' gia' una scelta di costo: a 1920 costerebbe 3,5 volte tanto.
LATO_LUNGO = 1024
PROPORZIONE = 16 / 9

#: STIMA, non recupero: 1038 caratteri di istruzione (misurati) / ~3,5
#: caratteri per token in italiano. Sovrastimare qui e' innocuo, il peso vero
#: e' l'immagine.
TOKEN_ISTRUZIONE = 300
#: STIMA: un JSON con 3-5 oggetti. Sovrascrivibile.
TOKEN_USCITA = 250

#: RECUPERATO: l'API a lotti costa meta', ma e' asincrona — inutile per il
#: video dal vivo, decisiva per il modo a fotografie.
SCONTO_LOTTI = 0.50


def token_immagine(lato_lungo=LATO_LUNGO, proporzione=PROPORZIONE) -> int:
    lato_corto = lato_lungo / proporzione
    return int(lato_lungo * lato_corto / (LATO_RIQUADRO ** 2))


def costo_fotogramma(modello="haiku-4.5", lotti=False, **kw) -> float:
    ingresso, uscita = PREZZI[modello]
    t_in = token_immagine(**kw) + TOKEN_ISTRUZIONE
    costo = (t_in * ingresso + TOKEN_USCITA * uscita) / 1_000_000
    return costo * (SCONTO_LOTTI if lotti else 1.0)


def passata(minuti=10.0, ritmo_secondi=2.5, modello="haiku-4.5", lotti=False):
    """Quanto costa camminare per `minuti` a un fotogramma ogni `ritmo`."""
    fotogrammi = int(minuti * 60 / ritmo_secondi)
    unitario = costo_fotogramma(modello, lotti)
    return {
        "fotogrammi": fotogrammi,
        "token_immagine": token_immagine(),
        "costo_fotogramma": unitario,
        "costo_passata": fotogrammi * unitario,
        "costo_ora": (3600 / ritmo_secondi) * unitario,
    }


def stampa(minuti=10.0, ritmo=2.5, modello=None):
    modelli = [modello] if modello else list(PREZZI)
    print(f"occhio — costo di una passata\n")
    print(f"  prezzi dichiarati il {PREZZI_VERIFICATI_IL}. Se oggi e' molto piu'")
    print(f"  tardi di quella data, riaprili prima di decidere qualcosa.\n")
    print(f"  fotogramma {LATO_LUNGO}px  ->  ~{token_immagine()} token di immagine")
    print(f"  + {TOKEN_ISTRUZIONE} di istruzione (stima), {TOKEN_USCITA} in uscita (stima)\n")
    print(f"  {minuti:g} minuti di cammino a un fotogramma ogni {ritmo:g} s:\n")
    intest = f"  {'modello':<12} {'$/fotogr.':>10} {'$/passata':>11} {'$/ora':>9}   {'$/ora a lotti':>13}"
    print(intest)
    print("  " + "-" * (len(intest) - 2))
    for m in modelli:
        d = passata(minuti, ritmo, m)
        dl = passata(minuti, ritmo, m, lotti=True)
        print(f"  {m:<12} {d['costo_fotogramma']:>10.5f} {d['costo_passata']:>11.2f}"
              f" {d['costo_ora']:>9.2f}   {dl['costo_ora']:>13.2f}")
    print(f"\n  {passata(minuti, ritmo)['fotogrammi']} chiamate in {minuti:g} minuti.")
    print("  La variabile che governa la spesa e' il ritmo, non la grafica.")
    print("  Lo sconto a lotti vale solo per il modo a fotografie: e' asincrono,")
    print("  quindi inutile per il video dal vivo.\n")
    print("  Cio' che questo calcolo NON dice, e che nessun calcolo puo' dire:")
    print("  quanti oggetti vengono letti per ogni fotogramma. Il costo per")
    print("  OGGETTO — l'unico che conti — si ottiene solo camminando e contando.")
