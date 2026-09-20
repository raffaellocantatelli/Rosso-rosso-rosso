"""La sentinella: un contatore che sale non e' qualcuno che e' arrivato.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Nessun test chiama GitHub. Quello che va provato non e' l'API — e' che
un evento prodotto dall'autore non finisca mai fra quelli che valgono
per H2, e che la sentinella non scriva niente.
"""

import json

import pytest

import sentinella


@pytest.fixture(autouse=True)
def mai_la_rete(monkeypatch):
    def vietato(*a, **k):
        raise AssertionError("un test ha provato a chiamare GitHub davvero")
    monkeypatch.setattr(sentinella.urllib.request, "urlopen", vietato)


def _risposte(forks=(), stelle=(), watcher=(), issue=()):
    def finto(percorso):
        if "/forks" in percorso:
            return [{"owner": {"login": l}, "created_at": "2026-09-19T00:00:00Z",
                     "html_url": f"https://github.com/{l}/x"} for l in forks]
        if "/stargazers" in percorso:
            return [{"login": l} for l in stelle]
        if "/subscribers" in percorso:
            return [{"login": l} for l in watcher]
        if "/issues" in percorso:
            return [{"user": {"login": l}, "created_at": "2026-09-19T00:00:00Z",
                     "html_url": f"https://github.com/x/{n}"}
                    for n, l in enumerate(issue)]
        return []
    return finto


def test_il_fork_dell_autore_non_vale(monkeypatch):
    """Il caso vero del 20/09: forks_count=1, e il fork era suo."""
    monkeypatch.setattr(sentinella, "_get", _risposte(forks=["Claudioterzi82"]))
    r = sentinella.guarda()
    assert r["esterni"] == []
    assert len(r["interni"]) == 1
    assert r["interni"][0]["perche_non_vale"] == "l'autore, secondo account"


def test_uno_sconosciuto_esce_come_esterno(monkeypatch):
    monkeypatch.setattr(sentinella, "_get", _risposte(stelle=["una-persona-vera"]))
    r = sentinella.guarda()
    assert len(r["esterni"]) == 1
    assert r["esterni"][0]["chi"] == "una-persona-vera"
    assert r["esterni"][0]["verifica"], "senza verifica la voce non serve a niente"


def test_il_confronto_non_dipende_dalle_maiuscole(monkeypatch):
    """GitHub restituisce 'Claudioterzi82'; la lista lo ha in minuscolo."""
    monkeypatch.setattr(sentinella, "_get", _risposte(forks=["CLAUDIOTERZI82"]))
    assert sentinella.guarda()["esterni"] == []


def test_non_scrive_niente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sentinella, "_get", _risposte(stelle=["qualcuno"]))
    sentinella.stampa(sentinella.guarda())
    assert list(tmp_path.iterdir()) == [], "la sentinella ha scritto su disco"


def test_uscita_3_solo_se_c_e_qualcuno_da_fuori(monkeypatch, capsys):
    monkeypatch.setattr(sentinella, "_get", _risposte(forks=["raffaellocantatelli"]))
    assert sentinella.stampa(sentinella.guarda()) == 0
    monkeypatch.setattr(sentinella, "_get", _risposte(forks=["estraneo"]))
    assert sentinella.stampa(sentinella.guarda()) == 3


def test_un_errore_di_rete_non_diventa_un_silenzio(monkeypatch):
    """Se non ho potuto guardare, deve dirlo: «zero esterni» e «non ho
    guardato» sono due cose diverse, e confonderle e' il §4."""
    monkeypatch.setattr(sentinella, "_get", lambda p: {"_errore": "HTTP 403"})
    r = sentinella.guarda()
    assert r["esterni"] == []
    assert len(r["errori"]) == 4, "ogni contatore non letto va dichiarato"


def test_i_tipi_proposti_sono_accettati_da_sdq1():
    from sdq1.__main__ import TIPI_INDIPENDENTI
    for genere, tipo in sentinella.TIPO.items():
        assert tipo in TIPI_INDIPENDENTI, f"{genere} proporrebbe --tipo {tipo}, rifiutato"


def test_la_lista_degli_interni_e_corta_ed_esplicita():
    """Ogni nome in piu' e' un modo per scartare un contatto vero."""
    assert len(sentinella.INTERNI) <= 8
    assert all(n == n.lower() for n in sentinella.INTERNI), "confronto in minuscolo"
    assert all(v for v in sentinella.INTERNI.values()), "ogni nome dice perche'"
