"""Registro Ipotesi — framework epistemologico R³∞.

Principi:
  P5 — niente auto-conferma: un'ipotesi non può confermarsi da sola.
  P6 — serve la contro-forza: ogni ipotesi deve dichiarare come potrebbe
       essere falsificata. Se non lo dichiara, non può mai essere confermata.

P6 non è soddisfatto da un campo pieno: è soddisfatto da un criterio che dice
davvero cosa smentirebbe l'ipotesi. Un segnaposto («da definire», «TBD») è un
campo pieno che non dichiara nulla, e per il registro vale quanto il vuoto:
`criterio_definito` lo riconosce come tale e `aggiorna_stato` rifiuta di
confermare l'ipotesi che lo porta.
"""
import argparse
import json
import os
import sys

REGISTRO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registro_ipotesi.json")

APERTA = "APERTA"
CONFERMATA = "CONFERMATA"
FALSIFICATA = "FALSIFICATA"

STATI = (APERTA, CONFERMATA, FALSIFICATA)

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
        "stato": APERTA,
        "criterio_falsificazione": CRITERIO_DA_DEFINIRE,
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
        "scadenza": "2026-12-11",
    },
    {
        "id": "H3",
        "testo": "La regola dell'italiano garantisce trasparenza",
        "stato": CONFERMATA,
        "criterio_falsificazione": "Falsificata se una risposta del sistema non è in italiano senza motivo dichiarato.",
        "scadenza": None,
    },
]


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
            return json.load(f)
    _save(IPOTESI_INIZIALI)
    return [dict(h) for h in IPOTESI_INIZIALI]


def _save(ipotesi):
    with open(REGISTRO_PATH, "w", encoding="utf-8") as f:
        json.dump(ipotesi, f, ensure_ascii=False, indent=2)


def aggiungi(id_, testo, criterio_falsificazione, scadenza=None):
    if not criterio_definito(criterio_falsificazione):
        raise ValueError(
            "P6 violato: ogni ipotesi deve dichiarare un criterio di falsificazione. "
            "Un segnaposto («da definire», «TBD») non è un criterio."
        )
    ipotesi = _load()
    ipotesi.append({
        "id": id_,
        "testo": testo,
        "stato": APERTA,
        "criterio_falsificazione": criterio_falsificazione,
        "scadenza": scadenza,
    })
    _save(ipotesi)
    return ipotesi


def aggiorna_stato(id_, nuovo_stato):
    if nuovo_stato not in STATI:
        raise ValueError(f"Stato sconosciuto: {nuovo_stato!r}. Attesi: {', '.join(STATI)}.")
    ipotesi = _load()
    trovata = False
    for h in ipotesi:
        if h["id"] == id_:
            trovata = True
            if nuovo_stato == CONFERMATA and not criterio_definito(h.get("criterio_falsificazione", "")):
                raise ValueError(
                    f"P6 violato: {id_} non dichiara come potrebbe essere falsificata, "
                    "quindi non può essere confermata. Scrivi prima il criterio."
                )
            h["stato"] = nuovo_stato
    if not trovata:
        raise KeyError(f"Ipotesi {id_} non trovata")
    _save(ipotesi)
    return ipotesi


def definisci_criterio(id_, criterio):
    """Scrive il criterio dove non c'era. Non riscrive quello che ne ha già uno.

    Serve per l'ipotesi registrata prima che il suo criterio esistesse (H1). Il
    divieto di riscrittura è la stessa contro-forza di P6 vista da dopo: un
    criterio che si può cambiare quando i dati sono già arrivati non è un
    bersaglio, è un commento. Chi vuole un criterio diverso registra un'ipotesi
    nuova, e la vecchia resta a memoria di cosa si era previsto.
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
        if h["stato"] != APERTA:
            raise ValueError(
                f"{id_} è {h['stato']}: darle un criterio adesso giustificherebbe a "
                "posteriori un verdetto già emesso."
            )
        h["criterio_falsificazione"] = criterio
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
        print(f"   Criterio di falsificazione: {h['criterio_falsificazione']}")
        if not criterio_definito(h.get("criterio_falsificazione", "")):
            print("   ⚠  Criterio non dichiarato: per P6 questa ipotesi non è confermabile.")
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
    args = parser.parse_args(argv)
    if args.criterio:
        id_, testo = args.criterio
        try:
            definisci_criterio(id_, testo)
        except (ValueError, KeyError) as e:
            print(f"Rifiutato: {e.args[0] if e.args else e}", file=sys.stderr)
            return 1
        print(f"Criterio scritto per {id_}. Da ora {id_} è falsificabile, quindi confermabile.\n")
    stampa_stato()
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
