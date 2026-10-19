"""Connessione a Redis per ONDA.

La password arriva da `ONDA_REDIS_PASSWORD` o dal file in
`ONDA_REDIS_PASSWORD_FILE` (secret di Docker). Senza password il client si
rifiuta di partire: un Redis aperto è un bus su cui chiunque in rete pubblica.
Per un Redis di prova senza password serve dichiararlo a mano con
`ONDA_REDIS_SENZA_PASSWORD=1`.
"""
import os
from urllib.parse import urlsplit

import redis


class ConfigurazioneMancante(Exception):
    pass


def password_da_ambiente():
    if os.environ.get("ONDA_REDIS_PASSWORD"):
        return os.environ["ONDA_REDIS_PASSWORD"]
    file = os.environ.get("ONDA_REDIS_PASSWORD_FILE")
    if file:
        # utf-8-sig: un file salvato dal Blocco note di Windows porta il BOM.
        with open(file, encoding="utf-8-sig") as f:
            return f.read().strip()
    return None


def url_da_ambiente():
    return os.environ.get("ONDA_REDIS_URL", "redis://127.0.0.1:6379/0")


def url_per_log(url):
    """L'URL senza credenziali, per il log."""
    p = urlsplit(url)
    host = p.hostname or "?"
    porta = f":{p.port}" if p.port else ""
    return f"{p.scheme}://{host}{porta}{p.path}"


def connetti(url=None, password=None, timeout=5.0):
    url = url or url_da_ambiente()
    password = password if password is not None else password_da_ambiente()
    if urlsplit(url).password:
        raise ConfigurazioneMancante(
            "password dentro ONDA_REDIS_URL: finirebbe nei log e in `ps`. "
            "Usa ONDA_REDIS_PASSWORD o ONDA_REDIS_PASSWORD_FILE.")
    if not password and os.environ.get("ONDA_REDIS_SENZA_PASSWORD") != "1":
        raise ConfigurazioneMancante(
            "nessuna password Redis (ONDA_REDIS_PASSWORD o ONDA_REDIS_PASSWORD_FILE)")
    return redis.Redis.from_url(
        url, password=password or None, decode_responses=False,
        socket_timeout=timeout, socket_connect_timeout=timeout,
        health_check_interval=30)
