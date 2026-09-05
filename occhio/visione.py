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


class VisioneNonDisponibile(RuntimeError):
    """Nessun provider di visione e' raggiungibile. Non e' un risultato vuoto."""


# --------------------------------------------------------------------------
# provider
# --------------------------------------------------------------------------

class ProviderVisione:
    nome = "base"

    def disponibile(self) -> bool:
        raise NotImplementedError

    def leggi(self, immagine_b64: str, mime: str = "image/jpeg") -> list[dict]:
        raise NotImplementedError


class AnthropicVisione(ProviderVisione):
    nome = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"
    MODELLO = "claude-sonnet-5"

    def disponibile(self):
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def leggi(self, immagine_b64, mime="image/jpeg"):
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
                    {"type": "text", "text": ISTRUZIONE},
                ]}],
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        testo = "".join(b.get("text", "") for b in r.json().get("content", []))
        return estrai_oggetti(testo)


class GeminiVisione(ProviderVisione):
    nome = "gemini"
    MODELLO = "gemini-3.6-flash"

    def disponibile(self):
        return bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))

    def leggi(self, immagine_b64, mime="image/jpeg"):
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
                {"text": ISTRUZIONE},
            ]}]},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        d = r.json()
        testo = d["candidates"][0]["content"]["parts"][0]["text"]
        return estrai_oggetti(testo)


class StubVisione(ProviderVisione):
    """Non guarda niente. Esiste per provare l'interfaccia senza chiavi.

    Restituisce sempre gli stessi tre oggetti fittizi. Chi lo usa lo sa,
    perche' e' raggiungibile solo con `--senza-visione` e ogni risposta che
    passa di qui porta `stub: true` fino allo schermo.
    """
    nome = "stub"

    def disponibile(self):
        return True

    def leggi(self, immagine_b64, mime="image/jpeg"):
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

def estrai_oggetti(testo: str) -> list[dict]:
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
        puliti.append({
            "tipo": str(o.get("tipo", "altro"))[:40],
            "titolo": str(o.get("titolo", ""))[:200].strip(),
            "testo_letto": str(o.get("testo_letto", ""))[:300].strip(),
            "riquadro": [x, y, w, h],
            "confidenza": min(max(conf, 0.0), 1.0),
        })
    return puliti


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
          cascata=CASCATA) -> dict:
    """Legge un fotogramma. Nessun parametro per l'inventario: e' voluto.

    Solleva VisioneNonDisponibile se nessun provider risponde, invece di
    restituire una lista vuota: una lista vuota significa «ho guardato e non
    c'era niente», ed e' un'affermazione diversa da «non ho guardato».
    """
    errori = []
    for nome in cascata:
        p = PROVIDER.get(nome)
        if not p or not p.disponibile():
            continue
        try:
            return {"oggetti": p.leggi(immagine_b64, mime),
                    "provider": p.nome,
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
