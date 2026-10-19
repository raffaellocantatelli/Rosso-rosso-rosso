"""ONDA/1.0 con Redis reale: C3-C7 e il comando persistente. Nessun processo agente."""
import time

import pytest
import redis

from onda import envelope as E
from onda.chiavi import ChiavePrivata, Portachiavi, genera
from onda.lock import Lock, LockOccupato
from onda.nodo import Controllo, comando_persistente
from onda.validatore import RITMO_MAX, Validatore

from ._onda_supporto import PASSWORD, RedisVero


@pytest.fixture(scope="module")
def server():
    s = RedisVero()
    yield s
    s.chiudi()


@pytest.fixture
def r(server):
    c = redis.Redis(port=server.porta, password=PASSWORD)
    c.flushall()
    return c


@pytest.fixture
def k(tmp_path):
    for i, ruolo in [("RAFFA-001", "agente"), ("CONTROLLO-001", "controllo")]:
        genera(i, ruolo, str(tmp_path))
    pc = Portachiavi.carica(str(tmp_path))
    return (ChiavePrivata.carica("RAFFA-001", str(tmp_path)),
            ChiavePrivata.carica("CONTROLLO-001", str(tmp_path)), pc)


def test_c3_redis_rifiuta_senza_password(server):
    with pytest.raises(redis.AuthenticationError):
        redis.Redis(port=server.porta).ping()
    with pytest.raises(redis.AuthenticationError):
        redis.Redis(port=server.porta, password="sbagliata").ping()


def test_c4_idempotenza_per_ricevente(r, k):
    _, ctl, pc = k
    env = E.serializza(E.crea(ctl, "COMANDO", "*", {"azione": "PAUSA"}, epoch=0))
    v = Validatore(r, pc, "RAFFA-001")
    v.valida(env)
    with pytest.raises(E.EnvelopeRifiutato) as e:
        v.valida(env)
    assert e.value.motivo == "gia_visto"
    # Un broadcast vale una volta PER nodo, non una volta in tutto.
    Validatore(r, pc, "MEMO-002").valida(env)


def test_non_per_me(r, k):
    _, ctl, pc = k
    env = E.serializza(E.crea(ctl, "RICHIESTA", "SENTIN-004", {"testo": "x"}, epoch=0))
    with pytest.raises(E.EnvelopeRifiutato) as e:
        Validatore(r, pc, "RAFFA-001").valida(env)
    assert e.value.motivo == "non_per_me"


def test_c5_epoch_avanzato_invalida_il_vecchio(r, k):
    _, ctl, pc = k
    c = Controllo(r, ctl, pc)
    vecchio = E.serializza(E.crea(ctl, "EVENTO", "*", {}, epoch=0))
    assert c.avanza_epoch() == 1
    with pytest.raises(E.EnvelopeRifiutato) as e:
        Validatore(r, pc, "RAFFA-001").valida(vecchio)
    assert e.value.motivo == "epoch_superato"
    Validatore(r, pc, "RAFFA-001").valida(E.serializza(E.crea(ctl, "EVENTO", "*", {}, epoch=1)))


def test_solo_il_controllo_avanza_epoch(r, k):
    raffa, _, pc = k
    with pytest.raises(PermissionError):
        Controllo(r, raffa, pc).avanza_epoch()


def test_c6_lock(r):
    a, b = Lock(r, "prova", ttl_s=0.5), Lock(r, "prova", ttl_s=0.5)
    assert a.prendi() and not b.prendi()
    assert not b.rilascia(), "un token diverso non deve rilasciare il lock altrui"
    assert r.exists("onda:lock:prova")
    assert a.rinnova()
    time.sleep(0.7)
    assert not a.rinnova(), "scaduto: il rinnovo deve fallire"
    assert b.prendi()
    with pytest.raises(LockOccupato):
        with Lock(r, "prova", ttl_s=1):
            pass
    assert b.rilascia() and not r.exists("onda:lock:prova")


def test_c7_limite_di_frequenza(r, k):
    _, ctl, pc = k
    v = Validatore(r, pc, "RAFFA-001")
    adesso = time.time()
    motivi = []
    for _ in range(RITMO_MAX + 5):
        env = E.serializza(E.crea(ctl, "EVENTO", "*", {}, epoch=0, adesso=adesso))
        try:
            v.valida(env, adesso=adesso)
        except E.EnvelopeRifiutato as e:
            motivi.append(e.motivo)
    assert motivi == ["ritmo"] * 5


def test_un_falso_non_consuma_il_ritmo_altrui(r, k):
    raffa, ctl, pc = k
    v = Validatore(r, pc, "RAFFA-001")
    falso = E.crea(raffa, "EVENTO", "*", {}, epoch=0)
    falso["mittente"] = "CONTROLLO-001"
    for _ in range(RITMO_MAX + 5):
        with pytest.raises(E.EnvelopeRifiutato):
            v.valida(E.serializza(falso))
    v.valida(E.serializza(E.crea(ctl, "EVENTO", "*", {}, epoch=0)))


def test_comando_persistente_firmato_e_piu_recente(r, k):
    raffa, ctl, pc = k
    c = Controllo(r, ctl, pc)
    c.comando("PAUSA", "RAFFA-001")
    assert comando_persistente(r, pc, "RAFFA-001")["corpo"]["azione"] == "PAUSA"
    time.sleep(0.01)
    c.comando("STOP", "*")
    assert comando_persistente(r, pc, "RAFFA-001")["corpo"]["azione"] == "STOP"
    # Un comando scritto da chi ha solo la password Redis (firma di un agente) non vale.
    falso = E.crea(raffa, "COMANDO", "RAFFA-001", {"azione": "RIPRENDI"}, epoch=0)
    r.set("onda:comando:*", E.serializza(falso))
    assert comando_persistente(r, pc, "RAFFA-001")["corpo"]["azione"] == "PAUSA"
    # Dopo un avanzamento di epoch il vecchio comando persistito non vale più.
    c.avanza_epoch()
    assert comando_persistente(r, pc, "RAFFA-001") is None
