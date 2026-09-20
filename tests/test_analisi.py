"""Il bot che legge: /analizza, e la seconda porta chiusa.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Nessun test chiama TypeSafe per davvero. Quello che va provato qui non e'
il giudizio di Jev — e' che **il bot non registri niente da solo** e che
una risposta incerta non venga mostrata come una risposta.
"""

import json

import pytest

typesafe_sdk = pytest.importorskip("typesafe_sdk")
ChoiceAnswer = typesafe_sdk.ChoiceAnswer
NoulAnswer = typesafe_sdk.NoulAnswer
ScoreAnswer = typesafe_sdk.ScoreAnswer
SystemOneResponse = typesafe_sdk.SystemOneResponse

from valvola.analisi import (
    RISCHIO_INTERNO_MAX, SOGLIA_MOSTRA, Lettura, analizza, riassunto,
)


@pytest.fixture(autouse=True)
def mai_la_rete(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)

    def vietato(*a, **k):
        raise AssertionError("un test ha provato a chiamare TypeSafe davvero")

    monkeypatch.setattr(typesafe_sdk, "TypeSafeClient", vietato)


def finto(classe=("indipendente", 0.95), mittente=("persona", 0.95),
          genere=("lettore", 0.95), appiglio=0.9, risposta=0.8, urgenza=1.0,
          mittente_prob=None):
    class C:
        def system_one(self, state, questions, **kw):
            return SystemOneResponse(
                model="jev-latest",
                usage={"input_tokens": 1, "output_tokens": 1},
                answers={
                    "classe": ChoiceAnswer(type="choice", choice=classe[0],
                                           confidence=classe[1],
                                           probabilities={classe[0]: classe[1]}),
                    "mittente": ChoiceAnswer(
                        type="choice", choice=mittente[0], confidence=mittente[1],
                        probabilities=mittente_prob or {mittente[0]: mittente[1]}),
                    "genere": ChoiceAnswer(type="choice", choice=genere[0],
                                           confidence=genere[1],
                                           probabilities={genere[0]: genere[1]}),
                    "appiglio": NoulAnswer(type="noul", noul=appiglio),
                    "chiede_risposta": NoulAnswer(type="noul", noul=risposta),
                    "urgenza": ScoreAnswer(type="score", score=urgenza,
                                           confidence=0.9, legend={}, probabilities={}),
                },
            )
    return C()


# --- niente viene mai registrato ------------------------------------------

def test_analizza_non_scrive_niente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    analizza("un messaggio", client=finto())
    assert list(tmp_path.iterdir()) == [], "analizza ha scritto su disco"


def test_vale_come_conferma_sempre_falso():
    for c in (finto(), finto(mittente=("tu_stesso", 0.99))):
        assert analizza("x", client=c).vale_come_conferma is False
    assert analizza("x").vale_come_conferma is False   # senza chiave


# --- l'incertezza si vede ---------------------------------------------------

def test_una_risposta_incerta_non_viene_mostrata_come_risposta():
    """Trovato eseguendo sull'API vera: una nota a se stesso usciva come
    'persona (24%)', cioe' un lancio di moneta stampato come lettura."""
    l = analizza("x", client=finto(mittente=("persona", 0.24)))
    t = riassunto(l)
    assert "non lo so" in t
    assert "persona  (24%)" not in t


def test_sotto_soglia_non_si_propone_niente():
    l = analizza("x", client=finto(genere=("lettore", SOGLIA_MOSTRA - 0.01)))
    assert l.tipo_suggerito() is None


# --- la massa, non l'etichetta vincente ------------------------------------

def test_una_pec_passa_anche_se_nessuna_etichetta_vince():
    """Il caso vero che la prima versione perdeva: un ufficio che risponde
    non e' 'una persona' in senso stretto, nessuna etichetta vince, ma la
    probabilita' che sia tua o automatica e' bassa. Conta quella."""
    l = analizza("x", client=finto(
        mittente=("persona", 0.33), genere=("istituzione", 0.94),
        mittente_prob={"persona": 0.80, "automatico": 0.15, "tu_stesso": 0.05},
    ))
    assert l.rischio_interno() == pytest.approx(0.20)
    assert l.tipo_suggerito() == "istituzione"


def test_una_newsletter_non_si_propone():
    l = analizza("x", client=finto(
        genere=("nessuno", 0.9),
        mittente_prob={"automatico": 0.98, "persona": 0.02},
    ))
    assert l.rischio_interno() > RISCHIO_INTERNO_MAX
    assert l.tipo_suggerito() is None


def test_il_genere_proposto_e_un_tipo_che_sdq1_accetta():
    from sdq1.__main__ import TIPI_INDIPENDENTI
    from valvola.analisi import CRITERI_GENERE
    for g in CRITERI_GENERE:
        if g == "nessuno":
            continue
        assert g in TIPI_INDIPENDENTI, f"il bot proporrebbe --tipo {g}, che sdq1 rifiuta"


# --- la seconda porta -------------------------------------------------------

def test_registra_contatto_e_fermato_dalla_valvola(tmp_path, monkeypatch):
    """Fino al 20/09 il bot scriveva nella metrica di H2 senza controlli,
    mentre il comando CLI li aveva: due porte, una sola con la serratura."""
    import valvola
    import autonomous_core_v3 as ac
    from valvola.jev import DECLASSA, Verdetto

    monkeypatch.setattr(ac, "CONTATTI_FILE", str(tmp_path / "contatti.jsonl"))
    monkeypatch.setattr(valvola, "controlla", lambda *a, **k: Verdetto(
        stato=DECLASSA, motivo="finto", classe_dichiarata="indipendente",
        classe_letta="trasmissione", confidenza=0.99))

    with pytest.raises(ac.ValvolaHaFermato):
        ac.registra_contatto("lettore", "n", "v")
    assert not (tmp_path / "contatti.jsonl").exists()

    voce = ac.registra_contatto("lettore", "n", "v", forza=True)
    assert voce["valvola_scavalcata"] is True
    assert voce["valvola"]["vale_come_conferma"] is False


def test_le_due_porte_usano_la_stessa_mappa_sette():
    import autonomous_core_v3 as ac
    from sdq1.__main__ import classe_sette, TIPI_INDIPENDENTI, TIPI_TRASMISSIONE, TIPI_INTERNI
    for t in list(TIPI_INDIPENDENTI) + list(TIPI_TRASMISSIONE) + list(TIPI_INTERNI):
        assert ac._classe_sette(t) == classe_sette(t), f"le due porte divergono su {t}"
