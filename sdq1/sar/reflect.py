"""SAR — Scacchiera Auto-Riflessiva: auto-riflessione strutturata a 10 livelli
applicata a una tensione dichiarata come "Polo A ↔ Polo B".

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import json
import os
import time

STATE_PATH = os.path.join(os.path.dirname(__file__), "state.json")

LEVELS = [
    "Riconoscimento — nominare la tensione così com'è, senza addolcirla",
    "Origine — quando è comparsa per la prima volta questa tensione",
    "Pattern — in quali situazioni ricorre, con quale frequenza",
    "Segnale — come si manifesta nel corpo o nel comportamento",
    "Costo — cosa costa mantenere questa tensione irrisolta",
    "Credenza — quale convinzione tiene in piedi il polo '{a}'",
    "Contro-evidenza — un fatto reale che contraddice quella convinzione",
    "Alternativa — cosa cambierebbe scegliendo consapevolmente '{b}'",
    "Esperimento — un'azione singola, concreta e verificabile da provare",
    "Integrazione — come i due poli possono coesistere invece di escludersi",
]


def _split_tension(tension):
    for sep in ("↔", "<->", "<=>", " vs "):
        if sep in tension:
            a, b = tension.split(sep, 1)
            return a.strip(), b.strip()
    return tension.strip(), tension.strip()


def _load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _append_state(risultato):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    stato = _load_state()
    stato.append(risultato)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(stato, f, ensure_ascii=False, indent=2)


def reflect(tension):
    a, b = _split_tension(tension)
    livelli = [
        {"livello": i, "descrizione": template.format(a=a, b=b)}
        for i, template in enumerate(LEVELS, start=1)
    ]
    risultato = {
        "tensione": tension,
        "polo_a": a,
        "polo_b": b,
        "livelli": livelli,
        "timestamp": time.time(),
    }
    _append_state(risultato)
    return risultato


def stato_corrente():
    return _load_state()
