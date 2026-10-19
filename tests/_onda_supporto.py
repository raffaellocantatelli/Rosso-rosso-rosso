"""Supporto ai test ONDA: un redis-server VERO su porta libera, con password e AOF.

Niente fakeredis: i criteri C3-C14 della specifica chiedono Redis reale.
Se `redis-server` manca, i test d'integrazione vengono SALTATI — e pytest lo
dice nel riepilogo, così nessuno li conta come passati.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASSWORD = "test-" + os.urandom(8).hex()


def porta_libera():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def attendi(cond, timeout=10.0, passo=0.05):
    limite = time.time() + timeout
    while time.time() < limite:
        v = cond()
        if v:
            return v
        time.sleep(passo)
    return cond()


class RedisVero:
    def __init__(self):
        if not shutil.which("redis-server"):
            pytest.skip("redis-server non installato: integrazione NON eseguita")
        self.dir = tempfile.mkdtemp(prefix="onda-redis-")
        self.porta = porta_libera()
        self.url = f"redis://127.0.0.1:{self.porta}/0"
        self.proc = None
        self.avvia()

    def avvia(self):
        self.proc = subprocess.Popen(
            ["redis-server", "--port", str(self.porta), "--bind", "127.0.0.1",
             "--requirepass", PASSWORD, "--dir", self.dir, "--appendonly", "yes",
             "--appendfsync", "always", "--save", ""],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import redis
        r = redis.Redis(port=self.porta, password=PASSWORD)
        assert attendi(lambda: self._ping(r), 10), "redis-server non risponde"

    @staticmethod
    def _ping(r):
        try:
            return r.ping()
        except Exception:
            return False

    def ferma(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(10)

    def riavvia(self):
        self.ferma()
        self.avvia()

    def chiudi(self):
        self.ferma()
        shutil.rmtree(self.dir, ignore_errors=True)


def ambiente(redis_vero, chiavi_dir, hb="0.3", **extra):
    env = dict(os.environ)
    env.update({"ONDA_REDIS_URL": redis_vero.url, "ONDA_REDIS_PASSWORD": PASSWORD,
                "ONDA_CHIAVI_DIR": chiavi_dir, "ONDA_HB_SECONDI": hb,
                "PYTHONPATH": RADICE})
    env.pop("ONDA_REDIS_PASSWORD_FILE", None)
    env.pop("ONDA_REDIS_SENZA_PASSWORD", None)
    env.update(extra)
    return env


def avvia_agente(id_nodo, env, log_dir):
    log = open(os.path.join(log_dir, f"{id_nodo}.log"), "ab")
    return subprocess.Popen([sys.executable, "-m", "onda", "agente", id_nodo],
                            cwd=RADICE, env=env, stdout=log, stderr=log)
