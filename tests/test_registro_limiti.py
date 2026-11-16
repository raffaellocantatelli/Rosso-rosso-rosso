"""Un limite dichiarato e' una resa che ogni nodo dopo di te eredita.

CLAUDE.md §4 dice che il sistema parla a se' stesso e registra l'eco come
risposta. Un limite scritto senza prova e' la stessa malattia applicata non ai
dati ma alle rinunce: «qui non si puo'» diventa un fatto del progetto perche'
nessuno lo ritenta. E' successo in questa sessione — un nodo (io) ha scritto
che non c'era un demone Docker senza provare ad avviarlo; c'era.

Questi test bloccano i due modi di sbagliare in direzioni opposte: accettare un
limite che non e' stato provato, e dichiarare caduto un limite che regge.

    python -m pytest tests/test_registro_limiti.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import registro_nodi as rn  # noqa: E402


def _isolato(tmp_path):
    rn.REGISTRO = str(tmp_path / "registro.jsonl")
    return pathlib.Path(rn.REGISTRO)


def _voci(percorso):
    if not percorso.exists():
        return []
    return [json.loads(r) for r in percorso.read_text(encoding="utf-8").splitlines() if r.strip()]


def test_un_limite_il_cui_comando_riesce_viene_rifiutato(tmp_path, capsys):
    reg = _isolato(tmp_path)
    assert rn.limite("prova", "non si puo' uscire con zero", "true") == 1
    assert "RIFIUTATO" in capsys.readouterr().out
    assert _voci(reg) == []          # e non lascia traccia: non era un limite


def test_un_limite_vero_viene_registrato_col_comando(tmp_path):
    reg = _isolato(tmp_path)
    assert rn.limite("prova", "questo fallisce", "false") == 0
    voci = _voci(reg)
    assert len(voci) == 1
    assert voci[0]["tipo"] == "limite"
    assert voci[0]["comando"] == "false"
    assert voci[0]["uscita"] != 0


def test_il_comando_viene_eseguito_davvero(tmp_path):
    # Se il registro si limitasse a credere alla stringa, questo file non
    # esisterebbe. E' la stessa trappola di registro_ipotesi.aggiorna_stato,
    # che controllava solo che il criterio fosse una stringa non vuota.
    _isolato(tmp_path)
    testimone = tmp_path / "testimone.txt"
    rn.limite("prova", "x", "echo scritto > %s; false" % testimone)
    assert testimone.exists(), "il comando non e' stato eseguito"


def test_ritenta_dichiara_caduto_un_limite_che_ora_riesce(tmp_path, capsys):
    reg = _isolato(tmp_path)
    bandiera = tmp_path / "bandiera"
    comando = "test -f %s" % bandiera
    assert rn.limite("prova", "la bandiera non c'e'", comando) == 0
    bandiera.write_text("ci sono", encoding="utf-8")   # il mondo e' cambiato
    assert rn.ritenta() == 0
    out = capsys.readouterr().out
    assert "CADUTO" in out and "adesso riesce" in out
    assert len(_voci(reg)) == 1                        # ritentare non riscrive


def test_ritenta_non_spaccia_per_vero_un_limite_che_regge(tmp_path, capsys):
    _isolato(tmp_path)
    rn.limite("prova", "questo fallisce", "false")
    assert rn.ritenta() == 1
    out = capsys.readouterr().out
    assert "regge" in out and "Nessun limite caduto" in out
    assert "nessuno li ha ancora fatti cadere" in out


def test_senza_limiti_ritenta_non_ha_niente_da_dire(tmp_path, capsys):
    _isolato(tmp_path)
    assert rn.ritenta() == 0
    assert "Nessun limite" in capsys.readouterr().out


def test_un_comando_che_non_torna_non_blocca_il_registro(tmp_path):
    _isolato(tmp_path)
    uscita, riga = rn._esegui("sleep 5", secondi=1)
    assert uscita == 124 and "scaduto" in riga


# --- il loopback dentro lo strumento fatto per impedirlo --------------------

def test_un_comando_che_cerca_nel_progetto_viene_rifiutato(tmp_path, capsys):
    # Successo il 23/09/2026: il comando cercava una stringa nel repository, e
    # la stringa e' finita nella documentazione del limite stesso. Il limite
    # e' "caduto" senza che fosse cambiato niente nel mondo. §4, dentro lo
    # strumento costruito per impedirlo — come gia' al registro delle ipotesi.
    reg = _isolato(tmp_path)
    for comando in ('grep -rqs "X" .', "git grep X", "rg X", "grep -R X ."):
        assert rn.limite("prova", "x", comando) == 2, comando
    assert "RIFIUTATO" in capsys.readouterr().out
    assert _voci(reg) == []


def test_una_condizione_del_mondo_va_bene(tmp_path):
    _isolato(tmp_path)
    assert rn.limite("prova", "manca la chiave", 'test -n "$CHIAVE_CHE_NON_ESISTE"') == 0


def test_l_ultima_dichiarazione_supera_le_precedenti(tmp_path):
    reg = _isolato(tmp_path)
    rn.limite("prova", "lo stesso limite", "false")
    rn.limite("prova", "lo stesso limite", 'test -n "$ALTRA_COSA"')
    assert len(_voci(reg)) == 2, "append-only: la storia non si cancella"
    vigenti = rn._limiti_dichiarati()
    assert len(vigenti) == 1, "ma due dichiarazioni della stessa cosa non valgono entrambe"
    assert vigenti[0]["comando"] == 'test -n "$ALTRA_COSA"'


def test_limiti_diversi_restano_tutti_e_due(tmp_path):
    _isolato(tmp_path)
    rn.limite("prova", "primo limite", "false")
    rn.limite("prova", "secondo limite", "false")
    assert len(rn._limiti_dichiarati()) == 2
