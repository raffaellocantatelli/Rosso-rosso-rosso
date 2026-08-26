"""CLI di SDQ-1 — Sistema Di Quadranti v1.5."""
import argparse
import json
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from .llm.router import Router, COME_ATTIVARE, REAL_PROVIDERS
from .memory.vector_store import VectorStore
from .agents import pipeline
from .monitoring.health import run_health_check
from .sar import reflect as sar_reflect
from . import daily as daily_mod
from . import backup as backup_mod

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import registro_ipotesi  # noqa: E402
import verificatore  # noqa: E402

CONTATTI_PATH = os.path.join("output", "contatti.jsonl")


def build_parser():
    p = argparse.ArgumentParser(prog="sdq1", description="SDQ-1 — Sistema Di Quadranti v1.5")
    p.add_argument("messaggio", nargs="?", help="Messaggio da elaborare")

    profilo = p.add_mutually_exclusive_group()
    profilo.add_argument("--economia", action="store_true", help="Gemini(free) -> DeepSeek -> Stub")
    profilo.add_argument("--locale", action="store_true", help="Ollama -> Gemini -> Stub")
    profilo.add_argument("--no-api", action="store_true", help="Solo Stub, offline puro")

    p.add_argument("--check", action="store_true", help="Il Core è acceso? Diagnostica dei provider")
    p.add_argument("--purga-memoria", action="store_true", dest="purga_memoria",
                   help="Rimuove dalla memoria gli output Stub (attività senza pensiero)")
    p.add_argument("--health", action="store_true", help="Stato del sistema")
    p.add_argument("--backup", action="store_true", help="Snapshot completo dello stato")
    p.add_argument("--restore", metavar="PATH", help="Ripristina uno snapshot")

    p.add_argument("--daily", action="store_true",
                   help="Riflessione giornaliera sui fatti eseguiti (non entra in memoria)")
    p.add_argument("--ipotesi", action="store_true",
                   help="Stampa il registro delle ipotesi")
    p.add_argument("--verifica-ipotesi", action="store_true", dest="verifica_ipotesi",
                   help="Esegue i criteri di falsificazione invece di leggerli")
    p.add_argument("--prova", action="store_true",
                   help="Con --verifica-ipotesi: esegue senza scrivere niente")

    p.add_argument("--sar", metavar="TENSIONE", help='Es. "Controllo ↔ Fiducia"')
    p.add_argument("--sar-stato", action="store_true", dest="sar_stato")

    p.add_argument("--contatto", action="store_true", help="Registra un contatto reale (per H2)")
    p.add_argument("--tipo")
    p.add_argument("--nota")
    p.add_argument("--verifica")

    return p


def profilo_da_args(args):
    if args.economia:
        return "economia"
    if args.locale:
        return "locale"
    if args.no_api:
        return "no-api"
    return "default"


BANNER_SPENTO = (
    "==============================================================\n"
    "  IL CORE È SPENTO — QUESTO NON È PENSIERO\n"
    "  Nessun provider LLM disponibile: il testo qui sotto è una\n"
    "  ricostruzione strutturale locale (Stub), non l'output di un\n"
    "  modello. Esegui `python -m sdq1 --check` per accenderlo.\n"
    "==============================================================\n"
)


def cmd_check(router):
    """Dice, senza ambiguità, se il Core può pensare e cosa manca."""
    stato = router.stato_provider()
    reali = router.provider_reali_disponibili()

    print("=== SDQ-1 · Il Core è acceso? ===\n")
    for nome in REAL_PROVIDERS:
        segno = "OK  " if stato.get(nome) else "--  "
        riga = f"  {segno}{nome}"
        if not stato.get(nome):
            riga += f"  →  {COME_ATTIVARE[nome]}"
        print(riga)

    print()
    if reali:
        print(f"CORE ACCESO — provider disponibili: {', '.join(reali)}")
        print("Le riflessioni giornaliere saranno generate da un modello vero.")
        return 0

    print("CORE SPENTO — nessun provider reale disponibile.")
    print("Il sistema continuerà a produrre file, ma saranno output Stub:")
    print("attività senza pensiero. Per accenderlo basta UNA delle righe sopra.")
    return 1


def cmd_contatto(args):
    if not args.tipo:
        print("Errore: --contatto richiede almeno --tipo", file=sys.stderr)
        sys.exit(1)
    os.makedirs(os.path.dirname(CONTATTI_PATH), exist_ok=True)
    voce = {
        "tipo": args.tipo,
        "nota": args.nota or "",
        "verifica": args.verifica or "",
        "timestamp": time.time(),
        "data_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(CONTATTI_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(voce, ensure_ascii=False) + "\n")
    print(f"Contatto registrato: {voce}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    router = Router()
    memory = VectorStore()

    if args.check:
        sys.exit(cmd_check(router))

    if args.purga_memoria:
        rimosse = memory.purga_stub()
        print(f"Voci Stub rimosse dalla memoria: {rimosse}")
        print(f"Voci rimaste: {len(memory)}")
        if len(memory) == 0:
            print("\nLa memoria è vuota. È il risultato corretto: non c'era")
            print("nessun pensiero da conservare, solo la registrazione della")
            print("sua assenza. Una memoria vuota è più onesta di una piena di nulla.")
        return

    if args.health:
        record = run_health_check(router, memory)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return

    if args.backup:
        dest = backup_mod.crea_backup()
        print(f"Backup creato in: {dest}")
        return

    if args.restore:
        ripristinati = backup_mod.ripristina_backup(args.restore)
        print("File ripristinati:")
        for f in ripristinati:
            print(f"  - {f}")
        return

    if args.daily:
        profilo = profilo_da_args(args)
        prompt = daily_mod.costruisci_prompt(router)
        try:
            ctx = pipeline.esegui(prompt, profilo, router, memory, memorizza=False)
        except RuntimeError as exc:
            print(f"[sdq1] {exc}", file=sys.stderr)
            sys.exit(2)
        if ctx.provider_used and ctx.provider_used.startswith("stub"):
            print(BANNER_SPENTO)
        print(ctx.final)
        print(f"\n[provider: {ctx.provider_used} | profilo: {profilo}]", file=sys.stderr)
        return

    if args.ipotesi:
        registro_ipotesi.stampa_stato()
        return

    if args.verifica_ipotesi:
        risultati = verificatore.verifica(scrivi=not args.prova)
        verificatore.stampa(risultati)
        if args.prova:
            print("\n(--prova: niente è stato scritto)")
        return

    if args.sar:
        risultato = sar_reflect.reflect(args.sar)
        print(f"=== SAR — {risultato['tensione']} ===\n")
        for livello in risultato["livelli"]:
            print(f"{livello['livello']:>2}. {livello['descrizione']}")
        return

    if args.sar_stato:
        stato = sar_reflect.stato_corrente()
        if not stato:
            print("Nessuna riflessione SAR registrata finora.")
            return
        for r in stato:
            print(f"- {r['tensione']}  ({len(r['livelli'])} livelli, {time.strftime('%Y-%m-%d %H:%M', time.gmtime(r['timestamp']))} UTC)")
        return

    if args.contatto:
        cmd_contatto(args)
        return

    if not args.messaggio:
        build_parser().print_help()
        sys.exit(1)

    profilo = profilo_da_args(args)
    try:
        ctx = pipeline.esegui(args.messaggio, profilo, router, memory)
    except RuntimeError as exc:
        # Nessun provider reale: non inventiamo un output: usciamo con errore,
        # così il fallback esplicito del chiamante (--economia, --no-api) parte.
        print(f"[sdq1] {exc}", file=sys.stderr)
        sys.exit(2)

    if ctx.provider_used and ctx.provider_used.startswith("stub"):
        print(BANNER_SPENTO)

    print(ctx.final)
    print(f"\n[provider: {ctx.provider_used} | profilo: {profilo}]", file=sys.stderr)
    if ctx.manipulation.get("detected"):
        print(f"[SENTIN-004: segnali -> {ctx.manipulation['signals']}]", file=sys.stderr)


if __name__ == "__main__":
    main()
