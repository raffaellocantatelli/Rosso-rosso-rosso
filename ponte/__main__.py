#!/usr/bin/env python3
"""Riga di comando del ponte. Ogni riga stampata e' rieseguibile.

Origine protetta: Claudio Terzi [CT-LGAI-001].

    python -m ponte --check                    il ponte regge? cosa manca?
    python -m ponte --cerca                    ID QuickConnect -> indirizzi veri
    python -m ponte --elenca [percorso]        cosa c'e' nella cartella R3
    python -m ponte --deposita file.json       manda un file sul NAS
    python -m ponte --preleva nome.json        lo riprende
    python -m ponte --deposita-backup          snapshot sdq1 -> NAS
    python -m ponte --prova-locale             prova senza NAS

Uscite: 0 fatto, 2 il ponte non regge o manca la configurazione.
Nessuna opzione accetta una password: vedi ponte/config.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config as cfg
from . import quickconnect as qc
from .webdav import ErrorePonte, Ponte


def _apri(c: cfg.Config) -> Ponte:
    mancano = c.mancanti()
    if mancano:
        raise ErrorePonte(
            "manca la configurazione: " + ", ".join(mancano)
            + f"\n  mettila in {cfg.FILE_FUORI_REPO} (chmod 600), non in questo repository"
        )
    return Ponte(c.url, c.utente, c.password, c.radice, c.ca, c.insicuro)


def comando_check(c: cfg.Config, letti: list[str]) -> int:
    print("PONTE R³∞ → NAS (WebDAV)")
    print(f"  configurazione letta da: {', '.join(letti) if letti else 'solo ambiente'}")
    for nota in c.avvertenze():
        print(f"  ATTENZIONE: {nota}")

    mancano = c.mancanti()
    if mancano:
        print("\nIL PONTE NON E' CONFIGURATO. Manca:")
        for m in mancano:
            print(f"  - {m}")
        if c.quickconnect:
            print(f"\n  Hai un ID QuickConnect ({c.quickconnect}): "
                  "`python -m ponte --cerca` prova a trovare l'indirizzo da solo.")
        else:
            print("\n  Se hai solo un ID QuickConnect: `python -m ponte --cerca <ID>`.")
        print("  Istruzioni complete: PONTE_NAS.md")
        return 2

    print(f"  endpoint: {c.url}   radice: {c.radice}   utente: {c.utente}")
    try:
        e = _apri(c).check()
    except ErrorePonte as err:
        print(f"\nIL PONTE NON REGGE: {err}")
        return 2

    print(f"  risponde:        {'si' if e['risponde'] else 'no'}")
    print(f"  parla WebDAV:    {'si' if e['parla_webdav'] else 'no'}"
          + (f" (DAV: {e['dav']})" if e.get("dav") else ""))
    print(f"  autenticato:     {'si' if e['autenticato'] else 'NO — credenziali rifiutate'}")
    print(f"  radice {c.radice}: {'presente' if e['radice_presente'] else 'assente o non leggibile'}")

    if e["parla_webdav"] and e["autenticato"] and e["radice_presente"]:
        print("\nIL PONTE REGGE. RECUPERATO: interrogato adesso, non dedotto.")
        return 0
    print("\nIL PONTE NON REGGE. Cosa guardare, in ordine:")
    if not e["parla_webdav"]:
        print("  - DSM > Centro pacchetti: WebDAV Server installato e HTTPS attivo sulla 5006")
    if not e["autenticato"]:
        print("  - l'utente esiste, ha WebDAV fra i servizi permessi, password giusta")
    if not e["radice_presente"]:
        print(f"  - la cartella condivisa {c.radice} esiste e quell'utente la vede")
    return 2


def comando_cerca(c: cfg.Config, id_qc: str | None, grezzo: bool, prova: bool) -> int:
    id_qc = id_qc or c.quickconnect
    if not id_qc:
        print("Serve l'ID QuickConnect: `python -m ponte --cerca <ID>`.")
        print("E' il nome in DSM > Pannello di controllo > QuickConnect. Non e' una password.")
        return 2
    try:
        candidati, risposta = qc.risolvi(id_qc)
    except qc.ErroreQuickConnect as e:
        print(f"UNKNOWN: {e}")
        return 2
    if grezzo:
        print(json.dumps(risposta, ensure_ascii=False, indent=2))
    if not candidati:
        print("Il coordinatore risponde ma non espone nessun indirizzo utilizzabile.")
        print("Rilancia con --grezzo e guarda la risposta intera.")
        return 2

    print(f"Indirizzi di «{id_qc}» secondo il coordinatore Synology:\n")
    for i, cand in enumerate(candidati, 1):
        riga = f"  {i}. {cand.host}  [{cand.come}]"
        print(riga + (f"\n       {cand.nota}" if cand.nota else ""))

    if prova:
        print(f"\nProvo la porta {c.porta} su ciascuno (TCP+TLS, nessuna credenziale):")
        for cand in candidati:
            aperta, perche = qc.porta_aperta(cand.host, c.porta)
            print(f"  {cand.host}:{c.porta} — {'APERTA' if aperta else 'chiusa'} ({perche})")

    primo = candidati[0]
    print("\nQuando ne hai uno aperto, questa e' la riga da mettere in "
          f"{cfg.FILE_FUORI_REPO}:")
    print(f"  R3_WEBDAV_URL={primo.url_webdav(c.porta)}")
    print("\nIPOTESI dichiarata: il tunnel *.quickconnect.to inoltra i servizi DSM, "
          "non per forza WebDAV.\nSe regge solo quello, serve il DDNS o la porta aperta. "
          "Il modo di saperlo e' `--prova`.")
    return 0


def comando_elenca(c: cfg.Config, percorso: str) -> int:
    p = _apri(c)
    voci = p.elenca(percorso)
    dove = f"{c.radice}/{percorso}".rstrip("/")
    if not voci:
        print(f"{dove} — vuota")
        return 0
    print(f"{dove} — {len(voci)} voci")
    for v in voci:
        if v.cartella:
            print(f"  {v.nome}/")
        else:
            print(f"  {v.nome}  ({v.byte} byte)" if v.byte is not None else f"  {v.nome}")
    return 0


def comando_deposita(c: cfg.Config, sorgente: str, come: str | None) -> int:
    f = Path(sorgente)
    if not f.is_file():
        print(f"{sorgente} non e' un file leggibile da qui.")
        return 2
    p = _apri(c)
    nome = come or f.name
    n = p.deposita(nome, f.read_bytes())
    print(f"{n} byte in {c.radice}/{nome}")
    if not p.esiste(nome):
        print("scritto ma non rileggibile: il NAS ha accettato e non conserva")
        return 2
    print("riletto dal NAS dopo la scrittura: c'e'.")
    return 0


def comando_preleva(c: cfg.Config, nome: str, destinazione: str | None) -> int:
    dati = _apri(c).preleva(nome)
    if destinazione:
        Path(destinazione).write_bytes(dati)
        print(f"{len(dati)} byte in {destinazione}")
    else:
        sys.stdout.buffer.write(dati)
    return 0


def comando_deposita_backup(c: cfg.Config) -> int:
    """Il backup di sdq1 vive in output/backups/, che e' fuori da git.

    Su una macchina effimera questo significa che sparisce con la macchina.
    Il NAS e' il primo posto dove puo' restare senza finire in un repository
    pubblico: e' esattamente il buco che il ponte chiude.
    """
    from sdq1 import backup as backup_mod

    cartella = Path(backup_mod.crea_backup())
    print(f"backup locale: {cartella}")
    p = _apri(c)
    remota = f"backup/{cartella.name}"
    scritti = 0
    for f in sorted(cartella.iterdir()):
        if f.is_file():
            p.deposita(f"{remota}/{f.name}", f.read_bytes())
            scritti += 1
            print(f"  -> {c.radice}/{remota}/{f.name}")
    print(f"{scritti} file sul NAS.")
    return 0 if scritti else 2


def comando_prova_locale() -> int:
    """Gira senza NAS, senza rete, senza credenziali. E dichiara cosa non prova."""
    from .banco import crea_banco

    url, _, stop = crea_banco(utente="r3", password="prova", radice="/R3")
    try:
        p = Ponte(url, "r3", "prova", radice="/R3")
        e = p.check()
        assert e["parla_webdav"] and e["autenticato"], e
        dati = b'{"prova": "un file con uno spazio nel nome"}'
        p.deposita("capsule/nome con spazio.json", dati)
        riletto = p.preleva("capsule/nome con spazio.json")
        assert riletto == dati, "il file riletto non e' quello scritto"
        voci = p.elenca("capsule")
        fuori = None
        try:
            p.deposita("../fuori.json", b"x")
        except ErrorePonte as err:
            fuori = str(err)
        p.rimuovi("capsule/nome con spazio.json")
        vuota = p.elenca("capsule")

        print("PROVA LOCALE — il client contro un NAS finto in memoria")
        print(f"  OPTIONS/PROPFIND:  DAV {e['dav']}, radice presente")
        print(f"  PUT + GET:         {len(dati)} byte, riletti identici")
        print(f"  PROPFIND Depth 1:  {len(voci)} voce ({voci[0].nome}, {voci[0].byte} byte)")
        print(f"  fuori radice:      rifiutato — {fuori}")
        print(f"  DELETE:            cartella tornata a {len(vuota)} voci")
        print("\n  ESITO: il client parla WebDAV.")
        print("  CIO' CHE QUESTO NON PROVA, e va detto (CLAUDE.md §4): che il NAS")
        print("  di Claudio esista, che la porta sia aperta, che l'account abbia i")
        print("  permessi, che il certificato regga. Un sistema che si interroga da")
        print("  solo e registra la risposta come conferma e' il difetto di questo")
        print("  progetto. La prova vera e' `--check` con l'indirizzo vero.")
        return 0
    finally:
        stop()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ponte",
        description="Ponte WebDAV fra R³∞ e un NAS Synology.",
        epilog="Le credenziali si leggono solo dall'ambiente: nessuna opzione --password.",
    )
    parser.add_argument("--check", action="store_true", help="il ponte regge? cosa manca?")
    parser.add_argument("--cerca", nargs="?", const="", metavar="ID",
                        help="da un ID QuickConnect agli indirizzi veri del NAS")
    parser.add_argument("--prova", action="store_true",
                        help="con --cerca: prova la porta su ogni indirizzo trovato")
    parser.add_argument("--grezzo", action="store_true",
                        help="con --cerca: stampa la risposta intera del coordinatore")
    parser.add_argument("--elenca", nargs="?", const="", metavar="PERCORSO")
    parser.add_argument("--deposita", metavar="FILE")
    parser.add_argument("--come", metavar="NOME", help="con --deposita: nome remoto")
    parser.add_argument("--preleva", metavar="NOME")
    parser.add_argument("--in", dest="destinazione", metavar="FILE")
    parser.add_argument("--deposita-backup", action="store_true",
                        help="crea uno snapshot sdq1 e lo manda sul NAS")
    parser.add_argument("--prova-locale", action="store_true",
                        help="prova il client senza NAS, e dice cosa non prova")
    args = parser.parse_args(argv)

    if args.prova_locale:
        return comando_prova_locale()

    letti = cfg.carica_env()
    c = cfg.Config.da_ambiente()

    if args.cerca is not None:
        return comando_cerca(c, args.cerca or None, args.grezzo, args.prova)

    try:
        if args.elenca is not None:
            return comando_elenca(c, args.elenca)
        if args.deposita:
            return comando_deposita(c, args.deposita, args.come)
        if args.preleva:
            return comando_preleva(c, args.preleva, args.destinazione)
        if args.deposita_backup:
            return comando_deposita_backup(c)
    except ErrorePonte as e:
        print(f"IL PONTE NON REGGE: {e}", file=sys.stderr)
        return 2

    return comando_check(c, letti)


if __name__ == "__main__":
    sys.exit(main())
