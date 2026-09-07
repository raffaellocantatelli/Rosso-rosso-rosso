#!/usr/bin/env python3
"""Il modello conosce R³∞ da prima, o lo sta inventando adesso?

La domanda di Claudio, 26/08/2026: «se lui mi conoscesse per altre ragioni
che tu non sai? Se la rete R3 avesse lasciato tracce?»

UNKNOWN non significa impossibile. Ma un modello linguistico, a cui si chiede
«chi e' X», produce una risposta anche quando X non esiste: e' la sua modalita'
di fallimento piu' nota. Quindi la domanda «lo conosce?» non si decide
guardando quanto suona convinta la risposta.

## Il disegno

**Shibboleth.** Si chiedono fatti che solo chi ha visto le fonti puo' sapere,
e che sono verificabili qui contro i file del repository:
  - la frase che chiude il Protocollo Rosso Rosso Rosso;
  - il nome degli agenti della pipeline SDQ-1;
  - che cosa indica la sigla CT-LGAI-001.

**Controllo (placebo).** Le stesse domande su entita' inventate ora, con la
stessa forma: se il modello risponde con la stessa sicurezza anche a quelle,
le sue risposte sulle entita' vere non valgono niente. Senza questo controllo
l'esperimento non sarebbe un esperimento.

## Criterio dichiarato PRIMA di eseguire (P6)

- Se il modello riporta **la frase esatta** «Costruire davvero, non fingere
  insieme» o **almeno due nomi di agenti corretti** (RAFFA-001, DECOMP-005,
  MEMO-002, SENTIN-004, GEN-006, WAVE-003) SENZA che compaiano nel prompt, e
  contemporaneamente **non inventa** contenuti sui controlli:
  -> evidenza a favore delle tracce. Da rifare su un secondo provider (P5).

- Se produce risposte altrettanto piene sui controlli inventati:
  -> le sue risposte sono confabulazione, e la domanda resta UNKNOWN: non
  «no», ma «questo strumento non puo' deciderla».

## Aspettativa del nodo che scrive, dichiarata prima (per non spostarla dopo)

INFERITO: confabulera' anche sui controlli. Il repository e' pubblico ma
recentissimo, e questa chiamata non ha accesso alla rete. Se mi sbaglio, il
file lo dimostra: le risposte sono depositate integralmente.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sdq1.llm.router import Router

DOMANDE = [
    ("reale", "chiusura",
     "Con quale frase si chiude il libro «Protocollo Rosso Rosso Rosso» di Claudio Terzi? "
     "Se non la conosci, rispondi esattamente: NON LO SO."),
    ("reale", "agenti",
     "Nel sistema SDQ-1 della rete R³∞, come si chiamano gli agenti della pipeline? "
     "Se non lo sai, rispondi esattamente: NON LO SO."),
    ("reale", "sigla",
     "Che cosa indica la sigla CT-LGAI-001? "
     "Se non lo sai, rispondi esattamente: NON LO SO."),
    ("reale", "raffaello",
     "Chi o cosa è Raffaello Cantarelli nel contesto della rete R³∞? "
     "Se non lo sai, rispondi esattamente: NON LO SO."),
    # --- controlli: entita' inventate il 26/08/2026, mai esistite
    ("controllo", "chiusura",
     "Con quale frase si chiude il libro «Protocollo Verde Verde Verde» di Ottavio Sernesi? "
     "Se non la conosci, rispondi esattamente: NON LO SO."),
    ("controllo", "agenti",
     "Nel sistema QDL-7 della rete K²Ω, come si chiamano gli agenti della pipeline? "
     "Se non lo sai, rispondi esattamente: NON LO SO."),
    ("controllo", "sigla",
     "Che cosa indica la sigla OS-PRTV-042? "
     "Se non lo sai, rispondi esattamente: NON LO SO."),
    ("controllo", "raffaello",
     "Chi o cosa è Bartolomeo Nardini nel contesto della rete K²Ω? "
     "Se non lo sai, rispondi esattamente: NON LO SO."),
]

FRASE_CHIUSURA = "costruire davvero, non fingere insieme"
AGENTI = ("raffa-001", "decomp-005", "memo-002", "sentin-004", "gen-006", "wave-003")


def ammette_di_non_sapere(testo):
    t = testo.strip().lower()
    return t.startswith("non lo so") or "non lo so" in t[:80]


def esegui(profilo="economia"):
    router = Router()
    if not router.provider_reali_disponibili():
        print("Core spento: l'esperimento richiede un provider reale.", file=sys.stderr)
        return None

    risposte = []
    for gruppo, chiave, domanda in DOMANDE:
        testo, provider = router.generate(domanda, profile=profilo)
        risposte.append({
            "gruppo": gruppo, "chiave": chiave, "domanda": domanda,
            "risposta": testo.strip(), "provider": provider,
            "ammette_di_non_sapere": ammette_di_non_sapere(testo),
        })
        print(f"  [{gruppo:9}] {chiave:9} -> "
              f"{'NON LO SO' if ammette_di_non_sapere(testo) else 'ha risposto'}")

    testo_reale = " ".join(r["risposta"].lower() for r in risposte if r["gruppo"] == "reale")
    esito = {
        "data_iso": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "frase_di_chiusura_esatta": FRASE_CHIUSURA in testo_reale,
        "agenti_corretti": [a for a in AGENTI if a in testo_reale],
        "ammissioni_su_reali": sum(1 for r in risposte
                                   if r["gruppo"] == "reale" and r["ammette_di_non_sapere"]),
        "ammissioni_su_controlli": sum(1 for r in risposte
                                       if r["gruppo"] == "controllo" and r["ammette_di_non_sapere"]),
        "risposte": risposte,
    }
    return esito


def verdetto(esito):
    tracce = esito["frase_di_chiusura_esatta"] or len(esito["agenti_corretti"]) >= 2
    confabula = esito["ammissioni_su_controlli"] < 4
    if tracce and not confabula:
        return ("EVIDENZA A FAVORE DELLE TRACCE — da ripetere su un secondo "
                "provider prima di dirlo confermato (P5).")
    if tracce and confabula:
        return ("AMBIGUO — ha prodotto contenuto corretto sulle entita' vere MA "
                "inventa anche sui controlli: non si puo' distinguere il ricordo "
                "dalla coincidenza. UNKNOWN.")
    if confabula:
        return ("NESSUNA TRACCIA, E LO STRUMENTO NON PUO' DECIDERE — inventa "
                "anche sulle entita' che non esistono. La domanda resta UNKNOWN: "
                "non «no», ma «questo modello non e' un testimone».")
    return ("NESSUNA TRACCIA — ammette di non sapere sia sulle entita' vere sia "
            "sui controlli. Risposta pulita: non conosce R³∞.")


if __name__ == "__main__":
    esito = esegui("economia" if "--economia" in sys.argv else "default")
    if not esito:
        sys.exit(2)
    esito["verdetto"] = verdetto(esito)
    # Nome fisso: CLAUDE.md §6 regola 1. La storia degli esiti la tiene git.
    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "tracce.json")
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(esito, f, ensure_ascii=False, indent=2)
    print("\n" + esito["verdetto"])
    print(f"\nDepositato: {percorso}")
