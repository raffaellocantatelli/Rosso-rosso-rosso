#!/usr/bin/env python3
"""occhio.visione — la passata di lettura su un fotogramma. Cieca al registro.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Questo modulo fa una cosa sola: prende i pixel di un fotogramma e restituisce
un elenco di oggetti visti, con il riquadro in cui si trovano. **Non riceve
mai l'inventario gia' raccolto**, e la firma della funzione lo rende
impossibile per costruzione: `leggi(immagine_b64)` non ha un parametro dove
infilarlo.

Non e' pignoleria. E' il difetto di CLAUDE.md §4 nella sua forma piu'
seducente: dare al modello la lista dei DVD gia' catalogati «per aiutarlo a
riconoscerli» produce un sistema che li rilegge tutti con altissima
confidenza — anche quando l'inquadratura e' vuota. Il conteggio salirebbe,
l'accuratezza apparente pure, e nessuna informazione nuova sarebbe entrata.

Politica sui provider, identica a quella di `sdq1` (§3): **senza un provider
di visione reale non si produce un risultato che sembra una lettura.**
Si fallisce, oppure si chiede esplicitamente lo stub, che marchia ogni sua
risposta con `"stub": true` e fa comparire una fascia a strisce nell'interfaccia.
"""

from __future__ import annotations

import base64
import json
import os
import re

import requests

TIMEOUT = float(os.environ.get("OCCHIO_TIMEOUT", "45"))

# Le chiavi non devono mai comparire in un messaggio d'errore: gli errori
# finiscono nei log e questo repository e' pubblico (§2.5). Riusa la funzione
# gia' scritta e collaudata in sdq1 invece di riscriverne una seconda (§6.2).
try:
    from sdq1.llm.router import oscura_segreti
except Exception:  # pragma: no cover - sdq1 assente
    def oscura_segreti(t):
        return str(t)


ISTRUZIONE = """Sei un lettore di scaffali. Guarda l'immagine e elenca SOLO gli oggetti
di cui riesci a leggere o riconoscere l'identita': dorsi e copertine di DVD, Blu-ray, VHS,
CD, vinili, libri, riviste, scatole con etichetta, apparecchi con marca e modello visibili.

Regole non negoziabili:
- Riporta solo cio' che vedi in QUESTA immagine. Non completare titoli a memoria:
  se leggi "MATR" scrivi testo_letto "MATR" e titolo "" e confidenza bassa.
- Se non leggi nulla di identificabile, restituisci una lista vuota. Una lista vuota
  e' una risposta corretta e utile.
- Non inventare autori, anni, registi o edizioni che non siano scritti sull'oggetto.
- riquadro e' [x, y, larghezza, altezza] in frazioni della larghezza/altezza
  dell'immagine, tra 0 e 1, attorno al SINGOLO oggetto.
- confidenza: 0.0-1.0, quanto sei sicuro di aver letto bene il titolo.

Rispondi SOLO con JSON valido, senza testo attorno:
{"oggetti": [{"tipo": "dvd", "titolo": "...", "testo_letto": "...",
              "riquadro": [0.1, 0.2, 0.05, 0.3], "confidenza": 0.9}]}"""


ISTRUZIONE_OGGETTI = """Sei un lettore di oggetti. Guarda l'immagine ed elenca gli oggetti
distinti che vedi in primo piano, ANCHE SE non hanno nessuna scritta sopra.

Questo e' l'inventario di una casa: vasi, piatti, sottopiatti, posacenere, scatole,
lampade, cuscini, asciugamani, soprammobili. Quasi nessuno ha un'etichetta, e non
importa: un oggetto si nomina per categoria, materiale, colore e forma.

Regole non negoziabili:
- Nomina solo cio' che vedi in QUESTA immagine. Non dedurre marca, prezzo, epoca
  o provenienza: se non e' scritto sull'oggetto, non lo sai.
- Un oggetto per voce. Un vaso col suo coperchio e' UN oggetto se il coperchio e'
  appoggiato sopra; sono DUE se il coperchio sta separato.
- Includi anche gli oggetti piatti o poco vistosi: un sottopiatto, una tovaglietta,
  un vassoio contano quanto un vaso.
- Se non distingui niente, restituisci una lista vuota. Una lista vuota e' una
  risposta corretta e utile.
- nome: come lo direbbe una persona, breve. Es. "Vaso di porcellana bianco e rosso".
- materiale e colore: solo se li vedi. Stringa vuota se incerto.
- riquadro e' [x, y, larghezza, altezza] in frazioni della larghezza/altezza
  dell'immagine, tra 0 e 1, attorno al SINGOLO oggetto.
- confidenza: 0.0-1.0, quanto sei sicuro che sia un oggetto distinto e ben nominato.
  NON e' la sicurezza di aver letto un testo: qui non c'e' testo da leggere.

Rispondi SOLO con JSON valido, senza testo attorno:

{"oggetti": [{"tipo": "vaso", "nome": "Vaso di porcellana bianco e rosso con coperchio",
              "materiale": "porcellana", "colore": "bianco e rosso",
              "riquadro": [0.1, 0.2, 0.05, 0.3], "confidenza": 0.8}]}
"""

# `media` legge i titoli, `oggetti` nomina le cose senza scritte. Sono due
# prodotti diversi e vanno tenuti separati: la confidenza significa cose
# diverse nei due modi, e H6 misura solo il primo.
MODI = {"media": ISTRUZIONE, "oggetti": ISTRUZIONE_OGGETTI}
MODO_PREDEFINITO = os.environ.get("OCCHIO_MODO", "media")


class VisioneNonDisponibile(RuntimeError):
    """Nessun provider di visione e' raggiungibile. Non e' un risultato vuoto."""


# --------------------------------------------------------------------------
# provider
# --------------------------------------------------------------------------

class ProviderVisione:
    nome = "base"

    def disponibile(self) -> bool:
        raise NotImplementedError

    def leggi(self, immagine_b64: str, mime: str = "image/jpeg",
              modo: str = "media") -> list[dict]:
        raise NotImplementedError


class AnthropicVisione(ProviderVisione):
    nome = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"
    MODELLO = "claude-sonnet-5"

    def disponibile(self):
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def leggi(self, immagine_b64, mime="image/jpeg", modo="media"):
        key = os.environ["ANTHROPIC_API_KEY"]
        r = requests.post(
            self.URL,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={
                "model": os.environ.get("OCCHIO_MODELLO_ANTHROPIC", self.MODELLO),
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64",
                                                 "media_type": mime,
                                                 "data": immagine_b64}},
                    {"type": "text", "text": MODI.get(modo, ISTRUZIONE)},
                ]}],
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        testo = "".join(b.get("text", "") for b in r.json().get("content", []))
        return estrai_oggetti(testo, modo)


class GeminiVisione(ProviderVisione):
    nome = "gemini"
    MODELLO = "gemini-3.6-flash"

    def disponibile(self):
        return bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))

    def leggi(self, immagine_b64, mime="image/jpeg", modo="media"):
        key = os.environ.get("GOOGLE_API_KEY") or os.environ["GEMINI_API_KEY"]
        modello = os.environ.get("OCCHIO_MODELLO_GEMINI", self.MODELLO)
        # Chiave in header, mai nella query string: il 26/08/2026 un 429 ha
        # stampato l'URL intero in stderr (vedi sdq1/llm/providers/gemini_provider.py).
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modello}:generateContent"
        r = requests.post(
            url,
            headers={"x-goog-api-key": key},
            json={"contents": [{"parts": [
                {"inline_data": {"mime_type": mime, "data": immagine_b64}},
                {"text": MODI.get(modo, ISTRUZIONE)},
            ]}]},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        d = r.json()
        testo = d["candidates"][0]["content"]["parts"][0]["text"]
        return estrai_oggetti(testo, modo)


class StubVisione(ProviderVisione):
    """Non guarda niente. Esiste per provare l'interfaccia senza chiavi.

    Restituisce sempre gli stessi tre oggetti fittizi. Chi lo usa lo sa,
    perche' e' raggiungibile solo con `--senza-visione` e ogni risposta che
    passa di qui porta `stub: true` fino allo schermo.
    """
    nome = "stub"

    def disponibile(self):
        return True

    def leggi(self, immagine_b64, mime="image/jpeg", modo="media"):
        return [normalizza(o, modo) for o in self._finti(modo)]

    def _finti(self, modo):
        if modo == "oggetti":
            # Oggetti senza scritte, come quelli veri: nessun testo_letto.
            return [
                {"tipo": "vaso", "nome": "ESEMPIO FINTO — Vaso di porcellana con coperchio",
                 "materiale": "porcellana", "colore": "bianco e rosso",
                 "riquadro": [0.30, 0.15, 0.22, 0.35], "confidenza": 0.0},
                {"tipo": "vaso", "nome": "ESEMPIO FINTO — Vaso bianco a rami",
                 "materiale": "ceramica", "colore": "bianco",
                 "riquadro": [0.28, 0.55, 0.30, 0.38], "confidenza": 0.0},
                {"tipo": "sottopiatto", "nome": "ESEMPIO FINTO — Sottopiatto in fibra intrecciata",
                 "materiale": "fibra vegetale", "colore": "naturale",
                 "riquadro": [0.62, 0.28, 0.20, 0.26], "confidenza": 0.0},
                # il quarto e' incerto apposta, come nel modo media: senza un
                # caso dubbio non si vede mai la parte in cui il sistema ammette
                # di non sapere.
                {"tipo": "altro", "nome": "", "materiale": "", "colore": "",
                 "riquadro": [0.70, 0.05, 0.18, 0.20], "confidenza": 0.0},
            ]
        return [
            {"tipo": "dvd", "titolo": "ESEMPIO FINTO — Il Padrino",
             "testo_letto": "IL PADRINO", "riquadro": [0.12, 0.18, 0.08, 0.55],
             "confidenza": 0.0},
            {"tipo": "dvd", "titolo": "ESEMPIO FINTO — Blade Runner",
             "testo_letto": "BLADE RUNNER", "riquadro": [0.24, 0.16, 0.07, 0.58],
             "confidenza": 0.0},
            {"tipo": "libro", "titolo": "ESEMPIO FINTO — Se questo e un uomo",
             "testo_letto": "SE QUESTO E UN UOMO", "riquadro": [0.42, 0.20, 0.09, 0.52],
             "confidenza": 0.0},
            # il quarto e' illeggibile apposta: senza un caso INCERTO non si
            # vedrebbe mai la parte dell'interfaccia in cui il sistema ammette
            # di non sapere e chiede, che e' quella che tiene alta la soglia.
            {"tipo": "dvd", "titolo": "", "testo_letto": "K?BR?CK  2O?",
             "riquadro": [0.33, 0.19, 0.07, 0.54], "confidenza": 0.0},
        ]


PROVIDER = {p.nome: p for p in (AnthropicVisione(), GeminiVisione(), StubVisione())}
CASCATA = ("anthropic", "gemini")

COME_ATTIVARE = {
    "anthropic": "ANTHROPIC_API_KEY in .env",
    "gemini": "GOOGLE_API_KEY (o GEMINI_API_KEY) in .env",
}


# --------------------------------------------------------------------------
# lettura del JSON prodotto dal modello
# --------------------------------------------------------------------------

def estrai_oggetti(testo: str, modo: str = "media") -> list[dict]:
    """Legge la risposta del modello senza fidarsene.

    Un modello di visione risponde spesso con il JSON dentro un blocco
    markdown, o con una frase davanti. Ogni campo viene ricostruito e
    limitato: un riquadro fuori da [0,1] verrebbe disegnato fuori schermo,
    una confidenza inventata a 1.5 falserebbe le soglie.
    """
    if not testo:
        return []
    grezzo = testo.strip()
    grezzo = re.sub(r"^```(?:json)?\s*|\s*```$", "", grezzo, flags=re.MULTILINE).strip()
    dati = None
    try:
        dati = json.loads(grezzo)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", grezzo, re.DOTALL)
        if m:
            try:
                dati = json.loads(m.group(0))
            except json.JSONDecodeError:
                return []
    if dati is None:
        return []
    grezzi = dati.get("oggetti", dati) if isinstance(dati, dict) else dati
    if not isinstance(grezzi, list):
        return []

    puliti = []
    for o in grezzi:
        if not isinstance(o, dict):
            continue
        puliti.append(normalizza(o, modo))
    return puliti


def normalizza(o: dict, modo: str = "media") -> dict:
    """Porta un record alla forma unica, da qualunque provider arrivi.

    Esiste perche' lo Stub non passa dal parser: il 08/09 il modo `oggetti`
    e' esploso con KeyError 'titolo' proprio li'. Un provider che emette un
    record parziale rompe tutto a valle — quindi la forma la decide una
    funzione sola.
    """
    if True:
        riq = o.get("riquadro") or o.get("box") or [0, 0, 0, 0]
        try:
            x, y, w, h = (float(v) for v in list(riq)[:4])
        except (TypeError, ValueError):
            x = y = w = h = 0.0
        x, y = min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0)
        w, h = min(max(w, 0.0), 1.0 - x), min(max(h, 0.0), 1.0 - y)
        try:
            conf = float(o.get("confidenza", o.get("confidence", 0.0)))
        except (TypeError, ValueError):
            conf = 0.0
        voce = {
            "tipo": str(o.get("tipo", "altro"))[:40],
            "titolo": str(o.get("titolo", ""))[:200].strip(),
            "testo_letto": str(o.get("testo_letto", ""))[:300].strip(),
            "riquadro": [x, y, w, h],
            "confidenza": min(max(conf, 0.0), 1.0),
        }
        if modo == "oggetti":
            # Un oggetto senza scritte non ha un testo letto, e dirlo vuoto e'
            # piu' onesto che riempirlo col nome: `testo_letto` significa
            # «questo c'era scritto sopra», e qui non c'era scritto niente.
            voce["nome"] = str(o.get("nome", o.get("titolo", "")))[:200].strip()
            voce["materiale"] = str(o.get("materiale", ""))[:60].strip()
            voce["colore"] = str(o.get("colore", ""))[:60].strip()
            voce["testo_letto"] = ""
            voce["letto_come"] = "oggetto"
            # `titolo` resta popolato col nome perche' l'inventario, la
            # deduplicazione e la console leggono quel campo: cambiarlo qui
            # spezzerebbe tutto a valle senza aggiungere niente.
            if not voce["titolo"]:
                voce["titolo"] = voce["nome"]
        else:
            voce["letto_come"] = "media"
        return voce


# --------------------------------------------------------------------------
# ingresso pubblico
# --------------------------------------------------------------------------

def scegli(cascata=CASCATA) -> ProviderVisione | None:
    for nome in cascata:
        p = PROVIDER.get(nome)
        if p and p.disponibile():
            return p
    return None


def leggi(immagine_b64: str, mime: str = "image/jpeg",
          cascata=CASCATA, modo: str | None = None) -> dict:
    """Legge un fotogramma. Nessun parametro per l'inventario: e' voluto.

    Solleva VisioneNonDisponibile se nessun provider risponde, invece di
    restituire una lista vuota: una lista vuota significa «ho guardato e non
    c'era niente», ed e' un'affermazione diversa da «non ho guardato».
    """
    modo = modo or MODO_PREDEFINITO
    if modo not in MODI:
        raise ValueError(f"modo sconosciuto: {modo!r}. Sono {sorted(MODI)}")
    errori = []
    for nome in cascata:
        p = PROVIDER.get(nome)
        if not p or not p.disponibile():
            continue
        try:
            return {"oggetti": p.leggi(immagine_b64, mime, modo),
                    "provider": p.nome,
                    "modo": modo,
                    "stub": p.nome == "stub"}
        except Exception as e:  # rete, quota, 5xx: si prova il prossimo
            errori.append(f"{nome}: {oscura_segreti(e)}")
    raise VisioneNonDisponibile(
        "nessun provider di visione ha risposto. "
        + ("Errori: " + " | ".join(errori) if errori else
           "Nessuna chiave configurata: " + "; ".join(f"{k} -> {v}" for k, v in COME_ATTIVARE.items()))
    )


def stato() -> dict:
    """Diagnostica per `--check`: chi c'e' e cosa manca. Nessuna chiave stampata."""
    return {
        "provider": {n: PROVIDER[n].disponibile() for n in CASCATA},
        "attivo": (scegli() or StubVisione()).nome if scegli() else None,
        "come_attivare": COME_ATTIVARE,
    }


def da_file(percorso) -> tuple[str, str]:
    """Carica un'immagine da disco per la prova a riga di comando."""
    from pathlib import Path
    p = Path(percorso)
    mime = {"png": "image/png", "webp": "image/webp"}.get(
        p.suffix.lower().lstrip("."), "image/jpeg")
    return base64.b64encode(p.read_bytes()).decode("ascii"), mime
