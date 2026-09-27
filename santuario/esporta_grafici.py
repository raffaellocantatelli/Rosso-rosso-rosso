#!/usr/bin/env python3
"""
Esporta ogni blocco ```mermaid di un file markdown in SVG, PNG e PDF,
compone un PDF unico, un indice HTML e un backup verificabile.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Uso:
    python santuario/esporta_grafici.py santuario/santuario-master.md
    python santuario/esporta_grafici.py FILE.md --formati svg,pdf --tema dark
    python santuario/esporta_grafici.py FILE.md --solo-estrai   # niente Chromium

Differenze rispetto alla guida incollata in chat (27/09), e perché:

- ID stabili. La guida numera i blocchi in ordine (G01, G02...). Ma G14 e
  G17 sono tabelle, non Mermaid: dal quindicesimo in poi ogni file avrebbe
  l'ID sbagliato. Qui l'ID si legge da un commento `%% G05 · Titolo` come
  prima riga del blocco; in sua assenza dal titolo markdown che precede;
  solo in ultima istanza dall'ordine.
- index.html con i dati dentro. La guida fa fetch('elenco.json'), che da
  file:// il browser blocca: l'indice si apriva vuoto.
- Nessun successo finto. Se un grafico non si converte, lo dice, lo scrive
  nel rapporto e l'uscita è 1. La guida con `set -e` si fermava al primo
  errore senza dire quanti ne restavano.
- mmdc 12 (settembre 2026) non accetta più -w, -H, -f: con i comandi
  della guida ogni PNG falliva con «unknown option». Versione fissata in
  santuario/package.json.
- Chromium da root in un container richiede --no-sandbox: il config di
  puppeteer viene generato qui.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from html import escape
from pathlib import Path

QUI = Path(__file__).resolve().parent
RE_ID = re.compile(r"^\s*%%\s*(G\d{2,3})\s*[·:\-–—]?\s*(.*)$")
RE_TITOLO_MD = re.compile(r"^#{1,6}\s+(.*)$")
RE_ID_IN_TITOLO = re.compile(r"\b(G\d{2,3})\b\s*[·:\-–—]?\s*(.*)")
CHROMIUM_NOTI = [
    "/opt/pw-browsers/chromium",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
]


def estrai(testo):
    """Restituisce [{id, titolo, sorgente}] per ogni blocco mermaid."""
    blocchi, righe = [], testo.splitlines()
    ultimo_titolo, dentro, corpo, n = "", False, [], 0
    for riga in righe:
        if not dentro:
            m = RE_TITOLO_MD.match(riga)
            if m:
                ultimo_titolo = m.group(1).strip()
            if re.match(r"^\s*```+\s*mermaid\s*$", riga):
                dentro, corpo = True, []
            continue
        if re.match(r"^\s*```+\s*$", riga):
            dentro, n = False, n + 1
            gid, titolo = None, ""
            prima = next((r for r in corpo if r.strip()), "")
            m = RE_ID.match(prima)
            if m:
                gid, titolo = m.group(1), m.group(2).strip()
            else:
                m = RE_ID_IN_TITOLO.search(ultimo_titolo)
                if m:
                    gid, titolo = m.group(1), m.group(2).strip()
            # uno slot con solo commenti %% è un posto da riempire, non un
            # grafico: renderlo produrrebbe un file che sembra un risultato.
            vuoto = not any(r.strip() and not r.strip().startswith("%%")
                            for r in corpo)
            blocchi.append({
                "id": gid,
                "titolo": titolo or ultimo_titolo,
                "sorgente": "\n".join(corpo).rstrip() + "\n",
                "ordine": n,
                "vuoto": vuoto,
            })
            continue
        corpo.append(riga)
    if dentro:
        raise SystemExit("ERRORE: un blocco ```mermaid non è mai chiuso.")

    usati = {b["id"] for b in blocchi if b["id"]}
    dup = sorted(i for i in usati if sum(b["id"] == i for b in blocchi) > 1)
    if dup:
        raise SystemExit(f"ERRORE: ID duplicati: {', '.join(dup)}")
    for b in blocchi:
        if not b["id"]:
            k = b["ordine"]
            while f"G{k:02d}" in usati:
                k += 1
            b["id"] = f"G{k:02d}"
            usati.add(b["id"])
            b["id_da_ordine"] = True
    return blocchi


def trova_mmdc():
    for c in [os.environ.get("MMDC"), shutil.which("mmdc"),
              str(QUI / "node_modules/.bin/mmdc")]:
        if c and Path(c).exists():
            return c
    return None


def config_puppeteer(dest):
    cfg = {"args": ["--no-sandbox", "--disable-setuid-sandbox"]}
    exe = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    exe = exe or next((p for p in CHROMIUM_NOTI if Path(p).exists()), None)
    if exe:
        cfg["executablePath"] = exe
    dest.write_text(json.dumps(cfg))
    return dest


def converti(mmdc, src, out, fmt, tema, sfondo, config, pcfg, larghezza):
    cmd = [mmdc, "-i", str(src), "-o", str(out), "-t", tema, "-b", sfondo,
           "-p", str(pcfg), "-q"]
    if config:
        cmd += ["-c", str(config)]
    if fmt == "png":
        # mmdc 12 ha tolto -w/-H/-f (la guida li usa ancora): ora è --size,
        # e il PDF si adatta da solo al grafico.
        cmd += ["--size", str(larghezza), "-s", "2"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    ok = r.returncode == 0 and out.exists() and out.stat().st_size > 0
    return ok, (r.stderr or r.stdout).strip()[-600:]


def unisci_pdf(pdfs, dest):
    try:
        from pypdf import PdfWriter
    except ImportError:
        return "pypdf non installato: `pip install pypdf` per il PDF unico"
    w = PdfWriter()
    for p in pdfs:
        w.append(str(p), outline_item=p.stem)
    with open(dest, "wb") as f:
        w.write(f)
    return None


def indice_html(elementi, dest, formati):
    carte = []
    for e in elementi:
        link = " ".join(
            f'<a href="{f}/{e["id"]}.{f}" download>{f.upper()}</a>'
            for f in formati if e["esiti"].get(f) == "ok")
        if e.get("vuoto"):
            carte.append(f'<div class="card"><h3>{e["id"]} · {escape(e["titolo"])}</h3>'
                         '<p class="vuoto">da incollare</p></div>')
            continue
        anteprima = (f'<img src="svg/{e["id"]}.svg" alt="{escape(e["titolo"])}" loading="lazy">'
                     if e["esiti"].get("svg") == "ok"
                     else '<p class="ko">anteprima non disponibile</p>')
        errore = "".join(f'<p class="ko">{f}: fallito</p>'
                         for f, v in e["esiti"].items() if v != "ok")
        carte.append(f'<div class="card"><h3>{e["id"]} · {escape(e["titolo"])}</h3>'
                     f'{anteprima}{errore}<div class="actions">{link} '
                     f'<a href="sorgenti/{e["id"]}.mmd">MMD</a></div></div>')
    dest.write_text(f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Grafici del Santuario</title>
<style>
:root{{--bg:#fff;--fg:#111827;--card:#F3F4F6;--bd:#E5E7EB;--acc:#1E40AF;--ko:#B91C1C}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0F172A;--fg:#E5E7EB;--card:#1E293B;--bd:#334155;--acc:#93C5FD;--ko:#FCA5A5}}}}
body{{font-family:system-ui,sans-serif;background:var(--bg);color:var(--fg);max-width:1200px;margin:2rem auto;padding:0 16px}}
h1{{color:var(--acc)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(360px,100%),1fr));gap:1.5rem}}
.card{{border:1px solid var(--bd);border-radius:8px;overflow:hidden}}
.card h3{{margin:0;padding:.75rem 1rem;background:var(--card);font-size:1rem}}
.card img{{width:100%;display:block;background:#fff}}
.actions{{padding:.5rem 1rem;display:flex;gap:.75rem;font-size:.875rem}}
.actions a{{color:var(--acc)}} .ko{{color:var(--ko);padding:0 1rem}}
.vuoto{{padding:2rem 1rem;opacity:.6;font-style:italic}}
</style></head><body>
<h1>Grafici del Santuario</h1>
<p>{len(elementi)} grafici · generato {time.strftime("%Y-%m-%d %H:%M")}</p>
<div class="grid">{''.join(carte)}</div>
</body></html>
""")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def backup(base, ingresso, elementi):
    """Archivio .tar.gz di sorgenti + master + elenco, con impronte SHA-256.

    Le sorgenti bastano a rigenerare tutto il resto: il backup conserva
    quelle, non i 3×N file derivati.
    """
    cartella = base / "backup"
    cartella.mkdir(exist_ok=True)
    marca = time.strftime("%Y%m%dT%H%M%S")
    arch = cartella / f"grafici-{marca}.tar.gz"
    file_ = [ingresso, base / "elenco.json"] + sorted((base / "sorgenti").glob("*.mmd"))
    with tarfile.open(arch, "w:gz") as t:
        for f in file_:
            t.add(f, arcname=f"{marca}/{f.name}")
    impronte = {f.name: sha256(f) for f in file_}
    (cartella / f"grafici-{marca}.sha256.json").write_text(json.dumps(
        {"archivio": arch.name, "sha256_archivio": sha256(arch),
         "file": impronte}, indent=2, ensure_ascii=False))
    # verifica: si rilegge ciò che si è scritto, non ci si fida del tar
    with tarfile.open(arch) as t:
        dentro = {Path(m.name).name for m in t.getmembers()}
    mancanti = set(impronte) - dentro
    if mancanti:
        raise SystemExit(f"ERRORE backup: mancano {sorted(mancanti)}")
    return arch


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ingresso", type=Path)
    ap.add_argument("--uscita", type=Path, default=None,
                    help="cartella di destinazione (default: grafici/ accanto al file)")
    ap.add_argument("--formati", default="svg,png,pdf")
    ap.add_argument("--tema", default="neutral",
                    choices=["default", "neutral", "dark", "forest", "base"])
    ap.add_argument("--config", type=Path, default=None,
                    help="config Mermaid JSON (es. santuario/mermaid-config.json)")
    ap.add_argument("--larghezza", type=int, default=2400)
    ap.add_argument("--solo-estrai", action="store_true")
    ap.add_argument("--senza-backup", action="store_true")
    a = ap.parse_args()

    if not a.ingresso.exists():
        raise SystemExit(f"ERRORE: {a.ingresso} non esiste.")
    base = a.uscita or a.ingresso.parent / "grafici"
    formati = [f.strip() for f in a.formati.split(",") if f.strip()]
    for d in ["sorgenti"] + formati:
        (base / d).mkdir(parents=True, exist_ok=True)

    blocchi = estrai(a.ingresso.read_text(encoding="utf-8"))
    if not blocchi:
        raise SystemExit("Nessun blocco ```mermaid trovato.")
    print(f"━━ Estratti {len(blocchi)} blocchi da {a.ingresso}")
    for b in blocchi:
        (base / "sorgenti" / f"{b['id']}.mmd").write_text(b["sorgente"])
        nota = "  (ID dall'ordine: aggiungi `%% Gnn · Titolo`)" if b.get("id_da_ordine") else ""
        print(f"   {b['id']}  {b['titolo'][:60]}{nota}")

    elementi = [{"id": b["id"], "titolo": b["titolo"], "esiti": {},
                 "vuoto": b["vuoto"]} for b in blocchi]
    vuoti = [e["id"] for e in elementi if e["vuoto"]]
    if vuoti:
        print(f"━━ {len(vuoti)} slot vuoti, da incollare: {', '.join(vuoti)}")
    fallimenti = []
    if not a.solo_estrai:
        mmdc = trova_mmdc()
        if not mmdc:
            raise SystemExit(
                "ERRORE: mmdc non trovato. Installa in santuario/ con\n"
                "  cd santuario && PUPPETEER_SKIP_DOWNLOAD=1 npm install @mermaid-js/mermaid-cli\n"
                "oppure usa --solo-estrai.")
        pcfg = config_puppeteer(base / ".puppeteer.json")
        for e in elementi:
            if e["vuoto"]:
                continue
            src = base / "sorgenti" / f"{e['id']}.mmd"
            for fmt in formati:
                sfondo = "white" if fmt == "pdf" else "transparent"
                ok, err = converti(mmdc, src, base / fmt / f"{e['id']}.{fmt}", fmt,
                                   a.tema, sfondo, a.config, pcfg, a.larghezza)
                e["esiti"][fmt] = "ok" if ok else "fallito"
                print(f"   {'✓' if ok else '✗'} {e['id']}.{fmt}")
                if not ok:
                    fallimenti.append({"file": f"{e['id']}.{fmt}", "errore": err})

        if "pdf" in formati:
            pdfs = [base / "pdf" / f"{e['id']}.pdf" for e in elementi
                    if e["esiti"].get("pdf") == "ok"]
            msg = unisci_pdf(pdfs, base / "tutti-grafici.pdf") if pdfs else "nessun PDF"
            print(f"━━ PDF unico: {msg or base / 'tutti-grafici.pdf'}")

    (base / "elenco.json").write_text(json.dumps(elementi, indent=2, ensure_ascii=False))
    indice_html(elementi, base / "index.html", formati)
    if fallimenti:
        (base / "fallimenti.json").write_text(json.dumps(fallimenti, indent=2, ensure_ascii=False))
    elif (base / "fallimenti.json").exists():
        (base / "fallimenti.json").unlink()

    if not a.senza_backup:
        print(f"━━ Backup: {backup(base, a.ingresso, elementi)}")

    fatti = sum(v == "ok" for e in elementi for v in e["esiti"].values())
    attesi = (len(elementi) - len(vuoti)) * (0 if a.solo_estrai else len(formati))
    print(f"━━ {fatti}/{attesi} file generati · indice: {base / 'index.html'}")
    if fallimenti:
        print(f"✗ {len(fallimenti)} falliti — dettagli in {base / 'fallimenti.json'}")
        sys.exit(1)


if __name__ == "__main__":
    main()
