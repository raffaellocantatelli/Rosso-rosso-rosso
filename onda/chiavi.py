"""Chiavi Ed25519 dei nodi ONDA.

Due file, con due destini diversi:

- `<DIR>/<ID>.key` — chiave privata, permessi 0600. **Mai nel repository.**
- `<DIR>/portachiavi.json` — chiavi pubbliche e ruoli. Si può copiare su
  ogni nodo: senza le private non serve a firmare.

La cartella di default è `~/.r3/onda/`, fuori dal repository perché il
repository è pubblico (CLAUDE.md §2.5).
"""
import base64
import json
import os

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from .envelope import ID_NODO

# agente: processo con heartbeat che serve richieste.
# controllo: l'unico che comanda (STOP/PAUSA/RIPRENDI) e avanza l'epoch.
# osservatore: interroga ed emette eventi (monitor, verifica sul NAS), non comanda.
RUOLI = ("agente", "controllo", "osservatore")


def cartella_default():
    return os.environ.get("ONDA_CHIAVI_DIR") or os.path.join(
        os.path.expanduser("~"), ".r3", "onda")


def _b64(b):
    return base64.b64encode(bytes(b)).decode("ascii")


class ChiavePrivata:
    def __init__(self, id_nodo, signing_key):
        self.id_nodo = id_nodo
        self._sk = signing_key

    def firma(self, dati):
        return _b64(self._sk.sign(dati).signature)

    @property
    def pubblica(self):
        return _b64(self._sk.verify_key)

    @classmethod
    def carica(cls, id_nodo, cartella=None):
        percorso = os.path.join(cartella or cartella_default(), f"{id_nodo}.key")
        with open(percorso, "rb") as f:
            seme = base64.b64decode(f.read().strip())
        return cls(id_nodo, SigningKey(seme))


class Voce:
    def __init__(self, id_nodo, pubblica, ruolo):
        self.id_nodo = id_nodo
        self.ruolo = ruolo
        self._vk = VerifyKey(base64.b64decode(pubblica))

    def verifica(self, dati, firma_b64):
        try:
            self._vk.verify(dati, base64.b64decode(firma_b64, validate=True))
            return True
        except (BadSignatureError, ValueError):
            return False


class Portachiavi:
    def __init__(self, voci):
        self._voci = voci

    def voce(self, id_nodo):
        return self._voci.get(id_nodo)

    def ruolo(self, id_nodo):
        v = self._voci.get(id_nodo)
        return v.ruolo if v else None

    def ids(self, ruolo=None):
        return sorted(i for i, v in self._voci.items() if ruolo is None or v.ruolo == ruolo)

    @classmethod
    def da_dict(cls, dati):
        voci = {}
        for id_nodo, d in dati.items():
            if not ID_NODO.match(id_nodo) or d.get("ruolo") not in RUOLI:
                raise ValueError(f"voce del portachiavi non valida: {id_nodo}")
            voci[id_nodo] = Voce(id_nodo, d["pubblica"], d["ruolo"])
        return cls(voci)

    @classmethod
    def carica(cls, cartella=None):
        with open(os.path.join(cartella or cartella_default(), "portachiavi.json"),
                  encoding="utf-8") as f:
            return cls.da_dict(json.load(f))


def genera(id_nodo, ruolo, cartella=None):
    """Crea la chiave privata (se non esiste) e registra la pubblica.

    Non sovrascrive mai una chiave privata esistente: rigenerarla
    invaliderebbe in silenzio la firma di quel nodo su tutti gli altri.
    """
    if not ID_NODO.match(id_nodo):
        raise ValueError(f"ID non valido: {id_nodo}")
    if ruolo not in RUOLI:
        raise ValueError(f"ruolo non valido: {ruolo}")
    cartella = cartella or cartella_default()
    os.makedirs(cartella, mode=0o700, exist_ok=True)
    percorso = os.path.join(cartella, f"{id_nodo}.key")
    if os.path.exists(percorso):
        chiave = ChiavePrivata.carica(id_nodo, cartella)
        creata = False
    else:
        sk = SigningKey.generate()
        fd = os.open(percorso, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(base64.b64encode(bytes(sk)))
        chiave = ChiavePrivata(id_nodo, sk)
        creata = True

    pc = os.path.join(cartella, "portachiavi.json")
    dati = {}
    if os.path.exists(pc):
        with open(pc, encoding="utf-8") as f:
            dati = json.load(f)
    dati[id_nodo] = {"pubblica": chiave.pubblica, "ruolo": ruolo}
    tmp = pc + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dati, f, indent=2, sort_keys=True)
    os.replace(tmp, pc)
    return chiave, creata
