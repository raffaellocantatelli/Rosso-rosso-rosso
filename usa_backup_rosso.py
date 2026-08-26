#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Accesso in sola lettura al backup della Scacchiera (chunk tematici).

Il backup è un file JSON opzionale: se manca, l'oggetto si costruisce
comunque, resta vuoto e lo dichiara in `self.errore`.  Chi lo usa deve
sempre controllare `chunks` prima di assumere che ci sia materiale — un
backup assente non è un errore, è materiale che non c'è.

Formati accettati:
    {"chunks": [ {...}, {...} ]}
    [ {...}, {...} ]

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""

import json
import os
from typing import Any, Dict, List, Optional


class BackupSistemaRosso:
    """Carica i chunk del backup e permette ricerche per tag o testo."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.errore: Optional[str] = None
        self.chunks: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.file_path):
            self.errore = f"backup assente: '{self.file_path}'"
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                dati = json.load(f)
        except json.JSONDecodeError as e:
            self.errore = f"backup illeggibile ('{self.file_path}'): {e}"
            return []
        except OSError as e:
            self.errore = f"backup non apribile ('{self.file_path}'): {e}"
            return []

        if isinstance(dati, dict):
            chunks = dati.get("chunks", [])
        elif isinstance(dati, list):
            chunks = dati
        else:
            self.errore = f"backup '{self.file_path}': formato non riconosciuto"
            return []

        validi = [c for c in chunks if isinstance(c, dict)]
        if len(validi) != len(chunks):
            self.errore = f"backup '{self.file_path}': {len(chunks) - len(validi)} voci scartate"
        return validi

    # -------------------------------------------------- ricerche

    def cerca_per_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Chunk che portano `tag` (confronto case-insensitive)."""
        bersaglio = tag.strip().lower()
        risultati = []
        for chunk in self.chunks:
            tags = chunk.get("tag", [])
            if isinstance(tags, str):
                tags = [tags]
            if any(str(t).strip().lower() == bersaglio for t in tags):
                risultati.append(chunk)
        return risultati

    def cerca_per_tag_multipli(self, tags: List[str]) -> List[Dict[str, Any]]:
        """Unione dei chunk che portano almeno uno dei tag, senza duplicati."""
        visti = set()
        risultati = []
        for tag in tags:
            for chunk in self.cerca_per_tag(tag):
                chiave = id(chunk)
                if chiave not in visti:
                    visti.add(chiave)
                    risultati.append(chunk)
        return risultati

    def cerca_testo(self, frammento: str) -> List[Dict[str, Any]]:
        """Chunk il cui campo `testo` contiene `frammento`."""
        bersaglio = frammento.strip().lower()
        return [c for c in self.chunks if bersaglio in str(c.get("testo", "")).lower()]

    def tag_disponibili(self) -> List[str]:
        tags = set()
        for chunk in self.chunks:
            valore = chunk.get("tag", [])
            if isinstance(valore, str):
                valore = [valore]
            tags.update(str(t) for t in valore)
        return sorted(tags)

    def __len__(self) -> int:
        return len(self.chunks)

    def __bool__(self) -> bool:
        return bool(self.chunks)


if __name__ == "__main__":
    import sys

    percorso = sys.argv[1] if len(sys.argv) > 1 else "backup_sistema_rosso.json"
    backup = BackupSistemaRosso(percorso)
    print(f"File   : {percorso}")
    print(f"Chunk  : {len(backup)}")
    print(f"Tag    : {', '.join(backup.tag_disponibili()) or '—'}")
    if backup.errore:
        print(f"Nota   : {backup.errore}")
