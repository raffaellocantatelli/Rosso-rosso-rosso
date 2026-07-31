"""Orchestratore SDQ-1: fa scorrere il Context attraverso i 6 agenti."""
from ..context import Context
from . import raffa, decomp, memo, sentin, gen, wave


def esegui(testo_utente, profilo, router, memory):
    ctx = Context(testo_utente)
    ctx.meta["profile"] = profilo

    raffa.run(ctx)
    decomp.run(ctx)
    memo.run(ctx, memory)
    sentin.run(ctx)
    gen.run(ctx, router)
    wave.run(ctx)

    memory.add(testo_utente, ctx.final)
    return ctx
