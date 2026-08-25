"""Lo strumento vale solo se avrebbe suonato prima.

L'ipotesi che giustifica latenza.py è: il fallimento dei 23 giorni di Stub non
fu di rilevamento — il rilevamento era perfetto, 25 letture su 25 — ma di
conseguenza. Falsificabile in modo secco: se applicato ai dati reali troncati
al terzo giorno lo strumento non segnala niente, non aggiunge nulla a ciò che
health_log già diceva, e va buttato.

    python test_latenza.py     # oppure: pytest
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import latenza  # noqa: E402

REALE = pathlib.Path(__file__).resolve().parent / "output" / "health_log.jsonl"


def _log(tmp_path, letture):
    """letture: lista di (data_iso, [provider reali disponibili])."""
    p = tmp_path / "health.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for data, reali in letture:
            providers = {n: {"disponibile": n in reali, "circuito_aperto": False}
                         for n in ("anthropic", "gemini", "deepseek", "ollama")}
            providers["stub"] = {"disponibile": True, "circuito_aperto": False}
            f.write(json.dumps({"data_iso": data, "providers": providers}) + "\n")
    latenza.HEALTH = str(p)
    latenza.CONTATTI = str(tmp_path / "contatti-inesistenti.jsonl")
    return p


def test_avrebbe_suonato_al_terzo_giorno(tmp_path):
    """La prova, sui dati veri: troncato al terzo check, lo strumento segnala."""
    righe_vere = REALE.read_text(encoding="utf-8").strip().splitlines()
    p = tmp_path / "health.jsonl"
    p.write_text("\n".join(righe_vere[:3]) + "\n", encoding="utf-8")
    latenza.HEALTH = str(p)
    latenza.CONTATTI = str(tmp_path / "niente.jsonl")

    r = latenza.rapporto(soglia=3)
    assert r, "al terzo giorno non segnala: lo strumento non aggiunge niente, va buttato"
    assert r[0]["lettura"] == "nessun provider reale"
    assert r[0]["dal"] == "2026-07-31" and r[0]["ancora_in_corso"]


def test_sui_dati_veri_completi_trova_i_23_giorni(tmp_path):
    latenza.HEALTH = str(REALE)
    latenza.CONTATTI = str(tmp_path / "niente.jsonl")
    r = latenza.rapporto(soglia=3)
    assert len(r) == 1
    assert r[0]["rilevazioni"] == 25 and r[0]["giorni"] == 23


def test_una_lettura_che_cambia_spezza_la_serie(tmp_path):
    """Se qualcosa cambia, la serie si chiude: è il caso che NON deve allarmare."""
    _log(tmp_path, [
        ("2026-07-31T10:00:00Z", []),
        ("2026-08-01T10:00:00Z", []),
        ("2026-08-02T10:00:00Z", ["anthropic"]),
        ("2026-08-03T10:00:00Z", ["anthropic"]),
    ])
    assert latenza.rapporto(soglia=3) == [], "serie spezzata segnalata comunque"

    r = latenza.rapporto(soglia=2)
    assert len(r) == 2
    assert [x["ancora_in_corso"] for x in r] == [False, True], "solo l'ultima serie è in corso"


def test_soglia_rispettata(tmp_path):
    _log(tmp_path, [(f"2026-08-0{i}T10:00:00Z", []) for i in range(1, 4)])
    assert latenza.rapporto(soglia=4) == []
    assert len(latenza.rapporto(soglia=3)) == 1


def test_registro_vuoto_non_esplode(tmp_path):
    latenza.HEALTH = str(tmp_path / "non-esiste.jsonl")
    latenza.CONTATTI = str(tmp_path / "nemmeno.jsonl")
    assert latenza.rapporto() == []


def test_contatti_vuoti_segnalati_solo_col_registro(tmp_path):
    """Il ramo (b) di H2 si misura in giorni solo se c'è un orologio: il health log."""
    contatti = tmp_path / "contatti.jsonl"
    contatti.write_text("", encoding="utf-8")
    _log(tmp_path, [(f"2026-08-0{i}T10:00:00Z", []) for i in range(1, 4)])
    latenza.CONTATTI = str(contatti)
    fonti = [r["fonte"] for r in latenza.rapporto(soglia=3)]
    assert any("contatti" in f for f in fonti), "contatti.jsonl vuoto non segnalato"


if __name__ == "__main__":
    import tempfile

    h, c = latenza.HEALTH, latenza.CONTATTI
    falliti = 0
    for nome, funzione in sorted(globals().items()):
        if not nome.startswith("test_"):
            continue
        with tempfile.TemporaryDirectory() as d:
            try:
                funzione(pathlib.Path(d))
                print(f"ok    {nome}")
            except AssertionError as e:
                falliti += 1
                print(f"FALLITO {nome}: {e}")
            finally:
                latenza.HEALTH, latenza.CONTATTI = h, c
    print(f"\n{falliti} falliti" if falliti else "\nTutti i test passano.")
    sys.exit(1 if falliti else 0)
