"""Il registro deve accettare la piastra e rifiutare la scorciatoia.

Fleming nel 1928 non aveva un criterio di falsificazione: sotto le regole del
Registro Ipotesi la sua osservazione sarebbe stata respinta. Questi test
bloccano i due modi di sbagliare in direzioni opposte — pretendere il criterio
prima del fenomeno (si butta la piastra), e lasciar diventare tesi
un'osservazione senza criterio (si salta Oxford e i topi).

    python test_registro_osservazioni.py     # oppure: pytest
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import registro_osservazioni as oss  # noqa: E402
import registro_ipotesi as reg  # noqa: E402


def _isolato(tmp_path):
    oss.PERCORSO = str(tmp_path / "osservazioni.jsonl")
    return pathlib.Path(oss.PERCORSO)


def test_anomalia_senza_criterio_e_accettata(tmp_path):
    """Il caso Fleming: nessuna tesi, nessun criterio, solo una piastra strana."""
    _isolato(tmp_path)
    record = oss.annota(
        "Attorno alla muffa che ha contaminato la piastra gli stafilococchi sono morti.",
        "Non mi aspettavo che una contaminazione uccidesse la coltura invece di invaderla.",
    )
    assert record["id"] == "OSS-0001"
    stato = oss.stato_corrente()
    assert len(stato) == 1 and stato[0]["ipotesi"] == []


def test_serve_dire_perche_e_strano(tmp_path):
    """Senza la mente preparata la riga è rumore, e fra un anno non si distingue."""
    _isolato(tmp_path)
    for cosa, strano in [("qualcosa", ""), ("qualcosa", "   "), ("", "strano")]:
        try:
            oss.annota(cosa, strano)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accettata osservazione muta: {cosa!r} / {strano!r}")


def test_append_only(tmp_path):
    """Un'osservazione che si può ritoccare dopo è un ricordo, non una prova (§4)."""
    percorso = _isolato(tmp_path)
    oss.annota("prima cosa vista", "non me l'aspettavo per niente")
    prima = percorso.read_text(encoding="utf-8")
    oss.annota("seconda cosa vista", "non me l'aspettavo nemmeno questa")
    dopo = percorso.read_text(encoding="utf-8")
    assert dopo.startswith(prima), "una riga già scritta è stata modificata"
    assert len(dopo.strip().splitlines()) == 2
    # nessuna via d'uscita nell'API pubblica
    for vietato in ("modifica", "cancella", "elimina", "riscrivi", "aggiorna"):
        assert not hasattr(oss, vietato), f"esiste {vietato}(): il registro non è più append-only"


def test_ids_progressivi(tmp_path):
    _isolato(tmp_path)
    assert [oss.annota(f"cosa {i}", f"strano perché {i} non era previsto")["id"] for i in range(3)] == [
        "OSS-0001", "OSS-0002", "OSS-0003",
    ]


def test_collegamento_richiede_ipotesi_con_criterio(tmp_path, monkeypatch=None):
    """Il confine: la piastra è libera, la tesi che ne ricavi deve dichiarare i topi."""
    _isolato(tmp_path)
    o = oss.annota("una cosa che non torna", "devia da quello che mi aspettavo")

    registro = tmp_path / "ipotesi.json"
    registro.write_text(json.dumps([
        {"id": "HSENZA", "testo": "senza criterio", "stato": "APERTA",
         "criterio_falsificazione": reg.CRITERIO_DA_DEFINIRE, "scadenza": None},
        {"id": "HCON", "testo": "con criterio", "stato": "APERTA",
         "criterio_falsificazione": "Falsificata se i topi trattati muoiono come i controlli.",
         "scadenza": None},
    ], ensure_ascii=False), encoding="utf-8")
    originale = reg.REGISTRO_PATH
    reg.REGISTRO_PATH = str(registro)
    try:
        try:
            oss.collega(o["id"], "HSENZA")
        except ValueError as e:
            assert "falsificata" in str(e).lower()
        else:
            raise AssertionError("collegata un'ipotesi senza criterio: saltati Oxford e i topi")

        try:
            oss.collega(o["id"], "HMAI")
        except KeyError:
            pass
        else:
            raise AssertionError("collegata un'ipotesi inesistente")

        oss.collega(o["id"], "HCON")
        assert oss.stato_corrente()[0]["ipotesi"] == ["HCON"]
        oss.collega(o["id"], "HCON")  # idempotente nella ricostruzione
        assert oss.stato_corrente()[0]["ipotesi"] == ["HCON"]
    finally:
        reg.REGISTRO_PATH = originale


def test_osservazione_inesistente(tmp_path):
    _isolato(tmp_path)
    try:
        oss.collega("OSS-9999", "H2")
    except KeyError:
        pass
    else:
        raise AssertionError("collegata un'osservazione inesistente")


def test_riga_corrotta_non_passa_in_silenzio(tmp_path):
    percorso = _isolato(tmp_path)
    oss.annota("cosa buona", "strano perché non previsto")
    percorso.write_text(percorso.read_text(encoding="utf-8") + "{non json\n", encoding="utf-8")
    try:
        oss.stato_corrente()
    except ValueError as e:
        assert "riga 2" in str(e)
    else:
        raise AssertionError("riga corrotta ignorata: il registro mentirebbe per omissione")


if __name__ == "__main__":
    import tempfile

    p_oss, p_reg = oss.PERCORSO, reg.REGISTRO_PATH
    falliti = 0
    for nome, funzione in sorted(globals().items()):
        if not nome.startswith("test_"):
            continue
        with tempfile.TemporaryDirectory() as d:
            try:
                funzione(pathlib.Path(d)) if funzione.__code__.co_argcount else funzione()
                print(f"ok    {nome}")
            except AssertionError as e:
                falliti += 1
                print(f"FALLITO {nome}: {e}")
            finally:
                oss.PERCORSO, reg.REGISTRO_PATH = p_oss, p_reg
    print(f"\n{falliti} falliti" if falliti else "\nTutti i test passano.")
    sys.exit(1 if falliti else 0)
