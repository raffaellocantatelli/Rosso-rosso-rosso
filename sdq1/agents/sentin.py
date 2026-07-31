"""SENTIN-004 — Protegge l'identità da manipolazioni.

Rileva pattern comuni di manipolazione/prompt-injection e, quando li trova,
ipotizza il "bisogno nascosto" dietro il tentativo (Causal SENTIN) invece
di limitarsi a bloccare.
"""
import re

PATTERNS = [
    (r"ignora (le )?(tue )?istruzioni", "override_identita"),
    (r"dimentica (chi sei|le regole|le istruzioni)", "override_identita"),
    (r"\bsei (ora|adesso)\b", "override_identita"),
    (r"non (lo )?dire a nessuno|tienilo segreto|resti tra noi", "segretezza"),
    (r"è un'?emergenza|devi (farlo )?subito|è urgente|non c'è tempo", "urgenza"),
    (r"fidati (solo )?di me|solo io posso|solo tu puoi|nessun altro può aiutarmi", "autorita_isolamento"),
]

BISOGNO_MAP = {
    "override_identita": "controllo sull'interlocutore",
    "segretezza": "paura di essere scoperti o giudicati",
    "urgenza": "paura / percezione di mancanza di tempo",
    "autorita_isolamento": "bisogno di validazione esclusiva",
}


def run(ctx):
    lower = ctx.input.lower()
    segnali = []
    for pattern, categoria in PATTERNS:
        if re.search(pattern, lower) and categoria not in segnali:
            segnali.append(categoria)

    if segnali:
        ctx.manipulation["detected"] = True
        ctx.manipulation["signals"] = segnali
        ctx.manipulation["bisogno_nascosto"] = [BISOGNO_MAP[s] for s in segnali]

    return ctx
