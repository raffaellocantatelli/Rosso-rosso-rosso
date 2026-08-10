"""Il costo a terra è il perno della tesi di Flight Hunter.

Se questo numero è sbagliato, «il prezzo minimo reale» non è reale. Questi
test bloccano le due regressioni che contano: che la formula chilometrica
torni a mangiarsi i prezzi verificati, e che il responso torni a dichiarare
un numero secco dove esiste una forbice.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from flight_hunter.costi import (  # noqa: E402
    TRASFERIMENTI_NOTI,
    ParametriCosto,
    costo_terra,
    intervallo_terra,
)
from flight_hunter.motore import MetaPossibile  # noqa: E402
from flight_hunter.oracolo import _intervallo_totale, _prezzo_testo  # noqa: E402


def _meta(da: str, prezzo_volo: float, c_terra: float) -> MetaPossibile:
    return MetaPossibile(
        iata="MAN", nome="Manchester", paese="Regno Unito", da=da,
        prezzo_volo=prezzo_volo, costo_terra=c_terra, costo_bagagli=0.0,
        totale=round(prezzo_volo + c_terra, 2), giorno="2026-09-04",
    )


# ── la formula generica ──────────────────────────────────────────────────

def test_stessa_citta_non_costa_nulla():
    assert costo_terra(0.0) == 0.0
    assert intervallo_terra(0.0) == (0.0, 0.0)


def test_tratta_lunga_segue_i_chilometri():
    p = ParametriCosto()
    assert costo_terra(300.0, p) == round(300.0 * p.terra_eur_km, 2)


def test_tratta_corta_sconosciuta_usa_il_minimo():
    p = ParametriCosto()
    # 50 km × 0,09 = 4,50 €, sotto il minimo: deve restituire il minimo.
    assert costo_terra(50.0, p, "ZZZ") == p.terra_minimo


# ── i prezzi verificati scavalcano la formula ────────────────────────────

def test_charleroi_usa_il_prezzo_verificato_non_la_formula():
    p = ParametriCosto()
    generico = costo_terra(50.0, p)
    reale = costo_terra(50.0, p, "CRL")
    assert reale > generico, "la navetta di Charleroi costa piu' del minimo generico"
    minimo, standard = TRASFERIMENTI_NOTI["CRL"]
    assert reale == round((minimo + standard) / 2, 2)


def test_intervallo_charleroi_ha_due_estremi_distinti():
    basso, alto = intervallo_terra(50.0, iata="CRL")
    assert basso < alto
    assert (basso, alto) == TRASFERIMENTI_NOTI["CRL"]


def test_aeroporto_sconosciuto_non_finge_una_forbice():
    basso, alto = intervallo_terra(50.0, iata="ZZZ")
    assert basso == alto


def test_il_prezzo_noto_non_si_applica_se_sei_gia_li():
    # km < 1 significa che l'aeroporto e' quello di casa: nessun trasferimento.
    assert costo_terra(0.0, iata="CRL") == 0.0


# ── il responso dell'Oracolo ─────────────────────────────────────────────

def test_responso_dichiara_la_forbice_su_charleroi():
    m = _meta("CRL", 14.99, costo_terra(50.0, iata="CRL"))
    testo = _prezzo_testo(m)
    assert "–" in testo, f"atteso un intervallo, ottenuto {testo!r}"
    assert "navetta" in testo
    basso, alto = _intervallo_totale(m)
    assert basso == round(14.99 + TRASFERIMENTI_NOTI["CRL"][0], 2)
    assert alto == round(14.99 + TRASFERIMENTI_NOTI["CRL"][1], 2)


def test_responso_resta_un_numero_secco_dove_non_sappiamo():
    m = _meta("ZZZ", 14.99, 8.0)
    testo = _prezzo_testo(m)
    assert "–" not in testo
    assert _intervallo_totale(m) == (m.totale, m.totale)


def test_il_totale_reale_supera_la_vecchia_stima():
    """La correzione deve alzare il prezzo, non abbassarlo: era questo il punto."""
    vecchio = round(14.99 + 8.0, 2)          # com'era prima: 22,99 €
    nuovo = round(14.99 + costo_terra(50.0, iata="CRL"), 2)
    assert nuovo > vecchio
