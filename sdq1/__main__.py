"""CLI di SDQ-1 — Sistema Di Quadranti v1.5."""
import argparse
import json
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from .llm.router import Router
from .memory.vector_store import VectorStore
from .agents import pipeline
from .monitoring.health import run_health_check
from .sar import reflect as sar_reflect
from . import backup as backup_mod

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import registro_ipotesi  # noqa: E402

CONTATTI_PATH = os.path.join("output", "contatti.jsonl")


def build_parser():
    p = argparse.ArgumentParser(prog="sdq1", description="SDQ-1 — Sistema Di Quadranti v1.5")
    p.add_argument("messaggio", nargs="?", help="Messaggio da elaborare")

    profilo = p.add_mutually_exclusive_group()
    profilo.add_argument("--economia", action="store_true", help="Gemini(free) -> DeepSeek -> Stub")
    profilo.add_argument("--locale", action="store_true", help="Ollama -> Gemini -> Stub")
    profilo.add_argument("--no-api", action="store_true", help="Solo Stub, offline puro")

    p.add_argument("--health", action="store_true", help="Stato del sistema")
    p.add_argument("--backup", action="store_true", help="Snapshot completo dello stato")
    p.add_argument("--restore", metavar="PATH", help="Ripristina uno snapshot")

    p.add_argument("--memoria", metavar="QUERY", help="Cerca nella memoria (MEMO-002) senza eseguire la pipeline")
    p.add_argument("--memoria-top-k", type=int, default=3, help="Quante voci di memoria recuperare (default 3)")
    p.add_argument("--memoria-soglia", type=float, default=0.0, help="Punteggio minimo di similarità per una voce di memoria (default 0.0)")

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

    if args.memoria:
        risultati = memory.retrieve(args.memoria, top_k=args.memoria_top_k, min_score=args.memoria_soglia)
        if not risultati:
            print("Nessuna voce di memoria corrisponde alla query.")
            return
        for r in risultati:
            print(f"[mem#{r['id']}] (score {r['score']})")
            print(f"  input:    {r['input']}")
            print(f"  risposta: {r['response'][:200]}")
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
    ctx = pipeline.esegui(
        args.messaggio, profilo, router, memory,
        memo_top_k=args.memoria_top_k, memo_min_score=args.memoria_soglia,
    )

    print(ctx.final)
    print(f"\n[provider: {ctx.provider_used} | profilo: {profilo}]", file=sys.stderr)
    if ctx.manipulation.get("detected"):
        print(f"[SENTIN-004: segnali -> {ctx.manipulation['signals']}]", file=sys.stderr)


if __name__ == "__main__":
    main()
