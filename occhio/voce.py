#!/usr/bin/env python3
"""occhio.voce — parlare alla casa, e la cucitura con la parte privata.

Origine protetta: Claudio Terzi [CT-LGAI-001].
Idea della voce e del suggerimento creativo: Claudio Terzi, 3 settembre 2026.

Due cose in un modulo solo, perche' sono la stessa cosa vista da due lati.

**1. La voce.** «Che vini ho in cucina», «dov'e' il phon», «cosa posso
cucinare». Il riconoscimento e la sintesi stanno nel browser e non costano
niente; qui sta cio' che serve per rispondere.

**La regola che non si tocca: la voce NON SCRIVE MAI nel registro.** Legge,
cerca, propone. Non cataloga, non vende, non consegna. Il motivo non e'
prudenza generica: e' che a una voce non si puo' chiedere chi sta parlando.
In un alloggio in affitto la stanza e' piena di gente che non e' il
proprietario, e «vendi il televisore a dieci euro» detto ad alta voce da un
ospite deve non fare assolutamente niente. Scrivere richiede sempre la strada
esplicita — un comando, una conferma, una controfirma. C'e' un test.

**2. La cucitura.** Cio' che il sistema *sa fare* sta qui, in pubblico, ed e'
generale. Cio' che lo rende *bravo* — le regole di trattativa tarate, i
prezzi, la creativita' del suggerimento — puo' stare in `occhio/privato/`,
che non e' versionato. Se c'e', si innesta. Se non c'e', tutto continua a
funzionare con una risposta onesta e generica.

Non sono due copie dello stesso programma (§6 regola 2): e' un programma solo
con un punto d'innesto dichiarato. E la parte pubblica non finge mai di avere
la parte privata: quando manca, lo dice.

Una nota sincera sul segreto, perche' e' meglio saperla adesso: **cio' che
vale davvero non e' il codice, sono i dati e la taratura.** Le istruzioni date
a un modello si intuiscono dopo dieci minuti d'uso del prodotto; i prezzi che
funzionano davvero e le abitudini misurate su cento soggiorni no.
"""

from __future__ import annotations

import re
import unicodedata

from .inventario import _etichetta, normalizza

# --------------------------------------------------------------------------
# il punto d'innesto
# --------------------------------------------------------------------------

def _privato():
    """Il modulo privato, se c'e'. Nessun errore se non c'e'."""
    try:
        from .privato import completa  # type: ignore
        return completa
    except Exception:
        return None


def parte_privata_presente() -> bool:
    return _privato() is not None


# --------------------------------------------------------------------------
# capire la domanda
# --------------------------------------------------------------------------

ELENCA, DOVE, CUCINA, VENDITA, QUANTI, IGNOTO = (
    "elenca", "dove", "cucina", "vendita", "quanti", "ignoto")

#: Famiglie di parole -> tipo dell'inventario. Deliberatamente esplicite:
#: indovinare il tipo con un modello costerebbe una chiamata per ogni frase
#: e sbaglierebbe di piu' di questa tabella.
FAMIGLIE = {
    "vinile": ("vinile", "vinili", "dischi", "disco", "lp", "trentatre"),
    "dvd": ("dvd", "film", "pellicola", "pellicole", "blu-ray", "bluray"),
    "libro": ("libro", "libri", "romanzo", "romanzi", "lettura"),
    "vino": ("vino", "vini", "bottiglia", "bottiglie", "rosso", "bianco",
             "barolo", "chianti", "prosecco"),
    "cibo": ("cibo", "mangiare", "dispensa", "pasta", "riso", "conserve"),
    "elettronica": ("elettronica", "apparecchi", "elettrodomestici", "phon",
                    "televisore", "tv", "macchina del caffe"),
}

#: «cucina» da sola NON e' qui: e' anche il nome di una stanza, e «che vini
#: ho in cucina» finiva interpretato come una richiesta di ricette. Trovato
#: eseguendo. Restano i verbi, che una stanza non e'.
VERBI_CUCINA = ("cucinare", "cucino", "cuocere", "preparare", "preparo",
                "mangiare", "mangio", "ricetta", "ricette", "cena", "pranzo",
                "abbinare", "abbino", "abbinamento")
VERBI_DOVE = ("dov", "trovo", "sta", "stanno", "cerco", "cercare")
VERBI_VENDITA = ("vendita", "vendere", "comprare", "compro", "prezzo",
                 "quanto costa", "vetrina", "portavia")
VERBI_QUANTI = ("quanti", "quante", "quanto", "numero", "totale")


def _piatto(frase: str) -> str:
    t = unicodedata.normalize("NFKD", str(frase).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", t)


def interpreta(frase: str, luoghi_noti=()) -> dict:
    """Che cosa sta chiedendo, e con che filtri. Nessun modello: e' una
    tabella, e una tabella si puo' rileggere quando sbaglia."""
    t = _piatto(frase)
    parole = set(t.split())

    tipo = None
    for nome, sinonimi in FAMIGLIE.items():
        if parole & set(sinonimi) or any(s in t for s in sinonimi if " " in s):
            tipo = nome
            break

    luogo = None
    for l in luoghi_noti:
        primo = _piatto(l.split(" › ")[0])
        if primo and primo in t:
            luogo = l.split(" › ")[0]
            break

    if any(v in t for v in VERBI_CUCINA):
        intento = CUCINA
    elif any(t.startswith(v) or f" {v}" in t for v in VERBI_DOVE):
        intento = DOVE
    elif any(v in t for v in VERBI_VENDITA):
        intento = VENDITA
    elif any(v in parole for v in VERBI_QUANTI):
        intento = QUANTI
    elif tipo or luogo:
        intento = ELENCA
    else:
        intento = IGNOTO

    return {"intento": intento, "tipo": tipo, "luogo": luogo,
            "testo": str(frase).strip()}


# --------------------------------------------------------------------------
# rispondere
# --------------------------------------------------------------------------

def _filtra(registro, tipo=None, luogo=None) -> list[dict]:
    fuori = []
    for v in registro.voci:
        if tipo and normalizza(v.get("tipo", "")) != tipo:
            # il vino sta spesso sotto «altro»: si guarda anche il titolo
            if not (tipo == "vino" and "vino" not in v.get("tipo", "")
                    and any(s in _piatto(v.get("titolo", ""))
                            for s in FAMIGLIE["vino"])):
                continue
        if luogo:
            etichette = [_etichetta(l) for l in (v.get("luoghi") or [None])]
            if not any(_piatto(e).startswith(_piatto(luogo)) for e in etichette):
                continue
        fuori.append(v)
    return fuori


def _somiglianza(titolo: str, frase: str) -> float:
    """Quanta parte del titolo compare nella frase.

    Serve perche' «dov'e' il phon» deve trovare UN oggetto, non tutta
    l'elettronica della casa. Confrontare la famiglia bastava per elencare,
    non per cercare.
    """
    parole = [w for w in _piatto(titolo).split() if len(w) > 2]
    if not parole:
        return 0.0
    t = f" {_piatto(frase)} "
    return sum(1 for w in parole if f" {w} " in t) / len(parole)


#: Una parola su tre di un titolo di tre parole e' gia' un riscontro:
#: «phon» basta per «Phon Dyson Supersonic». A 0,34 non bastava — un terzo
#: e' 0,333, e la soglia tagliava proprio il caso che doveva prendere.
SOGLIA_TITOLO = 0.3


def _cerca_titolo(registro, frase, soglia=SOGLIA_TITOLO) -> list[dict]:
    punteggi = [(v, _somiglianza(v.get("titolo", ""), frase)) for v in registro.voci]
    migliori = [(v, p) for v, p in punteggi if p >= soglia]
    if not migliori:
        return []
    massimo = max(p for _, p in migliori)
    return [v for v, p in migliori if p >= massimo - 1e-9]


#: Parole che seguono «in» senza essere un luogo.
_NON_LUOGHI = {"casa", "vendita", "totale", "giro", "tutto", "generale", "piu"}


def _luogo_chiesto(frase: str) -> str | None:
    """La stanza nominata in una domanda, anche se non esiste.

    Serve a rispondere «non conosco nessun luogo che si chiami cantina»
    invece di «non ho capito»: la prima e' precisa, la seconda fa ripetere
    la domanda a vuoto.
    """
    m = re.search(r"\b(?:in|nel|nella|dentro)\s+(?:il|lo|la|l )?\s*([a-z]{3,})",
                  _piatto(frase))
    if not m:
        return None
    parola = m.group(1)
    return None if parola in _NON_LUOGHI else parola


def _elenco(oggetti, massimo=12) -> str:
    titoli = [o.get("titolo", "") for o in oggetti[:massimo]]
    coda = f" e altri {len(oggetti) - massimo}" if len(oggetti) > massimo else ""
    return ", ".join(titoli) + coda


def rispondi(registro, frase: str, portavia=None, regole=None) -> dict:
    """La risposta. Deterministica dove puo' esserlo.

    Cio' che si puo' contare si conta; cio' che richiede fantasia — cosa
    cucinare, quale vino abbinare — passa alla parte privata se c'e', e se non
    c'e' si dice, invece di improvvisare una ricetta con quello che capita.
    """
    luoghi = list(registro.per_luogo())
    d = interpreta(frase, luoghi)
    oggetti = _filtra(registro, d["tipo"], d["luogo"])
    dove = f" in {d['luogo']}" if d["luogo"] else ""

    if d["intento"] == QUANTI:
        return {**d, "oggetti": oggetti,
                "testo_risposta": f"{len(oggetti)}{dove}." if oggetti
                else f"Non risulta niente{dove}."}

    if d["intento"] == DOVE:
        # cercare e' diverso da elencare: prima il titolo, poi la famiglia.
        per_titolo = _cerca_titolo(registro, frase)
        oggetti = per_titolo or oggetti
        if not oggetti:
            return {**d, "oggetti": [], "testo_risposta":
                    "Non lo trovo nel registro. Se c'e', non e' ancora stato letto."}
        posti = []
        for o in oggetti[:5]:
            for l in (o.get("luoghi") or [None]):
                posti.append(f"{o.get('titolo','')}: {_etichetta(l)}")
        return {**d, "oggetti": oggetti, "testo_risposta": "; ".join(posti)}

    if d["intento"] == VENDITA:
        if not regole:
            return {**d, "oggetti": [], "testo_risposta":
                    "Non ci sono prezzi dichiarati: niente e' in vendita."}
        in_vendita = [(v, regole.esposto(v["chiave"])) for v in (oggetti or registro.voci)
                      if regole.vendibile(v["chiave"], v.get("titolo", ""))[0]]
        if not in_vendita:
            return {**d, "oggetti": [], "testo_risposta": f"Niente in vendita{dove}."}
        pezzi = [f"{v.get('titolo','')} a {p:.2f} {regole.valuta}" for v, p in in_vendita[:8]]
        return {**d, "oggetti": [v for v, _ in in_vendita],
                "testo_risposta": "In vendita: " + "; ".join(pezzi) + "."}

    if d["intento"] == CUCINA:
        dispensa = _filtra(registro, "cibo") + _filtra(registro, "vino")
        completa = _privato()
        if completa is None:
            return {**d, "oggetti": dispensa, "parte_privata": False,
                    "testo_risposta":
                    ("So cosa c'e' in dispensa: " + (_elenco(dispensa) or "niente")
                     + ". Il suggerimento su cosa cucinare lo fa la parte privata, "
                       "che qui non e' installata — quindi non me lo invento.")}
        return {**d, "oggetti": dispensa, "parte_privata": True,
                "testo_risposta": completa.suggerisci(dispensa, d)}

    if d["intento"] == IGNOTO:
        # Senza tipo ne' luogo, `_filtra` non filtra niente e la risposta
        # sarebbe l'inventario intero: a «che trattori ho in garage» il
        # sistema elencava tutta la casa. Non aver capito e' una risposta,
        # e va data — trovato eseguendo.
        chiesto = _luogo_chiesto(frase)
        if chiesto:
            noti = ", ".join(sorted({l.split(" › ")[0] for l in luoghi})) or "nessuno"
            return {**d, "oggetti": [], "testo_risposta":
                    f"Non conosco nessun luogo che si chiami «{chiesto}». "
                    f"Quelli che conosco: {noti}."}
        return {**d, "oggetti": [], "testo_risposta":
                "Non ho capito la domanda. So rispondere a: cosa c'e' in una "
                "stanza, dove sta un oggetto, quanti ne hai, cosa e' in "
                "vendita, e cosa puoi cucinare."}
    if not oggetti:
        return {**d, "oggetti": [], "testo_risposta":
                f"Non risulta niente{dove}. Prova: «che vini ho in cucina», "
                "«dov'e' il phon», «cosa posso cucinare»."}
    return {**d, "oggetti": oggetti,
            "testo_risposta": f"{len(oggetti)}{dove}: {_elenco(oggetti)}."}


def puo_scrivere() -> bool:
    """Sempre falso, e sta qui per essere citato da un test.

    A una voce non si puo' chiedere chi sta parlando. In un alloggio in
    affitto la stanza e' piena di gente che non e' il proprietario, e «vendi
    il televisore a dieci euro» detto ad alta voce deve non fare niente.
    """
    return False
