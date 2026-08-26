"""Il ciclo autonomo: cosa deve fare, e soprattutto cosa non deve fare."""

import json
import os
import threading

import pytest
import requests

import autonomous_core_v3 as core


@pytest.fixture
def sistema(monkeypatch, tmp_path):
    """Un Core isolato: niente rete, niente Telegram, file nel tmp_path."""
    monkeypatch.setattr(core, "STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setattr(core, "QUEUE_FILE", str(tmp_path / "queue.json"))
    monkeypatch.setattr(core, "CREATION_DIR", str(tmp_path / "creazioni"))
    monkeypatch.setattr(core, "CONTATTI_FILE", str(tmp_path / "contatti.jsonl"))
    monkeypatch.setattr(core, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(core, "TELEGRAM_CHAT_ID", "")
    return core.AutonomousCore(
        costituzione=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "costituzione_cev.json"),
        backup=str(tmp_path / "nessun-backup.json"),
    )


@pytest.fixture
def senza_rete(monkeypatch):
    """Il ledger non viene mai contattato durante i test."""
    inviate = []
    monkeypatch.setattr(core, "push_to_ledger",
                        lambda chiave, valore, tentativi=2: inviate.append(chiave) or True)
    monkeypatch.setattr(core, "flush_queue", lambda: 0)
    monkeypatch.setattr(core, "send_notification", lambda messaggio: True)
    return inviate


# ------------------------------------------------------------------
# Filtro di purezza
# ------------------------------------------------------------------

def test_purity_check_blocca_e_lascia_passare():
    assert core.purity_check("Un modulo abitativo nel Mare di Weddell.") is True
    assert core.purity_check("Testo che descrive un abuso sessuale.") is False
    assert core.purity_check("Contenuto con ABUSO   SESSUALE maiuscolo") is False


def test_purity_check_disattivabile(monkeypatch):
    monkeypatch.setattr(core, "PURITY_FILTER_ACTIVE", False)
    assert core.purity_check("abuso sessuale") is True


# ------------------------------------------------------------------
# Stato e coda
# ------------------------------------------------------------------

def test_stato_mancante_parte_dai_default(sistema):
    stato = core.load_state()
    assert stato["creations"] == [] and stato["cicli_eseguiti"] == 0


def test_stato_corrotto_non_ferma_il_sistema(sistema):
    with open(core.STATE_FILE, "w", encoding="utf-8") as f:
        f.write("{ non json")
    assert core.load_state()["creations"] == []


def test_stato_parziale_completato_senza_keyerror(sistema):
    """Uno state.json di una versione precedente non deve far esplodere il ciclo."""
    with open(core.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_run": "2026-01-01"}, f)
    stato = core.load_state()
    assert stato["creations"] == [] and stato["proposals"] == []


def test_stato_potato_a_cento_voci(sistema):
    stato = core.load_state()
    stato["creations"] = [{"id": str(i)} for i in range(150)]
    core.save_state(stato)
    assert len(core.load_state()["creations"]) == 100


def test_ledger_irraggiungibile_accoda(sistema, monkeypatch):
    monkeypatch.setattr(core.time, "sleep", lambda _: None)

    def esplode(*a, **k):
        raise requests.RequestException("rete assente")

    monkeypatch.setattr(core.requests, "post", esplode)
    assert core.push_to_ledger("chiave", {"a": 1}) is False
    coda = core.load_queue()
    assert len(coda) == 1 and coda[0]["key"] == "chiave"


def test_token_rifiutato_non_accoda(sistema, monkeypatch):
    """401 non è un problema di rete: riaccodare significherebbe ritentare
    all'infinito una voce che non passerà mai."""
    monkeypatch.setattr(core.time, "sleep", lambda _: None)

    class Risposta:
        status_code = 401

    monkeypatch.setattr(core.requests, "post", lambda *a, **k: Risposta())
    assert core.push_to_ledger("chiave", {"a": 1}) is False
    assert core.load_queue() == []


# ------------------------------------------------------------------
# Produzione
# ------------------------------------------------------------------

def test_creazione_senza_backup_usa_temi_di_riserva(sistema):
    creazione = sistema.auto_create()
    assert creazione["generato_da"] == "template"
    assert creazione["pensiero_llm"] is False
    assert os.path.exists(creazione["percorso"])


def test_creazione_usa_il_backup_quando_c_e(monkeypatch, tmp_path):
    percorso = tmp_path / "backup.json"
    percorso.write_text(json.dumps({"chunks": [
        {"id": "c1", "testo": "Tunnel sottomarino transoceanico", "tag": ["scacchiera"]},
    ]}), encoding="utf-8")
    monkeypatch.setattr(core, "CREATION_DIR", str(tmp_path / "creazioni"))
    sistema = core.AutonomousCore(backup=str(percorso))
    creazione = sistema.auto_create()
    assert creazione["generato_da"] == "backup:c1"
    assert "Tunnel sottomarino" in creazione["titolo"]


def test_proposte_sono_dichiarate_interne(sistema):
    proposte = sistema.generate_proposals()
    assert len(proposte) == core.MAX_PROPOSALS_PER_CYCLE
    assert all(p["origine"] == "interna" for p in proposte)
    assert all(p["pensiero_llm"] is False for p in proposte)


def test_moduli_mancanti_non_fermano_il_core(tmp_path):
    """RLAIF senza Costituzione, backup assente: il sistema prosegue."""
    sistema = core.AutonomousCore(
        costituzione=str(tmp_path / "niente.json"),
        backup=str(tmp_path / "niente-backup.json"),
    )
    assert sistema.rlaif is None
    assert not sistema.backup.chunks
    esito = sistema._valuta({"id": "x", "tipo": "proposta", "descrizione": "y"})
    assert esito["approvata"] is True and esito["valutato"] is False


# ------------------------------------------------------------------
# Ciclo completo
# ------------------------------------------------------------------

def test_ciclo_completo(sistema, senza_rete):
    riassunto = sistema.run_cycle()
    assert riassunto["ciclo"] == 1
    assert riassunto["creazioni_nuove"] == 1
    assert riassunto["proposte_nuove"] == core.MAX_PROPOSALS_PER_CYCLE
    assert riassunto["pensiero_llm"] is False
    assert "autonomous_cycle" in senza_rete
    stato = core.load_state()
    assert stato["cicli_eseguiti"] == 1 and stato["last_run"]


def test_il_ciclo_autonomo_non_scrive_mai_i_contatti(sistema, senza_rete):
    """CEV-3, e criterio (b) di H2.

    `output/contatti.jsonl` misura quanto il progetto tocca il mondo. Se il
    ciclo autonomo potesse scriverci, la metrica misurerebbe l'eco del
    sistema invece del mondo. Deve restare vuoto per costruzione.
    """
    for _ in range(3):
        sistema.run_cycle()
    assert not os.path.exists(core.CONTATTI_FILE)


def test_ciclo_resiliente_a_un_errore(sistema, senza_rete, monkeypatch):
    monkeypatch.setattr(sistema, "auto_create",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    sistema.running.set()
    thread = threading.Thread(target=sistema.loop, daemon=True)
    thread.start()
    sistema.shutdown.set()
    thread.join(timeout=10)
    assert not thread.is_alive()


def test_loop_si_ferma_su_shutdown(sistema, senza_rete):
    sistema.running.clear()
    thread = threading.Thread(target=sistema.loop, daemon=True)
    thread.start()
    sistema.shutdown.set()
    thread.join(timeout=10)
    assert not thread.is_alive()


# ------------------------------------------------------------------
# Contatti
# ------------------------------------------------------------------

def test_contatto_richiede_una_verifica(sistema):
    with pytest.raises(ValueError):
        core.registra_contatto("lettore", "mi ha scritto", "   ")


def test_contatto_registrato_nel_formato_di_sdq1(sistema):
    voce = core.registra_contatto("lettore", "mi ha scritto dopo il post",
                                  "email del 26/08")
    assert voce["origine"] == "telegram"
    with open(core.CONTATTI_FILE, "r", encoding="utf-8") as f:
        salvata = json.loads(f.readline())
    assert set(salvata) >= {"tipo", "nota", "verifica", "timestamp", "data_iso"}


# ------------------------------------------------------------------
# Diagnostica e CLI
# ------------------------------------------------------------------

def test_diagnostica(sistema):
    d = sistema.diagnostica()
    assert d["ciclo"] == "fermo" and d["contatti_reali"] == 0
    sistema.running.set()
    assert sistema.diagnostica()["ciclo"] == "attivo"


def test_main_senza_token_non_avvia_il_bot(monkeypatch, capsys):
    monkeypatch.setattr(core, "TELEGRAM_BOT_TOKEN", "")
    assert core.main([]) == 2


def test_main_con_token_ma_senza_admin_si_ferma(monkeypatch):
    """Un bot senza lista di admin rifiuterebbe ogni comando: meglio
    fermarsi con un messaggio chiaro che restare in ascolto inutilizzabile."""
    monkeypatch.setattr(core, "TELEGRAM_BOT_TOKEN", "finto:token")
    monkeypatch.setattr(core, "TELEGRAM_ADMIN_IDS", set())
    assert core.main([]) == 2


# ------------------------------------------------------------------
# Autorizzazione Telegram
# ------------------------------------------------------------------

def test_senza_admin_nessuno_e_autorizzato(monkeypatch):
    monkeypatch.setattr(core, "TELEGRAM_ADMIN_IDS", set())
    assert core.chat_autorizzata(12345) is False
    assert core.chat_autorizzata(None, None) is False


def test_solo_gli_admin_dichiarati(monkeypatch):
    monkeypatch.setattr(core, "TELEGRAM_ADMIN_IDS", {"111", "222"})
    assert core.chat_autorizzata(111) is True          # chat id, anche come int
    assert core.chat_autorizzata(999, 222) is True     # autorizzato come utente
    assert core.chat_autorizzata(999, 888) is False
    assert core.chat_autorizzata(None) is False


def test_costruisci_bot_registra_i_comandi(monkeypatch, sistema):
    telegram = pytest.importorskip("telegram")
    monkeypatch.setattr(core, "TELEGRAM_BOT_TOKEN", "123456:" + "A" * 35)
    application, _ = core.costruisci_bot(sistema)
    comandi = {
        c for handler in application.handlers[0]
        for c in getattr(handler, "commands", ())
    }
    assert {"start", "status", "run", "stop", "ciclo", "contatto"} <= comandi
