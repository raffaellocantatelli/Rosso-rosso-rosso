#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verdetto su Candidate A (OmniRoute 3.8.51 + modelVisibilityDenylist).

Origine protetta: Claudio Terzi [CT-LGAI-001].

Non misura niente da se': legge gli artefatti che `candidate_a.sh` ha scritto
eseguendo davvero il container. Se gli artefatti non ci sono, non inventa un
verdetto — esce 2 (UNKNOWN). E' la differenza fra un falsificatore e un
documento che dice di aver verificato.

I criteri sono dichiarati PRIMA di guardare i dati (P6). ADOPT A richiede
tutti e sei:

  A1  catalogo /v1/models raggiungibile prima e dopo (HTTP 200 entrambe)
  A2  PATCH accettato (2xx) e la RILETTURA di /api/settings riporta esattamente
      le voci inviate — non ci si fida della risposta del PATCH
  A3  ogni voce della denylist corrispondeva ad almeno un id nel catalogo
      PRIMA. Una voce che non corrisponde a niente non da' errore e non fa
      niente: e' il modo silenzioso in cui questa modifica finge di funzionare
  A4  nel catalogo DOPO, zero id corrispondenti alla denylist
  A5  nessun id non-negato e' sparito fra prima e dopo (nessun danno collaterale)
  A6  la completion con model="auto" e' riuscita e il modello risolto non e'
      fra quelli negati

Fuori dal verdetto, ma stampato sempre, perche' cambia cosa Candidate A compra
davvero:

  E1  un modello negato, CHIESTO PER NOME, risponde ancora. Upstream lo
      dichiara (docs/routing/MODEL_EXPOSURE_LIST.md, "What is NOT filtered"):
      la denylist toglie dalla vetrina e dal pool di `auto/*`, non blocca la
      chiamata esplicita. Se lo scopo era impedire l'uso, Candidate A non lo
      fa — ne' A ne' B, perche' e' il disegno upstream, non un difetto.

Uso:  python3 falsificatore_delta.py <cartella_delta>
Esce: 0 = ADOPT A · 1 = REJECT A · 2 = UNKNOWN (artefatti insufficienti, o un
      criterio non misurabile in questo ambiente — che non e' una bocciatura
      gentile: e' l'assenza di misura)
"""
import json
import os
import re
import sys

ESCAPE = re.compile(r"[.+^${}()|\[\]\\]")


def glob_to_regex(pattern):
    """Stessa semantica di src/shared/utils/globPattern.ts::globToRegex:
    escape degli specials, poi * -> .* e ? -> . , ancorato, case-insensitive.
    `*` attraversa anche le barre, esattamente come la'."""
    escaped = ESCAPE.sub(lambda m: "\\" + m.group(0), pattern)
    escaped = escaped.replace("*", ".*").replace("?", ".")
    return re.compile("^" + escaped + "$", re.IGNORECASE)


def voce_corrisponde(voce, candidati):
    """src/shared/utils/modelExposureList.ts::listMatchesAny, una voce sola.
    Match esatto (case-sensitive) prima; glob solo se la voce ha * o ?."""
    if voce in candidati:
        return True
    if not re.search(r"[*?]", voce):
        return False
    try:
        rx = glob_to_regex(voce)
    except re.error:
        return False
    return any(rx.search(c) for c in candidati)


def candidati_di(modello):
    """isModelExposureAllowed costruisce [modelId, provider/modelId]. Nel JSON
    di /v1/models l'id e' gia' quello del catalogo; il provider, quando c'e',
    sta in owned_by. INFERITO: che owned_by sia il `provider` passato al
    predicato e' deduzione dalla forma del catalogo, non letto nel codice
    della route — per questo si tiene anche l'id nudo."""
    ident = modello.get("id")
    if not isinstance(ident, str) or not ident:
        return []
    fuori = [ident]
    prov = modello.get("owned_by")
    if isinstance(prov, str) and prov:
        fuori.append(prov + "/" + ident)
        if "/" in ident:
            fuori.append(ident.split("/", 1)[1])
    return fuori


TABELLA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "provider_3851.json")


def _tabella():
    """alias -> id canonico e provider ritirati, estratti dal sorgente 3.8.51."""
    try:
        with open(TABELLA, encoding="utf-8") as f:
            dati = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}, set()
    return (dati.get("alias_verso_canonico") or {},
            {p.lower() for p in (dati.get("provider_ritirati") or [])})


def diagnosi_voce_a_vuoto(voce):
    """Perche' una voce non colpisce niente. Le due cause note sono nel codice
    3.8.51, non dedotte: il provider e' ritirato, oppure la voce e' scritta con
    l'alias mentre catalog.ts passa al predicato l'id canonico
    (`isModelExposureAllowed(aliasToProviderId[providerKey] || providerKey, ...)`,
    src/app/api/v1/models/catalog.ts)."""
    alias, ritirati = _tabella()
    prefisso = voce.split("/", 1)[0].strip().lower()
    if prefisso in ritirati:
        return "provider ritirato in 3.8.51 (410 PROVIDER_RETIRED): non c'e' niente da nascondere"
    if prefisso in alias:
        return ("scritta con l'alias; il predicato riceve l'id canonico '%s' — usa '%s/%s'"
                % (alias[prefisso], alias[prefisso], voce.split("/", 1)[1] if "/" in voce else ""))
    return "nessun id del catalogo le corrisponde"


def leggi_json(percorso):
    if not os.path.exists(percorso):
        return None
    try:
        with open(percorso, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def leggi_testo(percorso):
    if not os.path.exists(percorso):
        return ""
    with open(percorso, encoding="utf-8") as f:
        return f.read().strip()


def modelli_di(catalogo):
    if isinstance(catalogo, dict):
        dati = catalogo.get("data")
        if isinstance(dati, list):
            return [m for m in dati if isinstance(m, dict)]
    if isinstance(catalogo, list):
        return [m for m in catalogo if isinstance(m, dict)]
    return []


def negati(modelli, denylist):
    """Gli id del catalogo che almeno una voce della denylist colpisce."""
    colpiti = {}
    for modello in modelli:
        cands = candidati_di(modello)
        if not cands:
            continue
        for voce in denylist:
            if voce_corrisponde(voce, cands):
                colpiti.setdefault(voce, []).append(modello["id"])
    return colpiti


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    d = argv[1]
    if not os.path.isdir(d):
        print("UNKNOWN — la cartella %s non esiste. Esegui prima candidate_a.sh." % d)
        return 2

    denylist = [r.strip() for r in leggi_testo(os.path.join(d, "denylist.txt")).splitlines() if r.strip()]
    prima = leggi_json(os.path.join(d, "models_prima.json"))
    dopo = leggi_json(os.path.join(d, "models_dopo.json"))
    impostazioni = leggi_json(os.path.join(d, "settings_dopo.json"))
    auto_meta = leggi_json(os.path.join(d, "auto.meta.json"))
    auto_resp = leggi_json(os.path.join(d, "auto_risposta.json"))
    expl_meta = leggi_json(os.path.join(d, "explicit.meta.json"))
    auto_prima_meta = leggi_json(os.path.join(d, "auto_prima.meta.json"))

    if not denylist:
        print("UNKNOWN — nessuna denylist registrata in %s/denylist.txt." % d)
        return 2
    if prima is None or dopo is None:
        print("UNKNOWN — manca models_prima.json o models_dopo.json: "
              "l'esecuzione non e' arrivata in fondo. Guarda %s/container.log." % d)
        return 2

    esiti = []

    def stato(ok):
        return "PASS" if ok else "FAIL"

    # A1
    s_prima = leggi_testo(os.path.join(d, "models_prima.status"))
    s_dopo = leggi_testo(os.path.join(d, "models_dopo.status"))
    esiti.append(("A1 catalogo raggiungibile prima e dopo",
                  stato(s_prima == "200" and s_dopo == "200"),
                  "HTTP prima=%s dopo=%s" % (s_prima or "?", s_dopo or "?")))

    # A2
    s_patch = leggi_testo(os.path.join(d, "patch.status"))
    patch_ok = s_patch.isdigit() and 200 <= int(s_patch) < 300
    riletta = []
    if isinstance(impostazioni, dict):
        v = impostazioni.get("modelVisibilityDenylist")
        if isinstance(v, list):
            riletta = [x for x in v if isinstance(x, str)]
        if not riletta:
            annidato = impostazioni.get("settings")
            if isinstance(annidato, dict) and isinstance(
                    annidato.get("modelVisibilityDenylist"), list):
                riletta = [x for x in annidato["modelVisibilityDenylist"] if isinstance(x, str)]
    persiste = sorted(riletta) == sorted(denylist)
    esiti.append(("A2 PATCH accettato e denylist riletta dallo stato",
                  stato(patch_ok and persiste),
                  "HTTP %s; riletta %d/%d voci" % (s_patch or "?", len(riletta), len(denylist))))

    # A3
    m_prima = modelli_di(prima)
    colpiti_prima = negati(m_prima, denylist)
    orfane = [v for v in denylist if v not in colpiti_prima]
    esiti.append(("A3 ogni voce colpisce almeno un id del catalogo",
                  stato(not orfane),
                  "catalogo prima: %d modelli; voci a vuoto: %d" % (len(m_prima), len(orfane))))

    # A4
    m_dopo = modelli_di(dopo)
    colpiti_dopo = negati(m_dopo, denylist)
    rimasti = sorted({i for ids in colpiti_dopo.values() for i in ids})
    esiti.append(("A4 nel catalogo dopo non resta nessun id negato",
                  stato(not rimasti),
                  "rimasti: %s" % (", ".join(rimasti[:10]) if rimasti else "nessuno")))

    # A5
    ids_prima = {m["id"] for m in m_prima if isinstance(m.get("id"), str)}
    ids_dopo = {m["id"] for m in m_dopo if isinstance(m.get("id"), str)}
    attesi_via = {i for ids in colpiti_prima.values() for i in ids}
    collaterali = sorted((ids_prima - ids_dopo) - attesi_via)
    esiti.append(("A5 nessun id non-negato sparito",
                  stato(not collaterali),
                  "spariti senza motivo: %s"
                  % (", ".join(collaterali[:10]) if collaterali else "nessuno")))

    # A6 — con il controllo PRIMA del PATCH. `auto` che non risponde ne' prima
    # ne' dopo non dice niente sulla denylist: dice che qui non c'e' un provider.
    # UNKNOWN non e' una bocciatura gentile, e' l'assenza di misura (CLAUDE.md §1).
    http_auto = (auto_meta or {}).get("http")
    http_auto_prima = (auto_prima_meta or {}).get("http")
    auto_ok = isinstance(http_auto, int) and 200 <= http_auto < 300
    auto_ok_prima = isinstance(http_auto_prima, int) and 200 <= http_auto_prima < 300
    modello_scelto = ""
    if isinstance(auto_resp, dict) and isinstance(auto_resp.get("model"), str):
        modello_scelto = auto_resp["model"]
    scelto_negato = bool(modello_scelto) and bool(negati([{"id": modello_scelto}], denylist))
    if auto_ok:
        esiti.append(("A6 auto risponde e non sceglie un modello negato",
                      stato(not scelto_negato),
                      "HTTP %s; modello risolto: %s"
                      % (http_auto, modello_scelto or "non dichiarato")))
    elif auto_ok_prima:
        esiti.append(("A6 auto risponde e non sceglie un modello negato", "FAIL",
                      "funzionava prima del PATCH (HTTP %s) e dopo no (HTTP %s): "
                      "la denylist ha rotto il routing"
                      % (http_auto_prima, http_auto if http_auto is not None else "?")))
    else:
        esiti.append(("A6 auto risponde e non sceglie un modello negato", "UNKNOWN",
                      "auto non rispondeva gia' prima del PATCH (HTTP %s -> %s): "
                      "nessun provider configurato, non misurabile qui"
                      % (http_auto_prima if http_auto_prima is not None else "?",
                         http_auto if http_auto is not None else "?")))

    larghezza = max(len(n) for n, _, _ in esiti)
    print("DELTA Candidate A — %s" % os.path.abspath(d))
    print("immagine: %s" % (leggi_testo(os.path.join(d, "immagine.txt")) or "non registrata"))
    rev = leggi_testo(os.path.join(d, "sorgente_rev.txt"))
    if rev:
        print("sorgente: %s" % rev)
    print("-" * (larghezza + 14))
    for nome, st, dettaglio in esiti:
        print("%-*s  %-7s %s" % (larghezza, nome, st, dettaglio))
    print("-" * (larghezza + 14))

    if orfane:
        print("\nVoci che non colpiscono niente — passano il PATCH e non fanno nulla:")
        for voce in orfane:
            print("  %-45s %s" % (voce, diagnosi_voce_a_vuoto(voce)))

    http_expl = (expl_meta or {}).get("http")
    if isinstance(http_expl, int) and 200 <= http_expl < 300:
        print("\nE1  il modello negato '%s' chiamato per nome risponde ancora (HTTP %s)."
              % ((expl_meta or {}).get("modello", "?"), http_expl))
        print("    Atteso: upstream filtra la vetrina e il pool di auto/*, non il dispatch")
        print("    esplicito. Se lo scopo era impedire l'uso, questa modifica non lo fa.")
    elif http_expl is not None:
        print("\nE1  il modello negato chiamato per nome NON ha risposto (HTTP %s)." % http_expl)
        print("    Diverso da quanto dichiara upstream: verifica se e' la denylist o")
        print("    un provider assente prima di dedurne qualcosa.")

    bocciati = [n.split()[0] for n, st, _ in esiti if st == "FAIL"]
    non_misurati = [n.split()[0] for n, st, _ in esiti if st == "UNKNOWN"]
    if bocciati:
        print("\nVERDETTO: REJECT A — %s" % ", ".join(bocciati))
        return 1
    if non_misurati:
        print("\nVERDETTO: UNKNOWN — %s non misurabili qui. Il resto passa."
              % ", ".join(non_misurati))
        return 2
    print("\nVERDETTO: ADOPT A")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
