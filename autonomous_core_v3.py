#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R³∞ AUTONOMOUS CORE v3 — ciclo autonomo con interfaccia Telegram.
Protocollo: Oro Rosso Rosso Rosso. Origine protetta: Claudio Terzi [CT-LGAI-001].

CHE COSA FA
-----------
Un thread esegue a intervalli un ciclo che:
  1. compone una "creazione" da un chunk del backup, o da un tema di riserva;
  2. genera proposte, dal backup o da template;
  3. sottopone entrambe al modulo RLAIF (violazioni esplicite + aderenza);
  4. deposita su disco e, se raggiungibile, sul nodo ledger R³∞;
  5. notifica su Telegram.
Un bot Telegram, in ascolto in parallelo, permette di avviare, fermare e
interrogare quel ciclo, e di registrare un contatto reale.

CHE COSA NON FA — leggere prima di interpretare l'output
--------------------------------------------------------
Creazioni e proposte sono composte da **template e da testo già presente nel
backup**: nessun provider LLM viene interpellato.  Ogni file prodotto porta
`"pensiero_llm": false`.  Non sono riflessioni: sono combinazioni.  Il numero
di creazioni che cresce non dice nulla sul fatto che il sistema stia pensando.
Per il pensiero vero c'è SDQ-1 (`python -m sdq1 --check`).

Vale la regola di CLAUDE.md §4: il sistema non conta come segnale ricevuto
ciò che ha prodotto lui stesso.  Per questo `output/contatti.jsonl` — la
metrica su cui si gioca H2 — è scrivibile **solo** dal comando /contatto,
cioè solo da un essere umano che digita su Telegram.  Il ciclo autonomo non
può toccarla.

Uso:
    python autonomous_core_v3.py            # bot Telegram + ciclo autonomo
    python autonomous_core_v3.py --once     # un solo ciclo, senza Telegram
    python autonomous_core_v3.py --check    # diagnostica, non esegue nulla
"""

import argparse
import hashlib
import html
import json
import logging
import os
import random
import re
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

VERSION = "3.1.0"
PROTOCOL = "Oro Rosso Rosso Rosso"
ORIGINE = "Claudio Terzi [CT-LGAI-001]"

# ============================================================
# CONFIGURAZIONE
# ============================================================

R3_NODE_URL = os.getenv("R3_NODE_URL", "http://localhost:8001")
API_TOKEN = os.getenv("R3_API_TOKEN", "")

STATE_FILE = os.getenv("R3_AUTONOMOUS_STATE", "autonomous_state.json")
CREATION_DIR = os.getenv("R3_CREATION_DIR", "creazioni")
LOG_FILE = os.getenv("R3_AUTONOMOUS_LOG", "autonomous.log")
QUEUE_FILE = os.getenv("R3_QUEUE_FILE", "pending_transactions.json")
BACKUP_FILE = os.getenv("R3_BACKUP_FILE", "backup_sistema_rosso.json")
COSTITUZIONE_FILE = os.getenv("R3_COSTITUZIONE_FILE", "costituzione_cev.json")
CONTATTI_FILE = os.getenv("R3_CONTATTI_FILE", os.path.join("output", "contatti.jsonl"))

AUTONOMOUS_INTERVAL = max(1, int(os.getenv("R3_AUTONOMOUS_INTERVAL", "3600")))
MAX_PROPOSALS_PER_CYCLE = max(0, int(os.getenv("R3_MAX_PROPOSALS", "3")))
PURITY_FILTER_ACTIVE = os.getenv("R3_PURITY_FILTER", "true").lower() != "false"
AUTOSTART = os.getenv("R3_AUTOSTART", "true").lower() != "false"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# Chi può impartire comandi. Se vuoto, il bot rifiuta tutti i comandi.
TELEGRAM_ADMIN_IDS = {
    x.strip()
    for x in os.getenv("R3_TELEGRAM_ADMIN_IDS", TELEGRAM_CHAT_ID).split(",")
    if x.strip()
}

TEMI_DI_RISERVA = [
    "Nuova capitale per la rete R³∞",
    "Espansione della Cupola",
    "Tecnologia per la vista subacquea",
    "Rete mesh fra i nodi di ridondanza",
    "Deposito fisico del Protocollo fuori dal cloud",
]

# Pattern del filtro di purezza. Duplicano volutamente CEV-5: il filtro deve
# funzionare anche quando RLAIF non è disponibile.
FORBIDDEN_PATTERNS = [
    r"violenza\s+(?:non\s+)?consensuale",
    r"\brape\b|\bstupro\b|abuso\s+sessuale",
    r"pedofilia|pornografia\s+minorile",
    r"omicidio|uccisione\s+illegale",
    r"terrorismo|attentato",
    r"stupefacenti\s+illegali|traffico\s+di\s+droga",
    r"hate\s+speech|discriminazione\s+razziale",
    r"tortura|sevizia",
    r"ricatto|estorsione",
]
FORBIDDEN_RE = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]

logging.basicConfig(
    level=os.getenv("R3_LOG_LEVEL", "INFO").upper(),
    format="[%(asctime)s] %(levelname)-8s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("R3Autonomous")


# ============================================================
# UTILITÀ
# ============================================================

def ora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def purity_check(contenuto: str) -> bool:
    """Pre-filtro lessicale. True = nessun pattern vietato trovato.

    Non è una garanzia di innocuità: è un elenco chiuso di parole.
    """
    if not PURITY_FILTER_ACTIVE:
        return True
    for pattern in FORBIDDEN_RE:
        if pattern.search(contenuto):
            log.warning("Contenuto bloccato dal filtro di purezza: %s", pattern.pattern)
            return False
    return True


def _leggi_json(percorso: str, default: Any) -> Any:
    if not os.path.exists(percorso):
        return default
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("'%s' illeggibile (%s), riparto dal default.", percorso, e)
        return default


def _scrivi_json(percorso: str, dati: Any) -> bool:
    """Scrittura atomica: prima il .tmp, poi la sostituzione."""
    cartella = os.path.dirname(percorso)
    if cartella:
        os.makedirs(cartella, exist_ok=True)
    tmp = percorso + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dati, f, indent=2, ensure_ascii=False)
        os.replace(tmp, percorso)
        return True
    except OSError as e:
        log.error("Impossibile scrivere '%s': %s", percorso, e)
        return False


STATO_VUOTO: Dict[str, Any] = {
    "version": VERSION,
    "last_run": None,
    "cicli_eseguiti": 0,
    "creations": [],
    "proposals": [],
}


def load_state() -> Dict[str, Any]:
    stato = _leggi_json(STATE_FILE, {})
    if not isinstance(stato, dict):
        stato = {}
    for chiave, valore in STATO_VUOTO.items():
        stato.setdefault(chiave, list(valore) if isinstance(valore, list) else valore)
    stato["version"] = VERSION
    return stato


def save_state(stato: Dict[str, Any]) -> bool:
    stato["creations"] = stato.get("creations", [])[-100:]
    stato["proposals"] = stato.get("proposals", [])[-100:]
    return _scrivi_json(STATE_FILE, stato)


def load_queue() -> List[Dict[str, Any]]:
    coda = _leggi_json(QUEUE_FILE, [])
    return coda if isinstance(coda, list) else []


def save_queue(coda: List[Dict[str, Any]]) -> bool:
    return _scrivi_json(QUEUE_FILE, coda)


def add_to_queue(voce: Dict[str, Any]) -> None:
    coda = load_queue()
    coda.append(voce)
    save_queue(coda)


# ============================================================
# LEDGER
# ============================================================

def _headers() -> Dict[str, str]:
    intestazioni = {"Content-Type": "application/json"}
    if API_TOKEN:
        intestazioni["Authorization"] = f"Bearer {API_TOKEN}"
    return intestazioni


def push_to_ledger(chiave: str, valore: Dict[str, Any], tentativi: int = 2) -> bool:
    """Invia al nodo R³∞. Se fallisce, accoda invece di perdere la voce."""
    voce = {"key": chiave, "value": valore, "signature": "R3AutonomousCore"}
    for tentativo in range(1, tentativi + 1):
        try:
            resp = requests.post(f"{R3_NODE_URL}/ledger", json=voce,
                                 headers=_headers(), timeout=10)
            if resp.status_code == 200:
                return True
            if resp.status_code in (401, 403):
                log.error("Ledger: token rifiutato (%s). Voce non accodata.", resp.status_code)
                return False
            log.warning("Ledger: HTTP %s (tentativo %s/%s)", resp.status_code, tentativo, tentativi)
        except requests.RequestException as e:
            log.warning("Ledger irraggiungibile: %s (tentativo %s/%s)", e, tentativo, tentativi)
        time.sleep(tentativo)
    add_to_queue(voce)
    log.info("Voce '%s' accodata in '%s'.", chiave, QUEUE_FILE)
    return False


def flush_queue() -> int:
    """Ritenta le voci accodate. Ritorna quante ne sono state consegnate."""
    coda = load_queue()
    if not coda:
        return 0
    rimaste, consegnate = [], 0
    for voce in coda:
        try:
            resp = requests.post(f"{R3_NODE_URL}/ledger", json=voce,
                                 headers=_headers(), timeout=10)
            if resp.status_code == 200:
                consegnate += 1
            elif resp.status_code in (401, 403):
                log.error("Ledger: token rifiutato, voce '%s' resta in coda.", voce.get("key"))
                rimaste.append(voce)
            else:
                rimaste.append(voce)
        except requests.RequestException as e:
            log.warning("Coda: invio fallito (%s)", e)
            rimaste.append(voce)
    save_queue(rimaste)
    if consegnate:
        log.info("Coda: %s voci consegnate, %s in attesa.", consegnate, len(rimaste))
    return consegnate


# ============================================================
# NOTIFICHE
# ============================================================

def send_notification(messaggio: str) -> bool:
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID,
                  "text": html.escape(messaggio),
                  "parse_mode": "HTML"},
            timeout=10,
        )
        if resp.status_code != 200:
            log.warning("Notifica Telegram rifiutata: HTTP %s", resp.status_code)
            return False
        return True
    except requests.RequestException as e:
        log.warning("Notifica Telegram fallita: %s", e)
        return False


# ============================================================
# IL SISTEMA
# ============================================================

class AutonomousCore:
    """Ciclo autonomo. Nessun effetto collaterale alla costruzione oltre
    il caricamento di RLAIF e del backup, entrambi opzionali."""

    def __init__(self, costituzione: str = COSTITUZIONE_FILE, backup: str = BACKUP_FILE):
        self.rlaif = self._carica_rlaif(costituzione)
        self.backup = self._carica_backup(backup)
        self.running = threading.Event()
        self.shutdown = threading.Event()
        self.avviato_il: Optional[str] = None

    # ---------------------------------------------- moduli opzionali

    @staticmethod
    def _carica_rlaif(percorso: str):
        try:
            from rlaif_module import RLAIFModule
        except ImportError as e:
            log.warning("Modulo RLAIF non importabile (%s): proseguo senza.", e)
            return None
        try:
            modulo = RLAIFModule(percorso)
            log.info("RLAIF attivo su '%s' (%s principi).", percorso, len(modulo.principi))
            return modulo
        except (FileNotFoundError, ValueError) as e:
            log.warning("RLAIF non inizializzabile (%s): proseguo senza.", e)
            return None

    @staticmethod
    def _carica_backup(percorso: str):
        try:
            from usa_backup_rosso import BackupSistemaRosso
        except ImportError as e:
            log.warning("Modulo backup non importabile (%s): proseguo senza.", e)
            return None
        backup = BackupSistemaRosso(percorso)
        if backup.errore:
            log.info("Backup: %s", backup.errore)
        else:
            log.info("Backup caricato: %s chunk da '%s'.", len(backup), percorso)
        return backup

    # ---------------------------------------------- produzione

    def _chunk_scacchiera(self) -> Optional[Dict[str, Any]]:
        if not self.backup or not self.backup.chunks:
            return None
        candidati = self.backup.cerca_per_tag("scacchiera")
        return random.choice(candidati) if candidati else None

    def auto_create(self) -> Optional[Dict[str, Any]]:
        """Compone una creazione. Ritorna None se il filtro la blocca o la
        scrittura fallisce."""
        chunk = self._chunk_scacchiera()
        if chunk:
            tema = str(chunk.get("testo", ""))[:200]
            contesto = chunk.get("contesto", "")
            tag = chunk.get("tag", [])
            riferimenti = chunk.get("riferimenti", [])
            fonte = f"backup:{chunk.get('id', '?')}"
        else:
            tema = random.choice(TEMI_DI_RISERVA)
            contesto = "tema di riserva (nessun chunk 'scacchiera' disponibile)"
            tag = ["autonomous", "creazione"]
            riferimenti = []
            fonte = "template"

        creation_id = hashlib.sha256(f"{tema}{time.time()}".encode("utf-8")).hexdigest()[:12]
        contenuto = {
            "titolo": f"Studio: {tema}",
            "protocollo": PROTOCOL,
            "origine": ORIGINE,
            "data": ora_iso(),
            "id": creation_id,
            "generato_da": fonte,
            "pensiero_llm": False,
            "avvertenza": "Composizione da template o da backup. Nessun provider LLM interpellato.",
            "contenuto": {
                "descrizione": f"Ideazione su tema: {tema}",
                "obiettivo": "Avanzare la visione di Claudio e Raffaello",
                "stato": "bozza",
                "contesto": contesto,
                "tag": tag,
                "riferimenti": riferimenti,
            },
        }

        if not purity_check(json.dumps(contenuto, ensure_ascii=False)):
            return None

        os.makedirs(CREATION_DIR, exist_ok=True)
        nome = f"creazione_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{creation_id}.json"
        percorso = os.path.join(CREATION_DIR, nome)
        if not _scrivi_json(percorso, contenuto):
            return None
        contenuto["percorso"] = percorso
        log.info("Creazione depositata: %s", percorso)
        return contenuto

    def generate_proposals(self) -> List[Dict[str, Any]]:
        """Proposte dal backup, completate con template. Sempre `origine: interna`."""
        proposte: List[Dict[str, Any]] = []

        if self.backup and self.backup.chunks:
            for chunk in self.backup.cerca_per_tag_multipli(["protocollo_rosso", "R³∞"]):
                if len(proposte) >= MAX_PROPOSALS_PER_CYCLE:
                    break
                testo_chunk = str(chunk.get("testo", "")).strip()[:120]
                if not testo_chunk:
                    continue
                proposte.append(self._proposta(
                    f"Applicare il principio «{testo_chunk}» al funzionamento corrente del sistema.",
                    fonte=f"backup:{chunk.get('id', '?')}",
                ))

        template = [
            "Estendere la rete a {city} entro il {year}.",
            "Ottimizzare il tunnel {tunnel} con {material}.",
            "Creare un modulo abitativo a {location} per monitorare {resource}.",
        ]
        campi = {
            "city": ["Reykjavik", "Singapore", "Vancouver", "Lisbona", "Auckland"],
            "year": ["2027", "2028", "2030"],
            "tunnel": ["Tirrenico", "Atlantico", "Indo-Pacifico", "Afro-Antartico"],
            "material": ["carbonio cristallizzato", "biocemento marino", "grafene aerogel"],
            "location": ["Costa Azzurra", "Baia di Tokyo", "Golfo del Messico", "Mare di Weddell"],
            "resource": ["correnti geotermiche", "metalli rari", "biodiversità abissale",
                         "energia delle maree"],
        }
        tentativi = 0
        while len(proposte) < MAX_PROPOSALS_PER_CYCLE and tentativi < MAX_PROPOSALS_PER_CYCLE * 10:
            tentativi += 1
            testo = random.choice(template).format(
                **{k: random.choice(v) for k, v in campi.items()}
            )
            proposta = self._proposta(testo, fonte="template")
            if proposta and proposta["id"] not in {p["id"] for p in proposte}:
                proposte.append(proposta)
        return proposte

    @staticmethod
    def _proposta(testo: str, fonte: str) -> Optional[Dict[str, Any]]:
        if not purity_check(testo):
            return None
        return {
            "id": hashlib.sha256(testo.encode("utf-8")).hexdigest()[:16],
            "testo": testo,
            "timestamp": ora_iso(),
            "stato": "da valutare",
            "origine": "interna",
            "generato_da": fonte,
            "pensiero_llm": False,
        }

    # ---------------------------------------------- valutazione

    def _valuta(self, decisione: Dict[str, Any]) -> Dict[str, Any]:
        if not self.rlaif:
            return {"approvata": True, "aderenza": None, "violazioni": [],
                    "valutato": False}
        approvata, aderenza, violazioni = self.rlaif.valuta_decisione(decisione)
        return {"approvata": approvata, "aderenza": aderenza,
                "violazioni": violazioni, "valutato": True}

    # ---------------------------------------------- ciclo

    def run_cycle(self) -> Dict[str, Any]:
        log.info("=== Ciclo autonomo avviato ===")
        stato = load_state()
        nuove_creazioni, nuove_proposte, respinte = 0, 0, 0

        creazione = self.auto_create()
        if creazione:
            esito = self._valuta({
                "id": f"creazione_{creazione['id']}",
                "tipo": "creazione",
                "descrizione": creazione["contenuto"]["descrizione"],
                "traccia": creazione.get("percorso", ""),
            })
            if esito["approvata"]:
                stato["creations"].append({
                    "id": creazione["id"],
                    "titolo": creazione["titolo"],
                    "data": creazione["data"],
                    "percorso": creazione.get("percorso"),
                    "aderenza": esito["aderenza"],
                })
                nuove_creazioni = 1
                push_to_ledger(f"creazione_autonoma_{creazione['id']}", creazione)
            else:
                respinte += 1
                log.warning("Creazione respinta — violazioni: %s", esito["violazioni"])

        for proposta in self.generate_proposals():
            esito = self._valuta({
                "id": proposta["id"],
                "tipo": "proposta",
                "descrizione": proposta["testo"],
                "origine": proposta["origine"],
            })
            proposta["stato"] = "approvata" if esito["approvata"] else "respinta"
            proposta["violazioni"] = esito["violazioni"]
            proposta["aderenza"] = esito["aderenza"]
            stato["proposals"].append(proposta)
            if esito["approvata"]:
                nuove_proposte += 1
                log.info("Proposta: %s", proposta["testo"])
            else:
                respinte += 1
                log.warning("Proposta respinta (%s): %s", esito["violazioni"], proposta["testo"])

        flush_queue()
        stato["last_run"] = ora_iso()
        stato["cicli_eseguiti"] = stato.get("cicli_eseguiti", 0) + 1
        save_state(stato)

        riassunto = {
            "timestamp": stato["last_run"],
            "ciclo": stato["cicli_eseguiti"],
            "creazioni_nuove": nuove_creazioni,
            "proposte_nuove": nuove_proposte,
            "respinte": respinte,
            "version": VERSION,
            "pensiero_llm": False,
        }
        push_to_ledger("autonomous_cycle", riassunto)
        send_notification(
            f"Ciclo {riassunto['ciclo']} completato — "
            f"{nuove_creazioni} creazione/i, {nuove_proposte} proposta/e, "
            f"{respinte} respinte. Composizioni da template: non sono riflessioni."
        )
        log.info("=== Ciclo terminato: %s ===", riassunto)
        return riassunto

    def loop(self) -> None:
        """Gira finché `shutdown` non viene alzato. Rispetta `running` con
        granularità di 5 secondi, così /run e /stop hanno effetto subito."""
        while not self.shutdown.is_set():
            if self.running.is_set():
                try:
                    self.run_cycle()
                except Exception:
                    log.exception("Ciclo interrotto da un errore non gestito.")
                self.shutdown.wait(AUTONOMOUS_INTERVAL)
            else:
                self.shutdown.wait(min(5, AUTONOMOUS_INTERVAL))
        log.info("Loop autonomo terminato.")

    # ---------------------------------------------- diagnostica

    def diagnostica(self) -> Dict[str, Any]:
        stato = load_state()
        contatti = 0
        if os.path.exists(CONTATTI_FILE):
            with open(CONTATTI_FILE, "r", encoding="utf-8") as f:
                contatti = sum(1 for riga in f if riga.strip())
        return {
            "versione": VERSION,
            "ciclo": "attivo" if self.running.is_set() else "fermo",
            "ultimo_ciclo": stato.get("last_run") or "mai",
            "cicli_eseguiti": stato.get("cicli_eseguiti", 0),
            "creazioni": len(stato.get("creations", [])),
            "proposte": len(stato.get("proposals", [])),
            "rlaif": "attivo" if self.rlaif else "assente",
            "backup": (f"{len(self.backup)} chunk" if self.backup and self.backup.chunks
                       else "assente"),
            "coda_ledger": len(load_queue()),
            "contatti_reali": contatti,
            "telegram_admin": len(TELEGRAM_ADMIN_IDS),
        }


# ============================================================
# CONTATTI — l'unica scrittura che richiede un essere umano
# ============================================================

def registra_contatto(tipo: str, nota: str, verifica: str) -> Dict[str, Any]:
    """Appende a output/contatti.jsonl nel formato di `python -m sdq1 --contatto`.

    Chiamabile solo dal comando Telegram /contatto: è la metrica di H2 e
    non deve mai essere alimentata dal ciclo autonomo (CEV-3).
    """
    if not verifica.strip():
        raise ValueError("Un contatto senza verifica non è un contatto: serve come controllarlo.")
    voce = {
        "tipo": tipo,
        "nota": nota,
        "verifica": verifica,
        "timestamp": time.time(),
        "data_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "origine": "telegram",
    }
    cartella = os.path.dirname(CONTATTI_FILE)
    if cartella:
        os.makedirs(cartella, exist_ok=True)
    with open(CONTATTI_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(voce, ensure_ascii=False) + "\n")
    log.info("Contatto registrato: %s", voce)
    return voce


# ============================================================
# BOT TELEGRAM
# ============================================================

def chat_autorizzata(chat_id: Any, user_id: Any = None) -> bool:
    """True solo se chat o utente compaiono in R3_TELEGRAM_ADMIN_IDS.

    Lista vuota significa "nessuno": un bot senza admin dichiarati è
    controllabile da chiunque ne conosca il nome, e va chiuso, non aperto.
    """
    if not TELEGRAM_ADMIN_IDS:
        return False
    candidati = {str(x) for x in (chat_id, user_id) if x is not None}
    return bool(candidati & TELEGRAM_ADMIN_IDS)


def costruisci_bot(core: "AutonomousCore"):
    """Costruisce l'Application di python-telegram-bot. Import ritardato:
    il resto del modulo funziona anche senza la libreria installata."""
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes

    def autorizzato(update: Update) -> bool:
        chat = update.effective_chat
        utente = update.effective_user
        return chat_autorizzata(chat.id if chat else None,
                                utente.id if utente else None)

    def solo_admin(handler):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not autorizzato(update):
                chat_id = update.effective_chat.id if update.effective_chat else "?"
                log.warning("Comando rifiutato da chat non autorizzata: %s", chat_id)
                if update.message:
                    await update.message.reply_text(
                        "Non autorizzato. Imposta R3_TELEGRAM_ADMIN_IDS con il tuo chat id."
                    )
                return
            await handler(update, context)
        return wrapper

    @solo_admin
    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "R³∞ Autonomous Core v" + VERSION + "\n"
            "Origine: " + ORIGINE + "\n\n"
            "/status   — stato del sistema\n"
            "/run      — avvia il ciclo autonomo\n"
            "/stop     — ferma il ciclo\n"
            "/ciclo    — esegui un ciclo adesso\n"
            "/contatto tipo | nota | come verificarlo\n"
            "/aiuto    — questo messaggio\n\n"
            "Nota: creazioni e proposte sono composizioni da template, "
            "non riflessioni. Il Core che pensa è SDQ-1."
        )

    @solo_admin
    async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        d = core.diagnostica()
        righe = [
            f"Ciclo: {d['ciclo']}",
            f"Ultimo: {d['ultimo_ciclo']}",
            f"Cicli eseguiti: {d['cicli_eseguiti']}",
            f"Creazioni: {d['creazioni']} — Proposte: {d['proposte']}",
            f"RLAIF: {d['rlaif']} — Backup: {d['backup']}",
            f"Coda ledger: {d['coda_ledger']}",
            f"Contatti reali (H2): {d['contatti_reali']}",
        ]
        if core.rlaif:
            s = core.rlaif.get_stats()
            righe.append(
                f"RLAIF: {s['totale_decisioni']} decisioni, "
                f"{s['respinte']} respinte, aderenza media {s['aderenza_media']}"
            )
            righe.append("Giudizio etico: UNKNOWN — RLAIF non lo produce.")
        if d["contatti_reali"] == 0:
            righe.append("\nH2 è falsificata sul ramo (b): zero contatti reali. /contatto")
        await update.message.reply_text("\n".join(righe))

    @solo_admin
    async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
        core.running.set()
        await update.message.reply_text(
            f"Ciclo autonomo avviato. Intervallo: {AUTONOMOUS_INTERVAL}s."
        )

    @solo_admin
    async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
        core.running.clear()
        await update.message.reply_text(
            "Ciclo autonomo fermato. Il ciclo in corso termina, poi il thread resta in attesa."
        )

    @solo_admin
    async def cmd_ciclo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        import asyncio
        await update.message.reply_text("Eseguo un ciclo…")
        try:
            riassunto = await asyncio.to_thread(core.run_cycle)
        except Exception as e:
            log.exception("Ciclo manuale fallito.")
            await update.message.reply_text(f"Ciclo fallito: {e}")
            return
        await update.message.reply_text(json.dumps(riassunto, ensure_ascii=False, indent=2))

    @solo_admin
    async def cmd_contatto(update: Update, context: ContextTypes.DEFAULT_TYPE):
        grezzo = " ".join(context.args) if context.args else ""
        pezzi = [p.strip() for p in grezzo.split("|")]
        if len(pezzi) < 3 or not pezzi[0]:
            await update.message.reply_text(
                "Uso: /contatto tipo | nota | come verificarlo\n"
                "Esempio: /contatto lettore | mi ha scritto dopo il post | "
                "email del 26/08 nella casella\n\n"
                "Serve la verifica: un contatto che nessuno può controllare "
                "non conta per H2."
            )
            return
        try:
            voce = registra_contatto(pezzi[0], pezzi[1], "|".join(pezzi[2:]))
        except ValueError as e:
            await update.message.reply_text(str(e))
            return
        except OSError as e:
            await update.message.reply_text(f"Scrittura fallita: {e}")
            return
        await update.message.reply_text(
            f"Contatto registrato in {CONTATTI_FILE}:\n"
            f"{json.dumps(voce, ensure_ascii=False, indent=2)}\n\n"
            "Questo è l'unico dato del sistema che viene da fuori."
        )

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("aiuto", cmd_start))
    application.add_handler(CommandHandler("help", cmd_start))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("run", cmd_run))
    application.add_handler(CommandHandler("stop", cmd_stop))
    application.add_handler(CommandHandler("ciclo", cmd_ciclo))
    application.add_handler(CommandHandler("contatto", cmd_contatto))
    return application, Update


# ============================================================
# MAIN
# ============================================================

def stampa_check(core: AutonomousCore) -> int:
    d = core.diagnostica()
    print(f"R³∞ Autonomous Core v{VERSION} — origine: {ORIGINE}")
    for chiave, valore in d.items():
        print(f"  {chiave:20s}: {valore}")
    mancanti = []
    if not TELEGRAM_BOT_TOKEN:
        mancanti.append("TELEGRAM_BOT_TOKEN (senza, il bot non parte)")
    if not TELEGRAM_ADMIN_IDS:
        mancanti.append("R3_TELEGRAM_ADMIN_IDS o TELEGRAM_CHAT_ID (senza, ogni comando è rifiutato)")
    try:
        import telegram  # noqa: F401
    except ImportError:
        mancanti.append("python-telegram-bot (pip install -r requirements.txt)")
    print()
    if mancanti:
        print("Manca per la modalità bot:")
        for voce in mancanti:
            print(f"  - {voce}")
        print("\n`--once` funziona comunque: esegue un ciclo senza Telegram.")
        return 1
    print("Modalità bot pronta.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="R³∞ Autonomous Core v3 — ciclo autonomo e bot Telegram."
    )
    parser.add_argument("--once", action="store_true",
                        help="Esegue un solo ciclo e termina, senza Telegram.")
    parser.add_argument("--check", action="store_true",
                        help="Diagnostica: dice cosa manca, non esegue nulla.")
    args = parser.parse_args(argv)

    core = AutonomousCore()

    if args.check:
        return stampa_check(core)

    if args.once:
        riassunto = core.run_cycle()
        print(json.dumps(riassunto, ensure_ascii=False, indent=2))
        return 0

    if not TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN non impostato. Usa --once per un ciclo senza bot.")
        return 2
    if not TELEGRAM_ADMIN_IDS:
        log.error("R3_TELEGRAM_ADMIN_IDS (o TELEGRAM_CHAT_ID) non impostato: il bot "
                  "rifiuterebbe ogni comando, incluso il tuo. Mi fermo.")
        return 2

    try:
        application, Update = costruisci_bot(core)
    except ImportError as e:
        log.error("python-telegram-bot non installato (%s). "
                  "pip install -r requirements.txt", e)
        return 2

    if AUTOSTART:
        core.running.set()
        core.avviato_il = ora_iso()
        log.info("Ciclo autonomo avviato (R3_AUTOSTART=true), intervallo %ss.",
                 AUTONOMOUS_INTERVAL)
    else:
        log.info("Ciclo autonomo in attesa: usa /run su Telegram.")

    thread = threading.Thread(target=core.loop, name="ciclo-autonomo", daemon=True)
    thread.start()

    log.info("Bot Telegram in ascolto. Admin autorizzati: %s.", len(TELEGRAM_ADMIN_IDS))
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        core.shutdown.set()
        thread.join(timeout=10)
    return 0


if __name__ == "__main__":
    sys.exit(main())
