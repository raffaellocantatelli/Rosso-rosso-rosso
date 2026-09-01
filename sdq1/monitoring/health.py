"""Watchdog leggero: verifica lo stato dei provider e della memoria,
scrive un record in output/health_log.jsonl a ogni invocazione.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import json
import os
import time

HEALTH_LOG = os.path.join("output", "health_log.jsonl")


def run_health_check(router, memory):
    provider_status = {
        name: {"disponibile": provider.available(), "circuito_aperto": router.breaker.is_open(name)}
        for name, provider in router.providers.items()
    }
    record = {
        "timestamp": time.time(),
        "data_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "providers": provider_status,
        "memoria_voci": len(memory),
    }
    os.makedirs(os.path.dirname(HEALTH_LOG), exist_ok=True)
    with open(HEALTH_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
