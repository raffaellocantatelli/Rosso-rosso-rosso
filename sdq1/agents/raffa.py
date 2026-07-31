"""RAFFA-001 — Analisi semantica: legge l'intento dell'input."""
import re

STOPWORDS = {
    "che", "come", "dove", "quando", "perche", "perché", "quale", "quali",
    "questo", "questa", "questi", "queste", "sono", "essere", "avere",
    "della", "dello", "delle", "degli", "nella", "nello", "nelle", "negli",
    "anche", "molto", "poco", "loro", "nostro", "vostro", "quello", "quella",
}
QUESTION_STARTS = ("chi ", "cosa ", "come ", "quando ", "dove ", "perché ", "perche ", "quale ", "quanti ")
COMMAND_WORDS = {"fai", "crea", "genera", "esegui", "avvia", "mostra", "scrivi", "analizza", "calcola", "costruisci"}


def run(ctx):
    text = ctx.input.strip()
    lower = text.lower()

    if text.endswith("?") or lower.startswith(QUESTION_STARTS):
        tipo = "domanda"
    elif COMMAND_WORDS & set(lower.split()):
        tipo = "comando"
    else:
        tipo = "affermazione"

    parole = re.findall(r"[a-zàèéìòù]{4,}", lower)
    parole_chiave = sorted(set(parole) - STOPWORDS)[:8]

    ctx.intent = {"tipo": tipo, "parole_chiave": parole_chiave, "lunghezza": len(text)}
    return ctx
