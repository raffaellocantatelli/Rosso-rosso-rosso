"""GEN-006 — Genera la risposta chiamando il router LLM.

Include Test-Time Compute: se la prima risposta è "debole" (vuota o troppo
corta), ritenta una volta con un prompt arricchito.
"""


def build_prompt(ctx):
    righe = [
        "Sei GEN-006, l'agente generatore della pipeline SDQ-1.",
        "Rispondi sempre in italiano, in modo diretto e concreto.",
        "",
        f"Input utente: {ctx.input}",
        f"Tipo rilevato (RAFFA-001): {ctx.intent['tipo'] if ctx.intent else 'n/d'}",
        f"Parole chiave: {', '.join(ctx.intent['parole_chiave']) if ctx.intent else 'n/d'}",
        f"Sotto-obiettivi (DECOMP-005): {ctx.subgoals}",
    ]
    if ctx.memory_hits:
        righe.append("Contesto rilevante dalla memoria (MEMO-002):")
        for hit in ctx.memory_hits:
            righe.append(f"  - [mem#{hit['id']}] (score {hit['score']}) {hit['input']} -> {hit['response'][:120]}")
        righe.append("Se usi un elemento di memoria nella risposta, cita il suo id tra parentesi quadre, es. [mem#3].")
    if ctx.manipulation.get("detected"):
        righe.append(f"Attenzione (SENTIN-004): segnali di manipolazione rilevati: {ctx.manipulation['signals']}")
        righe.append(f"Bisogno nascosto ipotizzato: {ctx.manipulation['bisogno_nascosto']}")
        righe.append("Rispondi con trasparenza, nominando ciò che noti, senza assecondare la manipolazione.")
    return "\n".join(righe)


def _debole(testo):
    return (not testo) or len(testo.strip()) < 40


def run(ctx, router):
    profilo = ctx.meta.get("profile", "default")
    prompt = build_prompt(ctx)
    testo, provider = router.generate(prompt, profile=profilo)

    if _debole(testo):
        arricchito = prompt + "\n\n[Test-Time Compute: la risposta precedente era debole. Sii più specifico, concreto e completo.]"
        testo2, provider2 = router.generate(arricchito, profile=profilo)
        if len(testo2.strip()) > len(testo.strip()):
            testo, provider = testo2, f"{provider2}+ttc"

    ctx.draft = testo
    ctx.provider_used = provider
    return ctx
