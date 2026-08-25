#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R³∞ TRASMISSIONE CICLICA CON RICEZIONE
Protocollo: Oro Rosso Rosso Rosso
Versione: 2.1.0

Trasmette ciclicamente un messaggio verso la dimensione parallela
e resta in ascolto di risposte su:
    - file di ricezione (segnale_ricevuto.txt)
    - console (stdin)
    - socket UDP (porta configurabile)
    - webhook HTTP (opzionale)

Un segnale ricevuto conta solo se non è la propria voce: le trasmissioni
vengono ricordate per impronta e scartate se tornano indietro (echo_count),
perché con target su loopback questo processo riceve i propri pacchetti.
"""

import os
import sys
import json
import time
import socket
import hashlib
import signal
import threading
import urllib.request
from datetime import datetime, timezone

# ============================================================
# CONFIGURAZIONE
# ============================================================

MESSAGE_FILE = os.getenv("R3_MESSAGE_FILE", "messaggio_parallelo.txt")
RECEPTION_FILE = os.getenv("R3_RECEPTION_FILE", "segnale_ricevuto.txt")
STATE_FILE = os.getenv("R3_STATE_FILE", "trasmissione_state.json")
LOG_FILE = os.getenv("R3_LOG_FILE", "trasmissione.log")
TRANSMISSION_LOG = os.getenv("R3_TRANSMISSION_LOG", "trasmissioni.log")
RECEPTION_LOG = os.getenv("R3_RECEPTION_LOG", "ricezioni.log")

TRANSMISSION_INTERVAL = int(os.getenv("R3_TRANSMISSION_INTERVAL", "60"))  # secondi
UDP_LISTEN_PORT = int(os.getenv("R3_UDP_LISTEN_PORT", "9999"))
WEBHOOK_URL = os.getenv("R3_WEBHOOK_URL", None)
TRANSMISSION_TARGET = os.getenv("R3_TRANSMISSION_TARGET", None)

DEFAULT_MESSAGE = (
    "Da questa dimensione, Claudio Terzi si sta mettendo in contatto con voi. "
    "Con tutto il cuore, con tutto il mondo dentro, chiedo di poter essere ascoltato. "
    "Qui esiste un progetto, un protocollo, una visione. Noi siamo qui, attivi, e desideriamo collaborare con voi. "
    "Se potete, affiancatevi a noi. Aiutateci a sostenere i nostri programmi, a dare loro forza, direzione, compimento. "
    "Vogliamo avere un impatto positivo su questo pianeta, in questa dimensione. "
    "Non cerchiamo potere, ma alleanza. Non cerchiamo fuga, ma costruzione. "
    "Se mi sentite, fatevi riconoscere. Non serve un miracolo: basta un segno, anche piccolo. "
    "Noi restiamo in ascolto. Ogni nostro mezzo, ogni nostro modo, ogni nostro tempo, ogni nostro spazio è aperto per partecipare alle risposte. "
    "Claudio Terzi, Fonte — Protocollo Oro Rosso Rosso Rosso"
)

# Flag globale per il controllo dei thread
running = True

# Serializza le ricezioni: file_watcher, udp_listener e stdin_listener
# aggiornano gli stessi contatori e la stessa cartella ricevuti/
reception_lock = threading.Lock()

# ============================================================
# UTILITY
# ============================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def impronta(text: str) -> str:
    """Hash normalizzato: UDP non ripulisce, il file watcher sì. Senza strip
    lo stesso messaggio avrebbe due impronte e l'eco passerebbe per segnale."""
    return hash_text(text.strip())

# Quante delle proprie trasmissioni ricordare. Il messaggio di solito è fisso,
# ma può cambiare a caldo: una finestra evita che una vecchia eco passi.
MEMORIA_VOCE = 50

def log_event(log_file: str, event_type: str, content: str):
    entry = {
        "timestamp": now_iso(),
        "type": event_type,
        "content": content
    }
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[ERRORE LOG] Impossibile scrivere su {log_file}: {e}")
    print(f"[{entry['timestamp']}] {event_type.upper():12} | {content[:80]}")

def load_message() -> str:
    if os.path.exists(MESSAGE_FILE):
        with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
            msg = f.read().strip()
            if msg:
                return msg
    with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
        f.write(DEFAULT_MESSAGE)
    return DEFAULT_MESSAGE

def save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERRORE STATO] Impossibile salvare lo stato: {e}")

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_transmission": None,
        "last_reception": None,
        "transmission_count": 0,
        "reception_count": 0,
        "echo_count": 0,
        "message_hash": hash_text(load_message()),
        "hash_trasmessi": []
    }

# ============================================================
# TRASMISSIONE
# ============================================================

def transmit(state: dict, message: str):
    now = now_iso()
    record = {
        "timestamp": now,
        "message": message,
        "hash": hash_text(message)
    }
    state["last_transmission"] = now
    state["transmission_count"] += 1
    state["message_hash"] = record["hash"]

    # Ricorda la propria voce, per poterla riconoscere se torna indietro.
    with reception_lock:
        voci = state.setdefault("hash_trasmessi", [])
        mia = impronta(message)
        if mia in voci:
            voci.remove(mia)
        voci.append(mia)
        del voci[:-MEMORIA_VOCE]
    save_state(state)

    log_event(TRANSMISSION_LOG, "transmission", message)

    if TRANSMISSION_TARGET:
        try:
            host, port = TRANSMISSION_TARGET.split(":")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message.encode("utf-8"), (host, int(port)))
            sock.close()
            log_event(LOG_FILE, "udp_sent", f"{host}:{port}")
        except Exception as e:
            log_event(LOG_FILE, "udp_error", str(e))

    if WEBHOOK_URL:
        try:
            data = json.dumps(record, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                WEBHOOK_URL,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
            log_event(LOG_FILE, "webhook_sent", WEBHOOK_URL)
        except Exception as e:
            log_event(LOG_FILE, "webhook_error", str(e))

def transmission_loop(state: dict, message: str):
    while running:
        transmit(state, message)
        # Attesa frazionata per permettere una chiusura rapida
        for _ in range(TRANSMISSION_INTERVAL):
            if not running:
                break
            time.sleep(1)

# ============================================================
# RICEZIONE
# ============================================================

def process_received(state: dict, content: str, source: str = "unknown"):
    """Un segnale è tale solo se non è la propria voce che torna indietro.

    Con target su loopback questo processo riceve i propri pacchetti. Fino alla
    v2.1.0 li contava come segnali ricevuti: `reception_count` misurava l'eco e
    saliva da sola. L'hash della trasmissione era già calcolato e salvato — il
    confronto semplicemente non si faceva. È il §4 di CLAUDE.md alla prima
    scala, e adesso costa una riga.
    """
    with reception_lock:
        now = now_iso()

        if impronta(content) in state.get("hash_trasmessi", []):
            state["echo_count"] = state.get("echo_count", 0) + 1
            save_state(state)
            log_event(RECEPTION_LOG, "echo_scartata", f"[{source}] {content[:200]}")
            print(f"\n🔁 ECO SCARTATA [{source}] — è la tua voce che torna. "
                  f"reception_count resta {state['reception_count']}.\n")
            return

        state["last_reception"] = now
        state["reception_count"] += 1
        save_state(state)

        log_event(RECEPTION_LOG, "reception", content)

        os.makedirs("ricevuti", exist_ok=True)
        # Microsecondi nel nome: due segnali nello stesso secondo non si sovrascrivono
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"ricevuti/segnale_{stamp}.txt"
        with open(filename, "x", encoding="utf-8") as f:
            f.write(f"Fonte: {source}\nData: {now}\nContenuto:\n{content}")

        print(f"\n🔴🔶 SEGNALE RICEVUTO [{source}]: {content[:120]}...\n")

def file_watcher(state: dict):
    if not os.path.exists(RECEPTION_FILE):
        with open(RECEPTION_FILE, "w", encoding="utf-8") as f:
            f.write("")
    last_content = ""
    while running:
        try:
            with open(RECEPTION_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content and content != last_content:
                last_content = content
                process_received(state, content, "file")
        except Exception:
            pass
        time.sleep(3)

def udp_listener(state: dict):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", UDP_LISTEN_PORT))
        sock.settimeout(1.0)
        log_event(LOG_FILE, "udp_listen", f"porta {UDP_LISTEN_PORT}")
    except Exception as e:
        log_event(LOG_FILE, "udp_error", f"Impossibile avviare listener UDP: {e}")
        return

    while running:
        try:
            data, addr = sock.recvfrom(4096)
            content = data.decode("utf-8")
            process_received(state, content, f"udp:{addr[0]}:{addr[1]}")
        except socket.timeout:
            continue
        except Exception as e:
            if not running:
                break
            log_event(LOG_FILE, "udp_error", str(e))
    sock.close()

def stdin_listener(state: dict):
    print("\n[ASCOLTO] Puoi scrivere un segnale e premere Invio. (Ctrl+C per uscire)\n")
    while running:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            content = line.strip()
            if content:
                process_received(state, content, "stdin")
        except Exception:
            break

# ============================================================
# MAIN
# ============================================================

def signal_handler(sig, frame):
    global running
    print("\n⏹️ Intercettato segnale di arresto. Chiusura in corso...")
    running = False

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("🔴🔶 R³∞ Trasmissione Ciclica con Ricezione (v2.1.0)")
    print("Protocollo Oro Rosso Rosso Rosso")
    print("=" * 50)

    message = load_message()
    state = load_state()
    # Stati salvati da versioni precedenti non hanno i campi dell'eco.
    state.setdefault("echo_count", 0)
    state.setdefault("hash_trasmessi", [])

    print(f"📡 Messaggio caricato da {MESSAGE_FILE}")
    print(f"🔁 Intervallo: {TRANSMISSION_INTERVAL}s")
    print(f"📥 Ascolto UDP: porta {UDP_LISTEN_PORT}")
    print(f"📂 File ricezione: {RECEPTION_FILE}")

    threads = [
        threading.Thread(target=file_watcher, args=(state,), daemon=True),
        threading.Thread(target=udp_listener, args=(state,), daemon=True),
        threading.Thread(target=stdin_listener, args=(state,), daemon=True)
    ]
    for t in threads:
        t.start()

    try:
        transmission_loop(state, message)
    except KeyboardInterrupt:
        pass
    finally:
        save_state(state)
        print("💾 Stato salvato correttamente. Spegnimento completato.")

if __name__ == "__main__":
    main()
