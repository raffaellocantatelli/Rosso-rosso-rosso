"""Registro Ipotesi — framework epistemologico R³∞.

Principi:
  P5 — niente auto-conferma: un'ipotesi non può confermarsi da sola.
  P6 — serve la contro-forza: ogni ipotesi deve dichiarare come potrebbe
       essere falsificata. Se non lo dichiara, non può mai essere confermata.

Revisione del 2026-08-25 — perché il registro violava P5 nella forma corretta.

Fino a oggi `aggiorna_stato` accettava CONFERMATA se il criterio di
falsificazione era una stringa non vuota: controllava che la frase ci fosse,
non che qualcuno l'avesse eseguita. H3 risultava CONFERMATA senza che nessuna
verifica fosse mai stata registrata da nessuna parte.

Da qui in avanti il criterio di falsificazione non è più (solo) una frase:
è un **comando eseguibile** che risponde alla domanda "è caduta?". Lo stato
lo muove l'esecuzione, non la dichiarazione — vedi verificatore.py.

Gerarchia degli stati, dal più debole al più forte:

  NON_VERIFICABILE  nessun comando può deciderla. Per P6 non sarà mai
                    confermabile: è strato aspirazionale, e va detto.
  APERTA            ha un falsificatore, non è ancora stato eseguito.
  FALSIFICATA       il comando dice che la condizione di caduta è avvenuta.
  RETTA             ha superato N esecuzioni del proprio falsificatore.
  CONFERMATA        richiede una fonte esterna al formulatore (P5).

RETTA è il massimo che una macchina possa concedere: eseguire non è
confermare. Il registro adesso lo scrive invece di arrotondare.
"""
import json
import os

REGISTRO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registro_ipotesi.json")

APERTA = "APERTA"
RETTA = "RETTA"
CONFERMATA = "CONFERMATA"
FALSIFICATA = "FALSIFICATA"
NON_VERIFICABILE = "NON_VERIFICABILE"

STATI = (APERTA, RETTA, CONFERMATA, FALSIFICATA, NON_VERIFICABILE)

#: Stati che solo il verificatore può assegnare, eseguendo il falsificatore.
STATI_DA_ESECUZIONE = (RETTA, FALSIFICATA)

IPOTESI_INIZIALI = [
    {
        "id": "H1",
        "testo": 'Claude "ha capito senza capire" durante la scena con Jorge',
        "stato": NON_VERIFICABILE,
        "criterio_falsificazione": (
            "Nessun comando può deciderla: riguarda uno stato interno di un "
            "modello in una sessione conclusa, non osservabile da qui. "
            "Resta strato aspirazionale — e per P6 non sarà mai confermabile."
        ),
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
    if not criterio_falsificazione or not criterio_falsificazione.strip():
        raise ValueError("P6 violato: ogni ipotesi deve dichiarare un criterio di falsificazione.")
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
    voce.update(json.loads(json.dumps(CAMPI_DEFAULT)))
    voce["falsificatore"] = falsificatore
    ipotesi.append(voce)
    _save(ipotesi)
    return ipotesi


def aggiorna_stato(id_, nuovo_stato, prova_esterna=None):
    """Cambia stato a mano. Due porte restano chiuse, ed è il punto.

    * RETTA e FALSIFICATA li assegna solo il verificatore eseguendo il
      falsificatore: dichiararli a mano sarebbe la stessa auto-conferma di
      prima con un'etichetta nuova.
    * CONFERMATA richiede `prova_esterna`: una fonte diversa da chi ha
      formulato l'ipotesi (P5). Senza, solleva.
    """
    if nuovo_stato not in STATI:
        raise ValueError(f"Stato sconosciuto: {nuovo_stato}. Ammessi: {', '.join(STATI)}")
    if nuovo_stato in STATI_DA_ESECUZIONE:
        raise ValueError(
            f"P5 violato: {nuovo_stato} lo assegna solo l'esecuzione del falsificatore "
            "(python -m sdq1 --verifica-ipotesi), non una dichiarazione."
        )
    if nuovo_stato == CONFERMATA and not (prova_esterna or "").strip():
        raise ValueError(
            "P5 violato: CONFERMATA richiede una fonte esterna a chi ha formulato "
            "l'ipotesi. Eseguire un proprio comando non è confermare: è al massimo RETTA."
        )

    ipotesi = _load()
    trovata = False
    for h in ipotesi:
        if h["id"] == id_:
            trovata = True
            h["stato"] = nuovo_stato
            if prova_esterna:
                h["prova_esterna"] = prova_esterna
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
        falsificatore = h.get("falsificatore")
        if falsificatore:
            print(f"   Comando: {' '.join(falsificatore['comando'])}")
        else:
            print("   Comando: nessuno — per P6 non sarà mai confermabile")
        verifiche = h.get("verifiche") or {}
        if verifiche.get("eseguite"):
            print(f"   Verifiche: {verifiche['eseguite']} eseguite, "
                  f"{verifiche['cadute']} cadute, ultima {verifiche['ultima']}")
        if h.get("scadenza"):
            print(f"   Scadenza: {h['scadenza']}")
        print()


if __name__ == "__main__":
    stampa_stato()
