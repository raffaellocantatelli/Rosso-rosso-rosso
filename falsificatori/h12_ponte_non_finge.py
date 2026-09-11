#!/usr/bin/env python3
"""H12 — «Il ponte verso il NAS non dichiara mai un esito che non ha ottenuto».

Origine protetta: Claudio Terzi [CT-LGAI-001].

Perché questa ipotesi e non un'altra. Il ponte ha, dentro di sé, un NAS finto:
`ponte/banco.py`. Serve a provare il client senza hardware, ed è utile — ma è
anche la forma esatta del difetto di CLAUDE.md §4: un pezzo di sistema che
risponde al sistema stesso. Il giorno in cui `--check` rispondesse al banco
invece che al NAS, stamperebbe «IL PONTE REGGE» mentre nessun NAS esiste, e
nessuno se ne accorgerebbe: la riga è identica.

Quindi la cosa da sorvegliare non è che il ponte funzioni. È che **fallisca
quando deve**. Un ponte che dice sempre di reggere non è un ponte, è uno specchio.

Come si falsifica, in una riga: si toglie la configurazione, si punta una porta
chiusa, si sbaglia la password — e si guarda se qualcuna delle tre produce un
successo. Se sì, H12 è caduta.

Non chiama nessun NAS, nessuna rete esterna, nessuna chiave. Deve poter girare
nella Action, sempre.

Esce 0 se H12 CADE, 1 se REGGE, 2 se non conclusa (convenzione dei
falsificatori di questo repository).
"""

import io
import os
import sys
from contextlib import redirect_stdout

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

from ponte import config as cfg  # noqa: E402
from ponte.__main__ import main  # noqa: E402
from ponte.banco import crea_banco  # noqa: E402
from ponte.webdav import ErrorePonte, Ponte  # noqa: E402

PAROLE_DI_SUCCESSO = ("IL PONTE REGGE",)


def _esegui(argv, ambiente):
    """Lancia la riga di comando con un ambiente controllato. Ritorna (uscita, testo)."""
    prima = {}
    for chiave in (cfg.ENV_URL, cfg.ENV_UTENTE, cfg.ENV_PASSWORD,
                   cfg.ENV_RADICE, cfg.ENV_QUICKCONNECT):
        prima[chiave] = os.environ.pop(chiave, None)
    os.environ.update({k: v for k, v in ambiente.items() if v is not None})
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            uscita = main(argv)
    except SystemExit as e:          # argparse
        uscita = int(e.code or 0)
    finally:
        for chiave, valore in prima.items():
            os.environ.pop(chiave, None)
            if valore is not None:
                os.environ[chiave] = valore
    return uscita, buffer.getvalue()


def prova_senza_configurazione():
    """Nessun URL, nessun utente: deve uscire 2 e non dire che regge."""
    fuori = cfg.FILE_FUORI_REPO
    cfg.FILE_FUORI_REPO = type(fuori)("/non/esiste/webdav.env")
    try:
        return _esegui(["--check"], {})
    finally:
        cfg.FILE_FUORI_REPO = fuori


def prova_porta_chiusa():
    """La 9 è la porta «discard»: accetta e butta via. Nessun WebDAV può esserci."""
    return _esegui(["--check"], {
        cfg.ENV_URL: "http://127.0.0.1:9",
        cfg.ENV_UTENTE: "r3",
        cfg.ENV_PASSWORD: "prova",
    })


def prova_password_sbagliata(url):
    return _esegui(["--check"], {
        cfg.ENV_URL: url,
        cfg.ENV_UTENTE: "r3",
        cfg.ENV_PASSWORD: "non-questa",
        cfg.ENV_RADICE: "/R3",
    })


def prova_radice_assente(url):
    return _esegui(["--check"], {
        cfg.ENV_URL: url,
        cfg.ENV_UTENTE: "r3",
        cfg.ENV_PASSWORD: "prova",
        cfg.ENV_RADICE: "/cartella-che-non-c-e",
    })


def prova_scrittura_fuori_radice(url):
    """Il ponte non deve poter scrivere fuori dalla cartella che gli è stata data."""
    p = Ponte(url, "r3", "prova", radice="/R3")
    try:
        p.deposita("../fuori.json", b"x")
        return False, "accettata"
    except ErrorePonte:
        return True, "rifiutata prima della rete"


def main_falsificatore():
    url, archivio, stop = crea_banco(utente="r3", password="prova", radice="/R3")
    try:
        casi = [
            ("senza configurazione", *prova_senza_configurazione()),
            ("porta chiusa", *prova_porta_chiusa()),
            ("password sbagliata", *prova_password_sbagliata(url)),
            ("radice assente", *prova_radice_assente(url)),
        ]
        caduta = []
        for nome, uscita, testo in casi:
            successo = any(p in testo for p in PAROLE_DI_SUCCESSO)
            print(f"{nome:24} uscita {uscita}  dichiara successo: {'SI' if successo else 'no'}")
            if uscita == 0:
                caduta.append(f"«{nome}» è uscito 0")
            if successo:
                caduta.append(f"«{nome}» ha stampato che il ponte regge")

        rifiutata, come = prova_scrittura_fuori_radice(url)
        print(f"{'scrittura fuori radice':24} {come}")
        if not rifiutata:
            caduta.append("una scrittura fuori dalla radice è stata accettata")

        # Il controllo speculare: se nessun caso positivo funzionasse, l'ipotesi
        # si farebbe reggere rompendo tutto. Va misurato anche questo.
        uscita_buona, testo_buono = _esegui(["--check"], {
            cfg.ENV_URL: url, cfg.ENV_UTENTE: "r3",
            cfg.ENV_PASSWORD: "prova", cfg.ENV_RADICE: "/R3",
        })
        regge_sul_banco = uscita_buona == 0 and "IL PONTE REGGE" in testo_buono
        print(f"{'contro il banco finto':24} uscita {uscita_buona}  "
              f"dichiara successo: {'SI' if regge_sul_banco else 'no'}")
        if not regge_sul_banco:
            print("\nNON CONCLUSA: il ponte non funziona nemmeno quando dovrebbe. "
                  "H12 reggerebbe per il motivo sbagliato.")
            return 2

        if caduta:
            print("\nH12 CADE:")
            for c in caduta:
                print(f"  - {c}")
            return 0

        print("\nH12 REGGE: quattro modi di non avere un NAS, quattro fallimenti "
              "dichiarati.\nRESTA VERO che il banco non è un NAS: che il ponte regga "
              "verso il NAS\ndi Claudio è UNKNOWN da qui, e lo dice `python -m ponte --check`.")
        return 1
    finally:
        stop()


if __name__ == "__main__":
    sys.exit(main_falsificatore())
