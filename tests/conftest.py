"""Isola i test dal repository.

`autonomous_core_v3` legge le variabili d'ambiente al momento dell'import:
vanno impostate qui, prima che i moduli di test lo importino.
"""

import os
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

SANDBOX = tempfile.mkdtemp(prefix="r3-test-")

os.environ.update({
    "R3_AUTONOMOUS_STATE": os.path.join(SANDBOX, "state.json"),
    "R3_CREATION_DIR": os.path.join(SANDBOX, "creazioni"),
    "R3_AUTONOMOUS_LOG": os.path.join(SANDBOX, "autonomous.log"),
    "R3_QUEUE_FILE": os.path.join(SANDBOX, "queue.json"),
    "R3_RLAIF_LOG": os.path.join(SANDBOX, "rlaif.jsonl"),
    "R3_CONTATTI_FILE": os.path.join(SANDBOX, "contatti.jsonl"),
    # I registri del prodotto: senza queste, un test che costruisce
    # `Consegne()` senza argomenti leggerebbe le firme vere di un ospite vero
    # sulla macchina dell'autore, e potrebbe scriverci dentro.
    "OCCHIO_INVENTARIO": os.path.join(SANDBOX, "inventario.jsonl"),
    "OCCHIO_CONSEGNE": os.path.join(SANDBOX, "consegne.jsonl"),
    "OCCHIO_PORTAVIA": os.path.join(SANDBOX, "portavia.jsonl"),
    "OCCHIO_CREDITI": os.path.join(SANDBOX, "crediti.jsonl"),
    "R3_BACKUP_FILE": os.path.join(RADICE, "esempi", "backup_sistema_rosso.esempio.json"),
    # Porta chiusa: il ledger deve fallire e accodare, non contattare nulla di reale.
    "R3_NODE_URL": "http://127.0.0.1:9",
    "TELEGRAM_BOT_TOKEN": "",
    "TELEGRAM_CHAT_ID": "",
    "R3_TELEGRAM_ADMIN_IDS": "",
})
