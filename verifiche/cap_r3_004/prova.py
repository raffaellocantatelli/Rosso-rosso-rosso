#!/usr/bin/env python3
"""prova.py — la rassegna di CAP-R3-004, rieseguibile da chiunque.

Origine protetta: Claudio Terzi [CT-LGAI-001].

`rassegna.py` dice la regola di questo progetto: **si chiedono esecuzioni,
non pareri.** Questo file la applica a se stesso. La rassegna in RASSEGNA.md
non va creduta: va rieseguita.

    python3 verifiche/cap_r3_004/prova.py

Non legge il mio riassunto e non legge una copia del codice di Meta. Ricostruisce
i file da `PATCH_ORIGINALE.diff` — il diff come e' arrivato, non toccato — in
una cartella temporanea, li esegue, e riferisce cosa ha osservato.

**Uscita 0** = i difetti ci sono ancora: la rassegna regge, la patch non e'
pronta.
**Uscita 1** = almeno un difetto non si riproduce piu': qualcuno ha corretto
la patch, oppure la rassegna era sbagliata. In entrambi i casi RASSEGNA.md e'
superata e va riscritta.

Nessun difetto qui e' un parere. Ognuno e' una riga di output che puo'
smentirmi.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

QUI = Path(__file__).resolve().parent
DIFF = QUI / "PATCH_ORIGINALE.diff"


def ricostruisci(diff_txt: str, dove: Path) -> dict[str, int]:
    """Estrae i file dal diff. Ritorna {percorso: righe_attese}."""
    attese: dict[str, int] = {}
    cur, buf, atteso = None, [], None

    def scrivi():
        if cur is None:
            return
        p = dove / cur
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(buf) + "\n")
        attese[cur] = atteso

    for ln in diff_txt.splitlines():
        if ln.startswith("+++ b/"):
            scrivi()
            cur, buf, atteso = ln[6:].strip(), [], None
            continue
        if ln.startswith("@@"):
            # @@ -0,0 +1,68 @@  ->  68 righe attese
            try:
                atteso = int(ln.split("+")[1].split("@@")[0].strip().split(",")[1])
            except (IndexError, ValueError):
                atteso = None
            continue
        if ln.startswith("--- "):
            continue
        if cur and ln.startswith("+"):
            buf.append(ln[1:])
    scrivi()
    return attese


def main() -> int:
    if not DIFF.exists():
        print(f"manca {DIFF} — non posso ricostruire niente")
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="cap_r3_004_"))
    try:
        attese = ricostruisci(DIFF.read_text(), tmp)

        print("RICOSTRUZIONE — dal diff originale, non da una copia")
        print("─" * 52)
        fedele = True
        for f, atteso in sorted(attese.items()):
            if f == "capability_registry.yaml":
                # e' l'unica modifica a un file gia' esistente: il suo @@
                # conta anche le righe di contesto, che qui non ricostruiamo
                print(f"  --  {f:<34} (modifica, non confrontabile)")
                continue
            reali = len((tmp / f).read_text().rstrip("\n").splitlines())
            ok = atteso is None or reali == atteso
            fedele &= ok
            print(f"  {'ok ' if ok else 'NO '} {f:<34} {reali} righe"
                  + ("" if ok else f" (il diff ne dichiara {atteso})"))
        if not fedele:
            print("\n  la ricostruzione non e' fedele: mi fermo qui")
            return 2

        env = {**os.environ, "PYTHONPATH": str(tmp), "PYTHONDONTWRITEBYTECODE": "1"}
        esito = subprocess.run(
            [sys.executable, "-m", "pytest", str(tmp / "tests"), "-q"],
            capture_output=True, text=True, env=env, cwd=tmp,
        )
        verde = esito.returncode == 0
        print(f"\n  suite di Meta: {esito.stdout.strip().splitlines()[-1] if esito.stdout.strip() else esito.returncode}")

        sys.path.insert(0, str(tmp))
        from cap_r3_004.in_memory import InMemoryNodeRegistry
        from cap_r3_004.postgres import PostgreSQLNodeRegistry
        from cap_r3_004.fabric_node import FabricNode

        difetti: list[tuple[str, bool, str]] = []

        # D1 — il costruttore inghiotte il fallimento di connessione
        s = PostgreSQLNodeRegistry(dsn="postgresql://nessuno@host.inesistente:5432/db")
        d1 = (s._use_real is False and s._real_conn is None
              and isinstance(s._mem, dict))
        difetti.append(("DSN irraggiungibile -> nessuna eccezione, ripiega su dict",
                        d1, f"_use_real={s._use_real} _mem={type(s._mem).__name__}"))

        # D2 — from_env promette PostgreSQL e consegna RAM
        os.environ["NODE_REGISTRY_DSN"] = "postgresql://nessuno@host.inesistente:5432/db"
        n = FabricNode.from_env("nodo-produzione")
        n.register_key("k1", "pub1")
        d2 = (type(n.registry).__name__ == "PostgreSQLNodeRegistry"
              and n.registry._use_real is False
              and n.get_active() is not None)
        difetti.append(("from_env: register_key dice OK e non persiste nulla",
                        d2, f"store={type(n.registry).__name__} reale={n.registry._use_real}"))
        os.environ.pop("NODE_REGISTRY_DSN", None)

        # D3 — il ramo PostgreSQL non e' coperto da nessun test
        pg = (tmp / "cap_r3_004" / "postgres.py").read_text()
        sabotato = (pg
                    .replace("        if self._use_real:\n            import psycopg\n",
                             '        if self._use_real:\n            raise AssertionError("RAMO PG")\n')
                    .replace("        if self._use_real:\n            with self._real_conn.cursor() as cur:\n",
                             '        if self._use_real:\n            raise AssertionError("RAMO PG")\n'
                             "            with self._real_conn.cursor() as cur:\n"))
        n_sab = sabotato.count("RAMO PG")
        (tmp / "cap_r3_004" / "postgres.py").write_text(sabotato)
        dopo = subprocess.run(
            [sys.executable, "-m", "pytest", str(tmp / "tests"), "-q"],
            capture_output=True, text=True, env=env, cwd=tmp,
        )
        d3 = verde and dopo.returncode == 0 and n_sab == 5
        difetti.append((f"sabotati {n_sab}/5 metodi PostgreSQL: la suite resta verde",
                        d3, f"prima={esito.returncode} dopo={dopo.returncode}"))
        (tmp / "cap_r3_004" / "postgres.py").write_text(pg)

        # D4 — REVOKED non esiste: la chiave revocata torna con un'altra public key
        r = InMemoryNodeRegistry()
        r.register("n", "k1", "pub-ORIGINALE")
        r.revoke("n", "k1")
        try:
            r.register("n", "k1", "pub-DELL-ATTACCANTE")
            attiva = r.get_active("n")
            d4 = attiva is not None and attiva["public_key"] == "pub-DELL-ATTACCANTE"
        except Exception as e:
            d4, attiva = False, repr(e)
        difetti.append(("chiave revocata riaccettata con public_key diversa",
                        d4, str(attiva)))

        # D5 — una chiave ROTATED torna ACTIVE con una rotazione all'indietro
        r2 = InMemoryNodeRegistry()
        r2.register("n", "k1", "pub1")
        r2.rotate("n", "k1", "k2", "pub2")
        try:
            r2.rotate("n", "k2", "k1", "pub1")
            d5 = r2.get_active("n")["key_id"] == "k1"
        except Exception:
            d5 = False
        difetti.append(("chiave ROTATED rimessa ACTIVE (rotazione all'indietro)",
                        d5, f"attiva={r2.get_active('n')['key_id']}"))

        # D6 — il ramo di simulazione PostgreSQL non ha lock
        d6 = (hasattr(InMemoryNodeRegistry(), "_lock")
              and not hasattr(PostgreSQLNodeRegistry(dsn=None, use_real_db=False), "_lock"))
        difetti.append(("_mem di PostgreSQLNodeRegistry condiviso senza lock",
                        d6, "in_memory ha RLock, postgres no"))

        # D7 — initial_keys accettato e mai usato
        d7 = InMemoryNodeRegistry(initial_keys={("n", "k1")}).list_keys("n") == []
        difetti.append(("initial_keys accettato dal costruttore e ignorato",
                        d7, "list_keys() vuota"))

        print("\nDIFETTI — ognuno osservato eseguendo, non leggendo")
        print("─" * 52)
        for titolo, presente, prova in difetti:
            print(f"  {'SI ' if presente else 'no '} {titolo}")
            print(f"      {prova}")

        vivi = sum(1 for _, p, _ in difetti if p)
        print("\n" + "─" * 52)
        if vivi == len(difetti):
            print(f"  {vivi}/{len(difetti)} difetti ancora presenti — RASSEGNA.md regge.")
            print("  La patch non e' pronta per il merge.")
            return 0
        print(f"  {vivi}/{len(difetti)} difetti presenti: qualcosa e' cambiato.")
        print("  RASSEGNA.md e' superata — va riscritta su questa esecuzione,")
        print("  non su quella del 18/09.")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
