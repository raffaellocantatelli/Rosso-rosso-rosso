#!/usr/bin/env python3
"""Costruisce il sito statico da pubblicare — Vercel, Netlify, GitHub Pages.

Origine protetta: Claudio Terzi [CT-LGAI-001].

**Che cosa può stare su un sito, e che cosa no.** `occhio` non è un sito: è
un programma che legge fotografie e scrive un registro sul disco di casa di
qualcuno. Un sito statico non ha un disco e non ha una chiave di visione,
quindi quello che si pubblica è **la console con dati congelati**: si vede
com'è fatto il prodotto, non la casa di nessuno.

I dati sono quelli della dimostrazione — inventati, alloggio `via-esempio-12`.
Nessuna fotografia, nessun oggetto di casa di nessuno, nessuna firma.

Il sito NON si tiene a mano: si rigenera. Copiare console.html in una
seconda cartella sarebbe una seconda copia dello stesso concetto (§6 regola
2 di CLAUDE.md) e divergerebbe al primo ritocco.

    python3 sito/costruisci.py && ls sito/pubblico
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
USCITA = Path(__file__).resolve().parent / "pubblico"


def quadro_dai_dati(cartella: Path) -> dict:
    """Il quadro letto dal server VERO, non ricostruito a mano.

    Se lo ricostruissi qui, il sito mostrerebbe una forma che il prodotto
    non produce piu' il giorno in cui il quadro cambia.
    """
    for var, nome in (("OCCHIO_INVENTARIO", "inventario.jsonl"),
                      ("OCCHIO_CONSEGNE", "consegne.jsonl"),
                      ("OCCHIO_PORTAVIA", "portavia.jsonl"),
                      ("OCCHIO_CREDITI", "crediti.jsonl")):
        os.environ[var] = str(cartella / nome)
    sys.path.insert(0, str(RADICE))
    for modulo in [m for m in list(sys.modules) if m.startswith("occhio")]:
        del sys.modules[modulo]
    from occhio import server as srv
    from occhio.planimetria import carica

    srv.Handler.stato = srv.Stato(cartella / "inventario.jsonl", ("stub",),
                                  False, 0.75, carica(cartella / "pianta.json"))
    s = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{s.server_address[1]}/api/quadro", timeout=15) as r:
            return json.loads(r.read().decode())
    finally:
        s.shutdown(); s.server_close()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        dati = Path(tmp) / "dimostrazione"
        esito = subprocess.run(
            [sys.executable, str(RADICE / "esempi" / "dimostrazione.py"), "--qui"],
            cwd=tmp, capture_output=True, text=True,
            env={k: v for k, v in os.environ.items() if not k.startswith("OCCHIO_")})
        if esito.returncode != 0:
            print(esito.stderr[-2000:], file=sys.stderr)
            return 1
        quadro = quadro_dai_dati(dati)

    # Sul sito non si scrive: nessun server dietro, nessuna decisione da
    # prendere. La console lo legge e nasconde da sola cio' che scriverebbe.
    quadro["sola_lettura"] = True

    if USCITA.exists():
        shutil.rmtree(USCITA)
    USCITA.mkdir(parents=True)
    web = RADICE / "occhio" / "web"
    # La pagina dichiara da se' che legge un file invece di un server:
    # chiedere al server e fallire lascerebbe un 404 a ogni apertura.
    pagina = (web / "console.html").read_text(encoding="utf-8").replace(
        '<script src="console.js"></script>',
        '<script>window.QUADRO_STATICO = "quadro.json";</script>\n'
        '<script src="console.js"></script>', 1)
    (USCITA / "index.html").write_text(pagina, encoding="utf-8")
    for nome in ("console.css", "console.js"):
        shutil.copy(web / nome, USCITA / nome)
    (USCITA / "quadro.json").write_text(
        json.dumps(quadro, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"sito pronto in {USCITA}")
    print(f"  {quadro['totale']} oggetti, {len(quadro['zone'])} zone, "
          f"{len(quadro['vendite'])} vendite — tutti dati inventati")
    for f in sorted(USCITA.iterdir()):
        print(f"  {f.name:<14} {f.stat().st_size:>7} byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
