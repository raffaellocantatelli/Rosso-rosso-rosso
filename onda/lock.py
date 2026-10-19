"""Lock distribuiti con scadenza (SET NX PX + Lua confronta-e-agisci)."""
import uuid

_RILASCIA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""
_RINNOVA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('pexpire', KEYS[1], ARGV[2])
end
return 0
"""


class LockOccupato(Exception):
    pass


class Lock:
    def __init__(self, r, nome, ttl_s):
        self.r = r
        self.chiave = f"onda:lock:{nome}"
        self.ttl_ms = int(ttl_s * 1000)
        self.token = uuid.uuid4().hex.encode()
        self.tenuto = False

    def prendi(self):
        self.tenuto = bool(self.r.set(self.chiave, self.token, nx=True, px=self.ttl_ms))
        return self.tenuto

    def rinnova(self):
        """False se il lock è scaduto o è passato a un altro: va trattato come perso."""
        self.tenuto = bool(self.r.eval(_RINNOVA, 1, self.chiave, self.token, self.ttl_ms))
        return self.tenuto

    def rilascia(self):
        ok = bool(self.r.eval(_RILASCIA, 1, self.chiave, self.token))
        self.tenuto = False
        return ok

    def __enter__(self):
        if not self.prendi():
            raise LockOccupato(self.chiave)
        return self

    def __exit__(self, *_):
        self.rilascia()
