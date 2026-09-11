#!/usr/bin/env python3
"""Pubblica su Vercel una cartella preparata da `tools/prepare_release.py`.

Origine protetta: Claudio Terzi [CT-LGAI-001].

    py tools\\publish.py "..\\Claudio-release"                # ANTEPRIMA
    py tools\\publish.py "..\\Claudio-release" --produzione   # il sito vero

Due scelte che vale la pena spiegare, perche' sono deliberate.

**L'anteprima e' il default.** Senza `--produzione` questo script pubblica su
un indirizzo temporaneo: il sito pubblico non cambia. Si apre quell'indirizzo
dal telefono, si guarda se la barra va a capo e se il Canone Alpha si apre, e
solo dopo si decide. Pubblicare e' irreversibile nel senso che conta — chi ha
visto ha visto — e una riga di comando non deve poterlo fare per distrazione.

**La produzione chiede conferma a voce.** `--produzione` si ferma e aspetta che
tu scriva `pubblica`. Non e' burocrazia: e' l'unico punto del processo in cui
una persona dice si'. Con `--si` si salta, per quando sai gia' cosa stai
facendo e non vuoi la domanda.

Uscite: 0 pubblicata, 2 qualcosa non torna (e dice cosa).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

MANIFESTO = "RELEASE.json"
INDIRIZZO = re.compile(r"https://[\w.-]+\.vercel\.app")


class Fermata(Exception):
    pass


def trova_vercel() -> str:
    """Su Windows il comando e' `vercel.cmd`: shutil.which lo trova da se'."""
    for nome in ("vercel", "vercel.cmd"):
        percorso = shutil.which(nome)
        if percorso:
            return percorso
    raise Fermata(
        "vercel non e' installato, o non e' nel PATH.\n"
        "  npm.cmd install --global vercel\n"
        "  vercel.cmd login\n"
        "  (su Windows chiudi e riapri il terminale dopo l'installazione: "
        "il PATH viene letto all'avvio)"
    )


def comando(vercel: str, args: list[str]) -> list[str]:
    """Su Windows un .cmd non si avvia direttamente: passa da cmd.exe."""
    if os.name == "nt" and vercel.lower().endswith((".cmd", ".bat")):
        return ["cmd.exe", "/c", vercel, *args]
    return [vercel, *args]


def chi_sei(vercel: str) -> str | None:
    esito = subprocess.run(comando(vercel, ["whoami"]), capture_output=True, text=True)
    if esito.returncode != 0:
        return None
    return esito.stdout.strip() or None


def leggi_manifesto(cartella: Path) -> dict:
    f = cartella / MANIFESTO
    if not f.is_file():
        raise Fermata(
            f"{cartella} non contiene {MANIFESTO}: non l'ha preparata prepare_release.py.\n"
            "  Pubblicare una cartella qualsiasi significa pubblicare senza sapere cosa "
            "c'e' dentro.\n"
            '  py tools\\prepare_release.py "..\\Claudio-sito" "..\\Claudio-release"'
        )
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Fermata(f"{f} illeggibile: {e}") from e


def conferma(cartella: Path, manifesto: dict) -> bool:
    print("\n" + "=" * 64)
    print("STAI PER CAMBIARE IL SITO PUBBLICO.")
    print(f"  cartella:  {cartella}")
    print(f"  preparata: {manifesto.get('preparato', '?')}")
    sorgente = manifesto.get("sorgente") or {}
    if sorgente.get("ultimo"):
        print(f"  dal sito:  {sorgente['ultimo']}")
    for voce in manifesto.get("file", []):
        print(f"  {voce['esito']:11} {voce['file']}")
    for voce in manifesto.get("patch", []):
        print(f"  {voce['esito']:11} {voce['patch']}")
    print("=" * 64)
    try:
        risposta = input('Scrivi «pubblica» per procedere, qualunque altra cosa per fermarti: ')
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return risposta.strip().lower() == "pubblica"


def pubblica(vercel: str, cartella: Path, produzione: bool, dry: bool) -> tuple[int, str | None]:
    args = ["deploy", str(cartella), "--yes"]
    if produzione:
        args.append("--prod")
    riga = " ".join(comando(vercel, args))
    print(f"\n$ {riga}\n")
    if dry:
        print("(--dry: non eseguito)")
        return 0, None
    esito = subprocess.run(comando(vercel, args), capture_output=True, text=True)
    sys.stdout.write(esito.stdout)
    sys.stderr.write(esito.stderr)
    trovato = INDIRIZZO.findall(esito.stdout + esito.stderr)
    return esito.returncode, (trovato[-1] if trovato else None)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="publish.py",
        description="Pubblica su Vercel una cartella preparata da prepare_release.py.",
    )
    parser.add_argument("cartella", help="la cartella preparata (contiene RELEASE.json)")
    parser.add_argument("--produzione", action="store_true",
                        help="pubblica sul sito vero invece che su un'anteprima")
    parser.add_argument("--si", action="store_true",
                        help="con --produzione: salta la domanda di conferma")
    parser.add_argument("--dry", action="store_true",
                        help="stampa il comando senza eseguirlo")
    args = parser.parse_args(argv)

    cartella = Path(args.cartella).expanduser().resolve()
    try:
        if not cartella.is_dir():
            raise Fermata(f"{cartella} non esiste.")
        manifesto = leggi_manifesto(cartella)
        vercel = trova_vercel()

        print(f"vercel:    {vercel}")
        utente = chi_sei(vercel)
        if utente:
            print(f"account:   {utente}")
        elif not args.dry:
            raise Fermata(
                "vercel non sa chi sei: nessun account collegato.\n"
                "  vercel.cmd login\n"
                "  (si apre il browser, si conferma dalla mail, poi si rilancia questo comando)"
            )
        print(f"cartella:  {cartella}")
        print(f"bersaglio: {'PRODUZIONE — il sito pubblico' if args.produzione else 'anteprima (il sito pubblico non cambia)'}")

        if args.produzione and not args.si and not args.dry:
            if not conferma(cartella, manifesto):
                print("Fermato. Niente e' stato pubblicato.")
                return 2

        codice, indirizzo = pubblica(vercel, cartella, args.produzione, args.dry)
    except Fermata as e:
        print(f"\nFERMO: {e}", file=sys.stderr)
        return 2

    if codice != 0:
        print(f"\nVercel ha risposto {codice}: niente e' stato pubblicato.", file=sys.stderr)
        return 2
    if args.dry:
        return 0

    print("\nPUBBLICATA.")
    if indirizzo:
        print(f"  {indirizzo}")
    if not args.produzione:
        print("\n  Questa e' un'anteprima: il sito pubblico non e' cambiato.")
        print("  Aprila dal telefono e guarda due cose, che sono quelle che erano rotte:")
        print("    - la barra in alto va a capo e mostra tutte le voci")
        print("    - /alpha si apre e mostra una carta, senza restare vuota")
        print(f'\n  Se va bene:  py tools\\publish.py "{args.cartella}" --produzione')
    return 0


if __name__ == "__main__":
    sys.exit(main())
