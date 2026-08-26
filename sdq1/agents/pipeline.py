"""Orchestratore SDQ-1: fa scorrere il Context attraverso i 6 agenti."""
from ..context import Context
from . import raffa, decomp, memo, sentin, gen, wave


def esegui(testo_utente, profilo, router, memory, memorizza=True):
    ctx = Context(testo_utente)
    ctx.meta["profile"] = profilo

    raffa.run(ctx)
    decomp.run(ctx)
    memo.run(ctx, memory)
    sentin.run(ctx)
    gen.run(ctx, router)
    wave.run(ctx)

    # Il provider viene passato perche' la memoria rifiuti gli output Stub:
    # un giorno senza pensiero non deve diventare il contesto del giorno dopo.
    #
    # memorizza=False serve al daily. Il fix del 22/08 fermava solo gli Stub,
    # ma il difetto non era lo Stub: era che il sistema rileggeva le proprie
    # riflessioni come "contesto rilevante". Con un provider vero succedeva
    # di nuovo, senza nemmeno il banner ad avvisare. Il verbale del daily e'
    # il file in output/, non una voce di memoria.
    if memorizza:
        memory.add(testo_utente, ctx.final, provider=ctx.provider_used)
    return ctx
