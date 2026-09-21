"""Il falsificatore del DELTA deve bocciare, non solo approvare.

Un verificatore che dice sempre PASS e' il difetto di CLAUDE.md §4 dentro lo
strumento costruito per impedirlo: il registro delle ipotesi si era
auto-confermato esattamente cosi'. Qui ogni criterio ha un caso che lo fa
fallire da solo, e la semantica del match e' confrontata con quella upstream
(globPattern.ts / modelExposureList.ts), non con quella che mi aspettavo.

    python -m pytest tests/test_falsificatore_omniroute.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from esperimenti.omniroute import falsificatore_delta as fd  # noqa: E402

DENY = ["kilo-gateway/anthropic/claude-opus-5", "felo/felo-chat"]


def _catalogo(ids):
    return {"object": "list",
            "data": [{"id": i, "object": "model", "owned_by": i.split("/")[0]} for i in ids]}


def _delta(tmp_path, *, prima, dopo, deny=DENY, patch="200", riletta=None,
           auto_http=200, auto_modello="openrouter/free-model", expl_http=200,
           auto_http_prima=200):
    d = tmp_path / "delta"
    d.mkdir()
    (d / "denylist.txt").write_text("\n".join(deny) + "\n", encoding="utf-8")
    (d / "models_prima.json").write_text(json.dumps(_catalogo(prima)), encoding="utf-8")
    (d / "models_dopo.json").write_text(json.dumps(_catalogo(dopo)), encoding="utf-8")
    (d / "models_prima.status").write_text("200", encoding="utf-8")
    (d / "models_dopo.status").write_text("200", encoding="utf-8")
    (d / "patch.status").write_text(patch, encoding="utf-8")
    (d / "settings_dopo.json").write_text(json.dumps(
        {"modelVisibilityDenylist": deny if riletta is None else riletta}), encoding="utf-8")
    (d / "auto.meta.json").write_text(json.dumps({"http": auto_http, "secondi": 1.0}),
                                      encoding="utf-8")
    (d / "auto_risposta.json").write_text(json.dumps({"model": auto_modello}), encoding="utf-8")
    (d / "auto_prima.meta.json").write_text(json.dumps({"http": auto_http_prima}), encoding="utf-8")
    (d / "explicit.meta.json").write_text(json.dumps(
        {"http": expl_http, "modello": deny[0]}), encoding="utf-8")
    return str(d)


# --- semantica del match, confrontata con l'upstream -------------------------

def test_glob_attraversa_le_barre_come_upstream():
    # globToRegex traduce * in .*, che in JS non si ferma alla barra.
    assert fd.voce_corrisponde("anthropic/*", ["anthropic/claude/opus"])
    assert fd.voce_corrisponde("openai/gpt-4*", ["openai/gpt-4o"])


def test_glob_e_case_insensitive_ma_l_esatto_no():
    assert fd.voce_corrisponde("OPENAI/GPT-4*", ["openai/gpt-4o"])
    # Senza wildcard upstream usa candidates.includes(entry): case-sensitive.
    assert not fd.voce_corrisponde("OpenAI/GPT-4o", ["openai/gpt-4o"])
    assert fd.voce_corrisponde("openai/gpt-4o", ["openai/gpt-4o"])


def test_voce_senza_wildcard_non_diventa_prefisso():
    assert not fd.voce_corrisponde("felo", ["felo/felo-chat"])


# --- i criteri, uno per uno --------------------------------------------------

def test_adopt_quando_tutto_torna(tmp_path, capsys):
    d = _delta(tmp_path,
               prima=["kilo-gateway/anthropic/claude-opus-5", "felo/felo-chat", "or/libero"],
               dopo=["or/libero"])
    assert fd.main(["x", d]) == 0
    assert "ADOPT A" in capsys.readouterr().out


def test_a3_voce_che_non_colpisce_niente_boccia(tmp_path, capsys):
    # La trappola: la voce e' scritta male, il PATCH passa, non succede nulla.
    d = _delta(tmp_path, prima=["felo/felo-chat", "or/libero"], dopo=["or/libero"])
    assert fd.main(["x", d]) == 1
    out = capsys.readouterr().out
    assert "A3" in out and "REJECT A" in out
    assert "kilo-gateway/anthropic/claude-opus-5" in out


def test_a4_modello_negato_ancora_in_vetrina_boccia(tmp_path, capsys):
    d = _delta(tmp_path,
               prima=["kilo-gateway/anthropic/claude-opus-5", "felo/felo-chat", "or/libero"],
               dopo=["kilo-gateway/anthropic/claude-opus-5", "or/libero"])
    assert fd.main(["x", d]) == 1
    assert "A4" in capsys.readouterr().out


def test_a5_danno_collaterale_boccia(tmp_path, capsys):
    d = _delta(tmp_path,
               prima=["kilo-gateway/anthropic/claude-opus-5", "felo/felo-chat", "or/libero"],
               dopo=[])
    assert fd.main(["x", d]) == 1
    out = capsys.readouterr().out
    assert "A5" in out and "or/libero" in out


def test_a6_auto_che_sceglie_un_negato_boccia(tmp_path, capsys):
    d = _delta(tmp_path,
               prima=["kilo-gateway/anthropic/claude-opus-5", "felo/felo-chat", "or/libero"],
               dopo=["or/libero"],
               auto_modello="felo/felo-chat")
    assert fd.main(["x", d]) == 1
    assert "A6" in capsys.readouterr().out


def test_a2_denylist_che_non_persiste_boccia(tmp_path, capsys):
    d = _delta(tmp_path,
               prima=["kilo-gateway/anthropic/claude-opus-5", "felo/felo-chat", "or/libero"],
               dopo=["or/libero"],
               riletta=[])
    assert fd.main(["x", d]) == 1
    assert "A2" in capsys.readouterr().out


def test_artefatti_mancanti_non_producono_un_verdetto(tmp_path, capsys):
    vuota = tmp_path / "vuota"
    vuota.mkdir()
    assert fd.main(["x", str(vuota)]) == 2
    assert "UNKNOWN" in capsys.readouterr().out


def test_e1_dispatch_esplicito_viene_sempre_detto(tmp_path, capsys):
    d = _delta(tmp_path,
               prima=["kilo-gateway/anthropic/claude-opus-5", "felo/felo-chat", "or/libero"],
               dopo=["or/libero"])
    fd.main(["x", d])
    out = capsys.readouterr().out
    assert "E1" in out and "risponde ancora" in out


# --- diagnosi delle voci a vuoto (fatti letti nel sorgente 3.8.51) -----------

def test_diagnosi_provider_ritirato():
    # RUNTIME_RETIRED_PROVIDER_IDS in src/shared/constants/providerRetirement.ts
    d = fd.diagnosi_voce_a_vuoto("felo/felo-chat")
    assert "ritirato" in d and "PROVIDER_RETIRED" in d


def test_diagnosi_forma_alias_propone_il_canonico():
    # catalog.ts passa isModelExposureAllowed(aliasToProviderId[k] || k, ...)
    d = fd.diagnosi_voce_a_vuoto("oc/big-pickle")
    assert "alias" in d and "opencode/big-pickle" in d


def test_diagnosi_non_inventa_una_causa():
    assert fd.diagnosi_voce_a_vuoto("provider-che-non-esiste/x") == \
        "nessun id del catalogo le corrisponde"


def test_le_voci_a_vuoto_sono_stampate_con_la_causa(tmp_path, capsys):
    d = _delta(tmp_path, prima=["or/libero"], dopo=["or/libero"],
               deny=["felo/felo-chat", "oc/big-pickle"])
    assert fd.main(["x", d]) == 1
    out = capsys.readouterr().out
    assert "ritirato" in out and "opencode/big-pickle" in out


# --- tre stati: PASS, FAIL e UNKNOWN non sono la stessa cosa -----------------

def test_auto_mai_funzionante_e_unknown_non_reject(tmp_path, capsys):
    # Senza provider configurati `auto` non risponde ne' prima ne' dopo: non
    # dice niente sulla denylist. UNKNOWN, non una bocciatura.
    d = _delta(tmp_path,
               prima=["kilo-gateway/anthropic/claude-opus-5", "felo/felo-chat", "or/libero"],
               dopo=["or/libero"], auto_http=503, auto_http_prima=503)
    assert fd.main(["x", d]) == 2
    out = capsys.readouterr().out
    assert "UNKNOWN" in out and "non misurabile" in out


def test_auto_che_smette_di_funzionare_dopo_il_patch_e_reject(tmp_path, capsys):
    # Funzionava prima, non funziona dopo: il controllo rende questo un FAIL.
    d = _delta(tmp_path,
               prima=["kilo-gateway/anthropic/claude-opus-5", "felo/felo-chat", "or/libero"],
               dopo=["or/libero"], auto_http=503, auto_http_prima=200)
    assert fd.main(["x", d]) == 1
    out = capsys.readouterr().out
    assert "A6" in out and "rotto il routing" in out
