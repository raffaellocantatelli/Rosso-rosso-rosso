#!/usr/bin/env python3
"""Client WebDAV minimo, sola libreria standard.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Perche' scritto a mano e non `pip install webdavclient3`: in questo progetto
un modulo che chiede un `pip install` per partire non viene provato (vedi
PROSSIMO_PASSO §1-bis, stessa scelta fatta per `occhio`). Qui bastano cinque
metodi HTTP — PROPFIND, MKCOL, PUT, GET, DELETE — e `urllib` li sa gia' fare.

Cosa NON fa, dichiarato: niente lock, niente COPY/MOVE, niente Digest auth
(Synology accetta Basic su HTTPS). Se servira', si aggiunge.
"""

from __future__ import annotations

import base64
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

DAV = "{DAV:}"
TIMEOUT = 20

PROPFIND_CORPO = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<d:propfind xmlns:d="DAV:"><d:prop>'
    "<d:resourcetype/><d:getcontentlength/><d:getlastmodified/>"
    "</d:prop></d:propfind>"
)


class ErrorePonte(Exception):
    """Il ponte non ha funzionato, e il messaggio dice cosa fare."""


@dataclass
class Voce:
    nome: str
    percorso: str
    cartella: bool
    byte: int | None = None
    modificato: str | None = None


def _contesto_tls(ca: str | None, insicuro: bool) -> ssl.SSLContext:
    if insicuro:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    if ca:
        return ssl.create_default_context(cafile=ca)
    return ssl.create_default_context()


def _normalizza(percorso: str) -> str:
    """`/R3/capsule/` e `R3//capsule` diventano la stessa cosa: /R3/capsule.

    Risolve anche `..`, e deve farlo qui: se restasse nella stringa, il
    controllo «sei dentro la radice» guarderebbe `/R3/../fuori`, vedrebbe che
    comincia per `/R3/` e lo lascerebbe passare. Il NAS invece lo risolve.
    """
    pezzi: list[str] = []
    for p in percorso.split("/"):
        if p in ("", "."):
            continue
        if p == "..":
            if pezzi:
                pezzi.pop()
            continue
        pezzi.append(p)
    return "/" + "/".join(pezzi)


class Ponte:
    """Un endpoint WebDAV e una cartella dentro cui il ponte ha diritto di scrivere.

    Il ponte non e' autorizzato fuori dalla radice: `deposita("../altro")` viene
    rifiutato prima di uscire, non dal NAS. Non e' paranoia, e' la condizione
    per poter usare un account con accesso alla sola cartella R3.
    """

    def __init__(self, url, utente, password, radice="/R3", ca=None,
                 insicuro=False, timeout=TIMEOUT):
        if not url:
            raise ErrorePonte("nessun URL WebDAV: vedi `python -m ponte --check`")
        self.base = url.rstrip("/")
        self.radice = _normalizza(radice)
        self.timeout = timeout
        self._auth = base64.b64encode(
            f"{utente or ''}:{password or ''}".encode("utf-8")
        ).decode("ascii")
        ctx = _contesto_tls(ca, insicuro)
        self._opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))

    # ------------------------------------------------------------------ rete

    def _url(self, percorso: str = "") -> str:
        pieno = _normalizza(f"{self.radice}/{percorso}") if percorso else self.radice
        return self.base + urllib.parse.quote(pieno)

    def _dentro_radice(self, percorso: str) -> str:
        pieno = _normalizza(f"{self.radice}/{percorso}")
        if pieno != self.radice and not pieno.startswith(self.radice.rstrip("/") + "/"):
            raise ErrorePonte(
                f"percorso fuori dalla radice {self.radice}: «{percorso}» rifiutato dal ponte"
            )
        return pieno

    def _chiama(self, metodo, url, corpo=None, intestazioni=None):
        testa = {"Authorization": f"Basic {self._auth}", "User-Agent": "R3-ponte/1"}
        testa.update(intestazioni or {})
        req = urllib.request.Request(url, data=corpo, headers=testa, method=metodo)
        try:
            with self._opener.open(req, timeout=self.timeout) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            # 207, 404, 405 sono risposte, non guasti: le gira a chi ha chiamato.
            return e.code, e.read(), dict(e.headers or {})
        except ssl.SSLCertVerificationError as e:
            raise ErrorePonte(
                f"certificato del NAS non verificato ({e.verify_message}). "
                f"Se e' autofirmato: esporta il certificato e indica R3_WEBDAV_CA. "
                f"R3_WEBDAV_INSICURO=1 salta la verifica, e va detto che salta"
            ) from e
        except urllib.error.URLError as e:
            raise ErrorePonte(f"{self.base} non raggiungibile: {e.reason}") from e
        except OSError as e:
            raise ErrorePonte(f"{self.base} non raggiungibile: {e}") from e

    def _controlla(self, stato, percorso, attesi):
        if stato in attesi:
            return
        if stato == 401:
            raise ErrorePonte(
                "credenziali rifiutate (401). Sul NAS: l'account esiste, ha accesso "
                "alla cartella, e WebDAV Server e' attivo per quell'utente"
            )
        if stato == 403:
            raise ErrorePonte(f"accesso negato a {percorso} (403): permessi della cartella")
        if stato == 404:
            raise ErrorePonte(f"{percorso} non esiste sul NAS (404)")
        if stato == 405:
            raise ErrorePonte(
                f"metodo non permesso su {percorso} (405): "
                "l'URL risponde ma non e' un endpoint WebDAV"
            )
        raise ErrorePonte(f"il NAS ha risposto {stato} su {percorso}")

    # --------------------------------------------------------------- lettura

    def check(self) -> dict:
        """Dice se il ponte regge, e cosa esattamente non regge. Non scrive nulla."""
        esito = {"url": self.base, "radice": self.radice}
        stato, _, testa = self._chiama("OPTIONS", self.base + "/")
        esito["risponde"] = stato < 500
        dav = testa.get("DAV") or testa.get("Dav") or ""
        esito["parla_webdav"] = bool(dav)
        esito["dav"] = dav or None
        esito["metodi"] = testa.get("Allow")
        stato, corpo, _ = self._chiama(
            "PROPFIND", self._url(), PROPFIND_CORPO.encode("utf-8"),
            {"Depth": "0", "Content-Type": "application/xml; charset=utf-8"},
        )
        esito["stato_radice"] = stato
        esito["autenticato"] = stato not in (401, 403)
        esito["radice_presente"] = stato == 207
        if stato == 207 and not esito["parla_webdav"]:
            # Alcune configurazioni non espongono l'intestazione DAV su OPTIONS
            # ma rispondono 207: vale la risposta, non l'annuncio.
            esito["parla_webdav"] = True
        return esito

    def elenca(self, percorso: str = "") -> list[Voce]:
        pieno = self._dentro_radice(percorso)
        stato, corpo, _ = self._chiama(
            "PROPFIND", self._url(percorso), PROPFIND_CORPO.encode("utf-8"),
            {"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
        )
        self._controlla(stato, pieno, (207,))
        return self._leggi_propfind(corpo, pieno)

    @staticmethod
    def _leggi_propfind(corpo: bytes, percorso_richiesto: str) -> list[Voce]:
        try:
            albero = ET.fromstring(corpo)
        except ET.ParseError as e:
            raise ErrorePonte(f"risposta PROPFIND illeggibile: {e}") from e
        voci = []
        for risposta in albero.findall(f"{DAV}response"):
            href = risposta.findtext(f"{DAV}href") or ""
            percorso = _normalizza(urllib.parse.unquote(urllib.parse.urlsplit(href).path))
            if percorso == percorso_richiesto:
                continue  # la cartella stessa
            prop = risposta.find(f"{DAV}propstat/{DAV}prop")
            cartella = False
            byte = modificato = None
            if prop is not None:
                tipo = prop.find(f"{DAV}resourcetype")
                cartella = tipo is not None and tipo.find(f"{DAV}collection") is not None
                lunghezza = prop.findtext(f"{DAV}getcontentlength")
                byte = int(lunghezza) if (lunghezza or "").strip().isdigit() else None
                modificato = prop.findtext(f"{DAV}getlastmodified")
            voci.append(Voce(percorso.rstrip("/").rsplit("/", 1)[-1], percorso,
                             cartella, byte, modificato))
        return sorted(voci, key=lambda v: (not v.cartella, v.nome))

    def preleva(self, percorso: str) -> bytes:
        pieno = self._dentro_radice(percorso)
        stato, corpo, _ = self._chiama("GET", self._url(percorso))
        self._controlla(stato, pieno, (200, 206))
        return corpo

    def esiste(self, percorso: str) -> bool:
        self._dentro_radice(percorso)
        stato, _, _ = self._chiama(
            "PROPFIND", self._url(percorso), PROPFIND_CORPO.encode("utf-8"),
            {"Depth": "0", "Content-Type": "application/xml; charset=utf-8"},
        )
        if stato in (401, 403):
            self._controlla(stato, percorso, ())
        return stato == 207

    # -------------------------------------------------------------- scrittura

    def crea_cartella(self, percorso: str) -> bool:
        """Vero se creata adesso, falso se c'era gia'. Idempotente di proposito."""
        pieno = self._dentro_radice(percorso)
        stato, _, _ = self._chiama("MKCOL", self._url(percorso))
        if stato in (405, 301):
            return False
        if stato == 409:
            padre = percorso.rstrip("/").rsplit("/", 1)[0]
            if padre and padre != percorso:
                self.crea_cartella(padre)
                stato, _, _ = self._chiama("MKCOL", self._url(percorso))
                if stato in (405, 301):
                    return False
        self._controlla(stato, pieno, (200, 201, 204))
        return True

    def deposita(self, percorso: str, dati: bytes, tipo="application/octet-stream") -> int:
        """Scrive un file e ne verifica la presenza. Ritorna i byte scritti."""
        pieno = self._dentro_radice(percorso)
        if not isinstance(dati, (bytes, bytearray)):
            raise ErrorePonte("deposita() vuole byte: chi chiama decide la codifica")
        cartella = percorso.rstrip("/").rsplit("/", 1)[0] if "/" in percorso.strip("/") else ""
        if cartella:
            self.crea_cartella(cartella)
        stato, _, _ = self._chiama(
            "PUT", self._url(percorso), bytes(dati),
            {"Content-Type": tipo, "Content-Length": str(len(dati))},
        )
        if stato == 409:
            # cartella padre assente: il NAS lo dice cosi'.
            self.crea_cartella(cartella or "")
            stato, _, _ = self._chiama(
                "PUT", self._url(percorso), bytes(dati),
                {"Content-Type": tipo, "Content-Length": str(len(dati))},
            )
        self._controlla(stato, pieno, (200, 201, 204))
        return len(dati)

    def rimuovi(self, percorso: str) -> None:
        pieno = self._dentro_radice(percorso)
        if pieno == self.radice:
            raise ErrorePonte("il ponte non cancella la propria radice")
        stato, _, _ = self._chiama("DELETE", self._url(percorso))
        self._controlla(stato, pieno, (200, 204, 404))
