"""RAFFA-001 — Analisi semantica: legge l'intento dell'input.

Classifica l'atto linguistico (domanda / comando / affermazione) ed estrae
le parole chiave che orientano DECOMP-005 e GEN-006. Nessuna dipendenza
esterna: tokenizzazione a regex e conteggi, come il resto di sdq1.
"""
import re
from collections import Counter

# L'apostrofo resta fuori dalla classe di caratteri: così l'elisione
# italiana si spezza da sola ("l'emergenza" -> "l", "emergenza") e la
# parola piena si conserva senza doverla trattare a parte.
TOKEN_RE = re.compile(r"[a-zàáèéìíòóùú]+")

LUNGHEZZA_MINIMA = 4
MAX_PAROLE_CHIAVE = 8

INTERROGATIVI = {
    "chi", "cosa", "come", "dove", "quando", "perche", "perché",
    "quale", "quali", "quanto", "quanta", "quanti", "quante",
}

VERBI_COMANDO = {
    "fai", "crea", "genera", "esegui", "avvia", "mostra", "scrivi",
    "analizza", "calcola", "costruisci", "apri", "chiudi", "elenca",
    "spiega", "aggiungi", "rimuovi", "cerca", "trova", "controlla",
    "verifica", "aggiorna", "ripristina", "salva",
}

# Solo parole da LUNGHEZZA_MINIMA in su: le più corte sono già escluse dal
# filtro sulla lunghezza, elencarle qui darebbe l'illusione di un controllo
# che non viene mai esercitato.
_STOPWORDS_BASE = {
    "adesso", "allora", "anche", "ancora", "avere", "aveva", "avete",
    "dagli", "dalla", "dalle", "dallo", "degli", "della", "delle", "dello",
    "dopo", "erano", "essere", "fare", "fatto", "loro", "molto", "negli",
    "nella", "nelle", "nello", "nostra", "nostro", "ogni", "però", "poco",
    "prima", "quindi", "quella", "quelle", "quelli", "quello", "questa",
    "queste", "questi", "questo", "sempre", "senza", "siamo", "sono",
    "stata", "stato", "sugli", "sulla", "sulle", "sullo", "tutta", "tutte",
    "tutti", "tutto", "vostra", "vostro",
}

# Gli interrogativi aprono la frase ma non dicono di cosa parla: servono a
# classificarla, non a descriverne il contenuto.
STOPWORDS = _STOPWORDS_BASE | INTERROGATIVI


def _tokenizza(testo):
    return TOKEN_RE.findall(testo.lower())


def _classifica(testo, tokens):
    """Restituisce (tipo, interrogativo_iniziale)."""
    primo = tokens[0] if tokens else ""

    if testo.endswith("?"):
        return "domanda", primo if primo in INTERROGATIVI else None
    if primo in INTERROGATIVI:
        return "domanda", primo
    # In italiano l'imperativo sta in testa: "crea il file" è un comando,
    # "il file che ho creato" no. La posizione pesa più della presenza, per
    # questo il primo token viene controllato prima del resto della frase.
    if primo in VERBI_COMANDO:
        return "comando", None
    if VERBI_COMANDO.intersection(tokens):
        return "comando", None
    return "affermazione", None


def _parole_chiave(tokens):
    """Ordina per frequenza, poi per lunghezza decrescente.

    Prima era `sorted(set(parole) - STOPWORDS)[:8]`: ordine alfabetico
    troncato a otto, cioè le parole chiave venivano scelte in base alla
    loro iniziale. Con più di otto candidate, tutto ciò che cominciava per
    lettera alta spariva per quanto fosse centrale nella frase.

    A parità di frequenza vince la parola più lunga (più specifica) e in
    ultima istanza l'ordine alfabetico, così il risultato resta
    deterministico.
    """
    frequenze = Counter(
        t for t in tokens if len(t) >= LUNGHEZZA_MINIMA and t not in STOPWORDS
    )
    ordinate = sorted(frequenze, key=lambda p: (-frequenze[p], -len(p), p))
    return ordinate[:MAX_PAROLE_CHIAVE]


def run(ctx):
    testo = ctx.input.strip()
    tokens = _tokenizza(testo)
    tipo, interrogativo = _classifica(testo, tokens)

    ctx.intent = {
        "tipo": tipo,
        "parole_chiave": _parole_chiave(tokens),
        "lunghezza": len(testo),
        "interrogativo": interrogativo,
        "token": len(tokens),
    }
    return ctx
