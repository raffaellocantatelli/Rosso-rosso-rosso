"""Registro Ipotesi — framework epistemologico R³∞.

Principi:
  P5 — niente auto-conferma: un'ipotesi non può confermarsi da sola.
  P6 — serve la contro-forza: ogni ipotesi deve dichiarare come potrebbe
       essere falsificata. Se non lo dichiara, non può mai essere confermata.
"""
import json
import os

REGISTRO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registro_ipotesi.json")

APERTA = "APERTA"
CONFERMATA = "CONFERMATA"
FALSIFICATA = "FALSIFICATA"

IPOTESI_INIZIALI = [
    {
        "id": "H1",
        "testo": 'Claude "ha capito senza capire" durante la scena con Jorge',
        "stato": APERTA,
        "criterio_falsificazione": "Da definire esplicitamente prima che possa essere confermata (P6).",
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
    if not criterio_falsificazione or not criterio_falsificazione.strip():
        raise ValueError("P6 violato: ogni ipotesi deve dichiarare un criterio di falsificazione.")
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
    ipotesi = _load()
    trovata = False
    for h in ipotesi:
        if h["id"] == id_:
            trovata = True
            if nuovo_stato == CONFERMATA and not h["criterio_falsificazione"].strip():
                raise ValueError(
                    "P5 violato: non può essere confermata un'ipotesi senza criterio di falsificazione dichiarato."
                )
            h["stato"] = nuovo_stato
    if not trovata:
        raise KeyError(f"Ipotesi {id_} non trovata")
    _save(ipotesi)
    return ipotesi


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
        if h.get("scadenza"):
            print(f"   Scadenza: {h['scadenza']}")
        print()


if __name__ == "__main__":
    stampa_stato()
