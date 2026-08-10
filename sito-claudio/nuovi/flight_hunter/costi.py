"""Modello del costo REALE — dove i comparatori barano per omissione.

Il prezzo del biglietto è solo una parte. Qui si sommano: bagagli, tratte via
terra per il posizionamento, notti forzate, e un margine di rischio per i
self-transfer (biglietti separati = nessuna protezione se perdi la coincidenza).
Tutte stime prudenziali, parametrizzabili.

Nota sulla stima a terra
────────────────────────
La formula generica (€/km con un minimo) descrive bene un treno regionale, ma
sottostima gli aeroporti low cost lontani dalla città di cui portano il nome:
là il collegamento è spesso una navetta in regime di monopolio, e il prezzo non
segue i chilometri. Charleroi dista ~50 km da Bruxelles — la formula darebbe
4,50 €, il minimo la porta a 8 €, la navetta ne costa fra 13,90 e 19.

Per questo esiste TRASFERIMENTI_NOTI: una tabella di prezzi verificati alla
fonte, con data, che scavalca la formula. Ogni voce va verificata davvero.
Meglio una tabella corta e vera che una lunga e inventata.
"""
from __future__ import annotations

from dataclasses import dataclass

# Navette aeroportuali in regime di monopolio: (minimo prenotando in anticipo,
# prezzo standard) in euro, per tratta, una persona.
# Chiave: codice IATA dell'aeroporto da raggiungere via terra.
TRASFERIMENTI_NOTI: dict[str, tuple[float, float]] = {
    # Flibco, Bruxelles ↔ Brussels South Charleroi. Verificato il 10/08/2026:
    # early booking da 13,90 €, tariffa standard ~19 €.
    "CRL": (13.90, 19.00),
    # Da aggiungere solo dopo verifica alla fonte, con la data nel commento:
    # "BVA" (Parigi Beauvais), "HHN" (Francoforte Hahn), "NRN" (Weeze)…
}


@dataclass(frozen=True)
class ParametriCosto:
    bagaglio_stiva: float = 30.0      # € per tratta-biglietto low cost
    notte: float = 35.0               # € ostello/guesthouse per notte forzata
    terra_eur_km: float = 0.09        # € al km per bus/treno regionale
    terra_minimo: float = 8.0         # € minimo di una tratta via terra (limite
                                      # inferiore: per gli aeroporti in
                                      # TRASFERIMENTI_NOTI vale il prezzo vero)
    margine_self_transfer: float = 15.0  # € accantonati per ogni coincidenza fai-da-te
    ore_minime_scalo: float = 3.0     # sotto questa soglia il rischio sale


def costo_terra(km: float, p: ParametriCosto = ParametriCosto(),
                iata: str | None = None) -> float:
    """Stima bus/treno per il posizionamento verso un altro aeroporto.

    Se `iata` è un aeroporto con navetta a prezzo noto, si usa la media fra
    tariffa anticipata e tariffa standard invece della formula chilometrica.
    """
    if km < 1:
        return 0.0
    noto = TRASFERIMENTI_NOTI.get(iata or "")
    if noto is not None:
        minimo, standard = noto
        return round((minimo + standard) / 2, 2)
    return round(max(p.terra_minimo, km * p.terra_eur_km), 2)


def intervallo_terra(km: float, p: ParametriCosto = ParametriCosto(),
                     iata: str | None = None) -> tuple[float, float]:
    """Estremi plausibili del costo a terra: (prenotando presto, tariffa piena).

    Per gli aeroporti non censiti i due estremi coincidono: non sappiamo di
    più, e fingere una forbice sarebbe peggio che ammettere un punto solo.
    """
    if km < 1:
        return (0.0, 0.0)
    noto = TRASFERIMENTI_NOTI.get(iata or "")
    if noto is not None:
        return noto
    stima = round(max(p.terra_minimo, km * p.terra_eur_km), 2)
    return (stima, stima)


def ore_terra(km: float) -> float:
    """Tempo stimato del trasferimento via terra (media 75 km/h porta a porta)."""
    return round(km / 75.0, 1) if km >= 1 else 0.0
