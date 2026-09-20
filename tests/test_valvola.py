"""La valvola: puo' declassare, non puo' promuovere.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Questi test non chiamano l'API di TypeSafe. Verificano la sola cosa che
deve valere anche quando la sorella risponde male: che **nessun percorso
dentro valvola/ faccia salire una voce**. Il comportamento della rete
resta UNKNOWN finche' non c'e' una chiave, e i test lo dicono invece di
fingere il contrario.
"""

import json

import pytest

typesafe_sdk = pytest.importorskip(
    "typesafe_sdk", reason="pip install typesafe-sdk — senza SDK non c'e' niente da provare"
)
ChoiceAnswer = typesafe_sdk.ChoiceAnswer
NoulAnswer = typesafe_sdk.NoulAnswer
SystemOneResponse = typesafe_sdk.SystemOneResponse

from valvola.jev import (
    ASSENTE, CONCORDE, DECLASSA, ERRORE, INCERTO, ORDINE, controlla, stato_sorella,
)


class FintoClient:
    """Risponde cio' che gli si dice, e ricorda cosa ha ricevuto."""

    def __init__(self, classe, confidenza, noul=0.9, probabilita=None):
        self.classe, self.confidenza, self.noul = classe, confidenza, noul
        self.probabilita = probabilita or {classe: confidenza}
        self.visto = None

    def system_one(self, state, questions, **kw):
        self.visto = {"state": state, "questions": questions}
        return SystemOneResponse(
            model="jev-latest",
            usage={"input_tokens": 1, "output_tokens": 1},
            answers={
                "classe": ChoiceAnswer(
                    type="choice", choice=self.classe,
                    confidence=self.confidenza, probabilities=self.probabilita,
                ),
                "verificabile": NoulAnswer(type="noul", noul=self.noul),
            },
        )


class ClientRotto:
    def system_one(self, state, questions, **kw):
        raise RuntimeError("rete giu'")


# --- la garanzia centrale --------------------------------------------------

@pytest.mark.parametrize("letta,dichiarata", [
    ("indipendente", "trasmissione"),
    ("indipendente", "interno"),
    ("trasmissione", "interno"),
])
def test_non_promuove_mai(letta, dichiarata):
    """Jev legge PIU' in alto del dichiarato: non deve succedere niente.

    E' il §7 reso impossibile da violare: un modello non puo' far salire
    una voce verso 'vale per H2', con nessuna confidenza.
    """
    v = controlla("x", "y", dichiarata, client=FintoClient(letta, 0.99))
    assert v.stato == CONCORDE
    assert not v.blocca()
    assert v.classe_dichiarata == dichiarata, "la classe dichiarata resta quella"
    assert v.vale_come_conferma is False


@pytest.mark.parametrize("letta,dichiarata", [
    ("trasmissione", "indipendente"),
    ("interno", "indipendente"),
    ("interno", "trasmissione"),
])
def test_declassa_e_ferma(letta, dichiarata):
    v = controlla("x", "y", dichiarata, client=FintoClient(letta, 0.95))
    assert v.stato == DECLASSA
    assert v.blocca()


def test_vale_come_conferma_e_falso_su_ogni_percorso():
    casi = [
        controlla("x", "y", "indipendente", client=FintoClient("indipendente", 0.99)),
        controlla("x", "y", "indipendente", client=FintoClient("interno", 0.99)),
        controlla("x", "y", "indipendente", client=FintoClient("interno", 0.10)),
        controlla("x", "y", "indipendente", client=ClientRotto()),
        controlla("x", "y", "indipendente", api_key=None),
    ]
    assert [c.vale_come_conferma for c in casi] == [False] * 5


# --- l'incertezza non decide ----------------------------------------------

def test_sotto_soglia_non_decide():
    v = controlla("x", "y", "indipendente", client=FintoClient("interno", 0.42))
    assert v.stato == INCERTO
    assert v.blocca(), "l'incertezza ferma: non contare cio' che nessuno sa"
    assert "0.42" in v.motivo


def test_il_dubbio_verso_l_alto_non_ferma_niente():
    """Dichiarato 'interno' (che non conta per H2), Jev incerto legge piu'
    in alto. Non c'e' niente sotto: la valvola non ha nulla da togliere e
    non deve fermare.

    Prima versione: fermava. Trovato da falsificatori/h12, non da me.
    La domanda giusta non e' «quanto e' sicuro Jev», e' «quanta
    probabilita' sta SOTTO cio' che hai dichiarato».
    """
    v = controlla("x", "y", "interno", client=FintoClient("indipendente", 0.30))
    assert v.stato == CONCORDE
    assert not v.blocca()


def test_massa_sotto_ferma_anche_se_vince_un_altra_opzione():
    """La vincente non e' piu' bassa, ma un terzo della distribuzione dice
    che lo e'. Quel terzo e' il motivo per chiamare una persona."""
    c = FintoClient(
        "indipendente", 0.55,
        probabilita={"indipendente": 0.55, "trasmissione": 0.40, "interno": 0.05},
    )
    v = controlla("x", "y", "indipendente", client=c)
    assert v.stato == INCERTO
    assert v.blocca()
    assert "45%" in v.motivo


def test_massa_sotto_piccola_lascia_passare():
    c = FintoClient(
        "indipendente", 0.92,
        probabilita={"indipendente": 0.92, "trasmissione": 0.06, "interno": 0.02},
    )
    assert controlla("x", "y", "indipendente", client=c).stato == CONCORDE


# --- Jev non vede l'etichetta ---------------------------------------------

def test_jev_non_riceve_il_tipo_dichiarato():
    """Se ricevesse l'etichetta, risponderebbe l'etichetta: eco con una
    probabilita' davanti, che sembra una misura e non lo e'."""
    def inviato(tipo):
        c = FintoClient("indipendente", 0.99)
        controlla("un lettore ha scritto", "mail del 20/09", tipo, client=c)
        return c.visto

    a, b, d = inviato("indipendente"), inviato("trasmissione"), inviato("interno")

    # Stessa nota, tre etichette diverse: cio' che parte deve essere
    # identico. Se differisse anche di un carattere, l'etichetta starebbe
    # entrando, e la risposta la rifletterebbe.
    assert a["state"] == b["state"] == d["state"]
    def domande(v):
        return {k: q.model_dump() for k, q in v["questions"].items()}
    assert domande(a) == domande(b) == domande(d)

    # E cio' che parte e' solo il fatto e il suo controllo.
    corpo = json.loads(a["state"])
    assert corpo == {
        "accaduto": "un lettore ha scritto",
        "come_si_controlla": "mail del 20/09",
    }


# --- i guasti non si propagano --------------------------------------------

def test_errore_non_alza_eccezione():
    v = controlla("x", "y", "indipendente", client=ClientRotto())
    assert v.stato == ERRORE and "rete" in v.motivo
    assert not v.blocca(), "un fornitore giu' non deve bloccare la registrazione"


def test_senza_chiave_e_assente_e_non_ferma(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    v = controlla("x", "y", "indipendente")
    assert v.stato == ASSENTE
    assert not v.blocca()
    assert stato_sorella()["attiva"] is False


def test_tipo_sconosciuto_non_viene_inventato():
    v = controlla("x", "y", "pizza", client=FintoClient("interno", 0.99))
    assert v.classe_dichiarata is None
    assert v.stato == CONCORDE and not v.blocca()


# --- le due copie del §7 non devono divergere -----------------------------

def test_il_sette_di_sdq1_e_quello_della_valvola_coincidono():
    from sdq1.__main__ import (
        TIPI_INDIPENDENTI, TIPI_INTERNI, TIPI_TRASMISSIONE, classe_sette,
    )
    atteso = {
        **{t: "indipendente" for t in TIPI_INDIPENDENTI},
        **{t: "trasmissione" for t in TIPI_TRASMISSIONE},
        **{t: "interno" for t in TIPI_INTERNI},
    }
    for tipo, classe in atteso.items():
        assert classe_sette(tipo) == classe
        assert classe in ORDINE, "sdq1 produce una classe che la valvola non conosce"
    assert classe_sette("pizza") is None


# --- la porta nel comando vero ---------------------------------------------

def _voce_finta(stato, **kw):
    from valvola.jev import Verdetto
    return Verdetto(stato=stato, motivo="finto", **kw)


def _args(**kw):
    import argparse
    d = dict(tipo="lettore", nota="n", verifica="v", comunque=False)
    d.update(kw)
    return argparse.Namespace(**d)


def _esegui(tmp_path, monkeypatch, verdetto, **kw):
    """Lancia cmd_contatto in una cartella isolata. output/contatti.jsonl
    vero non va mai toccato da un test: e' la misura di H2."""
    import valvola
    import sdq1.__main__ as m

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(m, "CONTATTI_PATH", str(tmp_path / "output" / "contatti.jsonl"))
    monkeypatch.setattr(valvola, "controlla", lambda *a, **k: verdetto)
    try:
        m.cmd_contatto(_args(**kw))
        uscita = 0
    except SystemExit as e:
        uscita = e.code
    f = tmp_path / "output" / "contatti.jsonl"
    righe = [json.loads(l) for l in f.read_text().splitlines()] if f.exists() else []
    return uscita, righe


def test_declassa_impedisce_la_scrittura(tmp_path, monkeypatch):
    uscita, righe = _esegui(
        tmp_path, monkeypatch,
        _voce_finta(DECLASSA, classe_dichiarata="indipendente",
                    classe_letta="trasmissione", confidenza=0.9),
    )
    assert uscita == 3
    assert righe == [], "la voce fermata non deve finire nella misura di H2"


def test_assente_lascia_passare_come_prima(tmp_path, monkeypatch):
    uscita, righe = _esegui(tmp_path, monkeypatch, _voce_finta(ASSENTE))
    assert uscita == 0
    assert len(righe) == 1 and righe[0]["indipendente"] is True
    assert righe[0]["valvola"]["stato"] == ASSENTE
    assert righe[0]["valvola_scavalcata"] is False


def test_comunque_scavalca_ma_lascia_la_traccia(tmp_path, monkeypatch):
    """La persona decide (§7: la fonte e' l'autore). Ma resta scritto che
    la valvola aveva obiettato, altrimenti lo scavalco sparisce."""
    uscita, righe = _esegui(
        tmp_path, monkeypatch,
        _voce_finta(DECLASSA, classe_dichiarata="indipendente",
                    classe_letta="interno", confidenza=0.99),
        comunque=True,
    )
    assert uscita == 0
    assert len(righe) == 1
    assert righe[0]["valvola_scavalcata"] is True
    assert righe[0]["valvola"]["classe_letta"] == "interno"
    assert righe[0]["valvola"]["vale_come_conferma"] is False


def test_un_guasto_della_sorella_non_blocca_la_registrazione(tmp_path, monkeypatch):
    uscita, righe = _esegui(tmp_path, monkeypatch, _voce_finta(ERRORE))
    assert uscita == 0 and len(righe) == 1
