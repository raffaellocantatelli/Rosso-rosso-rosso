"""P6 deve reggere anche quando il campo è pieno.

Il registro rifiutava solo il criterio vuoto. Un segnaposto («Da definire...»)
passava il controllo, e H1 — che per CLAUDE.md §3 «non ha ancora un criterio di
falsificazione» — poteva essere confermata. Questi test bloccano quel ritorno,
e il secondo buco della stessa serratura: uno stato non canonico ("confermata")
che non veniva confrontato con CONFERMATA e scavalcava il controllo del tutto.

    python test_registro_ipotesi.py      # oppure: pytest test_registro_ipotesi.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import registro_ipotesi as reg  # noqa: E402


def _registro_isolato(tmp_path, ipotesi):
    """Punta il modulo a un registro usa-e-getta: i test non toccano quello vero."""
    percorso = tmp_path / "registro_test.json"
    percorso.write_text(json.dumps(ipotesi, ensure_ascii=False), encoding="utf-8")
    reg.REGISTRO_PATH = str(percorso)
    return percorso


def _ipotesi(criterio, stato=reg.APERTA):
    return [{"id": "HX", "testo": "ipotesi di prova", "stato": stato,
             "criterio_falsificazione": criterio, "scadenza": None}]


def test_segnaposto_non_e_un_criterio():
    assert not reg.criterio_definito(reg.CRITERIO_DA_DEFINIRE)
    assert not reg.criterio_definito("")
    assert not reg.criterio_definito("   ")
    assert not reg.criterio_definito("TBD")
    assert not reg.criterio_definito("-")
    assert not reg.criterio_definito("Criterio da stabilire in seguito")


def test_criterio_reale_e_accettato():
    assert reg.criterio_definito(
        "Falsificata se output/contatti.jsonl ha zero voci valide al 2026-12-11."
    )
    for h in reg.IPOTESI_INIZIALI:
        if h["id"] in ("H2", "H3"):
            assert reg.criterio_definito(h["criterio_falsificazione"]), h["id"]


def test_conferma_rifiutata_senza_criterio(tmp_path):
    percorso = _registro_isolato(tmp_path, _ipotesi(reg.CRITERIO_DA_DEFINIRE))
    try:
        reg.aggiorna_stato("HX", reg.CONFERMATA)
    except ValueError as e:
        assert "P6" in str(e)
    else:
        raise AssertionError("P6 non applicato: confermata un'ipotesi senza criterio")
    # Il rifiuto non deve lasciare il registro a metà.
    assert json.loads(percorso.read_text(encoding="utf-8"))[0]["stato"] == reg.APERTA


def test_falsificare_resta_sempre_possibile(tmp_path):
    """P6 blocca la conferma, non la smentita: si può sempre chiudere in negativo."""
    _registro_isolato(tmp_path, _ipotesi(reg.CRITERIO_DA_DEFINIRE))
    assert reg.aggiorna_stato("HX", reg.FALSIFICATA)[0]["stato"] == reg.FALSIFICATA


def test_stato_non_canonico_rifiutato(tmp_path):
    """"confermata" non è CONFERMATA: senza questo controllo aggirava P6."""
    percorso = _registro_isolato(tmp_path, _ipotesi(reg.CRITERIO_DA_DEFINIRE))
    try:
        reg.aggiorna_stato("HX", "confermata")
    except ValueError as e:
        assert "Stato sconosciuto" in str(e)
    else:
        raise AssertionError("stato non canonico accettato: P6 aggirabile")
    assert json.loads(percorso.read_text(encoding="utf-8"))[0]["stato"] == reg.APERTA


def test_aggiungi_rifiuta_il_segnaposto(tmp_path):
    _registro_isolato(tmp_path, [])
    for criterio in ("", "   ", "TODO", reg.CRITERIO_DA_DEFINIRE):
        try:
            reg.aggiungi("HY", "ipotesi nuova", criterio)
        except ValueError as e:
            assert "P6" in str(e)
        else:
            raise AssertionError(f"criterio accettato ma non dichiarato: {criterio!r}")


def test_definisci_criterio_riempie_il_vuoto(tmp_path):
    """Il caso H1: l'ipotesi c'è, il criterio no, e finora non c'era modo di scriverlo."""
    percorso = _registro_isolato(tmp_path, _ipotesi(reg.CRITERIO_DA_DEFINIRE))
    reale = "Falsificata se in un test cieco il criterio non regge su dati nuovi."
    reg.definisci_criterio("HX", reale)
    assert json.loads(percorso.read_text(encoding="utf-8"))[0]["criterio_falsificazione"] == reale
    # Con un criterio vero, P6 non blocca più la conferma. Resta P5, che prima
    # non era applicato: e' il varco da cui H3 e' rimasta CONFERMATA per
    # settimane senza che nessuno avesse verificato niente (riconciliazione
    # dei due rami del 25/08).
    try:
        reg.aggiorna_stato("HX", reg.CONFERMATA)
        assert False, "P5 non applicato: conferma senza fonte esterna"
    except ValueError as errore:
        assert "P5" in str(errore) and "P6" not in str(errore)
    assert reg.aggiorna_stato(
        "HX", reg.CONFERMATA, prova_esterna="verifica di un terzo, 2026-09-01"
    )[0]["stato"] == reg.CONFERMATA


def test_definisci_criterio_non_riscrive(tmp_path):
    """Un bersaglio che si sposta non è un bersaglio."""
    gia = "Falsificata se il contatore resta a zero al 2026-12-11."
    percorso = _registro_isolato(tmp_path, _ipotesi(gia))
    try:
        reg.definisci_criterio("HX", "Falsificata se qualcosa di molto piu comodo.")
    except ValueError as e:
        assert "sposta il bersaglio" in str(e)
    else:
        raise AssertionError("criterio riscritto: il bersaglio si è spostato")
    assert json.loads(percorso.read_text(encoding="utf-8"))[0]["criterio_falsificazione"] == gia


def test_definisci_criterio_rifiuta_segnaposto(tmp_path):
    _registro_isolato(tmp_path, _ipotesi(reg.CRITERIO_DA_DEFINIRE))
    try:
        reg.definisci_criterio("HX", "da definire meglio piu avanti")
    except ValueError as e:
        assert "P6" in str(e)
    else:
        raise AssertionError("segnaposto accettato come criterio")


def test_definisci_criterio_non_giustifica_a_posteriori(tmp_path):
    """Dare un criterio a un verdetto già emesso è scrivere la scommessa dopo la corsa."""
    _registro_isolato(tmp_path, _ipotesi(reg.CRITERIO_DA_DEFINIRE, stato=reg.FALSIFICATA))
    try:
        reg.definisci_criterio("HX", "Falsificata se il contatore resta a zero.")
    except ValueError as e:
        assert "a posteriori" in str(e)
    else:
        raise AssertionError("criterio scritto a verdetto già emesso")


def test_ipotesi_sconosciuta(tmp_path):
    _registro_isolato(tmp_path, _ipotesi("Falsificata se il contatore resta a zero."))
    try:
        reg.aggiorna_stato("H-inesistente", reg.CONFERMATA)
    except KeyError:
        pass
    else:
        raise AssertionError("ipotesi inesistente aggiornata senza errore")


if __name__ == "__main__":
    import tempfile

    originale = reg.REGISTRO_PATH
    falliti = 0
    for nome, funzione in sorted(globals().items()):
        if not nome.startswith("test_"):
            continue
        with tempfile.TemporaryDirectory() as d:
            try:
                if funzione.__code__.co_argcount:
                    funzione(pathlib.Path(d))
                else:
                    funzione()
                print(f"ok    {nome}")
            except AssertionError as e:
                falliti += 1
                print(f"FALLITO {nome}: {e}")
            finally:
                reg.REGISTRO_PATH = originale
    print(f"\n{falliti} falliti" if falliti else "\nTutti i test passano.")
    sys.exit(1 if falliti else 0)
