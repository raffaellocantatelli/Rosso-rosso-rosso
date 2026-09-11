#!/usr/bin/env python3
"""Da un ID QuickConnect agli indirizzi reali del NAS.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Il punto che bloccava il ponte: QuickConnect non e' WebDAV. L'ID «casa-mia»
non e' un URL, e nessun client WebDAV ci si puo' collegare. Serviva un
indirizzo esterno — DDNS, dominio, IP — e l'unico modo noto per ottenerlo era
aprire DSM da fuori casa e leggerlo dalla barra degli indirizzi.

RECUPERATO (11/09/2026, eseguito da questa sessione). Non e' l'unico modo.
Il coordinatore di Synology risponde in HTTP a chiunque chieda dove si trova
un ID, e l'ID non e' una credenziale: e' un nome pubblico. Con un ID
inesistente:

    POST https://global.quickconnect.to/Serv.php
    {"version":1,"command":"get_server_info","stop_when_error":false,
     "stop_when_success":false,"id":"dsm_portal_https","serverID":"..."}

    -> {"command":"get_server_info","errno":4,"suberrno":1,
        "errinfo":"get_server_info.go:92[Alias not found]","version":1}

Quindi: dato l'ID vero, la risposta contiene gli indirizzi. Da li' il ponte
si configura da solo.

IPOTESI, e va detta perche' cambia cosa aspettarsi (P6 — si falsifica
eseguendo `python -m ponte --cerca <ID>` con l'ID vero):

 1. i nomi dei campi qui sotto sono dedotti dalla forma della risposta, non
    letti su una risposta reale con dati dentro. Il lettore e' scritto per
    non rompersi se un campo manca o si chiama diversamente, e `--cerca
    --grezzo` stampa la risposta intera: se la deduzione e' sbagliata, si
    vede li' e si corregge in dieci minuti.
 2. il tunnel `*.quickconnect.to` inoltra i servizi DSM che si registrano
    con lui, e WebDAV sulla 5006 in generale non e' fra quelli. Per questo il
    candidato «relay» viene elencato per ultimo e marcato: se regge solo
    quello, serve comunque il DDNS o l'apertura della porta.
"""

from __future__ import annotations

import json
import socket
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

COORDINATORE = "https://global.quickconnect.to/Serv.php"
TIMEOUT = 15


class ErroreQuickConnect(Exception):
    pass


@dataclass
class Candidato:
    host: str
    come: str          # ddns | dominio | wan | lan | relay
    porta_dsm: int | None = None
    nota: str = ""

    def url_webdav(self, porta: int) -> str:
        # IPv6 va fra parentesi quadre, altrimenti i due punti dell'indirizzo
        # e quelli della porta diventano la stessa cosa e l'URL non e' valido.
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"https://{host}:{porta}"


def interroga(id_qc: str, servizio="dsm_portal_https", timeout=TIMEOUT) -> dict:
    """Chiede al coordinatore dove si trova un ID. Nessuna credenziale parte."""
    domanda = json.dumps({
        "version": 1,
        "command": "get_server_info",
        "stop_when_error": False,
        "stop_when_success": False,
        "id": servizio,
        "serverID": id_qc,
    }).encode("utf-8")
    req = urllib.request.Request(
        COORDINATORE, data=domanda,
        headers={"Content-Type": "application/json", "User-Agent": "R3-ponte/1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            grezzo = json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise ErroreQuickConnect(f"coordinatore non raggiungibile: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise ErroreQuickConnect(f"risposta del coordinatore illeggibile: {e}") from e
    errno = grezzo.get("errno")
    if errno not in (0, None):
        if errno == 4:
            raise ErroreQuickConnect(
                f"«{id_qc}» non risulta al coordinatore (errno 4, alias non trovato). "
                "L'ID QuickConnect e' quello scritto in DSM > Pannello di controllo > "
                "QuickConnect, senza «quickconnect.to/» davanti"
            )
        raise ErroreQuickConnect(
            f"il coordinatore risponde errno {errno}: {grezzo.get('errinfo', '')}"
        )
    return grezzo


def _aggiungi(candidati, visti, host, come, porta=None, nota=""):
    host = (host or "").strip().strip(".")
    if not host or host.upper() in ("NULL", "NONE") or host in visti:
        return
    visti.add(host)
    candidati.append(Candidato(host, come, porta, nota))


def candidati_da(grezzo: dict) -> list[Candidato]:
    """Estrae gli indirizzi dalla risposta, in ordine di utilita' per WebDAV.

    Ordine voluto: DDNS e dominio prima (indirizzi stabili raggiungibili da
    fuori), poi l'IP pubblico (cambia), poi la LAN (funziona solo da casa),
    infine il relay (vedi IPOTESI 2 in testa al file).
    """
    server = grezzo.get("server") or {}
    servizio = grezzo.get("service") or {}
    ambiente = grezzo.get("env") or {}
    porta = servizio.get("ext_port") or servizio.get("port")

    candidati: list[Candidato] = []
    visti: set[str] = set()

    _aggiungi(candidati, visti, server.get("ddns"), "ddns", porta,
              "nome Synology DDNS: e' l'indirizzo da mettere in R3_WEBDAV_URL")
    _aggiungi(candidati, visti, server.get("fqdn"), "dominio", porta)
    for chiave in ("external", "ipv6_tunnel"):
        blocco = server.get(chiave) or {}
        if isinstance(blocco, dict):
            _aggiungi(candidati, visti, blocco.get("ip"), "wan", porta,
                      "IP pubblico: funziona finche' non cambia")
    for rete in server.get("interface") or []:
        if isinstance(rete, dict):
            _aggiungi(candidati, visti, rete.get("ip"), "lan", porta,
                      "indirizzo interno: raggiungibile solo da casa")
            for v6 in rete.get("ipv6") or []:
                if isinstance(v6, dict):
                    _aggiungi(candidati, visti, v6.get("address"), "lan", porta)

    regione = ambiente.get("relay_region") or grezzo.get("smartdns", {}).get("host")
    serverid = grezzo.get("serverID") or server.get("serverID")
    if regione and serverid and "." not in str(regione):
        _aggiungi(candidati, visti, f"{serverid}.{regione}.quickconnect.to", "relay", None,
                  "tunnel QuickConnect: inoltra i servizi DSM, non per forza WebDAV")
    elif isinstance(regione, str) and "." in regione:
        _aggiungi(candidati, visti, regione, "relay", None,
                  "tunnel QuickConnect: inoltra i servizi DSM, non per forza WebDAV")
    return candidati


def risolvi(id_qc: str, timeout=TIMEOUT) -> tuple[list[Candidato], dict]:
    grezzo = interroga(id_qc, timeout=timeout)
    return candidati_da(grezzo), grezzo


def porta_aperta(host: str, porta: int, timeout=6) -> tuple[bool, str]:
    """Prova TCP+TLS. Dice se qualcosa risponde li', non se e' WebDAV."""
    try:
        with socket.create_connection((host, porta), timeout=timeout) as grezza:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE  # qui si misura la porta, non l'identita'
            with ctx.wrap_socket(grezza, server_hostname=host) as tls:
                cert = tls.getpeercert()
                return True, "TLS attivo" + (" (certificato presente)" if cert else "")
    except ssl.SSLError as e:
        return True, f"risponde ma non parla TLS come atteso: {e}"
    except socket.timeout:
        return False, "nessuna risposta entro il tempo (porta chiusa o filtrata)"
    except OSError as e:
        return False, str(e)
