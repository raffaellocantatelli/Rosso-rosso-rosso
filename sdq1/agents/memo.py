"""MEMO-002 — Recupera contesto rilevante dalla memoria vettoriale.

La ricerca vera e propria vive in memory.vector_store (chiamata dalla
pipeline, che ha il riferimento al VectorStore condiviso); questo modulo
resta un punto di estensione per logica di recupero più elaborata in futuro.
"""


def run(ctx, memory):
    top_k = ctx.meta.get("memo_top_k", 3)
    min_score = ctx.meta.get("memo_min_score", 0.0)
    ctx.memory_hits = memory.retrieve(ctx.input, top_k=top_k, min_score=min_score)
    return ctx
