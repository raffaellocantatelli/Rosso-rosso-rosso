"""MEMO-002 — Recupera contesto rilevante dalla memoria vettoriale.

La ricerca vera e propria vive in memory.vector_store (chiamata dalla
pipeline, che ha il riferimento al VectorStore condiviso); questo modulo
resta un punto di estensione per logica di recupero più elaborata in futuro.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""


def run(ctx, memory):
    ctx.memory_hits = memory.retrieve(ctx.input)
    return ctx
