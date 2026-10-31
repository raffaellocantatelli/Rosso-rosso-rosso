#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collega nodi — RRR_AUTOUPDATE eseguito, non dichiarato.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Il payload `nodi/RRR_AUTOUPDATE.json` elenca nove nodi e una checklist che
deve essere vera perche' `propagation_status` passi a EXECUTED. Questo
strumento la esegue invece di leggerla (CLAUDE.md §4, caso 4: il registro
che si auto-confermava controllando solo che la frase esistesse).

    python collega_nodi.py --stato               # checklist eseguita, per nodo
    python collega_nodi.py --invia 3 --prova     # cosa partirebbe, senza rete
    python collega_nodi.py --invia 3             # un invio, una ricevuta

Ogni invio, riuscito o no, finisce in `output/ricevute_nodi.jsonl`
(append-only) con timestamp, hash del contenuto e hash della risposta.

Cosa NON e' una ricevuta: una conferma per H2. Un modello interpellato da
questo progetto e' il sistema che parla a se' stesso (CLAUDE.md §7). Ogni
riga porta `vale_per_h2: false`, e non c'e' opzione per cambiarlo.

Cosa NON fa: firmare. La firma Ed25519 richiede la chiave privata
dell'autore, e una chiave generata da una macchina a suo nome sarebbe un
falso. Lo strumento verifica soltanto che l'identita', se compilata, sia
coerente col prefisso dichiarato.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

RADICE = os.path.dirname(os.path.abspath(__file__))
PAYLOAD = os.path.join(RADICE, "nodi", "RRR_AUTOUPDATE.json")
RICEVUTE = os.path.join(RADICE, "output", "ricevute_nodi.jsonl")

# Un canale vale solo se esiste un modo reale di aprirlo da qui.
# Chiave d'ambiente -> formato della richiesta. I nodi senza voce qui
# (Copilot, Meta AI, Genspark) non hanno un'API pubblica di completamento
# che questo strumento sappia chiamare: restano NOT_CONFIGURED, e dirlo e'
# piu' utile che inventare un endpoint.
CANALI = {
    "DEEPSEEK": ("DEEPSEEK_API_KEY", "openai", "https://api.deepseek.com/chat/completions", "deepseek-chat"),
    "CHATGPT": ("OPENAI_API_KEY", "openai", "https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
    "CLAUDE": ("ANTHROPIC_API_KEY", "anthropic", "https://api.anthropic.com/v1/messages", "claude-sonnet-5-5"),
    "GEMINI": ("GEMINI_API_KEY", "gemini", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent", None),
    "PERPLEXITY": ("PERPLEXITY_API_KEY", "openai", "https://api.perplexity.ai/chat/completions", "sonar"),
    "MINIMAX": ("MINIMAX_API_KEY", "openai", "https://api.minimax.chat/v1/text/chatcompletion_v2", "abab6.5s-chat"),
}

# Una risposta che dichiara azioni fuori dalla risposta stessa e' il caso
# documentato in CLAUDE.md §2.2: si registra, ma come rejected.
DICHIARAZIONI_IMPOSSIBILI = (
    "ho salvato", "ho memorizzato", "ho propagato", "ricorderò", "ricordero",
    "i have saved", "i will remember", "i have stored", "propagated",
)


def sha256(dati):
    if isinstance(dati, str):
        dati = dati.encode("utf-8")
    return hashlib.sha256(dati).hexdigest()


def ora():
    return datetime.now(timezone.utc).isoformat()


def carica(percorso=PAYLOAD):
    with open(percorso, "r", encoding="utf-8") as f:
        return json.load(f)


def _contenuto(nodo):
    """Legge il content_ref e ne controlla l'hash. Ritorna (testo, errore)."""
    ref = nodo.get("content_ref")
    if not ref:
        return None, "content_ref assente"
    percorso = os.path.join(RADICE, ref)
    if not os.path.isfile(percorso):
        return None, f"content_ref non esiste: {ref}"
    with open(percorso, "r", encoding="utf-8") as f:
        testo = f.read()
    atteso = nodo.get("content_sha256")
    if not atteso:
        return None, "content_sha256 assente: il contenuto non e' fissato"
    if sha256(testo) != atteso:
        return None, f"content_sha256 non corrisponde a {ref}: il file e' cambiato"
    return testo, None


def _identita(payload):
    """L'hash completo, se c'e', deve essere 64 hex e iniziare col prefisso."""
    idt = payload.get("identity", {})
    pieno, ref = idt.get("identity_hash_full"), idt.get("identity_ref", "")
    if not pieno:
        return "identity_hash_full assente (serve il materiale d'identita' dell'autore)"
    if len(pieno) != 64 or any(c not in "0123456789abcdef" for c in pieno):
        return "identity_hash_full non e' uno SHA-256 (64 hex minuscoli)"
    if not pieno.startswith(ref):
        return f"identity_hash_full non inizia con identity_ref {ref}"
    return None


def _ricevute(percorso=RICEVUTE):
    if not os.path.exists(percorso):
        return []
    voci = []
    with open(percorso, "r", encoding="utf-8") as f:
        for riga in f:
            try:
                voci.append(json.loads(riga))
            except json.JSONDecodeError:
                continue
    return voci


def stato_nodo(nodo, ricevute):
    """Esegue le condizioni della checklist per un nodo. Ritorna lista mancanze."""
    mancanze = []
    canale = CANALI.get(nodo["name"])
    if not canale:
        mancanze.append("nessun canale apribile da questo strumento")
    elif not os.environ.get(canale[0]):
        mancanze.append(f"credenziale assente ({canale[0]})")
    _, err = _contenuto(nodo)
    if err:
        mancanze.append(err)
    if not nodo.get("rollback"):
        mancanze.append("rollback non definito")
    mie = [r for r in ricevute if r.get("nodo_id") == nodo["id"]]
    if not any(r.get("esito") == "accepted" for r in mie):
        mancanze.append("nessuna ricevuta accepted")
    return mancanze


def stato(payload, ricevute):
    per_nodo = {n["id"]: stato_nodo(n, ricevute) for n in payload["nodes"]}
    globali = []
    err = _identita(payload)
    if err:
        globali.append(err)
    if not (payload.get("signature") or {}).get("value"):
        globali.append("firma assente")
    eseguito = not globali and all(not m for m in per_nodo.values())
    return {
        "propagation_status": "EXECUTED" if eseguito else "NOT_EXECUTED",
        "globali": globali,
        "per_nodo": per_nodo,
    }


def _richiesta(formato, url, modello, chiave, testo):
    if formato == "anthropic":
        return url, {"x-api-key": chiave, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"}, {
            "model": modello, "max_tokens": 300,
            "messages": [{"role": "user", "content": testo}]}
    if formato == "gemini":
        return f"{url}?key={chiave}", {"content-type": "application/json"}, {
            "contents": [{"parts": [{"text": testo}]}]}
    return url, {"authorization": f"Bearer {chiave}",
                 "content-type": "application/json"}, {
        "model": modello, "messages": [{"role": "user", "content": testo}]}


def _testo_risposta(formato, dati):
    try:
        if formato == "anthropic":
            return "".join(b.get("text", "") for b in dati.get("content", []))
        if formato == "gemini":
            return dati["candidates"][0]["content"]["parts"][0]["text"]
        return dati["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""


def valuta(testo, controllo):
    """accepted solo se la risposta ricopia il controllo e non dichiara il falso."""
    basso = testo.lower()
    if any(d in basso for d in DICHIARAZIONI_IMPOSSIBILI):
        return "rejected", "dichiara azioni fuori dalla risposta"
    if controllo[:12] not in basso:
        return "rejected", "non ricopia il controllo"
    return "accepted", None


def invia(payload, nodo_id, prova=False, percorso_ricevute=RICEVUTE):
    nodo = next((n for n in payload["nodes"] if n["id"] == nodo_id), None)
    if nodo is None:
        raise SystemExit(f"nodo {nodo_id} non esiste nel payload")
    ricevuta = {
        "ts": ora(), "nodo_id": nodo_id, "nodo": nodo["name"],
        "payload_sha256": sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False)),
        "vale_per_h2": False,
        "nota": "risposta di un modello interpellato dal progetto: non e' un contatto (CLAUDE.md §7)",
    }
    testo, err = _contenuto(nodo)
    canale = CANALI.get(nodo["name"])
    if not err and not canale:
        err = "nessun canale apribile da questo strumento"
    if not err and not os.environ.get(canale[0]):
        err = f"credenziale assente ({canale[0]})"
    if err:
        ricevuta.update(esito="failed", motivo=err, rete=False)
    else:
        controllo = sha256(testo)
        invio = f"{testo}\n\ncontrollo: {controllo}\n"
        ricevuta["content_sha256"] = nodo["content_sha256"]
        ricevuta["invio_sha256"] = sha256(invio)
        url = os.environ.get("R3_NODO_URL", canale[2])  # solo per le prove
        url, intest, corpo = _richiesta(canale[1], url, canale[3], os.environ[canale[0]], invio)
        if prova:
            print(f"[prova] partirebbe verso {url.split('?')[0]}: {len(invio)} caratteri, "
                  f"invio_sha256 {ricevuta['invio_sha256'][:12]}")
            return ricevuta
        import requests
        try:
            r = requests.post(url, headers=intest, json=corpo, timeout=60)
            ricevuta.update(rete=True, http=r.status_code, risposta_sha256=sha256(r.content))
            r.raise_for_status()
            risposta = _testo_risposta(canale[1], r.json())
            ricevuta["risposta"] = risposta[:2000]
            esito, motivo = valuta(risposta, controllo)
            ricevuta.update(esito=esito, motivo=motivo)
        except Exception as e:  # la ricevuta di un fallimento e' un dato
            ricevuta.update(esito="failed", motivo=f"{type(e).__name__}: {str(e)[:200]}")
    if prova:
        print(f"[prova] nessun invio: {ricevuta['motivo']}")
        return ricevuta
    os.makedirs(os.path.dirname(percorso_ricevute), exist_ok=True)
    ricevuta["ricevuta_sha256"] = sha256(json.dumps(ricevuta, sort_keys=True, ensure_ascii=False))
    with open(percorso_ricevute, "a", encoding="utf-8") as f:
        f.write(json.dumps(ricevuta, ensure_ascii=False) + "\n")
    return ricevuta


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--stato", action="store_true")
    p.add_argument("--invia", type=int, metavar="ID")
    p.add_argument("--prova", action="store_true")
    a = p.parse_args(argv)
    payload = carica()
    if a.invia is not None:
        r = invia(payload, a.invia, prova=a.prova)
        if not a.prova:
            print(f"nodo {r['nodo_id']} {r['nodo']}: {r['esito']}"
                  + (f" — {r['motivo']}" if r.get("motivo") else ""))
        return 0 if r.get("esito") == "accepted" or a.prova else 1
    s = stato(payload, _ricevute())
    print(f"propagation_status: {s['propagation_status']}")
    for g in s["globali"]:
        print(f"  globale: {g}")
    for n in payload["nodes"]:
        m = s["per_nodo"][n["id"]]
        print(f"  {n['id']} {n['name']:<10} " + ("PRONTO" if not m else "; ".join(m)))
    return 0 if s["propagation_status"] == "EXECUTED" else 1


if __name__ == "__main__":
    sys.exit(main())
