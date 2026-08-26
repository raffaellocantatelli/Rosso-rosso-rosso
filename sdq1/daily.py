"""Il daily riflette sui fatti, non sul vuoto.

Perché esiste
-------------
Il 26/08/2026, il primo giorno in cui un provider reale è stato disponibile,
il daily ha prodotto questo:

    Tasso di completamento sotto-obiettivi: 100%
    Allineamento al contesto: Elevato
    Stato sistema: OTTIMALE

Nessuno di quei numeri era stato misurato. Non è stata una bugia del modello:
il prompt era «Riflessione giornaliera del sistema SDQ-1.» e non conteneva
**nessun dato**. Gli si chiedeva di riflettere su un sistema senza dirgli
niente del sistema. Inventare era l'unica cosa che poteva fare.

Peggio: quel testo non è uno Stub, quindi la guardia anti-eco di
`vector_store.add` lo accettava, e il giorno dopo sarebbe tornato come
«contesto rilevante dalla memoria». È il difetto §4.2 di CLAUDE.md riaperto
con un provider vero — e senza banner che avverta.

Due correzioni, qui dentro:

1. il prompt porta i fatti **eseguiti**: health log, stato delle ipotesi,
   verifiche, contatti, osservazioni. Ogni numero che il modello scrive deve
   venire da qui, e se un dato manca deve scrivere UNKNOWN;
2. il daily **non entra in memoria** (`memorizza=False`). Il suo verbale è il
   file in `output/`. Un sistema che rilegge le proprie riflessioni come
   contesto si alimenta di sé stesso, che l'abbia pensate o no.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(RADICE, "output")


def _righe_jsonl(percorso, ultime=None):
    if not os.path.exists(percorso):
        return []
    voci = []
    with open(percorso, "r", encoding="utf-8") as f:
        for riga in f:
            riga = riga.strip()
            if not riga:
                continue
            try:
                voci.append(json.loads(riga))
            except json.JSONDecodeError:
                continue
    return voci[-ultime:] if ultime else voci


def raccogli_fatti(router=None):
    """Solo cose lette da file o osservate eseguendo. Niente stime."""
    fatti = {}

    health = _righe_jsonl(os.path.join(OUTPUT, "health_log.jsonl"))
    senza_provider = 0
    for record in health:
        provider = record.get("providers") or {}
        reali = [n for n in ("anthropic", "gemini", "deepseek", "ollama")
                 if (provider.get(n) or {}).get("disponibile")]
        if not reali:
            senza_provider += 1
    fatti["health"] = {
        "rilevazioni_totali": len(health),
        "rilevazioni_senza_provider_reale": senza_provider,
        "ultima": health[-1].get("data_iso") if health else None,
    }

    if router is not None:
        fatti["provider_disponibili_ora"] = router.provider_reali_disponibili()

    registro = os.path.join(RADICE, "registro_ipotesi.json")
    if os.path.exists(registro):
        with open(registro, "r", encoding="utf-8") as f:
            fatti["ipotesi"] = [
                {"id": h["id"], "stato": h["stato"],
                 "verifiche": (h.get("verifiche") or {}).get("eseguite", 0)}
                for h in json.load(f)
            ]

    verifiche = _righe_jsonl(os.path.join(OUTPUT, "verifiche.jsonl"), ultime=8)
    fatti["verifiche_recenti"] = [
        {"ipotesi": v.get("ipotesi"), "esito": v.get("esito"),
         "declassamento": v.get("declassamento"), "data": v.get("data_iso")}
        for v in verifiche
    ]

    contatti = _righe_jsonl(os.path.join(OUTPUT, "contatti.jsonl"))
    fatti["contatti_registrati"] = len(contatti)

    osservazioni = _righe_jsonl(os.path.join(RADICE, "registro_osservazioni.jsonl"))
    fatti["osservazioni_depositate"] = len(osservazioni)

    if os.path.isdir(OUTPUT):
        daily = sorted(n for n in os.listdir(OUTPUT) if n.startswith("daily_"))
        fatti["daily"] = {"totali": len(daily), "ultimo": daily[-1] if daily else None}

    return fatti


ISTRUZIONI = """\
Sei GEN-006. Scrivi la riflessione giornaliera del sistema SDQ-1.

Regole non negoziabili, dal Protocollo Rosso Rosso Rosso di Claudio Terzi:

1. Usa SOLO i fatti nel blocco DATI qui sotto. Non c'è nient'altro che tu
   sappia di questo sistema.
2. NON inventare metriche. Se un numero non è nei DATI, quel numero non
   esiste: scrivi UNKNOWN. Percentuali, punteggi di qualità e giudizi come
   «ottimale» o «elevato» non sono nei DATI e non vanno scritti.
3. Etichetta ogni affermazione: RECUPERATO (letto nei DATI), INFERITO
   (dedotto dai DATI), IPOTESI (da verificare), UNKNOWN (non decidibile
   da qui).
4. Se i DATI mostrano qualcosa che non va, dillo. Una riflessione che
   trova sempre tutto in ordine non sta guardando.
5. Al massimo 300 parole. Chiudi con una riga sola: la cosa più utile da
   fare domani, che sia verificabile.

DATI (letti dai file o osservati eseguendo, oggi):
"""


def costruisci_prompt(router=None, fatti=None):
    fatti = raccogli_fatti(router) if fatti is None else fatti
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"{ISTRUZIONI}\n{json.dumps(fatti, ensure_ascii=False, indent=2)}\n\n"
        f"Data di oggi: {oggi}."
    )
