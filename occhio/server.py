#!/usr/bin/env python3
"""occhio.server — server locale, solo libreria standard.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Nessuna dipendenza oltre `requests` (gia' nel progetto): niente FastAPI,
niente build front-end. Motivo pratico verificato il 03/09: in questo
ambiente `fastapi` e `Pillow` non sono installati, e un sistema che per
partire chiede prima un `pip install` e' un sistema che qualcuno non provera'.

I fotogrammi **non vengono mai salvati su disco.** Restano in memoria per il
tempo della chiamata al modello e poi spariscono. Sul disco finiscono solo
righe di testo: tipo, titolo, impronta a 64 bit, orario. Un inventario di
casa non ha bisogno delle fotografie di casa, e questo repository e' pubblico.

Il server ascolta su 127.0.0.1 e basta: `--host 0.0.0.0` esiste ma stampa
un avviso, perche' non c'e' autenticazione e chi apre la porta sta mettendo
la telecamera di casa su una rete.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import inventario as inv
from . import visione as vis

WEB = Path(__file__).parent / "web"
LIMITE_CORPO = 12 * 1024 * 1024  # un fotogramma JPEG a 1280px sta molto sotto


def sovrapposizione(a, b) -> float:
    """Intersezione su unione fra due riquadri [x, y, larghezza, altezza].

    Serve ad associare l'impronta calcolata su un fotogramma al riquadro che
    il modello riporta sul fotogramma successivo: fra uno scatto e l'altro la
    mano si muove, e due riquadri dello stesso oggetto non coincidono mai.
    """
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
        return 0.0
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    unione = aw * ah + bw * bh - inter
    return inter / unione if unione > 0 else 0.0


#: Sotto questa sovrapposizione due riquadri non sono lo stesso oggetto.
#: 0.4 tollera il movimento della mano fra due fotogrammi a 2,5 s di distanza
#: senza fondere due dorsi adiacenti sullo stesso scaffale.
SOGLIA_SOVRAPPOSIZIONE = 0.4


def impronta_vicina(riquadro, impronte):
    """Impronta gia' calcolata per il riquadro piu' sovrapposto, se c'e'."""
    migliore, punteggio = None, SOGLIA_SOVRAPPOSIZIONE
    for voce in impronte:
        if not isinstance(voce, dict):
            continue
        r = voce.get("riquadro")
        imp = voce.get("impronta")
        if not imp or not isinstance(r, list) or len(r) < 4:
            continue
        try:
            p = sovrapposizione(riquadro, [float(v) for v in r[:4]])
        except (TypeError, ValueError):
            continue
        if p > punteggio:
            migliore, punteggio = str(imp), p
    return migliore


class Stato:
    """Cio' che il server tiene fra una richiesta e l'altra."""

    def __init__(self, percorso_inventario, cascata, autoscrittura, soglia,
                 pianta=None):
        self.lock = threading.Lock()
        self.inventario = inv.Inventario(percorso_inventario)
        self.cascata = cascata
        self.autoscrittura = autoscrittura
        self.soglia = soglia
        self.pianta = pianta
        self.fotogrammi = 0
        self.letture_riuscite = 0
        self.errori = 0


class Handler(BaseHTTPRequestHandler):
    server_version = "occhio/1.0"
    stato: Stato = None  # iniettato in avvia()

    # -- utilita' ---------------------------------------------------------

    def _json(self, codice, dati):
        corpo = json.dumps(dati, ensure_ascii=False).encode("utf-8")
        self.send_response(codice)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _corpo(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return None
        if n <= 0 or n > LIMITE_CORPO:
            return None
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def log_message(self, formato, *args):
        # Il log predefinito stampa ogni richiesta: con un fotogramma al
        # secondo diventa illeggibile. Restano gli errori.
        if args and str(args[0]).startswith(("4", "5")):
            sys.stderr.write("%s - %s\n" % (self.address_string(), formato % args))

    # -- rotte ------------------------------------------------------------

    def do_GET(self):
        percorso = self.path.split("?")[0]
        if percorso == "/api/stato":
            s = self.stato
            return self._json(200, {
                "visione": vis.stato(),
                "cascata": list(s.cascata),
                "stub": s.cascata == ("stub",),
                "autoscrittura": s.autoscrittura,
                "soglia_confidenza": s.soglia,
                "inventario": {
                    "file": str(s.inventario.percorso),
                    "oggetti": len(s.inventario.voci),
                    "per_tipo": s.inventario.per_tipo(),
                },
                "fotogrammi": s.fotogrammi,
                "letture_riuscite": s.letture_riuscite,
                "errori": s.errori,
            })
        if percorso == "/api/quadro":
            return self._quadro()
        if percorso == "/api/inventario":
            with self.stato.lock:
                voci = sorted(self.stato.inventario.voci,
                              key=lambda v: v.get("visto_ultimo", ""), reverse=True)
            return self._json(200, {"oggetti": voci, "totale": len(voci)})
        if percorso == "/api/esporta.csv":
            with self.stato.lock:
                corpo = self.stato.inventario.csv().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="inventario.csv"')
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            return self.wfile.write(corpo)
        return self._statico(percorso)

    def do_POST(self):
        percorso = self.path.split("?")[0]
        if percorso == "/api/fotogramma":
            return self._fotogramma()
        if percorso == "/api/conferma":
            return self._conferma()
        if percorso == "/api/chat":
            return self._chat()
        if percorso == "/api/voce":
            return self._voce()
        return self._json(404, {"errore": "rotta sconosciuta"})

    # -- statico ----------------------------------------------------------

    def _quadro(self):
        """Tutto lo stato in una chiamata sola: la console lo disegna intero.

        Sono cinque letture che l'interfaccia farebbe comunque, e farle
        separate significa disegnare cinque volte una schermata incoerente
        mentre arrivano. Qui il quadro e' uno, e o c'e' tutto o non c'e'.
        """
        s = self.stato
        with s.lock:
            reg = s.inventario
            per_luogo = reg.per_luogo()
            voci = sorted(reg.voci, key=lambda v: v.get("visto_ultimo", ""), reverse=True)
            fusioni = reg.fusioni()

            quadro = {
                "oggetti": [{"chiave": v.get("chiave"), "tipo": v.get("tipo"),
                             "titolo": v.get("titolo"),
                             "zona": (self._zona(v)),
                             "avvistamenti": v.get("avvistamenti", 1),
                             "fonte": v.get("fonte")}
                            for v in voci],
                "zone": {z.split(" › ")[0]: len(o) for z, o in per_luogo.items()},
                "totale": len(reg.voci),
                "fusioni": [{"chiave": f["chiave"], "titoli": f["titoli_visti"]}
                            for f in fusioni],
                "pianta": s.pianta,
                "stub": s.cascata == ("stub",),
                "consegne": [], "differenza": None, "vendite": [], "chiari": None,
            }

        # TALLY, PORTAVIA e i chiari sono file a se': si leggono senza il lock
        # dell'inventario, e se mancano il quadro resta valido e lo dice.
        try:
            from .consegna import Consegne, differenza
            c = Consegne()
            alloggi = sorted({x.get("alloggio") for x in c.stati if x.get("alloggio")})
            for a in alloggi:
                prima, dopo = c.ultimo(a, "consegna"), c.ultimo(a, "riconsegna")
                controfirme = {v.get("riferimento") for v in c.stati
                               if v.get("tipo") == "controfirma"}
                quadro["consegne"].append({
                    "alloggio": a,
                    "consegna": {"momento": prima["momento"],
                                 "controfirmata": prima["impronta"] in controfirme,
                                 "oggetti": len(prima["oggetti"])} if prima else None,
                    "riconsegna": {"momento": dopo["momento"],
                                   "controfirmata": dopo["impronta"] in controfirme,
                                   "oggetti": len(dopo["oggetti"])} if dopo else None,
                })
                if prima and dopo and quadro["differenza"] is None:
                    quadro["differenza"] = differenza(prima, dopo)
        except Exception as e:
            quadro["consegne_errore"] = vis.oscura_segreti(e)

        try:
            from .portavia import Portavia, spiega_mancanti
            pv = Portavia()
            from .portavia import GENERI, MERCE, NOMI_DEI_GENERI
            quadro["vendite"] = pv.movimenti[-12:]
            quadro["generi"] = {g: NOMI_DEI_GENERI[g] for g in GENERI}
            for v in quadro["vendite"]:
                v.setdefault("genere", MERCE)
            quadro["incasso"] = pv.incasso()
            if quadro["differenza"]:
                quadro["differenza"] = spiega_mancanti(quadro["differenza"], pv)
        except Exception:
            pass

        try:
            from .crediti import Crediti
            quadro["chiari"] = Crediti().verifica()
        except Exception:
            pass

        return self._json(200, quadro)

    @staticmethod
    def _zona(voce):
        from .inventario import _etichetta
        luoghi = voce.get("luoghi") or [voce.get("luogo")]
        return _etichetta(luoghi[0]).split(" › ")[0] if luoghi and luoghi[0] else None

    def _statico(self, percorso):
        if percorso in ("/console", "/console/"):
            percorso = "/console.html"
        nome = "index.html" if percorso in ("/", "") else percorso.lstrip("/")
        # Nessuna risalita di directory: il server gira nella cartella di casa
        # di qualcuno, e `/../../.env` conterrebbe le chiavi.
        if not re.fullmatch(r"[A-Za-z0-9_.\-/]+", nome) or ".." in nome:
            return self._json(400, {"errore": "percorso non valido"})
        f = (WEB / nome).resolve()
        if not str(f).startswith(str(WEB.resolve())) or not f.is_file():
            return self._json(404, {"errore": "non trovato"})
        tipo = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        dati = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", tipo + ("; charset=utf-8" if tipo.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(dati)))
        self.end_headers()
        self.wfile.write(dati)

    # -- il cuore ---------------------------------------------------------

    def _fotogramma(self):
        """Un fotogramma entra, un elenco di oggetti con il loro stato esce.

        Ordine dei passi, che e' anche la garanzia anti-eco di §4:
          1. il modello legge i pixel — non sa nulla dell'inventario;
          2. il server confronta cio' che e' stato letto con il file;
          3. solo qui nasce il colore: verde = trovato nel registro.
        Invertire 1 e 2 farebbe leggere al modello cio' che gia' sappiamo.
        """
        dati = self._corpo()
        if not dati:
            return self._json(400, {"errore": "corpo mancante, illeggibile o troppo grande"})
        immagine = dati.get("immagine", "")
        mime = "image/jpeg"
        if immagine.startswith("data:"):
            testa, _, immagine = immagine.partition(",")
            mime = testa[5:].split(";")[0] or "image/jpeg"
        if not immagine:
            return self._json(400, {"errore": "campo 'immagine' vuoto"})

        # Impronte percettive calcolate dal browser sui ritagli dei riquadri
        # gia' visti in questa passata: `[{riquadro:[x,y,w,h], impronta:"hex"}]`.
        # Sono l'unica cosa che permette di riconoscere un oggetto il cui titolo
        # non e' leggibile: senza, ogni fotogramma lo ripresenterebbe come nuovo
        # e l'operatore verrebbe sommerso di richieste di conferma sullo stesso
        # dorso sfocato. Il calcolo sta nel browser perche' li' i pixel ci sono
        # gia' — e perche' cosi' il fotogramma non deve essere conservato.
        impronte = dati.get("impronte") or []
        if not isinstance(impronte, list):
            impronte = []

        s = self.stato
        s.fotogrammi += 1
        try:
            esito = vis.leggi(immagine, mime, cascata=s.cascata)
        except vis.VisioneNonDisponibile as e:
            s.errori += 1
            return self._json(503, {"errore": str(e), "visione": vis.stato()})
        except Exception as e:  # pragma: no cover - rete
            s.errori += 1
            return self._json(502, {"errore": vis.oscura_segreti(e)})
        s.letture_riuscite += 1

        risposta = []
        with s.lock:
            for i, o in enumerate(esito["oggetti"]):
                impronta = o.get("impronta") or impronta_vicina(o["riquadro"], impronte)
                stato_o, voce = s.inventario.riconosci(o["tipo"], o["titolo"], impronta)
                scritto = False
                if (stato_o == "NUOVO" and s.autoscrittura
                        and o["confidenza"] >= s.soglia and not esito["stub"]):
                    try:
                        s.inventario.registra(
                            o["tipo"], o["titolo"], impronta,
                            testo_letto=o["testo_letto"], confidenza=o["confidenza"])
                        scritto, stato_o = True, "CATALOGATO"
                    except ValueError:
                        stato_o = "INCERTO"
                elif stato_o in ("CATALOGATO", "RIVISTO") and voce is not None:
                    # ripassare aggiorna il contatore, non aggiunge una voce
                    voce["avvistamenti"] = voce.get("avvistamenti", 1)
                risposta.append({**o, "indice": i, "stato": stato_o,
                                 "scritto_ora": scritto,
                                 "avvistamenti": (voce or {}).get("avvistamenti", 0),
                                 "impronta_usata": bool(impronta)})
            totale = len(s.inventario.voci)

        self._json(200, {"oggetti": risposta, "provider": esito["provider"],
                         "stub": esito["stub"], "totale_inventario": totale})

    def _conferma(self):
        """L'umano corregge o conferma una lettura incerta. Sempre disponibile.

        E' la valvola che permette di tenere la soglia alta: cio' che il
        modello non e' sicuro di aver letto non entra da solo, entra se
        qualcuno lo conferma — e la voce porta `fonte: "umano"`, cosi' in
        seguito si potra' misurare quanto il modello ha letto da solo.
        """
        dati = self._corpo() or {}
        titolo = str(dati.get("titolo", "")).strip()
        tipo = str(dati.get("tipo", "altro")).strip() or "altro"
        if not titolo:
            return self._json(400, {"errore": "titolo mancante"})
        try:
            with self.stato.lock:
                voce = self.stato.inventario.registra(
                    tipo, titolo, dati.get("impronta"),
                    testo_letto=str(dati.get("testo_letto", "")),
                    confidenza=dati.get("confidenza"),
                    fonte="umano", note=str(dati.get("note", "")))
                totale = len(self.stato.inventario.voci)
        except ValueError as e:
            return self._json(400, {"errore": str(e)})
        return self._json(200, {"voce": voce, "totale_inventario": totale})


    def _voce(self):
        """Una domanda a voce. Legge, cerca, propone — non scrive mai.

        A una voce non si puo' chiedere chi sta parlando: in un alloggio in
        affitto la stanza e' piena di gente che non e' il proprietario, e
        «vendi il televisore a dieci euro» detto ad alta voce deve non fare
        assolutamente niente. Questa rotta non ha nessun percorso di scrittura.
        """
        dati = self._corpo() or {}
        frase = str(dati.get("frase", "")).strip()[:400]
        if not frase:
            return self._json(400, {"errore": "frase vuota"})
        from . import voce as vc
        with self.stato.lock:
            esito = vc.rispondi(self.stato.inventario, frase)
        return self._json(200, {
            "domanda": frase,
            "intento": esito["intento"],
            "risposta": esito["testo_risposta"],
            "oggetti": [{"tipo": o.get("tipo"), "titolo": o.get("titolo")}
                        for o in esito.get("oggetti", [])[:20]],
            "parte_privata": esito.get("parte_privata", vc.parte_privata_presente()),
            "scrive": vc.puo_scrivere(),
        })

    def _chat(self):
        """La conversazione che accompagna la passata con la telecamera.

        Qui il registro E' contesto, ed e' legittimo: la chat serve a
        interrogare l'inventario («quanti Kubrick ho?», «che cosa manca alla
        collana?»), non a produrlo. La regola che tiene separate le due cose:
        **da questa rotta non si scrive mai nell'inventario.** Cio' che il
        modello dice qui non diventa mai una voce; per scrivere serve una
        lettura di /api/fotogramma o una conferma esplicita su /api/conferma.
        Se la chat potesse scrivere, il sistema si detterebbe l'inventario da
        solo: sarebbe il loopback di CLAUDE.md §4, con un'altra faccia.
        """
        dati = self._corpo() or {}
        domanda = str(dati.get("messaggio", "")).strip()[:2000]
        if not domanda:
            return self._json(400, {"errore": "messaggio vuoto"})
        try:
            from sdq1.llm.router import Router
        except Exception as e:
            return self._json(503, {"errore": f"router sdq1 non disponibile: {e}"})
        with self.stato.lock:
            elenco = [f"- {v.get('tipo')}: {v.get('titolo')}"
                      for v in self.stato.inventario.voci[:400]]
            totale = len(self.stato.inventario.voci)
        contesto = ("\n".join(elenco) or "(il registro e' ancora vuoto)")
        prompt = (
            "Stai accompagnando una persona che sta inventariando casa propria "
            "con la telecamera. Rispondi in italiano, breve e concreto.\n"
            "Regole: non aggiungere oggetti che non sono nell'elenco; se ti "
            "chiedono qualcosa che non risulta dall'elenco, dillo apertamente.\n\n"
            f"INVENTARIO ATTUALE ({totale} oggetti):\n{contesto}\n\n"
            f"DOMANDA: {domanda}")
        try:
            r = Router()
            profilo = "no-api" if self.stato.cascata == ("stub",) else "default"
            # Router.generate ritorna (testo, nome_provider): verificato in
            # sdq1/llm/router.py:81. Il nome torna allo schermo, cosi' si vede
            # sempre chi ha risposto — stub compreso.
            testo, provider = r.generate(prompt, profile=profilo)
        except Exception as e:
            return self._json(502, {"errore": vis.oscura_segreti(e)})
        return self._json(200, {"risposta": str(testo), "provider": provider,
                                "stub": str(provider).startswith("stub"),
                                "totale_inventario": totale})


def avvia(host="127.0.0.1", porta=8777, percorso_inventario=inv.ARCHIVIO,
          cascata=vis.CASCATA, autoscrittura=True, soglia=0.75, pianta=None):
    Handler.stato = Stato(percorso_inventario, tuple(cascata), autoscrittura,
                          soglia, pianta)
    srv = ThreadingHTTPServer((host, porta), Handler)
    if host not in ("127.0.0.1", "localhost", "::1"):
        sys.stderr.write(
            "\n  AVVISO: in ascolto su %s, senza autenticazione.\n"
            "  Chi raggiunge questa porta vede il tuo inventario. Usa 127.0.0.1\n"
            "  a meno che tu non sappia esattamente cosa stai aprendo.\n\n" % host)
    print(f"  occhio in ascolto su  http://{host}:{porta}")
    print(f"  inventario:           {Handler.stato.inventario.percorso} "
          f"({len(Handler.stato.inventario.voci)} oggetti)")
    print(f"  cascata visione:      {' -> '.join(cascata)}")
    if tuple(cascata) == ("stub",):
        print("  MODO STUB: nessun modello guarda davvero. Gli oggetti sono finti.")
    print("  Ctrl-C per fermare.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  fermato.")
    finally:
        srv.server_close()
