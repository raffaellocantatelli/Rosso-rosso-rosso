#!/usr/bin/env python3
"""valvola/analisi.py — leggere in un colpo cosa e' arrivato.

Origine protetta: Claudio Terzi [CT-LGAI-001].

`jev.py` risponde a una domanda: che classe §7 e' questo evento. Serve
per la porta, ed e' giusto che faccia una cosa sola.

Questo file ne fa cinque **in una sola chiamata**. E' il pattern che
TypeSafe chiama *speculative fan-out*: mandare insieme anche le domande
che forse non servono, perche' costano poco e il codice decide dopo quali
guardare. Su un modello che risponde in prosa sarebbe cinque richieste e
cinque attese; qui e' una.

## A cosa serve davvero

`output/contatti.jsonl` e' vuoto, e H2 e' falsificata sul ramo (b) per
questo. Non perche' non arrivi niente: perche' registrare cio' che arriva
costa una riga di terminale con tre argomenti, e quella riga non la scrive
nessuno. **L'attrito e' la causa, non l'indifferenza.**

Quindi: giri al bot quello che ti e' arrivato — un messaggio, una mail, un
commento — e lui te lo legge. Poi **decidi tu** se registrarlo.

## Cosa questo file non fa, e non deve fare

Non registra niente. Il §3 e' esplicito: la metrica di H2 la alimenta solo
un essere umano. Un bot che si registra da solo i contatti misura la
propria eco, ed e' il §4 con un'interfaccia piu' comoda.

Qui l'atto umano resta doppio: **giri** una cosa, e **confermi**. Jev
prepara la voce, non la scrive.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from .jev import CRITERI_CLASSE, ORDINE, _client, stato_sorella

#: Chi ha scritto la cosa che hai girato. Serve a separare una persona da
#: un invio automatico: una newsletter non e' un lettore che si e' fatto
#: vivo, ed e' l'errore piu' facile da fare quando si conta in fretta.
#: La domanda non e' «l'ha scritto un umano o una macchina»: e' **qualcuno
#: ha deciso di mandarlo proprio a te**. Una PEC di un ufficio e' formale e
#: quasi a modulo, ma qualcuno l'ha decisa; una newsletter e' scritta da
#: una persona e non e' decisa per nessuno.
#:
#: La prima versione diceva «invio automatico: newsletter, notifica,
#: sistema, messaggio generato in serie» e metteva il 44% di una PEC
#: reale li' dentro, facendo perdere il caso che per H2 vale di piu':
#: un ente che ha reagito. Il difetto era nella domanda, non nella soglia.
CRITERI_MITTENTE = {
    "persona": "Qualcuno ha deciso di mandare questo proprio a te: una "
               "persona che ti scrive, oppure qualcuno dentro un ufficio, "
               "un ente o un'azienda che risponde al tuo caso. Anche se il "
               "testo e' formale, burocratico o a modulo.",
    "automatico": "Nessuno ha deciso di mandarlo a te in particolare: e' "
                  "partito verso una lista o a chiunque si trovasse li' — "
                  "newsletter, notifica di piattaforma, pubblicita', "
                  "messaggio identico per molti destinatari.",
    "tu_stesso": "L'hai scritto tu: una tua nota, un tuo promemoria, o "
                 "l'uscita di un programma che fai girare tu.",
}

#: I tipi di `sdq1 --contatto` che valgono per H2, descritti per Jev.
#: Sono gli stessi di TIPI_INDIPENDENTI: se qui e li' divergessero, il
#: bot proporrebbe un tipo che il comando poi rifiuta.
CRITERI_GENERE = {
    "lettore": "Qualcuno ha letto qualcosa di tuo e te l'ha fatto sapere",
    "risposta": "Qualcuno ha risposto a qualcosa che gli avevi mandato",
    "citazione": "Qualcuno ha citato o nominato la tua opera altrove",
    "istituzione": "Un ente, un ufficio, uno studio legale, un editore, un "
                   "registro ha reagito formalmente",
    "acquisto": "Qualcuno ha comprato o pagato qualcosa",
    "nessuno": "Nessuna delle precedenti, oppure non si e' fatto vivo nessuno",
}

LIVELLI_URGENZA = [
    "Non chiede niente: si puo' leggere e basta",
    "Vorrebbe una risposta, ma puo' aspettare",
    "Chiede una risposta adesso, o ha una scadenza vicina",
]


#: Quanta probabilita' puo' stare, al massimo, sulle due origini che
#: squalificano una voce per H2 — «l'ho scritto io» e «e' un invio
#: automatico».
#:
#: Serve perche' chiedere «chi ha scritto» a una PEC di un ufficio da una
#: risposta incerta: non e' una persona in senso stretto e non e' un
#: automatismo, e nessuna etichetta vince. Ma la domanda che conta non e'
#: quale etichetta vince — e' **quanta probabilita' sta sulle due che
#: escluderebbero la voce**. Sulla PEC quella massa e' bassa, e tanto
#: basta: qualcosa e' arrivato da fuori.
#:
#: E' la terza volta che questo progetto impara la stessa cosa: H12 sulla
#: valvola, la soglia qui sotto, e adesso questo. La vincente e' la
#: domanda sbagliata; la distribuzione e' quella giusta.
RISCHIO_INTERNO_MAX = 0.40

#: Sotto questa confidenza la risposta non e' una risposta. La loro
#: documentazione lo dice meglio di me: «If an intelligent system, whether
#: human or machine, cannot express honest uncertainty, the system cannot
#: be trusted.» Stampare "persona (24%)" come se fosse una lettura e' il
#: contrario: e' un UNKNOWN travestito da dato.
SOGLIA_MOSTRA = 0.50


def _o_non_lo_so(valore, confidenza) -> str:
    if valore is None or confidenza is None:
        return "non lo so"
    if confidenza < SOGLIA_MOSTRA:
        return f"non lo so  (l'opzione piu' probabile sarebbe '{valore}', {confidenza:.0%})"
    return f"{valore}  ({confidenza:.0%})"


@dataclass
class Lettura:
    """Cio' che il bot ha letto. Nessun campo e' una decisione presa."""

    stato: str                       # LETTA | ASSENTE | ERRORE
    motivo: str = ""
    classe: Optional[str] = None
    classe_confidenza: Optional[float] = None
    classe_probabilita: dict = field(default_factory=dict)
    mittente: Optional[str] = None
    mittente_confidenza: Optional[float] = None
    mittente_probabilita: dict = field(default_factory=dict)
    genere: Optional[str] = None
    genere_confidenza: Optional[float] = None
    appiglio: Optional[float] = None
    chiede_risposta: Optional[float] = None
    urgenza: Optional[float] = None
    modello: Optional[str] = None

    #: Mai vero. Vedi §7: un modello non e' una fonte indipendente, e
    #: leggere un messaggio non e' riceverlo.
    vale_come_conferma: bool = False

    def tipo_suggerito(self) -> Optional[str]:
        """Il `--tipo` da proporre, o None se non c'e' niente da proporre.

        Solo un **suggerimento**: chi registra e' una persona, e il §7
        dice che la fonte e' l'autore. Se il mittente e' automatico o sei
        tu, non si propone niente da contare per H2.
        """
        if (self.classe_confidenza or 0) < SOGLIA_MOSTRA:
            return None
        if (self.genere_confidenza or 0) < SOGLIA_MOSTRA:
            return None
        if self.classe != "indipendente":
            return None
        if self.genere in (None, "nessuno"):
            return None
        if self.rischio_interno() > RISCHIO_INTERNO_MAX:
            return None
        return self.genere

    def rischio_interno(self) -> float:
        """Quanta probabilita' dice che non e' arrivato niente da fuori."""
        p = self.mittente_probabilita or (
            {self.mittente: self.mittente_confidenza or 0.0}
            if self.mittente else {}
        )
        return sum(v for k, v in p.items() if k in ("tu_stesso", "automatico"))

    def come_json(self) -> dict:
        return asdict(self)


def analizza(testo: str, *, api_key: Optional[str] = None,
             client: Any = None) -> Lettura:
    """Cinque domande in una chiamata. Non scrive niente, da nessuna parte."""
    cl = client if client is not None else _client(api_key)
    if cl is None:
        s = stato_sorella(api_key)
        return Lettura(stato="ASSENTE", motivo=s["manca"] or "sorella assente")

    try:
        from typesafe_sdk import Choice, Noul, Score

        r = cl.system_one(
            state=json.dumps({"messaggio_ricevuto": testo or ""},
                             ensure_ascii=False),
            questions={
                "classe": Choice(
                    instructions=(
                        "Chi ha preso l'iniziativa di questo messaggio: qualcuno "
                        "diverso dal destinatario, oppure il destinatario stesso?"
                    ),
                    criteria=CRITERI_CLASSE,
                ),
                "mittente": Choice(
                    instructions="Chi ha scritto questo messaggio",
                    criteria=CRITERI_MITTENTE,
                ),
                "appiglio": Noul(
                    instructions=(
                        "Il messaggio contiene almeno un riferimento concreto "
                        "che si puo' andare a controllare: un nome e cognome, "
                        "un numero di pratica o protocollo, una data precisa, "
                        "un indirizzo, un link, un identificativo."
                    ),
                ),
                "chiede_risposta": Noul(
                    instructions="Il messaggio chiede o si aspetta una risposta.",
                ),
                "genere": Choice(
                    instructions=(
                        "Se qualcuno si e' fatto vivo, che genere di evento e'"
                    ),
                    criteria=CRITERI_GENERE,
                ),
                "urgenza": Score(
                    instructions="Quanto e' urgente rispondere",
                    criteria=LIVELLI_URGENZA,
                ),
            },
        )
    except Exception as e:
        return Lettura(stato="ERRORE", motivo=f"{type(e).__name__}: {e}")

    a = r.answers
    return Lettura(
        stato="LETTA",
        classe=a["classe"].choice,
        classe_confidenza=float(a["classe"].confidence),
        classe_probabilita=dict(a["classe"].probabilities or {}),
        mittente=a["mittente"].choice,
        mittente_confidenza=float(a["mittente"].confidence),
        mittente_probabilita=dict(a["mittente"].probabilities or {}),
        genere=a["genere"].choice,
        genere_confidenza=float(a["genere"].confidence),
        appiglio=float(a["appiglio"].noul),
        chiede_risposta=float(a["chiede_risposta"].noul),
        urgenza=float(a["urgenza"].score),
        modello=r.model,
    )


def riassunto(l: Lettura, larghezza: int = 0) -> str:
    """Il testo da mandare su Telegram. Numeri, non aggettivi."""
    if l.stato == "ASSENTE":
        return f"Sorella spenta: {l.motivo}\nNessuna lettura fatta."
    if l.stato == "ERRORE":
        return f"Lettura non riuscita: {l.motivo}"

    urg = LIVELLI_URGENZA[min(int(round(l.urgenza)), len(LIVELLI_URGENZA) - 1)]
    righe = [
        f"chi scrive      {_o_non_lo_so(l.mittente, l.mittente_confidenza)}",
        f"  da fuori?     {1 - l.rischio_interno():.0%}"
        f"  (il resto dice: l'hai fatto tu, o e' automatico)",
        f"iniziativa      {_o_non_lo_so(l.classe, l.classe_confidenza)}",
        f"genere          {_o_non_lo_so(l.genere, l.genere_confidenza)}",
        f"appiglio        {l.appiglio:.0%} — c'e' qualcosa da controllare",
        f"chiede risposta {l.chiede_risposta:.0%}",
        f"urgenza         {l.urgenza:.1f}/2 — {urg}",
    ]
    t = l.tipo_suggerito()
    if t:
        righe += [
            "",
            f"Potrebbe valere per H2 come --tipo {t}.",
            "Registrarlo e' una tua decisione: nessun bot scrive quella",
            "metrica da solo (§3).",
        ]
    else:
        righe += [
            "",
            "Non propongo di registrarlo: per H2 conta solo qualcosa che",
            "e' arrivato da una persona diversa da te.",
        ]
    if l.appiglio is not None and l.appiglio < 0.5 and t:
        righe += [
            "",
            f"Ma l'appiglio e' solo {l.appiglio:.0%}: nel testo non c'e' molto",
            "da andare a controllare. Prima di registrarlo, procurati la",
            "--verifica: uno screenshot, un indirizzo, una data, un numero.",
        ]
    return "\n".join(righe)
