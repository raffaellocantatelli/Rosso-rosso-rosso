"""DECOMP-005 — Decompone l'input in sotto-obiettivi.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import re

_SPLIT_RE = re.compile(r"\s*(?:,|;|\.\s+|\be poi\b|\bpoi\b|\be\b)\s*", re.IGNORECASE)


def run(ctx):
    text = ctx.input.strip()
    parti = [p.strip() for p in _SPLIT_RE.split(text) if p and p.strip()]
    ctx.subgoals = parti if parti else [text]
    return ctx
