#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verdetto su Candidate A (OmniRoute 3.8.51 + modelVisibilityDenylist).

Origine protetta: Claudio Terzi [CT-LGAI-001].

Non misura niente da se': legge gli artefatti che `candidate_a.sh` ha scritto
eseguendo davvero il container. Se non ci sono, non inventa un verdetto — esce
2 (UNKNOWN). E' la differenza fra un falsificatore e un documento che dichiara
di aver verificato.

**Perche' non confronta le stringhe.** Una prima versione di questo file
rifaceva a mano il match di `isModelExposureAllowed` sugli id stampati da
/v1/models. E' sbagliato, e la misura lo ha mostrato: il catalogo espone
`oc/big-pickle` con `owned_by: opencode`, `felo/felo-chat` con
`owned_by: felo-web`, `no-think/dva/claude-opus-5-max` con
`owned_by: devin-cli-agentic` — mentre il predicato upstream lavora sull'id
INTERNO del modello, che non e' quello stampato. Dedurre la corrispondenza dal
nome vuol dire indovinare. Qui si misura: si applica una voce per volta e si
guarda che cosa sparisce dal catalogo. Cio' che nessuna misura copre resta
UNKNOWN, non diventa un PASS.

I criteri sono dichiarati PRIMA di guardare i dati (P6). ADOPT A richiede
tutti e sei:

  A1  catalogo /v1/models raggiungibile prima e dopo (HTTP 200 entrambe)
  A2  la denylist completa e' accettata e la RILETTURA di /api/settings la
      riporta — non ci si fida del codice di risposta del PATCH: su 3.8.50 il
      PATCH risponde 200 e butta via la chiave in silenzio (misurato)
  A3  ogni voce, applicata DA SOLA, fa sparire almeno un id dal catalogo.
      Una voce che non fa sparire niente non da' errore e non fa niente
  A4  con la denylist intera spariscono tutti gli id che le voci facevano
      sparire da sole
  A5  e non sparisce nient'altro (nessun danno collaterale)
  A6  la completion con model="auto" risponde e non sceglie un modello che la
      denylist ha tolto

Fuori dal verdetto, ma stampato sempre, perche' cambia cosa Candidate A compra:

  E1  un modello negato, CHIESTO PER NOME, risponde ancora. Upstream lo
      dichiara (docs/routing/MODEL_EXPOSURE_LIST.md, "What is NOT filtered"):
      la denylist toglie dalla vetrina e dal pool di `auto/*`, non blocca il
      dispatch esplicito. Se lo scopo era impedire l'uso, non lo fa — ne' A ne'
      B, perche' e' il disegno upstream, non un difetto.

Uso:  python3 falsificatore_delta.py <cartella_delta>
Esce: 0 = ADOPT A · 1 = REJECT A · 2 = UNKNOWN (artefatti insufficienti, o un
      criterio non misurabile in questo ambiente — che non e' una bocciatura
      gentile: e' l'assenza di misura)
"""
import json
import os
import sys

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
    """Perche' una voce non fa sparire niente. Le cause note stanno nel codice
    3.8.51, non sono dedotte: il provider e' ritirato, oppure la voce e'
    scritta con l'alias mentre catalog.ts passa al predicato l'id canonico
    (`isModelExposureAllowed(aliasToProviderId[providerKey] || providerKey, ...)`,
    src/app/api/v1/models/catalog.ts)."""
    alias, ritirati = _tabella()
    prefisso = voce.split("/", 1)[0].strip().lower()
    coda = voce.split("/", 1)[1] if "/" in voce else ""
    if prefisso in ritirati:
        return "provider ritirato in 3.8.51 (410 PROVIDER_RETIRED): non c'e' niente da nascondere"
    if prefisso in alias:
        return ("scritta con l'alias; il predicato riceve l'id canonico '%s' — prova '%s/%s'"
                % (alias[prefisso], alias[prefisso], coda))
    return "nessun modello sparisce quando si applica questa voce da sola"


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


def ids_di(catalogo):
    """Gli id esposti da /v1/models, come insieme. Nient'altro viene dedotto."""
    if isinstance(catalogo, dict):
        dati = catalogo.get("data")
    elif isinstance(catalogo, list):
        dati = catalogo
    else:
        return set()
    if not isinstance(dati, list):
        return set()
    return {m["id"] for m in dati if isinstance(m, dict) and isinstance(m.get("id"), str)}


def misure_per_voce(d, ids_prima):
    """Per ogni voce applicata da sola: quali id sono spariti. Misurato."""
    cartella = os.path.join(d, "per_voce")
    if not os.path.isdir(cartella):
        return None
    misure = []
    n = 1
    while True:
        voce_f = os.path.join(cartella, "%d_voce.txt" % n)
        if not os.path.exists(voce_f):
            break
        voce = leggi_testo(voce_f)
        stato = leggi_testo(os.path.join(cartella, "%d_models.status" % n))
        catalogo = leggi_json(os.path.join(cartella, "%d_models.json" % n))
        if stato != "200" or catalogo is None:
            misure.append((voce, None))          # non misurata
        else:
            misure.append((voce, ids_prima - ids_di(catalogo)))
        n += 1
    return misure or None


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    d = argv[1]
    if not os.path.isdir(d):
        print("UNKNOWN — la cartella %s non esiste. Esegui prima candidate_a.sh." % d)
        return 2

    denylist = [r.strip() for r in leggi_testo(os.path.join(d, "denylist.txt")).splitlines()
                if r.strip()]
    prima = leggi_json(os.path.join(d, "models_prima.json"))
    dopo = leggi_json(os.path.join(d, "models_dopo.json"))
    impostazioni = leggi_json(os.path.join(d, "settings_dopo.json"))
    auto_meta = leggi_json(os.path.join(d, "auto.meta.json"))
    auto_prima_meta = leggi_json(os.path.join(d, "auto_prima.meta.json"))
    auto_resp = leggi_json(os.path.join(d, "auto_risposta.json"))
    expl_meta = leggi_json(os.path.join(d, "explicit.meta.json"))

    if not denylist:
        print("UNKNOWN — nessuna denylist registrata in %s/denylist.txt." % d)
        return 2
    if prima is None or dopo is None:
        print("UNKNOWN — manca models_prima.json o models_dopo.json: l'esecuzione non e' "
              "arrivata in fondo. Guarda %s/container.log." % d)
        return 2

    ids_prima = ids_di(prima)
    ids_dopo = ids_di(dopo)
    spariti = ids_prima - ids_dopo
    esiti = []

    def stato(ok):
        return "PASS" if ok else "FAIL"

    # A1
    s_prima = leggi_testo(os.path.join(d, "models_prima.status"))
    s_dopo = leggi_testo(os.path.join(d, "models_dopo.status"))
    esiti.append(("A1 catalogo raggiungibile prima e dopo",
                  stato(s_prima == "200" and s_dopo == "200"),
                  "HTTP prima=%s dopo=%s; %d modelli prima" % (s_prima or "?", s_dopo or "?",
                                                               len(ids_prima))))

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
    esiti.append(("A2 denylist riletta dallo stato, non solo accettata",
                  stato(patch_ok and sorted(riletta) == sorted(denylist)),
                  "PATCH HTTP %s; riletta %d/%d voci" % (s_patch or "?", len(riletta),
                                                         len(denylist))))

    # A3 — misurata, una voce per volta
    misure = misure_per_voce(d, ids_prima)
    inefficaci, non_misurate, unione = [], [], set()
    if misure is None:
        esiti.append(("A3 ogni voce, da sola, fa sparire almeno un id", "UNKNOWN",
                      "nessuna misura per voce in per_voce/: rilancia candidate_a.sh"))
    else:
        for voce, tolti in misure:
            if tolti is None:
                non_misurate.append(voce)
            elif not tolti:
                inefficaci.append(voce)
            else:
                unione |= tolti
        if non_misurate:
            esiti.append(("A3 ogni voce, da sola, fa sparire almeno un id", "UNKNOWN",
                          "%d voci non misurate (catalogo non leggibile)" % len(non_misurate)))
        else:
            esiti.append(("A3 ogni voce, da sola, fa sparire almeno un id",
                          stato(not inefficaci),
                          "%d/%d voci efficaci; %d id tolti in tutto"
                          % (len(misure) - len(inefficaci), len(misure), len(unione))))

    # A4 / A5 — coerenza fra le misure singole e la denylist intera
    if misure is None or non_misurate:
        esiti.append(("A4 la denylist intera toglie quello che tolgono le voci", "UNKNOWN",
                      "manca la misura per voce"))
        esiti.append(("A5 e non toglie nient'altro", "UNKNOWN", "manca la misura per voce"))
    else:
        mancanti = sorted(unione - spariti)
        extra = sorted(spariti - unione)
        esiti.append(("A4 la denylist intera toglie quello che tolgono le voci",
                      stato(not mancanti),
                      "rimasti in vetrina: %s"
                      % (", ".join(mancanti[:8]) if mancanti else "nessuno")))
        esiti.append(("A5 e non toglie nient'altro", stato(not extra),
                      "spariti senza una voce che li spieghi: %s"
                      % (", ".join(extra[:8]) if extra else "nessuno")))

    # A6 — con il controllo PRIMA del PATCH. `auto` che non risponde ne' prima
    # ne' dopo non dice niente sulla denylist: dice che qui non c'e' un provider.
    http_auto = (auto_meta or {}).get("http")
    http_auto_prima = (auto_prima_meta or {}).get("http")
    auto_ok = isinstance(http_auto, int) and 200 <= http_auto < 300
    auto_ok_prima = isinstance(http_auto_prima, int) and 200 <= http_auto_prima < 300
    scelto = ""
    if isinstance(auto_resp, dict) and isinstance(auto_resp.get("model"), str):
        scelto = auto_resp["model"]
    if auto_ok:
        esiti.append(("A6 auto risponde e non sceglie un modello tolto",
                      stato(scelto not in spariti),
                      "HTTP %s; modello risolto: %s" % (http_auto, scelto or "non dichiarato")))
    elif auto_ok_prima:
        esiti.append(("A6 auto risponde e non sceglie un modello tolto", "FAIL",
                      "funzionava prima del PATCH (HTTP %s) e dopo no (HTTP %s): la denylist "
                      "ha rotto il routing" % (http_auto_prima,
                                               http_auto if http_auto is not None else "?")))
    else:
        esiti.append(("A6 auto risponde e non sceglie un modello tolto", "UNKNOWN",
                      "auto non rispondeva gia' prima del PATCH (HTTP %s -> %s): nessun "
                      "provider configurato, non misurabile qui"
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

    if misure:
        print("\nEffetto misurato di ogni voce, applicata da sola:")
        for voce, tolti in misure:
            if tolti is None:
                print("  %-42s non misurata" % voce)
            elif not tolti:
                print("  %-42s NIENTE — %s" % (voce, diagnosi_voce_a_vuoto(voce)))
            else:
                elenco = ", ".join(sorted(tolti)[:4])
                print("  %-42s toglie %d: %s%s" % (voce, len(tolti), elenco,
                                                   " ..." if len(tolti) > 4 else ""))

    http_expl = (expl_meta or {}).get("http")
    if isinstance(http_expl, int) and 200 <= http_expl < 300:
        print("\nE1  il modello negato '%s' chiamato per nome risponde ancora (HTTP %s)."
              % ((expl_meta or {}).get("modello", "?"), http_expl))
        print("    Atteso: upstream filtra la vetrina e il pool di auto/*, non il dispatch")
        print("    esplicito. Se lo scopo era impedire l'uso, questa modifica non lo fa.")
    elif http_expl is not None:
        print("\nE1  il modello negato chiamato per nome NON ha risposto (HTTP %s)." % http_expl)
        print("    Non deducibile dalla denylist: puo' essere un provider assente o senza")
        print("    credenziali. Serve un'istanza con quel provider configurato.")

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
