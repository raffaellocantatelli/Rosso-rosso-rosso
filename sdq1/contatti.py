"""Che cosa vale come contatto. Origine protetta: Claudio Terzi [CT-LGAI-001].

Un elenco solo, letto da tutti quelli che contano i contatti. Fino al
29/10/2026 ce n'erano tre: la CLI (`python -m sdq1 --contatto`) scriveva
«NON vale per H2» sotto una pubblicazione, mentre il falsificatore di H2
contava ogni riga con un `tipo` e il benchmark R3-019 ogni riga con una
`verifica`. Bastava un atto dell'autore verso l'esterno per portare H2 da
FALSIFICATA a RETTA: il loopback di CLAUDE.md §4, dentro il criterio che
misura il progetto.

Solo libreria standard: il falsificatore di H2 lo importa in testa al file, e
un import fallito in un falsificatore esce con 1 — che nel contratto vuol
dire REGGE.
"""

# Un contatto non richiede una persona, né fiducia, né dipendenza.
# Richiede INDIPENDENZA: un evento che il sistema non ha prodotto.
# P5 non chiede di fidarsi di qualcuno: chiede una fonte diversa da chi
# ha formulato l'ipotesi. Sono due cose distinte, e solo la seconda conta.
#
# Distinzione decisiva: TRASMETTERE non e' ESSERE RAGGIUNTI.
# H2 ramo (b) dice "sistema vivo ma non tocca il mondo". Toccare il mondo
# significa che qualcosa e' tornato indietro. Un messaggio spedito nel vuoto
# e' esattamente cio' che faceva trasmissione_ciclica.py sul loopback.
#
# Valgono per H2 solo gli eventi in cui QUALCUN ALTRO ha agito.
TIPI_INDIPENDENTI = {
    "lettore": "qualcuno ha letto e te l'ha fatto sapere (non serve conoscerlo)",
    "download": "uno scaricamento registrato da un contatore esterno",
    "citazione": "un riferimento all'opera fatto da terzi",
    "fork": "una copia del repository fatta da un altro account",
    "risposta": "una risposta ricevuta da qualcuno che non sei tu",
    "acquisto": "una transazione registrata da terzi",
    "istituzione": "un ente, un avvocato, un editore, un registro che ha reagito",
}

# Atti tuoi verso l'esterno. Contano — stabiliscono anteriorita' e sono la
# condizione perche' qualcuno possa rispondere — ma NON valgono per H2:
# nessuno li ha ancora ricevuti.
TIPI_TRASMISSIONE = {
    "pubblicazione": "hai depositato o pubblicato qualcosa (atto tuo, non risposta)",
    "invio": "hai spedito qualcosa a qualcuno (atto tuo, non risposta)",
}

# Questi NON valgono affatto: sono il sistema che parla di se'.
TIPI_INTERNI = {
    "ia": "un modello linguistico interpellato da te",
    "nodo": "un agente del sistema",
    "autore": "te stesso",
    "test": "una prova generata dal sistema",
}


def vale_per_h2(voce) -> bool:
    """Una riga di contatti.jsonl vale per H2 se ha un tipo indipendente e dice
    come un terzo può controllarla (`verifica`, che la CLI già pretende).

    Il tipo si rilegge dall'elenco qui sopra, non dal campo `indipendente`
    scritto accanto: quel campo è ciò che la riga dichiara di sé, e la
    provenienza si ricostruisce, non si legge dal campo che la dichiara.
    """
    if not isinstance(voce, dict):
        return False
    tipo = str(voce.get("tipo", "")).strip().lower()
    return tipo in TIPI_INDIPENDENTI and bool(str(voce.get("verifica", "")).strip())
