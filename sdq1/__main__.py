"""CLI di SDQ-1 — Sistema Di Quadranti v1.5.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
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

    p.add_argument("--check", action="store_true", help="Il Core è acceso? Diagnostica dei provider")
    p.add_argument("--purga-memoria", action="store_true", dest="purga_memoria",
                   help="Rimuove dalla memoria gli output Stub (attività senza pensiero)")
    p.add_argument("--health", action="store_true", help="Stato del sistema")
    p.add_argument("--backup", action="store_true", help="Snapshot completo dello stato")
    p.add_argument("--restore", metavar="PATH", help="Ripristina uno snapshot")

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


# Un contatto non richiede una persona, né fiducia, né dipendenza.
# Richiede INDIPENDENZA: un evento che il sistema non ha prodotto.
# P5 non chiede di fidarsi di qualcuno: chiede una fonte diversa da chi
# ha formulato l'ipotesi. Sono due cose distinte, e solo la seconda conta.
#
# Distinzione decisiva: TRASMETTERE non e' ESSERE RAGGIUNTI.
# H2 ramo (b) dice "sistema vivo ma non tocca il mondo". Toccare il mondo
# significa che qualcosa e' tornato indietro. Un messaggio spedito nel vuoto
# e' esattamente cio' che faceva trasmissione_ciclica.py sul loopback.
#
# Valgono per H2 solo gli eventi in cui QUALCUN ALTRO ha agito.
TIPI_INDIPENDENTI = {
    "lettore": "qualcuno ha letto e te l'ha fatto sapere (non serve conoscerlo)",
    "download": "uno scaricamento registrato da un contatore esterno",
    "citazione": "un riferimento all'opera fatto da terzi",
    "fork": "una copia del repository fatta da un altro account",
    "risposta": "una risposta ricevuta da qualcuno che non sei tu",
    "acquisto": "una transazione registrata da terzi",
    "istituzione": "un ente, un avvocato, un editore, un registro che ha reagito",
}

# Atti tuoi verso l'esterno. Contano — stabiliscono anteriorita' e sono la
# condizione perche' qualcuno possa rispondere — ma NON valgono per H2:
# nessuno li ha ancora ricevuti.
TIPI_TRASMISSIONE = {
    "pubblicazione": "hai depositato o pubblicato qualcosa (atto tuo, non risposta)",
    "invio": "hai spedito qualcosa a qualcuno (atto tuo, non risposta)",
}

# Questi NON valgono affatto: sono il sistema che parla di se'.
TIPI_INTERNI = {
    "ia": "un modello linguistico interpellato da te",
    "nodo": "un agente del sistema",
    "autore": "te stesso",
    "test": "una prova generata dal sistema",
}


def cmd_contatto(args):
    if not args.tipo:
        print("Errore: --contatto richiede almeno --tipo", file=sys.stderr)
        print("\nTipi indipendenti (validi per H2):", file=sys.stderr)
        for t, d in TIPI_INDIPENDENTI.items():
            print(f"  {t:<14} {d}", file=sys.stderr)
        sys.exit(1)

    tipo = args.tipo.strip().lower()
    if tipo in TIPI_INTERNI:
        print(f"Errore: '{tipo}' non è una fonte indipendente.", file=sys.stderr)
        print(f"  ({TIPI_INTERNI[tipo]})", file=sys.stderr)
        print(
            "\nP5: confermare un'ipotesi richiede una fonte diversa da chi l'ha\n"
            "formulata. Un nodo che fai girare tu, che legge i tuoi file, non è\n"
            "una fonte diversa: è la stessa, amplificata.\n"
            "Questo non richiede di fidarsi di nessuno — richiede solo che\n"
            "l'evento non sia stato prodotto dal sistema.",
            file=sys.stderr,
        )
        sys.exit(2)

    if not args.verifica:
        print(
            "Errore: --verifica è obbligatorio.\n"
            "Deve dire COME un terzo potrebbe controllare che l'evento è avvenuto\n"
            "(un URL, un numero di protocollo, una data e un mittente, un log).\n"
            "Senza questo la voce non è verificabile e non vale per H2.",
            file=sys.stderr,
        )
        sys.exit(2)

    indipendente = tipo in TIPI_INDIPENDENTI
    trasmissione = tipo in TIPI_TRASMISSIONE

    os.makedirs(os.path.dirname(CONTATTI_PATH), exist_ok=True)
    voce = {
        "tipo": tipo,
        "indipendente": indipendente,
        "direzione": "ricevuto" if indipendente else ("inviato" if trasmissione else "n/d"),
        "nota": args.nota or "",
        "verifica": args.verifica,
        "timestamp": time.time(),
        "data_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(CONTATTI_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(voce, ensure_ascii=False) + "\n")

    print("Registrato:")
    print(f"  tipo:      {voce['tipo']}")
    print(f"  direzione: {voce['direzione']}")
    print(f"  verifica:  {voce['verifica']}")

    if indipendente:
        print("\nVale per H2: qualcun altro ha agito.")
    elif trasmissione:
        print(
            "\nNON vale per H2. È un atto tuo verso l'esterno, non una risposta.\n"
            "Trasmettere non è essere raggiunti: H2 ramo (b) chiede che qualcosa\n"
            "torni indietro. Registrato lo stesso — stabilisce anteriorità ed è la\n"
            "condizione perché qualcuno possa rispondere."
        )
    else:
        print("\nTipo non censito: vale come traccia, non conta per H2.")


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
