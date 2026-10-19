"""Processo agente ONDA e lato controllo.

Un agente è un processo con una casella (`onda:a:<ID>`), un lock d'istanza e
un heartbeat firmato. Cosa sa fare lo decide il `servizio` che riceve: per
RAFFA-001, MEMO-002 e SENTIN-004 è l'adattatore verso le funzioni reali
della pipeline (`adattatore.py`).
"""
import os
import signal
import socket
import time

import redis

from . import envelope as E
from .lock import Lock
from .registro import evento, logger
from .validatore import Validatore, epoch_corrente

HB_DEFAULT = 10.0

ESCE_OK = 0
ESCE_CONFIG = 2
ESCE_FERMATO = 3
ESCE_ISTANZA = 4

ATTIVO, IN_PAUSA, FERMATO, USCITO = "ATTIVO", "IN_PAUSA", "FERMATO", "USCITO"
_STATO_DA_AZIONE = {"STOP": FERMATO, "PAUSA": IN_PAUSA, "RIPRENDI": ATTIVO}


def intervallo_hb():
    return float(os.environ.get("ONDA_HB_SECONDI", HB_DEFAULT))


def casella(id_nodo):
    return f"onda:a:{id_nodo}"


class CopiaLocale:
    """Copia su disco dell'ultimo COMANDO firmato ricevuto da questo agente.

    Redis con AOF conserva i comandi attraverso un riavvio, ma non se il suo
    volume va perso o viene ricreato vuoto: in quel caso uno STOP sparirebbe
    e gli agenti riprenderebbero a lavorare senza che nessuno l'abbia deciso.
    La copia locale chiude quel buco. Non è una seconda autorità: vale solo
    perché è firmata dal controllo, e si ri-verifica a ogni lettura.
    """

    def __init__(self, cartella, id_nodo):
        self.percorso = os.path.join(cartella, f"{id_nodo}.comando.json")

    def leggi(self):
        try:
            with open(self.percorso, "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def scrivi(self, env):
        tmp = self.percorso + ".tmp"
        with open(tmp, "wb") as f:
            f.write(E.serializza(env))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.percorso)

    @classmethod
    def da_ambiente(cls, id_nodo):
        cartella = os.environ.get("ONDA_STATO_DIR")
        return cls(cartella, id_nodo) if cartella else None


def comando_persistente(r, pc, id_nodo, copia=None):
    """L'ultimo COMANDO valido per questo nodo, fra `:<ID>`, `:*` e la copia locale.

    Si ri-verificano firma, ruolo ed epoch, non la scadenza: uno STOP
    persistito deve fermare anche un riavvio di domani. Un valore
    manomesso o con epoch superato viene ignorato, non obbedito.
    """
    attuale = epoch_corrente(r)
    migliore = None
    fonti = [r.get(f"onda:comando:{id_nodo}"), r.get("onda:comando:*")]
    if copia is not None:
        fonti.append(copia.leggi())
    for grezzo in fonti:
        if grezzo is None:
            continue
        try:
            env = E.decodifica(grezzo)
            E.verifica_offline(env, pc, controlla_scadenza=False)
        except E.EnvelopeRifiutato:
            continue
        if env["tipo"] != "COMANDO" or env["destinatario"] not in ("*", id_nodo):
            continue
        if env["epoch"] < attuale:
            continue
        if migliore is None or env["ts"] > migliore["ts"]:
            migliore = env
    return migliore


class Agente:
    def __init__(self, chiave, portachiavi, servizio, connetti, hb=None, log=None):
        self.chiave = chiave
        self.id = chiave.id_nodo
        self.pc = portachiavi
        self.servizio = servizio
        self._connetti = connetti
        self.hb = hb or intervallo_hb()
        self.log = log or logger()
        self.stato = ATTIVO
        self.incarnazione = None
        self._termina = False
        self._ultimo_comando = None
        self.copia = CopiaLocale.da_ambiente(self.id)

    # -- ciclo di vita ---------------------------------------------------

    def esegui(self):
        signal.signal(signal.SIGTERM, self._su_segnale)
        signal.signal(signal.SIGINT, self._su_segnale)
        attesa = 1.0
        self.lock = None
        while True:
            try:
                codice = self._sessione()
                return codice
            except redis.AuthenticationError:
                # Riprovare con la stessa password non serve: si esce e lo si dice.
                evento(self.log, self.id, "redis_password_rifiutata", 40)
                return ESCE_CONFIG
            except (redis.ConnectionError, redis.TimeoutError) as e:
                evento(self.log, self.id, "redis_perso", 30, errore=type(e).__name__,
                       riprovo_tra_s=attesa)
                if self._termina:
                    return ESCE_OK
                time.sleep(attesa)
                attesa = min(attesa * 2, 30.0)

    def _su_segnale(self, *_):
        self._termina = True

    def _sessione(self):
        self.r = self._connetti()
        self.r.ping()
        self.v = Validatore(self.r, self.pc, self.id)

        if self.lock is None:
            self.lock = Lock(self.r, f"istanza:{self.id}", ttl_s=3 * self.hb)
        else:
            self.lock.r = self.r
        # Dopo una riconnessione il lock può essere ancora nostro (Redis
        # rimasto su, o riletto dall'AOF): prima si prova a rinnovarlo.
        if not (self.lock.tenuto and self.lock.rinnova()) and not self.lock.prendi():
            evento(self.log, self.id, "istanza_gia_attiva", 40)
            return ESCE_ISTANZA

        if self.incarnazione is None:
            self.incarnazione = int(self.r.incr(f"onda:incarnazione:{self.id}"))
        cmd = comando_persistente(self.r, self.pc, self.id, self.copia)
        if cmd is not None:
            self._ultimo_comando = cmd["id"]
            self.stato = _STATO_DA_AZIONE[cmd["corpo"]["azione"]]
            self._conserva(cmd)
        if self.stato == FERMATO:
            evento(self.log, self.id, "fermato_da_comando_persistente", 30,
                   comando=cmd["id"] if cmd else None)
            self._chiudi(FERMATO)
            return ESCE_FERMATO

        ps = self.r.pubsub(ignore_subscribe_messages=True)
        ps.subscribe(casella(self.id), "onda:tutti")
        evento(self.log, self.id, "avviato", stato=self.stato,
               incarnazione=self.incarnazione, hb_s=self.hb)
        prossimo_hb = 0.0
        try:
            while not self._termina:
                if time.time() >= prossimo_hb:
                    if not self._heartbeat():
                        evento(self.log, self.id, "lock_istanza_perso", 40)
                        return ESCE_ISTANZA
                    prossimo_hb = time.time() + self.hb
                msg = ps.get_message(timeout=min(0.2, self.hb / 2))
                if msg and msg["type"] == "message":
                    canale = msg["channel"].decode()
                    if self._gestisci(msg["data"], canale) == FERMATO:
                        self._chiudi(FERMATO)
                        return ESCE_OK
            self._chiudi(USCITO)
            return ESCE_OK
        finally:
            try:
                ps.close()
            except Exception:
                pass

    def _chiudi(self, stato):
        self.stato = stato
        try:
            self.r.hset(f"onda:agente:{self.id}", mapping={"stato": stato, "hb": b""})
            self.lock.rilascia()
        except redis.RedisError:
            pass
        evento(self.log, self.id, "chiuso", stato=stato)

    def _heartbeat(self):
        if not self.lock.rinnova():
            return False
        corpo = {"stato": self.stato, "incarnazione": self.incarnazione,
                 "pid": os.getpid(), "host": socket.gethostname()[:64]}
        env = E.crea(self.chiave, "HEARTBEAT", "*", corpo,
                     epoch_corrente(self.r), ttl=3 * self.hb)
        dati = E.serializza(env)
        p = self.r.pipeline()
        p.hset(f"onda:agente:{self.id}", mapping={"stato": self.stato, "hb": dati})
        p.publish("onda:hb", dati)
        p.execute()
        return True

    # -- messaggi --------------------------------------------------------

    def _gestisci(self, grezzo, canale):
        try:
            env = self.v.valida(grezzo, canale=canale)
        except E.EnvelopeRifiutato as e:
            evento(self.log, self.id, "rifiutato", 30, motivo=e.motivo,
                   canale=canale, byte=len(grezzo))
            return None
        tipo = env["tipo"]
        if tipo == "COMANDO":
            return self._comando(env)
        if tipo == "RICHIESTA":
            self._richiesta(env)
        return None

    def _conserva(self, env):
        """Scrive la copia locale. Se non riesce, lo dice: una protezione che
        manca in silenzio è peggio di una che non c'è."""
        if self.copia is None:
            return
        try:
            self.copia.scrivi(env)
        except OSError as e:
            evento(self.log, self.id, "copia_locale_non_scritta", 40,
                   errore=type(e).__name__)

    def _comando(self, env):
        azione = env["corpo"]["azione"]
        self._ultimo_comando = env["id"]
        self._conserva(env)
        precedente, self.stato = self.stato, _STATO_DA_AZIONE[azione]
        evento(self.log, self.id, "comando", azione=azione, da=env["mittente"],
               id=env["id"], stato_prima=precedente, stato_dopo=self.stato)
        if self.stato != FERMATO:
            self._heartbeat()
        return self.stato

    def _richiesta(self, env):
        t0 = time.time()
        if self.stato == IN_PAUSA:
            esito, corpo, tipo = "in_pausa", {"codice": "IN_PAUSA"}, "ERRORE"
        else:
            try:
                corpo, tipo, esito = self.servizio(env["corpo"]), "RISPOSTA", "ok"
            except ValueError as e:
                corpo, tipo, esito = {"codice": "RICHIESTA_NON_VALIDA",
                                      "messaggio": str(e)[:200]}, "ERRORE", "non_valida"
            except Exception as e:  # l'agente non deve morire per una richiesta
                corpo, tipo, esito = {"codice": "ERRORE_AGENTE",
                                      "classe": type(e).__name__}, "ERRORE", "errore"
        try:
            risposta = E.crea(self.chiave, tipo, env["mittente"], corpo,
                              epoch_corrente(self.r), ttl=30, correlazione=env["id"])
        except E.EnvelopeRifiutato:
            risposta = E.crea(self.chiave, "ERRORE", env["mittente"],
                              {"codice": "RISPOSTA_TROPPO_GRANDE"},
                              epoch_corrente(self.r), ttl=30, correlazione=env["id"])
            esito = "troppo_grande"
        self.r.publish(casella(env["mittente"]), E.serializza(risposta))
        evento(self.log, self.id, "richiesta", id=env["id"], da=env["mittente"],
               esito=esito, ms=round((time.time() - t0) * 1000, 1))


class NessunoInAscolto(Exception):
    pass


class TempoScaduto(Exception):
    pass


class Controllo:
    """Il lato che comanda e interroga. Firma con una chiave di ruolo `controllo`
    (per i comandi) o qualunque chiave registrata (per richieste e stato)."""

    def __init__(self, r, chiave, portachiavi):
        self.r = r
        self.chiave = chiave
        self.pc = portachiavi

    def comando(self, azione, destinatario):
        if azione not in E.AZIONI:
            raise ValueError(f"azione sconosciuta: {azione}")
        env = E.crea(self.chiave, "COMANDO", destinatario, {"azione": azione},
                     epoch_corrente(self.r), ttl=60)
        dati = E.serializza(env)
        canale = "onda:tutti" if destinatario == "*" else casella(destinatario)
        # Prima si persiste, poi si pubblica: un agente che si riavvia fra
        # i due passi trova comunque il comando.
        p = self.r.pipeline()
        p.set(f"onda:comando:{destinatario}", dati)
        p.publish(canale, dati)
        _, ricevuto = p.execute()
        return env, int(ricevuto)

    def richiesta(self, destinatario, corpo, timeout=10.0):
        v = Validatore(self.r, self.pc, self.chiave.id_nodo)
        ps = self.r.pubsub(ignore_subscribe_messages=True)
        ps.subscribe(casella(self.chiave.id_nodo))
        try:
            env = E.crea(self.chiave, "RICHIESTA", destinatario, corpo,
                         epoch_corrente(self.r), ttl=max(timeout, 1.0))
            if self.r.publish(casella(destinatario), E.serializza(env)) == 0:
                raise NessunoInAscolto(destinatario)
            limite = time.time() + timeout
            while time.time() < limite:
                msg = ps.get_message(timeout=min(0.5, max(0.01, limite - time.time())))
                if not msg or msg["type"] != "message":
                    continue
                try:
                    r = v.valida(msg["data"], canale=casella(self.chiave.id_nodo))
                except E.EnvelopeRifiutato:
                    continue
                if r["correlazione"] == env["id"] and r["mittente"] == destinatario:
                    return r
            raise TempoScaduto(destinatario)
        finally:
            ps.close()

    def avanza_epoch(self):
        if self.pc.ruolo(self.chiave.id_nodo) != "controllo":
            raise PermissionError("solo un nodo di ruolo controllo avanza l'epoch")
        return int(self.r.incr("onda:epoch"))

    def stato(self):
        return stato_agenti(self.r, self.pc)


def stato_agenti(r, pc, adesso=None):
    """Lo stato di ogni agente del portachiavi, dedotto dall'ultimo heartbeat FIRMATO.

    Online = heartbeat con firma valida e non scaduto. Il campo `stato`
    dell'hash è scritto in chiaro e chiunque abbia la password Redis
    potrebbe cambiarlo: qui si legge solo dall'envelope firmato.
    """
    adesso = time.time() if adesso is None else adesso
    righe = []
    for id_nodo in pc.ids("agente"):
        h = r.hgetall(f"onda:agente:{id_nodo}")
        riga = {"agente": id_nodo, "online": False, "stato": "MAI_VISTO"}
        if h:
            riga["stato"] = (h.get(b"stato") or b"?").decode()
            grezzo = h.get(b"hb") or b""
            if grezzo:
                try:
                    env = E.decodifica(grezzo)
                    E.verifica_offline(env, pc, adesso=adesso, canale="onda:hb")
                    if env["mittente"] == id_nodo and env["tipo"] == "HEARTBEAT":
                        riga.update(online=True, stato=env["corpo"]["stato"],
                                    incarnazione=env["corpo"]["incarnazione"],
                                    pid=env["corpo"]["pid"], host=env["corpo"]["host"],
                                    eta_hb_s=round(adesso - env["ts"], 1))
                except E.EnvelopeRifiutato as e:
                    riga["motivo"] = e.motivo
            if not riga["online"] and riga["stato"] in (ATTIVO, IN_PAUSA):
                riga["stato"] = "OFFLINE"
        righe.append(riga)
    return righe
