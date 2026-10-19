"""Envelope ONDA/1.0: costruzione, firma e controlli che non richiedono Redis.

I controlli che richiedono stato condiviso (epoch, idempotenza, frequenza)
stanno in `validatore.py`. Qui c'è solo ciò che si decide guardando il
messaggio e il portachiavi — e si può quindi provare senza un server.
"""
import json
import re
import time
import uuid

from . import VERSIONE

DIMENSIONE_MAX = 16_384
TTL_MAX = 300.0
TOLLERANZA_FUTURO = 30.0

TIPI = ("HEARTBEAT", "RICHIESTA", "RISPOSTA", "COMANDO", "EVENTO", "ERRORE")
AZIONI = ("STOP", "PAUSA", "RIPRENDI")
CAMPI = ("onda", "id", "tipo", "mittente", "destinatario", "epoch", "ts",
         "scadenza", "correlazione", "corpo", "firma")

ID_NODO = re.compile(r"^[A-Z][A-Z0-9]{1,15}-[0-9]{3}$")
ID_ENVELOPE = re.compile(r"^[0-9a-f]{32}$")


class EnvelopeRifiutato(Exception):
    """Envelope non valido. `motivo` è un codice breve, adatto al log."""

    def __init__(self, motivo, dettaglio=""):
        super().__init__(f"{motivo}: {dettaglio}" if dettaglio else motivo)
        self.motivo = motivo


def canonico(env):
    """Byte su cui si firma: tutto tranne `firma`, in forma deterministica."""
    senza = {k: v for k, v in env.items() if k != "firma"}
    return json.dumps(senza, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def serializza(env):
    return json.dumps(env, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def crea(chiave, tipo, destinatario, corpo, epoch, ttl=30.0,
         correlazione=None, adesso=None):
    """Costruisce e firma un envelope. `chiave` è una `ChiavePrivata`."""
    ts = time.time() if adesso is None else adesso
    env = {
        "onda": VERSIONE,
        "id": uuid.uuid4().hex,
        "tipo": tipo,
        "mittente": chiave.id_nodo,
        "destinatario": destinatario,
        "epoch": int(epoch),
        "ts": ts,
        "scadenza": ts + float(ttl),
        "correlazione": correlazione,
        "corpo": corpo,
    }
    env["firma"] = chiave.firma(canonico(env))
    controlla_struttura(env)
    if len(serializza(env)) > DIMENSIONE_MAX:
        raise EnvelopeRifiutato("troppo_grande", "in uscita")
    return env


def decodifica(grezzo):
    """Byte o str dal canale → dict. Controlla dimensione e JSON."""
    if isinstance(grezzo, str):
        grezzo = grezzo.encode("utf-8")
    if len(grezzo) > DIMENSIONE_MAX:
        raise EnvelopeRifiutato("troppo_grande", f"{len(grezzo)} byte")
    try:
        env = json.loads(grezzo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise EnvelopeRifiutato("json_non_valido", str(e)[:80])
    if not isinstance(env, dict):
        raise EnvelopeRifiutato("non_oggetto")
    return env


def _numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def controlla_struttura(env):
    if set(env) != set(CAMPI):
        mancanti = sorted(set(CAMPI) - set(env))
        in_piu = sorted(set(env) - set(CAMPI))
        raise EnvelopeRifiutato("campi", f"mancanti={mancanti} in_piu={in_piu}")
    if env["onda"] != VERSIONE:
        raise EnvelopeRifiutato("versione", repr(env["onda"])[:20])
    if not isinstance(env["id"], str) or not ID_ENVELOPE.match(env["id"]):
        raise EnvelopeRifiutato("id")
    if env["tipo"] not in TIPI:
        raise EnvelopeRifiutato("tipo", repr(env["tipo"])[:20])
    if not isinstance(env["mittente"], str) or not ID_NODO.match(env["mittente"]):
        raise EnvelopeRifiutato("mittente")
    d = env["destinatario"]
    if not isinstance(d, str) or not (d == "*" or ID_NODO.match(d)):
        raise EnvelopeRifiutato("destinatario")
    if not isinstance(env["epoch"], int) or isinstance(env["epoch"], bool) or env["epoch"] < 0:
        raise EnvelopeRifiutato("epoch_tipo")
    if not _numero(env["ts"]) or not _numero(env["scadenza"]):
        raise EnvelopeRifiutato("tempo_tipo")
    if not (env["ts"] < env["scadenza"] <= env["ts"] + TTL_MAX):
        raise EnvelopeRifiutato("ttl", "scadenza fuori da (ts, ts+300]")
    c = env["correlazione"]
    if c is not None and (not isinstance(c, str) or not ID_ENVELOPE.match(c)):
        raise EnvelopeRifiutato("correlazione")
    if env["tipo"] in ("RISPOSTA", "ERRORE") and c is None:
        raise EnvelopeRifiutato("correlazione_mancante")
    if not isinstance(env["corpo"], dict):
        raise EnvelopeRifiutato("corpo")
    if not isinstance(env["firma"], str):
        raise EnvelopeRifiutato("firma_tipo")


def controlla_tempo(env, adesso=None):
    adesso = time.time() if adesso is None else adesso
    if env["ts"] > adesso + TOLLERANZA_FUTURO:
        raise EnvelopeRifiutato("dal_futuro")
    if env["scadenza"] <= adesso:
        raise EnvelopeRifiutato("scaduto")


def autorizza(env, ruolo, canale=None):
    """Regole di §5. `ruolo` è quello del mittente nel portachiavi."""
    tipo = env["tipo"]
    if tipo == "HEARTBEAT":
        if ruolo != "agente":
            raise EnvelopeRifiutato("non_autorizzato", "heartbeat da non-agente")
        if env["destinatario"] != "*" or (canale is not None and canale != "onda:hb"):
            raise EnvelopeRifiutato("non_autorizzato", "heartbeat fuori da onda:hb")
    elif tipo == "COMANDO":
        if ruolo != "controllo":
            raise EnvelopeRifiutato("non_autorizzato", "comando da non-controllo")
        if env["corpo"].get("azione") not in AZIONI:
            raise EnvelopeRifiutato("azione")
    elif tipo == "RICHIESTA":
        if env["destinatario"] == "*":
            raise EnvelopeRifiutato("non_autorizzato", "richiesta senza destinatario")


def verifica_offline(env, portachiavi, adesso=None, canale=None, controlla_scadenza=True):
    """Passi 1-5 di §2.1 su un dict già decodificato. Ritorna il ruolo."""
    controlla_struttura(env)
    voce = portachiavi.voce(env["mittente"])
    if voce is None:
        raise EnvelopeRifiutato("mittente_ignoto", env["mittente"])
    if not voce.verifica(canonico(env), env["firma"]):
        raise EnvelopeRifiutato("firma")
    if controlla_scadenza:
        controlla_tempo(env, adesso)
    autorizza(env, voce.ruolo, canale)
    return voce.ruolo
