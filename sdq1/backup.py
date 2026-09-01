"""Backup universale: snapshot completo dello stato del sistema, e ripristino.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import json
import os
import shutil
import time

BACKUP_ROOT = os.path.join("output", "backups")
TARGETS = [
    os.path.join("sdq1", "memory", "store.json"),
    os.path.join("sdq1", "sar", "state.json"),
    "registro_ipotesi.json",
    os.path.join("output", "contatti.jsonl"),
    os.path.join("output", "health_log.jsonl"),
]


def crea_backup():
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    dest = os.path.join(BACKUP_ROOT, f"backup_{stamp}")
    os.makedirs(dest, exist_ok=True)

    manifest = {"timestamp": stamp, "file": []}
    for target in TARGETS:
        if os.path.exists(target):
            shutil.copy2(target, os.path.join(dest, os.path.basename(target)))
            manifest["file"].append(target)

    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return dest


def ripristina_backup(percorso):
    manifest_path = os.path.join(percorso, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Nessun manifest.json trovato in {percorso}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for target in manifest["file"]:
        src = os.path.join(percorso, os.path.basename(target))
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        shutil.copy2(src, target)

    return manifest["file"]
