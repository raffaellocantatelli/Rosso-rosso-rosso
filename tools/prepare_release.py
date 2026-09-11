#!/usr/bin/env python3
"""Prepara una cartella pronta da pubblicare, senza toccare il repository del sito.

Origine protetta: Claudio Terzi [CT-LGAI-001].

    py tools\\prepare_release.py "..\\Claudio-sito" "..\\Claudio-release"
    python3 tools/prepare_release.py ../Claudio-sito ../Claudio-release

Con anche l'Oracolo del Sovrano (il pacchetto scompattato):

    py tools\\prepare_release.py "..\\Claudio-sito" "..\\Claudio-release" ^
       --oracolo "..\\ORACOLO_SOVRANO_WEB_AUTORIZZATO"

Che cosa fa, e perche' in due cartelle invece di una.

`sito-claudio/` contiene lavoro verificato nel browser e mai applicato: la
sessione che l'ha prodotto non aveva permessi di scrittura su
`claudioterzi/Claudio`. Da allora quel lavoro sta li' e il sito pubblico gira
ancora con `alpha.html` rotto — la pagina del primo click — e con la barra di
navigazione che su telefono mostra 5 voci su 15.

Questo script prende il clone del sito (SORGENTE, che resta intatto), ne fa
una copia (DESTINAZIONE) e applica li' dentro la consegna. La sorgente non
viene mai modificata: se qualcosa va storto, si cancella la destinazione e non
si e' perso niente. Nessun commit, nessun push: la decisione di portare queste
modifiche dentro il repository resta di Claudio.

Alla fine scrive `RELEASE.json`, che `tools/publish.py` pretende di trovare:
una cartella non preparata da qui non viene pubblicata per sbaglio.

Uscite: 0 preparata, 2 qualcosa non torna (e dice cosa).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
MANIFESTO = "RELEASE.json"

# Le cartelle che non devono finire in una release, con il motivo.
ESCLUSI = {
    ".git",            # 28 MB di cronologia: la release non e' un repository
    ".vercel",         # aggancio al progetto Vercel di chi ha preparato: non e' del sito
    ".env",            # credenziali. Non deve mai entrare in una cartella che si pubblica
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".DS_Store",
}

# La consegna, dichiarata come dato e non come prosa: cosi' il codice e il
# README di `sito-claudio/` non possono divergere in silenzio.
COPIE = [
    ("nuovi/nav.js", "public/nav.js"),
    ("nuovi/alpha.html", "public/alpha.html"),
    ("nuovi/lettura.html", "public/lettura.html"),
    ("nuovi/enzo.html", "public/enzo.html"),
]

PATCH = [
    "patch/responsive-mobile.patch",
    "patch/costo-terra-reale.patch",
]

# Prove eseguite sulla release finita. Ognuna e' una riga verificabile: se una
# cade, la cartella non viene dichiarata pronta. `atteso=False` significa che
# quel testo NON deve esserci.
PROVE = [
    ("public/alpha.html", "api/alpha", False, "la pagina chiamava un'API che risponde 404"),
    ("public/nav.js", "flex-wrap", True, "la barra deve poter andare a capo"),
    ("public/valigia.html", "420px", True, "la tabella non deve piu' sbordare sotto i 420px"),
    ("flight_hunter/costi.py", "TRASFERIMENTI_NOTI", True, "il costo a terra verificato alla fonte"),
    # La riga che l'utente legge davvero, non il nome di una funzione: e' cio'
    # che cambia per chi guarda il responso. (Scritta prima come
    # «intervallo_terra», che sta in costi.py: la prova ha visto l'errore
    # mentre lo commettevo — era il suo mestiere.)
    ("flight_hunter/oracolo.py", "secondo quando prenoti la navetta", True,
     "il responso dichiara la forbice invece di un numero secco"),
]

PRESENTI = ["public/lettura.html", "public/enzo.html", "tests/test_costi_terra.py",
            "vercel.json", "tarocchi_web.py"]

ASSENTI = [".env", ".git"]

# ---------------------------------------------------------------- l'Oracolo
#
# Il pacchetto «ORACOLO_SOVRANO_WEB_AUTORIZZATO» e' una seconda consegna, con
# strumenti suoi. Non li riscrivo: sanno cose che io non so — quale progetto
# Vercel e' la destinazione, come fondere le route dentro `vercel.json` senza
# sostituirlo alla cieca, quali file estranei devono restare identici. Un
# secondo programma che fa la stessa cosa sarebbe la malattia delle copie
# (CLAUDE.md §6 regola 2) applicata al codice. Quindi: il suo prepare_release
# fa la copia e la fusione, il mio ci sovrappone la consegna di `sito-claudio/`
# e verifica il risultato.
#
# L'ordine e' obbligato, non scelto: il loro pretende una destinazione che non
# esiste ancora, quindi va per primo.

MANIFESTO_PACCHETTO = "MANIFEST_SHA256.json"
PREPARA_PACCHETTO = "tools/prepare_release.py"

# Quando l'Oracolo e' in gioco, questo file e' suo: la consegna del 04/09 non
# lo sovrascrive. Alpha deve usare le 74 Lame — deciso da Claudio l'11/09 — e
# la vecchia alpha.html e' un altro mazzo, non una versione piu' vecchia dello
# stesso. E' una scelta, quindi viene stampata invece che eseguita in silenzio.
DELL_ORACOLO = {"public/alpha.html"}

# Il difetto trovato leggendo, che nessuna delle due consegne puo' vedere da
# sola. Il pacchetto rinomina la voce di menu cercando  ['index.html', 'Tarocchi']
# con gli apici singoli, come e' scritta nel nav.js oggi in produzione. Il
# nav.js nuovo di `sito-claudio/` la scrive con i doppi apici: la sostituzione
# non trova niente, non fallisce, e il menu resta «Tarocchi» senza che nessuno
# se ne accorga. Un passaggio che sembra eseguito e non fa nulla e' l'eco di
# §4. Qui la rinomina viene rifatta sul file nuovo, e poi verificata.
RINOMINA_MENU = ('["index.html", "Tarocchi"]', '["index.html", "Oracolo del Sovrano"]')

PROVE_ORACOLO = [
    ("public/sovrano/lame.v1.json", '"id": 74', True, "le 74 Lame devono esserci tutte"),
    ("public/nav.js", "Oracolo del Sovrano", True, "la voce di menu rinominata"),
    ("vercel.json", "sovrano_entry.py", True, "le route devono puntare al nuovo ingresso"),
]

# Devono sparire dalla copia di rilascio — non dal repository, che resta il backup.
RITIRATI = ["public/cards", "public/tarocchi_quantici_alpha.json"]

# Devono restare identici alla sorgente. Il pacchetto lo verifica da se' e lo
# scrive nel proprio report; lo rifaccio sui file, perche' un controllo che si
# legge nel rapporto di chi l'ha eseguito non e' un controllo (P5).
INTATTI = ["public/soglia.js", "public/soglia.html", "public/oracolo.html",
           "public/atelier.html"]


class Fermata(Exception):
    """Qualcosa non torna, e il messaggio dice cosa fare."""


def _git(args, cwd) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def controlla_sorgente(sorgente: Path) -> dict:
    if not sorgente.is_dir():
        raise Fermata(
            f"{sorgente} non esiste.\n"
            '  git clone https://github.com/claudioterzi/Claudio.git "..\\Claudio-sito"'
        )
    for atteso in ("public", "vercel.json"):
        if not (sorgente / atteso).exists():
            raise Fermata(
                f"{sorgente} non sembra il sito: manca {atteso}.\n"
                "  Il primo argomento e' il clone di claudioterzi/Claudio, non questa repository."
            )
    info = {"percorso": str(sorgente)}
    origine = _git(["remote", "get-url", "origin"], sorgente)
    if origine.returncode == 0:
        url = origine.stdout.strip()
        info["origine"] = url
        if "claudioterzi" not in url.lower():
            print(f"  ATTENZIONE: origin e' {url}, non claudioterzi/Claudio.")
    commit = _git(["rev-parse", "HEAD"], sorgente)
    if commit.returncode == 0:
        info["commit"] = commit.stdout.strip()
        descrizione = _git(["log", "-1", "--format=%h %ad %s", "--date=short"], sorgente)
        info["ultimo"] = descrizione.stdout.strip()
    sporco = _git(["status", "--porcelain"], sorgente)
    if sporco.returncode == 0 and sporco.stdout.strip():
        n = len(sporco.stdout.strip().splitlines())
        info["modifiche_locali"] = n
        print(f"  ATTENZIONE: il clone ha {n} file modificati localmente: "
              "finiscono nella release cosi' come sono.")
    return info


def controlla_consegna(consegna: Path) -> None:
    if not consegna.is_dir():
        raise Fermata(f"{consegna} non esiste: e' la cartella `sito-claudio/` di questa repository.")
    mancanti = [n for n, _ in COPIE if not (consegna / n).is_file()]
    mancanti += [p for p in PATCH if not (consegna / p).is_file()]
    if mancanti:
        raise Fermata("la consegna e' incompleta, mancano:\n  " + "\n  ".join(mancanti))


def prepara_destinazione(destinazione: Path, forza: bool) -> None:
    if not destinazione.exists():
        return
    if not destinazione.is_dir():
        raise Fermata(f"{destinazione} esiste e non e' una cartella.")
    contenuto = list(destinazione.iterdir())
    if not contenuto:
        return
    # Una preparazione fallita a meta' lascia dietro questo file — lo scrive il
    # pacchetto dell'Oracolo. E' un segno inequivocabile: nessuna persona
    # chiama cosi' una cartella sua. Con --forza si rifa' senza chiedere, che
    # e' il caso in cui si trova chi rilancia dopo un errore.
    incompleta = destinazione / "RELEASE_INCOMPLETA_NON_PUBBLICARE.txt"
    if incompleta.is_file():
        if not forza:
            raise Fermata(
                f"{destinazione} contiene una preparazione interrotta.\n"
                "  Rilancia con --forza per rifarla da capo."
            )
        shutil.rmtree(destinazione)
        return
    # Cancellare una cartella indicata da riga di comando e' irreversibile.
    # Si cancella solo cio' che questo script ha preparato, e lo riconosce
    # dal manifesto: senza quello, si ferma e lo dice.
    if not (destinazione / MANIFESTO).is_file():
        raise Fermata(
            f"{destinazione} esiste, non e' vuota e non contiene {MANIFESTO}.\n"
            "  Non la cancello: non l'ho preparata io. Scegli un'altra cartella "
            "o svuotala tu."
        )
    if not forza:
        vecchio = json.loads((destinazione / MANIFESTO).read_text(encoding="utf-8"))
        raise Fermata(
            f"{destinazione} contiene gia' una release preparata il "
            f"{vecchio.get('preparato', '?')}.\n  Rilancia con --forza per rifarla."
        )
    shutil.rmtree(destinazione)


def copia_sito(sorgente: Path, destinazione: Path) -> int:
    def ignora(cartella, nomi):
        return {n for n in nomi if n in ESCLUSI or n.endswith(".pyc")}

    shutil.copytree(sorgente, destinazione, ignore=ignora, symlinks=True)
    return sum(1 for _ in destinazione.rglob("*") if _.is_file())


def applica_patch(consegna: Path, destinazione: Path) -> list[dict]:
    esiti = []
    for nome in PATCH:
        percorso = consegna / nome
        base = ["git", "apply", "--whitespace=nowarn", str(percorso)]
        prova = subprocess.run(base + ["--check"], cwd=str(destinazione),
                               capture_output=True, text=True)
        if prova.returncode != 0:
            indietro = subprocess.run(base + ["--check", "--reverse"], cwd=str(destinazione),
                                      capture_output=True, text=True)
            if indietro.returncode == 0:
                esiti.append({"patch": nome, "esito": "gia' applicata"})
                print(f"  {nome}: gia' applicata, salto")
                continue
            raise Fermata(
                f"{nome} non si applica piu' al sito:\n    "
                + prova.stderr.strip().replace("\n", "\n    ")
                + "\n  Il sito e' cambiato da quando la consegna e' stata preparata. "
                  "Va rifatta a mano, non forzata."
            )
        fatto = subprocess.run(base, cwd=str(destinazione), capture_output=True, text=True)
        if fatto.returncode != 0:
            raise Fermata(f"{nome} ha fallito durante l'applicazione:\n    {fatto.stderr.strip()}")
        esiti.append({"patch": nome, "esito": "applicata"})
        print(f"  {nome}: applicata")
    return esiti


def copia_file(consegna: Path, destinazione: Path, salta=()) -> list[dict]:
    esiti = []
    for origine, arrivo in COPIE:
        if arrivo in salta:
            esiti.append({"file": arrivo, "esito": "saltato: e' dell'Oracolo"})
            continue
        da = consegna / origine
        a = destinazione / arrivo
        nuovo = not a.exists()
        a.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(da, a)
        esiti.append({"file": arrivo, "esito": "creato" if nuovo else "sostituito",
                      "byte": a.stat().st_size})
        print(f"  {arrivo}: {'creato' if nuovo else 'sostituito'} ({a.stat().st_size} byte)")
    return esiti


def verifica(destinazione: Path, prove_extra=()) -> list[str]:
    """Le prove sulla release finita. Ritorna l'elenco di cio' che non torna."""
    guai = []
    for nome in PRESENTI:
        if not (destinazione / nome).exists():
            guai.append(f"manca {nome}")
    for nome in ASSENTI:
        if (destinazione / nome).exists():
            guai.append(f"{nome} e' finito nella release e non doveva")
    for nome, testo, atteso, perche in [*PROVE, *prove_extra]:
        f = destinazione / nome
        if not f.is_file():
            guai.append(f"manca {nome} (serviva per: {perche})")
            continue
        contenuto = f.read_text(encoding="utf-8", errors="replace")
        trovato = testo in contenuto
        if trovato != atteso:
            guai.append(
                f"{nome}: «{testo}» {'presente' if trovato else 'assente'} "
                f"ma doveva essere {'presente' if atteso else 'assente'} — {perche}"
            )
    return guai


def verifica_pacchetto(pacchetto: Path) -> int:
    """Ricalcola i SHA256 del pacchetto prima di eseguirne il codice.

    Sto per far girare un programma che non ho scritto io su una copia del
    sito. Il pacchetto porta le proprie impronte: se anche una sola non torna,
    non e' il pacchetto che Claudio ha ricevuto, e non si esegue.
    """
    import hashlib

    manifesto = pacchetto / MANIFESTO_PACCHETTO
    if not manifesto.is_file():
        raise Fermata(
            f"{pacchetto} non contiene {MANIFESTO_PACCHETTO}: non e' il pacchetto dell'Oracolo.\n"
            "  Indica la cartella che contiene LEGGIMI.md, app/ e tools/."
        )
    if not (pacchetto / PREPARA_PACCHETTO).is_file():
        raise Fermata(f"{pacchetto} non contiene {PREPARA_PACCHETTO}.")
    atteso = json.loads(manifesto.read_text(encoding="utf-8"))
    guai = []
    for percorso, impronta in atteso.items():
        f = pacchetto / percorso
        if not f.is_file():
            guai.append(f"manca {percorso}")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != impronta:
            guai.append(f"{percorso} non corrisponde alla propria impronta")
    if guai:
        raise Fermata("il pacchetto non corrisponde al proprio manifesto:\n  "
                      + "\n  ".join(guai[:10]))
    return len(atteso)


def applica_oracolo(pacchetto: Path, sorgente: Path, destinazione: Path) -> None:
    """Lascia fare al pacchetto la copia del sito e la fusione delle route.

    Non riscrivo il suo lavoro: chiamo il suo programma. Se si ferma, si ferma
    tutto — e la sua stessa procedura lascia sul posto un file che dice di non
    pubblicare quella cartella.
    """
    esito = subprocess.run(
        [sys.executable, str(pacchetto / PREPARA_PACCHETTO), str(sorgente), str(destinazione)],
        capture_output=True, text=True, timeout=900,
    )
    for riga in (esito.stdout or "").strip().splitlines()[-2:]:
        print(f"   | {riga}")
    if esito.returncode != 0:
        raise Fermata(
            "il prepare_release del pacchetto si e' fermato:\n    "
            + (esito.stderr or esito.stdout).strip().replace("\n", "\n    ")
        )
    if not destinazione.is_dir():
        raise Fermata("il pacchetto non ha creato la destinazione.")
    if (destinazione / "RELEASE_INCOMPLETA_NON_PUBBLICARE.txt").is_file():
        raise Fermata("il pacchetto ha lasciato la release incompleta: non va pubblicata.")


def rinomina_menu(destinazione: Path) -> str:
    """Rifa' sul nav.js nuovo la rinomina che il pacchetto non puo' trovarci."""
    nav = destinazione / "public/nav.js"
    if not nav.is_file():
        return "public/nav.js assente"
    testo = nav.read_text(encoding="utf-8")
    if RINOMINA_MENU[1] in testo:
        return "gia' rinominata dal pacchetto"
    if RINOMINA_MENU[0] not in testo:
        return f"UNKNOWN: «{RINOMINA_MENU[0]}» non trovata — il menu va guardato a mano"
    nav.write_text(testo.replace(*RINOMINA_MENU), encoding="utf-8")
    return "rinominata qui (il pacchetto cerca gli apici singoli e non l'avrebbe trovata)"


def controlla_intatti(sorgente: Path, destinazione: Path) -> list[str]:
    """I file estranei all'Oracolo devono essere identici alla sorgente."""
    import hashlib

    guai = []
    for nome in INTATTI:
        a, b = sorgente / nome, destinazione / nome
        if not a.is_file():
            continue
        if not b.is_file():
            guai.append(f"{nome} e' sparito dalla release")
        elif hashlib.sha256(a.read_bytes()).digest() != hashlib.sha256(b.read_bytes()).digest():
            guai.append(f"{nome} e' stato modificato e non doveva")
    for nome in RITIRATI:
        if (destinazione / nome).exists():
            guai.append(f"{nome} e' ancora nella release: il vecchio mazzo non e' stato ritirato")
    return guai


TEST_DELLA_CONSEGNA = "tests/test_costi_terra.py"


def prova_i_test(destinazione: Path) -> tuple[bool, str]:
    """Esegue i test che la consegna porta con se', dentro la release.

    Le prove qui sopra guardano il testo dei file; questi eseguono il codice.
    Sono i dieci test del costo a terra, ed e' il solo file che la consegna
    aggiunge: non tocco il resto della suite del sito, che ha dipendenze sue.

    Se pytest non c'e', non e' un fallimento della release: e' UNKNOWN, e va
    detto invece di essere nascosto in un ok.
    """
    if not (destinazione / TEST_DELLA_CONSEGNA).is_file():
        return True, f"{TEST_DELLA_CONSEGNA} assente: niente da eseguire"
    esito = subprocess.run(
        [sys.executable, "-m", "pytest", TEST_DELLA_CONSEGNA, "-q"],
        cwd=str(destinazione), capture_output=True, text=True, timeout=300,
    )
    uscita = (esito.stdout + esito.stderr).strip().splitlines()
    ultima = uscita[-1] if uscita else ""
    if "No module named pytest" in esito.stderr:
        return True, "UNKNOWN: pytest non installato qui, i test non sono stati eseguiti"
    return esito.returncode == 0, ultima


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="prepare_release.py",
        description="Prepara la cartella da pubblicare applicando sito-claudio/ a un clone del sito.",
    )
    parser.add_argument("sorgente", help="il clone di claudioterzi/Claudio (resta intatto)")
    parser.add_argument("destinazione", help="la cartella da creare, pronta da pubblicare")
    parser.add_argument("--consegna", default=str(RADICE / "sito-claudio"),
                        help="dove sta il lavoro da applicare (default: sito-claudio/)")
    parser.add_argument("--forza", action="store_true",
                        help="rifa' una release gia' preparata nella stessa cartella")
    parser.add_argument("--oracolo", metavar="CARTELLA",
                        help="il pacchetto ORACOLO_SOVRANO_WEB_AUTORIZZATO scompattato: "
                             "la copia e le route le fa lui, qui sopra si sovrappone "
                             "la consegna di sito-claudio/")
    args = parser.parse_args(argv)

    sorgente = Path(args.sorgente).expanduser().resolve()
    destinazione = Path(args.destinazione).expanduser().resolve()
    consegna = Path(args.consegna).expanduser().resolve()
    pacchetto = Path(args.oracolo).expanduser().resolve() if args.oracolo else None

    if destinazione == sorgente:
        print("FERMO: sorgente e destinazione sono la stessa cartella. "
              "La sorgente non va toccata.", file=sys.stderr)
        return 2

    print("PREPARAZIONE DELLA RELEASE")
    try:
        print(f"\n1. Sorgente: {sorgente}")
        info = controlla_sorgente(sorgente)
        if info.get("ultimo"):
            print(f"   ultimo commit: {info['ultimo']}")
        controlla_consegna(consegna)
        print(f"   consegna:      {consegna}")

        print(f"\n2. Copia in {destinazione}")
        prepara_destinazione(destinazione, args.forza)
        if pacchetto:
            quanti_file = verifica_pacchetto(pacchetto)
            print(f"   pacchetto Oracolo: {quanti_file} file, tutti corrispondenti "
                  "al proprio MANIFEST_SHA256")
            print(f"   la copia e le route le fa {pacchetto.name}/{PREPARA_PACCHETTO}:")
            applica_oracolo(pacchetto, sorgente, destinazione)
        else:
            quanti = copia_sito(sorgente, destinazione)
            print(f"   {quanti} file copiati (esclusi: {', '.join(sorted(ESCLUSI))})")

        print("\n3. Patch")
        esiti_patch = applica_patch(consegna, destinazione)

        print("\n4. File nuovi")
        salta = DELL_ORACOLO if pacchetto else set()
        for nome in sorted(salta):
            print(f"  {nome}: NON sostituito — e' dell'Oracolo, e Alpha deve "
                  "usare le 74 Lame")
        esiti_file = copia_file(consegna, destinazione, salta)

        prove_extra = ()
        if pacchetto:
            print("\n4-bis. Il menu, e i file che non dovevano cambiare")
            print(f"  public/nav.js: {rinomina_menu(destinazione)}")
            intatti = controlla_intatti(sorgente, destinazione)
            if intatti:
                print("   LA RELEASE NON E' BUONA:")
                for g in intatti:
                    print(f"     - {g}")
                return 2
            print(f"  ok  {len(INTATTI)} file estranei identici alla sorgente "
                  "(Soglia compresa), ricontrollati qui e non letti dal suo report")
            print(f"  ok  {len(RITIRATI)} vecchi mazzi ritirati dalla sola copia di rilascio")
            prove_extra = PROVE_ORACOLO

        print("\n5. Prove sulla cartella finita")
        guai = verifica(destinazione, prove_extra)
        if guai:
            print("   LA RELEASE NON E' BUONA:")
            for g in guai:
                print(f"     - {g}")
            print(f"\n   Non scrivo {MANIFESTO}: senza quello, publish.py si rifiuta "
                  "di pubblicare.")
            return 2
        for nome, testo, atteso, perche in [*PROVE, *prove_extra]:
            print(f"   ok  {nome}: «{testo}» {'presente' if atteso else 'assente'}")
        print(f"   ok  {len(PRESENTI)} file attesi presenti, "
              f"{len(ASSENTI)} esclusioni rispettate (.env, .git)")

        print("\n6. I test che la consegna porta con se'")
        passati, riga = prova_i_test(destinazione)
        print(f"   {'ok  ' if passati else 'NO  '}{TEST_DELLA_CONSEGNA}: {riga}")
        if not passati:
            print("\n   Non scrivo RELEASE.json: il codice della release non passa "
                  "i propri test.")
            return 2

    except Fermata as e:
        print(f"\nFERMO: {e}", file=sys.stderr)
        return 2

    manifesto = {
        "preparato": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strumento": "tools/prepare_release.py",
        "sorgente": info,
        "consegna": str(consegna),
        "patch": esiti_patch,
        "file": esiti_file,
        "oracolo": str(pacchetto) if pacchetto else None,
        "prove_superate": len(PROVE) + len(prove_extra) + len(PRESENTI) + len(ASSENTI),
    }
    (destinazione / MANIFESTO).write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nPRONTA: {destinazione}")
    print(f"Il clone in {sorgente} non e' stato toccato.")
    if pacchetto:
        # Il pacchetto pubblica con strumenti suoi, che conoscono il progetto
        # Vercel giusto e rifiutano di pubblicare su un altro. Il mio publish.py
        # non lo sa, quindi qui la strada e' la sua.
        print("\nIl passo dopo — anteprima protetta, con gli strumenti del pacchetto:")
        print(f'  py "{args.oracolo}\\tools\\publish.py" "{args.destinazione}"')
        print("Poi si apre l'anteprima e si guardano /tarot, /alpha, la Soglia e le immagini.")
        print("Solo dopo, e con la stessa riga piu' due parole:")
        print(f'  py "{args.oracolo}\\tools\\publish.py" "{args.destinazione}" '
              "--production --preview-tested")
    else:
        print("\nIl passo dopo — anteprima, non produzione:")
        print(f'  py tools\\publish.py "{args.destinazione}"')
        print("La produzione e' un'altra riga, e la digiti tu: --produzione")
    return 0


if __name__ == "__main__":
    sys.exit(main())
