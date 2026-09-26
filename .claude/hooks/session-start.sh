#!/bin/bash
# Avvio sessione Claude Code on the web: installa le dipendenze e dice subito
# se il Core SDQ-1 è acceso. L'output entra nel contesto della sessione, così
# nessun nodo deve ricordarsi di lanciare `python -m sdq1 --check` (CLAUDE.md §3).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

pip install -q --disable-pip-version-check -r requirements.txt >/dev/null 2>&1 \
  || echo "ATTENZIONE: pip install -r requirements.txt fallito"

echo "--- Avvio sessione: stato del Core (python -m sdq1 --check) ---"
# Core spento esce con codice != 0: è un'informazione, non un errore dell'hook.
python -m sdq1 --check 2>&1 || true
