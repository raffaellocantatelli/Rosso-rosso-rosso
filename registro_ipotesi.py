"""Registro Ipotesi — framework epistemologico R³∞.

Principi:
  P5 — niente auto-conferma: un'ipotesi non può confermarsi da sola.
  P6 — serve la contro-forza: ogni ipotesi deve dichiarare come potrebbe
       essere falsificata. Se non lo dichiara, non può mai essere confermata.

Questo file è la riconciliazione di due sessioni del 25/08/2026 che lo hanno
riscritto in parallelo su rami diversi, ciascuna chiudendo un varco che
l'altra non vedeva. Nessuna delle due correzioni è stata persa:

* **P6 non si soddisfa con un campo pieno** (ramo `todo-implementation`).
  Un segnaposto («da definire», «TBD») è un campo pieno che non dichiara
  nulla: `criterio_definito` lo riconosce e il registro lo tratta come vuoto.

* **P6 non si soddisfa nemmeno con una bella frase** (ramo `new-session`).
  Finché il criterio è solo testo, a eseguirlo non è nessuno: H3 è rimasta
  CONFERMATA per settimane senza che una verifica fosse mai stata registrata.
  Il criterio porta perciò un `falsificatore`: un comando che risponde «è
  caduta?», e lo stato lo muove l'esecuzione (vedi `verificatore.py`).

Gerarchia degli stati, dal più debole al più forte:

  NON_VERIFICABILE  nessun comando può deciderla. Per P6 non è confermabile:
                    è strato aspirazionale, e va scritto.
  APERTA            ha un falsificatore, non è ancora stato eseguito.
  FALSIFICATA       il comando dice che la condizione di caduta è avvenuta.
  RETTA             ha superato N esecuzioni del proprio falsificatore.
  CONFERMATA        richiede una fonte esterna al formulatore (P5).

RETTA è il tetto di un sistema che si verifica da sé: eseguire non è
confermare. Il registro adesso lo scrive invece di arrotondare.
"""
import argparse
import json
import os
import sys

REGISTRO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registro_ipotesi.json")

APERTA = "APERTA"
RETTA = "RETTA"
CONFERMATA = "CONFERMATA"
FALSIFICATA = "FALSIFICATA"
NON_VERIFICABILE = "NON_VERIFICABILE"

STATI = (APERTA, RETTA, CONFERMATA, FALSIFICATA, NON_VERIFICABILE)

#: Stati che solo il verificatore può assegnare, eseguendo il falsificatore.
#: C'è dentro RETTA e non FALSIFICATA, ed è un'asimmetria voluta: «ha retto»
#: è un'affermazione positiva e va eseguita; «è caduta» no. P6 blocca la
#: conferma, mai la smentita — un'ipotesi si può sempre chiudere in negativo,
#: anche da soli, perché uccidere la propria ipotesi è l'opposto dell'auto-
#: conferma. (Principio dal ramo `todo-implementation`, 25/08.)
STATI_DA_ESECUZIONE = (RETTA,)

#: Stati in cui un'ipotesi non ha ancora ricevuto un verdetto sul merito:
#: solo qui si può ancora scrivere il criterio mancante.
STATI_SENZA_VERDETTO = (APERTA, NON_VERIFICABILE)

# Testo usato quando un'ipotesi è registrata prima che il suo criterio esista.
CRITERIO_DA_DEFINIRE = "Da definire esplicitamente prima che possa essere confermata (P6)."

# Formule di rinvio: dichiarano l'intenzione di scrivere un criterio, non il
# criterio. Confrontate in minuscolo su tutto il testo del campo.
MARCATORI_RINVIO = (
    "da definire",
    "da stabilire",
    "da precisare",
    "da scrivere",
    "non definito",
    "non ancora",
    "tbd",
    "todo",
    "n/a",
)

# Sotto questa soglia un campo non può contenere una condizione di falsità
# ("-", "ok", "sì"): è rumore, non un criterio.
LUNGHEZZA_MINIMA_CRITERIO = 12

IPOTESI_INIZIALI = [
    {
        "id": "H1",
        "testo": 'Claude "ha capito senza capire" durante la scena con Jorge',
        "stato": NON_VERIFICABILE,
        "criterio_falsificazione": CRITERIO_DA_DEFINIRE,
        "falsificatore": None,
        "scadenza": None,
    },
    {
        "id": "H2",
        "testo": "Il disegno di Claudio darà ragione a entrambi entro 6 mesi (criterio: battito + contatto)",
        "stato": APERTA,
        "criterio_falsificazione": (
            "Falsificata se si verifica una delle due condizioni: "
            "(a) output/ non contiene daily output regolari (sistema morto); "
            "(b) output/contatti.jsonl ha zero voci valide (sistema vivo ma non tocca il mondo)."
        ),
        "falsificatore": {
            "comando": ["python3", "falsificatori/h2_battito_e_contatto.py"],
            "descrizione": "battito: daily recenti in output/ — contatto: righe valide in contatti.jsonl",
        },
        "scadenza": "2026-12-11",
    },
    {
        "id": "H3",
        "testo": "La regola dell'italiano garantisce trasparenza",
        "stato": APERTA,
        "criterio_falsificazione": (
            "Falsificata se un output del sistema non è in italiano senza motivo dichiarato."
        ),
        "falsificatore": {
            "comando": ["python3", "falsificatori/h3_italiano.py"],
            "descrizione": "controlla la lingua di tutti i daily in output/",
        },
        "scadenza": None,
    },
    {
        "id": "H4",
        "testo": (
            "Un contraddittorio interno — la macchina che esegue, non una terza persona — "
            "riesce a falsificare affermazioni che nessuno dei due nodi aveva messo in dubbio"
        ),
        "stato": APERTA,
        "criterio_falsificazione": (
            "Falsificata se, nella finestra degli ultimi 30 giorni, output/verifiche.jsonl "
            "contiene almeno 10 verifiche e nessuna di esse ha prodotto una caduta o un "
            "declassamento. Un contraddittorio che per un mese non contraddice mai non è "
            "un contraddittorio: è un timbro."
        ),
        "falsificatore": {
            "comando": ["python3", "falsificatori/h4_contraddittorio.py"],
            "descrizione": "il verificatore ha ancora la capacità di dire di no?",
        },
        "scadenza": "2026-09-30",
    },
]

#: Campi che ogni voce deve avere; le vecchie voci vengono completate al volo.
CAMPI_DEFAULT = {
    "falsificatore": None,
    "verifiche": {"eseguite": 0, "cadute": 0, "ultima": None, "ultimo_esito": None},
}


def criterio_definito(criterio):
    """Vero se il campo dichiara una condizione di falsità, non l'intenzione di scriverla."""
    if not criterio or not criterio.strip():
        return False
    testo = criterio.strip().lower()
    if len(testo) < LUNGHEZZA_MINIMA_CRITERIO:
        return False
    return not any(marcatore in testo for marcatore in MARCATORI_RINVIO)


def _load():
    if os.path.exists(REGISTRO_PATH):
        with open(REGISTRO_PATH, "r", encoding="utf-8") as f:
            return _completa(json.load(f))
    _save(IPOTESI_INIZIALI)
    return [dict(h) for h in IPOTESI_INIZIALI]


def _completa(ipotesi):
    """Aggiunge i campi nuovi alle voci scritte prima di questa revisione.

    Il falsificatore di una voce nota viene ripreso da IPOTESI_INIZIALI: non
    si inventa, si ricollega. Le voci sconosciute restano senza, e finiscono
    NON_VERIFICABILE alla prima esecuzione del verificatore.
    """
    noti = {h["id"]: h for h in IPOTESI_INIZIALI}
    for h in ipotesi:
        for campo, default in CAMPI_DEFAULT.items():
            if campo not in h:
                originale = noti.get(h["id"], {}).get(campo, default)
                h[campo] = json.loads(json.dumps(originale))
    for id_, nuova in noti.items():
        if not any(h["id"] == id_ for h in ipotesi):
            ipotesi.append(json.loads(json.dumps(nuova)))
    return ipotesi


def _save(ipotesi):
    with open(REGISTRO_PATH, "w", encoding="utf-8") as f:
        json.dump(ipotesi, f, ensure_ascii=False, indent=2)


def carica():
    """Il registro completo, con i campi nuovi già presenti."""
    return _load()


def salva(ipotesi):
    """Riscrive il registro. Usato dal verificatore dopo un'esecuzione."""
    _save(ipotesi)


def aggiungi(id_, testo, criterio_falsificazione, falsificatore=None, scadenza=None):
    if not criterio_definito(criterio_falsificazione):
        raise ValueError(
            "P6 violato: ogni ipotesi deve dichiarare un criterio di falsificazione. "
            "Un segnaposto («da definire», «TBD») non è un criterio."
        )
    ipotesi = _load()
    if any(h["id"] == id_ for h in ipotesi):
        raise ValueError(f"L'ipotesi {id_} esiste già: le ipotesi non si sovrascrivono.")
    voce = {
        "id": id_,
        "testo": testo,
        "stato": APERTA if falsificatore else NON_VERIFICABILE,
        "criterio_falsificazione": criterio_falsificazione,
        "falsificatore": falsificatore,
        "scadenza": scadenza,
    }
    voce["verifiche"] = json.loads(json.dumps(CAMPI_DEFAULT["verifiche"]))
    ipotesi.append(voce)
    _save(ipotesi)
    return ipotesi


def aggiorna_stato(id_, nuovo_stato, prova_esterna=None):
    """Cambia stato a mano. Tre porte restano chiuse, ed è il punto.

    * RETTA lo assegna solo il verificatore eseguendo il falsificatore:
      dichiarare a mano «ha retto» sarebbe l'auto-conferma di prima con
      un'etichetta nuova. FALSIFICATA invece resta sempre dichiarabile: la
      smentita non ha bisogno di permessi.
    * CONFERMATA richiede `prova_esterna`: una fonte diversa da chi ha
      formulato l'ipotesi (P5).
    * CONFERMATA richiede anche un criterio vero, non un segnaposto (P6).
    """
    if nuovo_stato not in STATI:
        raise ValueError(f"Stato sconosciuto: {nuovo_stato!r}. Attesi: {', '.join(STATI)}.")
    if nuovo_stato in STATI_DA_ESECUZIONE:
        raise ValueError(
            f"P5 violato: {nuovo_stato} lo assegna solo l'esecuzione del falsificatore "
            "(python -m sdq1 --verifica-ipotesi), non una dichiarazione. "
            "Per chiudere in negativo usa FALSIFICATA: quella non è mai bloccata."
        )

    ipotesi = _load()
    trovata = False
    for h in ipotesi:
        if h["id"] != id_:
            continue
        trovata = True
        if nuovo_stato == CONFERMATA:
            if not criterio_definito(h.get("criterio_falsificazione", "")):
                raise ValueError(
                    f"P6 violato: {id_} non dichiara come potrebbe essere falsificata, "
                    "quindi non può essere confermata. Scrivi prima il criterio."
                )
            if not (prova_esterna or "").strip():
                raise ValueError(
                    "P5 violato: CONFERMATA richiede una fonte esterna a chi ha formulato "
                    "l'ipotesi. Eseguire un proprio comando non è confermare: è al massimo RETTA."
                )
            h["prova_esterna"] = prova_esterna
        h["stato"] = nuovo_stato
    if not trovata:
        raise KeyError(f"Ipotesi {id_} non trovata")
    _save(ipotesi)
    return ipotesi


def definisci_criterio(id_, criterio, falsificatore=None):
    """Scrive il criterio dove non c'era. Non riscrive quello che ne ha già uno.

    Serve per l'ipotesi registrata prima che il suo criterio esistesse (H1). Il
    divieto di riscrittura è la stessa contro-forza di P6 vista da dopo: un
    criterio che si può cambiare quando i dati sono già arrivati non è un
    bersaglio, è un commento. Chi vuole un criterio diverso registra un'ipotesi
    nuova, e la vecchia resta a memoria di cosa si era previsto.

    Con `falsificatore` l'ipotesi diventa eseguibile e passa ad APERTA. Senza,
    il criterio resta una frase che nessuno esegue: l'ipotesi resta
    NON_VERIFICABILE, e il registro lo dice invece di lasciarlo credere.
    """
    if not criterio_definito(criterio):
        raise ValueError(
            "P6 violato: il criterio deve dire cosa smentirebbe l'ipotesi. "
            "Un segnaposto non è un criterio."
        )
    ipotesi = _load()
    for h in ipotesi:
        if h["id"] != id_:
            continue
        if criterio_definito(h.get("criterio_falsificazione", "")):
            raise ValueError(
                f"{id_} dichiara già un criterio. Riscriverlo sposta il bersaglio: "
                "registra un'ipotesi nuova con aggiungi()."
            )
        if h["stato"] not in STATI_SENZA_VERDETTO:
            raise ValueError(
                f"{id_} è {h['stato']}: darle un criterio adesso giustificherebbe a "
                "posteriori un verdetto già emesso."
            )
        h["criterio_falsificazione"] = criterio
        if falsificatore:
            h["falsificatore"] = falsificatore
            h["stato"] = APERTA
        else:
            h["stato"] = NON_VERIFICABILE
        _save(ipotesi)
        return ipotesi
    raise KeyError(f"Ipotesi {id_} non trovata")


def stato_corrente():
    return _load()


def stampa_stato():
    ipotesi = stato_corrente()
    print("=== Registro Ipotesi R³∞ ===")
    print("P5: niente auto-conferma  |  P6: serve la contro-forza\n")
    for h in ipotesi:
        print(f"[{h['id']}] {h['stato']}")
        print(f"   {h['testo']}")
        if criterio_definito(h.get("criterio_falsificazione", "")):
            print(f"   Criterio di falsificazione: {h['criterio_falsificazione']}")
        else:
            print("   Criterio di falsificazione: MANCANTE — nessuna condizione dichiarata.")
            print(f"   Scrivilo:  python registro_ipotesi.py --criterio {h['id']} \"...\"")
        falsificatore = h.get("falsificatore")
        if falsificatore:
            print(f"   Comando: {' '.join(falsificatore['comando'])}")
        else:
            print("   Comando: nessuno — nessuna macchina la mette alla prova")
        verifiche = h.get("verifiche") or {}
        if verifiche.get("eseguite"):
            print(f"   Verifiche: {verifiche['eseguite']} eseguite, "
                  f"{verifiche['cadute']} cadute, ultima {verifiche['ultima']}")
        if h.get("scadenza"):
            print(f"   Scadenza: {h['scadenza']}")
        print()


def _cli(argv=None):
    parser = argparse.ArgumentParser(
        description="Registro Ipotesi R³∞ — P5: niente auto-conferma | P6: serve la contro-forza."
    )
    parser.add_argument(
        "--criterio", nargs=2, metavar=("ID", "TESTO"),
        help="scrive il criterio di falsificazione di un'ipotesi che non ne ha ancora uno",
    )
    parser.add_argument(
        "--comando", nargs="+", metavar="ARG",
        help="con --criterio: il comando che esegue quel criterio (exit 0 = caduta)",
    )
    args = parser.parse_args(argv)
    if args.criterio:
        id_, testo = args.criterio
        falsificatore = None
        if args.comando:
            falsificatore = {"comando": list(args.comando), "descrizione": testo[:80]}
        try:
            definisci_criterio(id_, testo, falsificatore)
        except (ValueError, KeyError) as e:
            print(f"Rifiutato: {e.args[0] if e.args else e}", file=sys.stderr)
            return 1
        if falsificatore:
            print(f"Criterio e comando scritti per {id_}: da ora è eseguibile.\n")
        else:
            print(f"Criterio scritto per {id_}. Senza un comando che lo esegua resta "
                  f"NON_VERIFICABILE: nessuno lo metterà alla prova.\n")
    stampa_stato()
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
