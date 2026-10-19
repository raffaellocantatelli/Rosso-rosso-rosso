"""Validazione completa (§2.1): i controlli offline più epoch, idempotenza, frequenza."""
import math
import time

from . import envelope as E

RITMO_MAX = 50  # envelope al secondo per mittente


def epoch_corrente(r):
    v = r.get("onda:epoch")
    return int(v) if v is not None else 0


class Validatore:
    def __init__(self, r, portachiavi, ricevente):
        self.r = r
        self.pc = portachiavi
        # L'idempotenza è per ricevente: un heartbeat o un comando a "*"
        # arriva a più nodi, e ognuno deve poterlo accettare una volta.
        self.ricevente = ricevente

    def valida(self, grezzo, canale=None, adesso=None):
        """Ritorna l'envelope valido o solleva `EnvelopeRifiutato`.

        L'ordine conta: frequenza e idempotenza scrivono su Redis, quindi
        vengono dopo la firma — un falso non deve poter consumare il ritmo
        di un mittente vero, né segnare come «visto» un id altrui.
        """
        adesso = time.time() if adesso is None else adesso
        env = E.decodifica(grezzo)
        E.verifica_offline(env, self.pc, adesso=adesso, canale=canale)
        if env["destinatario"] not in ("*", self.ricevente):
            raise E.EnvelopeRifiutato("non_per_me", env["destinatario"])
        self._ritmo(env["mittente"], adesso)
        if env["epoch"] < epoch_corrente(self.r):
            raise E.EnvelopeRifiutato("epoch_superato", str(env["epoch"]))
        ttl = max(1, math.ceil(env["scadenza"] - adesso) + 1)
        if not self.r.set(f"onda:visto:{self.ricevente}:{env['id']}", b"1", nx=True, ex=ttl):
            raise E.EnvelopeRifiutato("gia_visto", env["id"])
        return env

    def _ritmo(self, mittente, adesso):
        chiave = f"onda:ritmo:{self.ricevente}:{mittente}:{int(adesso)}"
        p = self.r.pipeline()
        p.incr(chiave)
        p.expire(chiave, 2)
        n = p.execute()[0]
        if n > RITMO_MAX:
            raise E.EnvelopeRifiutato("ritmo", f"{n}/s")
