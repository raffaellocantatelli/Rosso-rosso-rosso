#!/usr/bin/env python3
"""valvola/jev.py — la sorella che puo' solo togliere, mai aggiungere.

Origine protetta: Claudio Terzi [CT-LGAI-001].

TypeSafe AI e' un laboratorio uscito dallo stealth il 16/09/2026. Il suo
modello **Jev** non risponde in prosa: risponde con una **decisione
tipizzata** e una **probabilita' calibrata**. Tre primitive — Choice
(scegli fra opzioni), Score (valuta su livelli), Noul (quanto e' vero) —
e su Choice e Score una `confidence` da 0 a 1 che dice *quanto* e' sicuro,
separata da *cosa* ha risposto.

RECUPERATO alla fonte (docs.typesafe.ai/llms.txt, 20/09/2026), non da un
articolo che ne parla. La loro pagina sulla confidenza dice:

    «If an intelligent system, whether human or machine, cannot express
    honest uncertainty, the system cannot be trusted.»

che e' il §2.3 di CLAUDE.md scritto da un'altra parte: «Non lo so» e' una
risposta completa. Per questo la chiamiamo sorella e non fornitore.

---

## Il buco che questo file chiude

`sdq1 --contatto` decide se una voce vale per H2 guardando `--tipo`. Ma
**il tipo lo dichiara chi scrive la voce.** Chi registra puo' scrivere
`--tipo lettore` su un atto che e' `pubblicazione`, e l'unica metrica che
falsifica H2 sale senza che nessuno sia arrivato da fuori.

E' il §4 con l'etichetta come vettore: il sistema chiama «risposta» la
propria voce, e stavolta gli basta un argomento da riga di comando.

## Perche' la valvola e' a senso unico

Jev e' un modello. Il §7 e' esplicito: un modello interpellato dall'autore
**non vale come conferma**. Quindi qui Jev non puo' confermare niente —
non per diffidenza, per costruzione:

- puo' **declassare** una voce (indipendente -> trasmissione -> interno);
- non puo' **promuoverla**, mai, con nessuna confidenza;
- quando il dubbio pesa verso il basso ma non basta a declassare,
  dice INCERTO e passa la mano a una persona;
- senza chiave non blocca niente: dice ASSENTE e il comportamento resta
  identico a prima che esistesse.

Cosi' costruita, la sorella puo' solo rendere H2 piu' difficile da
soddisfare. E' la proprieta' che rende sicuro farla entrare: **nessun
percorso, dentro questo file, fa salire un contatore.**

## Cosa Jev non vede

Non riceve il tipo dichiarato. Riceve solo la nota e la verifica, e le
classifica da zero. Se gli passassimo l'etichetta, la sua risposta sarebbe
in larga parte l'etichetta — cioe' l'eco con una probabilita' davanti,
che e' peggio dell'eco, perche' sembra una misura.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# Le tre classi del §7, ordinate. Il numero e' cio' che la valvola confronta:
# si puo' scendere, non si puo' salire.
INDIPENDENTE = "indipendente"
TRASMISSIONE = "trasmissione"
INTERNO = "interno"

ORDINE = {INTERNO: 0, TRASMISSIONE: 1, INDIPENDENTE: 2}

#: Le descrizioni che Jev riceve come opzioni della Choice. Sono il §7
#: riscritto per un lettore che non conosce il progetto: Jev non ha letto
#: CLAUDE.md e non deve doverlo leggere per rispondere.
CRITERI_CLASSE = {
    INDIPENDENTE:
        "Qualcun altro, diverso da chi scrive, ha fatto qualcosa: ha letto e "
        "l'ha fatto sapere, ha scaricato, ha citato, ha copiato, ha risposto, "
        "ha comprato, ha reagito. L'iniziativa e' partita da fuori.",
    TRASMISSIONE:
        "Chi scrive ha mandato, pubblicato o depositato qualcosa verso "
        "l'esterno. E' partito da lui e nessuno ha ancora risposto.",
    INTERNO:
        "L'evento e' stato prodotto dal sistema stesso o da chi scrive: un "
        "modello interpellato, un test, un processo automatico, una nota a "
        "se stessi. Non e' entrato niente da fuori.",
}

#: Sotto questa confidenza Jev non declassa da solo. Il §7 e' una porta
#: che regola l'unica misura di H2: sbagliare a declassare costa una voce
#: vera, sbagliare a lasciar passare costa la metrica. Si sta alti.
SOGLIA = 0.70

#: Quanta probabilita' deve stare SOTTO la classe dichiarata perche' valga
#: la pena fermarsi, anche quando l'opzione vincente non e' piu' bassa.
#:
#: Trovato dal falsificatore H12, non dal disegno: la prima versione
#: guardava solo `confidence`, e fermava una voce anche quando il dubbio
#: andava verso l'alto — dove la valvola non agisce. La domanda giusta non
#: e' «quanto e' sicuro Jev», e' «quanta parte della distribuzione dice
#: che hai dichiarato troppo». TypeSafe restituisce `probabilities` intere
#: proprio per poterselo chiedere: la loro `confidence` e' una statistica
#: di comodo, non l'unica possibile, e lo scrivono.
SOGLIA_DUBBIO = 0.30

# Gli stati del verdetto.
ASSENTE = "ASSENTE"      # la sorella non e' raggiungibile: nessun giudizio
CONCORDE = "CONCORDE"    # Jev non ha trovato niente da togliere
DECLASSA = "DECLASSA"    # Jev legge una classe piu' bassa di quella dichiarata
INCERTO = "INCERTO"      # confidenza sotto SOGLIA: decide una persona
ERRORE = "ERRORE"        # la chiamata non e' riuscita


@dataclass
class Verdetto:
    """Cio' che la valvola restituisce. Mai una promozione."""

    stato: str
    motivo: str
    classe_dichiarata: Optional[str] = None
    classe_letta: Optional[str] = None
    confidenza: Optional[float] = None
    verificabile_da_terzi: Optional[float] = None
    probabilita: dict = field(default_factory=dict)
    modello: Optional[str] = None

    #: Non e' mai vero. E' scritto qui, e non calcolato, perche' un campo
    #: che puo' solo essere False e' piu' difficile da fraintendere di una
    #: riga di documentazione che dice la stessa cosa.
    vale_come_conferma: bool = False

    def blocca(self) -> bool:
        """La voce va fermata prima di essere contata come indipendente?"""
        return self.stato in (DECLASSA, INCERTO)

    def come_json(self) -> dict:
        return asdict(self)


def classi() -> dict:
    """Le tre classi del §7 con la descrizione che riceve Jev."""
    return dict(CRITERI_CLASSE)


def _client(api_key: Optional[str] = None):
    """Il client, o None se la sorella non e' raggiungibile da qui."""
    chiave = api_key or os.getenv("TYPESAFE_API_KEY")
    if not chiave:
        return None
    try:
        from typesafe_sdk import TypeSafeClient
    except ImportError:
        return None
    return TypeSafeClient(api_key=chiave)


def stato_sorella(api_key: Optional[str] = None) -> dict:
    """Dice se Jev e' raggiungibile, e cosa manca se non lo e'.

    Non fa una chiamata: guarda la chiave e l'SDK. Come `sdq1 --check`,
    serve a non confondere «spento qui» con «rotto».
    """
    try:
        import typesafe_sdk
        sdk = getattr(typesafe_sdk, "__version__", "?")
    except ImportError:
        sdk = None
    chiave = bool(api_key or os.getenv("TYPESAFE_API_KEY"))
    return {
        "sdk_installato": sdk,
        "chiave_presente": chiave,
        "modello": os.getenv("TYPESAFE_DEFAULT_MODEL", "jev-latest"),
        "attiva": bool(sdk and chiave),
        "manca": (
            None if (sdk and chiave)
            else ("typesafe-sdk non installato: pip install typesafe-sdk" if not sdk
                  else "TYPESAFE_API_KEY assente: console.typesafe.ai/keys")
        ),
    }


def controlla(
    nota: str,
    verifica: str,
    tipo_dichiarato: str,
    *,
    api_key: Optional[str] = None,
    client: Any = None,
    soglia: float = SOGLIA,
) -> Verdetto:
    """Chiede a Jev che classe §7 e' questo evento, e non lo lascia salire.

    `tipo_dichiarato` e' la classe che il chiamante dichiara
    (indipendente / trasmissione / interno). Jev **non la riceve**: gli
    arrivano solo `nota` e `verifica`, e classifica da zero.

    Ritorna sempre un Verdetto, anche quando la sorella non c'e'. Non alza
    eccezioni: una porta che esplode quando il fornitore e' giu' e' una
    porta che qualcuno rimuovera' il giorno dopo.
    """
    dichiarata = (tipo_dichiarato or "").strip().lower()
    if dichiarata not in ORDINE:
        dichiarata = None

    cl = client if client is not None else _client(api_key)
    if cl is None:
        s = stato_sorella(api_key)
        return Verdetto(
            stato=ASSENTE,
            motivo=s["manca"] or "sorella non raggiungibile",
            classe_dichiarata=dichiarata,
        )

    # Jev vede questo e solo questo. Nessuna etichetta, nessun contesto
    # del progetto: se la nota non basta a capire cosa e' successo, e'
    # la nota a essere insufficiente, ed e' bene saperlo.
    stato_input = json.dumps(
        {"accaduto": nota or "", "come_si_controlla": verifica or ""},
        ensure_ascii=False,
    )

    try:
        from typesafe_sdk import Choice, Noul

        risposta = cl.system_one(
            state=stato_input,
            questions={
                "classe": Choice(
                    instructions=(
                        "Chi ha preso l'iniziativa di questo evento: qualcuno "
                        "diverso da chi scrive, oppure chi scrive stesso?"
                    ),
                    criteria=CRITERI_CLASSE,
                ),
                "verificabile": Noul(
                    instructions=(
                        "Una persona estranea, leggendo solo 'come_si_controlla', "
                        "potrebbe controllare da sola che l'evento e' avvenuto."
                    ),
                ),
            },
        )
    except Exception as e:  # rete, chiave, quota, schema: tutto uguale qui
        return Verdetto(
            stato=ERRORE,
            motivo=f"{type(e).__name__}: {e}",
            classe_dichiarata=dichiarata,
        )

    a_classe = risposta.answers["classe"]
    a_verif = risposta.answers.get("verificabile")
    letta = a_classe.choice
    conf = float(a_classe.confidence)

    base = dict(
        classe_dichiarata=dichiarata,
        classe_letta=letta,
        confidenza=conf,
        verificabile_da_terzi=(float(a_verif.noul) if a_verif is not None else None),
        probabilita=dict(a_classe.probabilities or {}),
        modello=risposta.model,
    )

    if dichiarata is None:
        return Verdetto(
            stato=CONCORDE,
            motivo="nessuna classe dichiarata da confrontare: niente da togliere",
            **base,
        )

    # Quanta probabilita' sta sotto la classe dichiarata. E' l'unica
    # direzione che interessa: verso l'alto la valvola non agisce, quindi
    # un dubbio verso l'alto non e' un motivo per fermare niente.
    prob = base["probabilita"] or {letta: conf}
    sotto = sum(
        p for c, p in prob.items()
        if c in ORDINE and ORDINE[c] < ORDINE[dichiarata]
    )

    if ORDINE[letta] < ORDINE[dichiarata] and conf >= soglia:
        return Verdetto(
            stato=DECLASSA,
            motivo=(
                f"dichiarata '{dichiarata}', letta '{letta}' con confidenza "
                f"{conf:.2f}. La valvola scende, non sale."
            ),
            **base,
        )

    if sotto >= SOGLIA_DUBBIO:
        return Verdetto(
            stato=INCERTO,
            motivo=(
                f"il {sotto:.0%} della probabilita' sta sotto '{dichiarata}' "
                f"(vince '{letta}' con {conf:.2f}, non abbastanza per "
                "declassare). Decide una persona."
            ),
            **base,
        )

    # Anche quando Jev legge PIU' in alto del dichiarato, non succede
    # niente. E' il punto di tutto il file: la promozione non esiste.
    return Verdetto(
        stato=CONCORDE,
        motivo=(
            "niente da togliere. Concorde non vuol dire confermato: §7, un "
            "modello non e' una fonte indipendente."
        ),
        **base,
    )
