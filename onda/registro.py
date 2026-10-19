"""Log ONDA: una riga JSON per evento, su stderr.

Mai password, chiavi o corpo delle richieste: solo id, tipo, mittente, esito.
"""
import json
import logging
import sys
import time


class _FormatoJSON(logging.Formatter):
    def format(self, record):
        riga = {"ts": round(record.created, 3), "livello": record.levelname,
                "nodo": getattr(record, "nodo", None), "evento": record.getMessage()}
        riga.update(getattr(record, "campi", {}))
        return json.dumps(riga, ensure_ascii=False)


def logger(nome="onda"):
    log = logging.getLogger(nome)
    if not log.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(_FormatoJSON())
        log.addHandler(h)
        log.setLevel(logging.INFO)
        log.propagate = False
    return log


def evento(log, nodo, nome, livello=logging.INFO, **campi):
    log.log(livello, nome, extra={"nodo": nodo, "campi": campi})


def adesso():
    return time.time()
