"""Il falsificatore del DELTA deve bocciare, non solo approvare.

Un verificatore che dice sempre PASS e' il difetto di CLAUDE.md §4 dentro lo
strumento costruito per impedirlo: il registro delle ipotesi si era
auto-confermato esattamente cosi'. Qui ogni criterio ha un caso che lo fa
fallire da solo, e i tre stati restano distinti: PASS, FAIL e UNKNOWN non sono
la stessa cosa, e UNKNOWN non e' una bocciatura gentile.

    python -m pytest tests/test_falsificatore_omniroute.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from esperimenti.omniroute import falsificatore_delta as fd  # noqa: E402

DENY = ["kilo-gateway/anthropic/claude-opus-5", "felo/felo-chat"]
CATALOGO = ["kg/anthropic/claude-opus-5", "felo/felo-chat", "or/libero"]


def _cat(ids):
    return {"object": "list",
            "data": [{"id": i, "object": "model", "owned_by": i.split("/")[0]} for i in ids]}


def _scrivi(d, nome, oggetto):
    (d / nome).write_text(json.dumps(oggetto), encoding="utf-8")


def _delta(tmp_path, *, prima=None, dopo, per_voce=None, deny=None, patch="200",
           riletta=None, auto_http=200, auto_modello="or/libero", expl_http=200,
           auto_http_prima=200, models_status="200", pool=(10, 9)):
    """per_voce: una lista di liste di id — il catalogo con la voce N da sola."""
    deny = list(DENY if deny is None else deny)
    prima = list(CATALOGO if prima is None else prima)
    d = tmp_path / "delta"
    d.mkdir()
    (d / "denylist.txt").write_text("\n".join(deny) + "\n", encoding="utf-8")
    _scrivi(d, "models_prima.json", _cat(prima))
    _scrivi(d, "models_dopo.json", _cat(dopo))
    (d / "models_prima.status").write_text("200", encoding="utf-8")
    (d / "models_dopo.status").write_text(models_status, encoding="utf-8")
    (d / "patch.status").write_text(patch, encoding="utf-8")
    _scrivi(d, "settings_dopo.json",
            {"modelVisibilityDenylist": deny if riletta is None else riletta})
    _scrivi(d, "auto.meta.json", {"http": auto_http, "secondi": 1.0})
    _scrivi(d, "auto_prima.meta.json", {"http": auto_http_prima})
    risposta = {"model": auto_modello}
    if pool is not None:
        risposta["diagnostics"] = {"poolSize": pool[1]}
        _scrivi(d, "auto_prima_risposta.json", {"diagnostics": {"poolSize": pool[0]}})
    _scrivi(d, "auto_risposta.json", risposta)
    _scrivi(d, "explicit.meta.json", {"http": expl_http, "modello": deny[0]})
    if per_voce is not None:
        pv = d / "per_voce"
        pv.mkdir()
        for n, ids in enumerate(per_voce, start=1):
            (pv / ("%d_voce.txt" % n)).write_text(deny[n - 1], encoding="utf-8")
            (pv / ("%d_models.status" % n)).write_text("200", encoding="utf-8")
            _scrivi(pv, "%d_models.json" % n, _cat(ids))
    return str(d)


# --- il caso che passa -------------------------------------------------------

def test_adopt_quando_ogni_voce_toglie_qualcosa(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["or/libero"],
               per_voce=[["felo/felo-chat", "or/libero"],          # voce 1 toglie il kg
                         ["kg/anthropic/claude-opus-5", "or/libero"]])  # voce 2 toglie il felo
    assert fd.main(["x", d]) == 0
    out = capsys.readouterr().out
    assert "ADOPT A" in out and "toglie 1" in out


# --- i criteri, uno per uno --------------------------------------------------

def test_a1_catalogo_irraggiungibile_boccia(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["or/libero"], models_status="500",
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 1
    assert "A1" in capsys.readouterr().out


def test_a2_denylist_che_non_persiste_boccia(tmp_path, capsys):
    # E' il comportamento misurato su 3.8.50: PATCH 200, chiave buttata via.
    d = _delta(tmp_path, dopo=["or/libero"], riletta=[],
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 1
    out = capsys.readouterr().out
    assert "A2" in out and "0/2" in out


def test_a3_voce_che_non_toglie_niente_boccia(tmp_path, capsys):
    # La voce 2 lascia il catalogo intatto: passa il PATCH e non fa nulla.
    d = _delta(tmp_path, dopo=["felo/felo-chat", "or/libero"],
               per_voce=[["felo/felo-chat", "or/libero"], list(CATALOGO)])
    assert fd.main(["x", d]) == 1
    out = capsys.readouterr().out
    assert "A3" in out and "NIENTE" in out


def test_a4_id_che_torna_in_vetrina_con_la_lista_intera_boccia(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["felo/felo-chat", "or/libero"],
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 1
    out = capsys.readouterr().out
    assert "A4" in out and "felo/felo-chat" in out


def test_a5_danno_collaterale_boccia(tmp_path, capsys):
    d = _delta(tmp_path, dopo=[],
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 1
    out = capsys.readouterr().out
    assert "A5" in out and "or/libero" in out


def test_a6_auto_che_sceglie_un_modello_tolto_boccia(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["or/libero"], auto_modello="felo/felo-chat",
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 1
    assert "A6" in capsys.readouterr().out


# --- UNKNOWN: l'assenza di misura non e' una bocciatura ----------------------

def test_auto_mai_funzionante_e_unknown(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["or/libero"], auto_http=503, auto_http_prima=503,
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 2
    out = capsys.readouterr().out
    assert "UNKNOWN" in out and "non misurabile" in out


def test_auto_che_smette_di_funzionare_dopo_il_patch_e_reject(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["or/libero"], auto_http=503, auto_http_prima=200,
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 1
    assert "rotto il routing" in capsys.readouterr().out


def test_senza_misura_per_voce_niente_verdetto_su_a3_a4_a5(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["or/libero"])
    assert fd.main(["x", d]) == 2
    out = capsys.readouterr().out
    assert "A3" in out and "A4" in out and "A5" in out and "UNKNOWN" in out


def test_artefatti_mancanti_non_producono_un_verdetto(tmp_path, capsys):
    vuota = tmp_path / "vuota"
    vuota.mkdir()
    assert fd.main(["x", str(vuota)]) == 2
    assert "UNKNOWN" in capsys.readouterr().out


# --- diagnosi delle voci a vuoto (fatti letti nel sorgente 3.8.51) -----------

def test_diagnosi_provider_ritirato():
    # RUNTIME_RETIRED_PROVIDER_IDS in src/shared/constants/providerRetirement.ts
    d = fd.diagnosi_voce_a_vuoto("felo/felo-chat")
    assert "ritirato" in d and "PROVIDER_RETIRED" in d


def test_non_dice_ritirato_se_i_modelli_sono_ancora_in_vetrina():
    # Su 3.8.50 i felo/* ci sono: chiamarli ritirati sarebbe falso.
    d = fd.diagnosi_voce_a_vuoto("felo/felo-chat", {"felo/felo-chat", "or/libero"})
    assert "ritirato" not in d


def test_diagnosi_provider_assente_dal_catalogo():
    d = fd.diagnosi_voce_a_vuoto("kilo-gateway/anthropic/claude-opus-5",
                                 {"oc/big-pickle", "or/libero"})
    assert "non compare in questo catalogo" in d and "Rimisurala" in d


def test_provider_presente_sotto_il_suo_alias_non_e_assente():
    # 'oc' in vetrina e' opencode: la voce canonica non va chiamata "assente".
    d = fd.diagnosi_voce_a_vuoto("opencode/big-pickle", {"oc/big-pickle"})
    assert "non compare" not in d


def test_diagnosi_forma_alias_propone_il_canonico():
    # catalog.ts chiama isModelExposureAllowed(aliasToProviderId[k] || k, ...)
    d = fd.diagnosi_voce_a_vuoto("oc/big-pickle", {"oc/big-pickle", "or/libero"})
    assert "alias" in d and "opencode/big-pickle" in d


def test_diagnosi_non_inventa_una_causa():
    assert "nessun modello sparisce" in fd.diagnosi_voce_a_vuoto("provider-che-non-esiste/x")


# --- E1 va detto sempre ------------------------------------------------------

def test_e1_dispatch_esplicito_viene_sempre_detto(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["or/libero"],
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    fd.main(["x", d])
    out = capsys.readouterr().out
    assert "E1" in out and "risponde ancora" in out


# --- A7: il pool di auto/*, il secondo punto di strozzatura ------------------

def test_a7_pool_che_cresce_boccia(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["or/libero"], pool=(9, 12),
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 1
    out = capsys.readouterr().out
    assert "A7" in out and "CRESCIUTO" in out


def test_a7_pool_che_perde_piu_di_quanto_sparisce_boccia(tmp_path, capsys):
    # 2 modelli tolti dalla vetrina, 7 candidati in meno: differenza non spiegata.
    d = _delta(tmp_path, dopo=["or/libero"], pool=(10, 3),
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 1
    assert "non spiegata" in capsys.readouterr().out


def test_a7_pool_fermo_mentre_la_vetrina_si_svuota_e_unknown(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["or/libero"], pool=(10, 10),
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 2
    out = capsys.readouterr().out
    assert "A7" in out and "non fossero candidati" in out


def test_a7_senza_poolsize_e_unknown(tmp_path, capsys):
    d = _delta(tmp_path, dopo=["or/libero"], pool=None,
               per_voce=[["felo/felo-chat", "or/libero"], ["kg/anthropic/claude-opus-5", "or/libero"]])
    assert fd.main(["x", d]) == 2
    assert "poolSize non riportato" in capsys.readouterr().out
