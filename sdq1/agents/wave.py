"""WAVE-003 — Affina tono e stile della risposta finale.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""


def run(ctx):
    text = (ctx.draft or "").strip()
    if text and text[-1] not in ".!?":
        text += "."
    ctx.final = text
    return ctx
