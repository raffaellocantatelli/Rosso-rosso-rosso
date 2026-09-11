"""Il ponte verso il NAS: cosa regge sul banco, e cosa il banco non prova.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Nessuna di queste prove tocca un NAS vero, e non deve pretendere di farlo:
girano contro il NAS finto di `ponte/banco.py`. Dicono che il client parla
WebDAV e che rifiuta quello che deve rifiutare. Che il NAS di Claudio
risponda e' UNKNOWN da qui, e lo dice `python -m ponte --check`.
"""

import json

import pytest

from ponte import config as cfg
from ponte.banco import crea_banco
from ponte.quickconnect import Candidato, candidati_da
from ponte.webdav import ErrorePonte, Ponte, _normalizza


@pytest.fixture
def nas():
    url, archivio, stop = crea_banco(utente="r3", password="prova", radice="/R3")
    try:
        yield url, archivio
    finally:
        stop()


@pytest.fixture
def ponte(nas):
    url, _ = nas
    return Ponte(url, "r3", "prova", radice="/R3")


# --------------------------------------------------------------- il giro vero

def test_deposita_e_rilegge_identico(ponte):
    dati = json.dumps({"stato": "prova", "accentate": "perché"}).encode("utf-8")
    assert ponte.deposita("capsule/stato.json", dati) == len(dati)
    assert ponte.preleva("capsule/stato.json") == dati


def test_crea_le_cartelle_mancanti(ponte):
    ponte.deposita("a/b/c/dentro.txt", b"x")
    assert ponte.esiste("a/b/c/dentro.txt")
    assert [v.nome for v in ponte.elenca("a/b")] == ["c"]


def test_nomi_con_spazi_e_accenti(ponte):
    ponte.deposita("un nome con spazi è accenti.txt", b"ok")
    assert ponte.preleva("un nome con spazi è accenti.txt") == b"ok"


def test_elenca_distingue_cartelle_e_file(ponte):
    ponte.deposita("capsule/uno.json", b"12345")
    voci = {v.nome: v for v in ponte.elenca()}
    assert voci["capsule"].cartella is True
    dentro = {v.nome: v for v in ponte.elenca("capsule")}
    assert dentro["uno.json"].cartella is False
    assert dentro["uno.json"].byte == 5


def test_rimuove(ponte):
    ponte.deposita("capsule/uno.json", b"1")
    ponte.rimuovi("capsule/uno.json")
    assert ponte.esiste("capsule/uno.json") is False


def test_rimuovere_di_nuovo_non_solleva(ponte):
    ponte.rimuovi("capsule/mai-esistito.json")


def test_crea_cartella_e_idempotente(ponte):
    assert ponte.crea_cartella("capsule") is True
    assert ponte.crea_cartella("capsule") is False


def test_check_dice_che_regge(ponte):
    e = ponte.check()
    assert e["parla_webdav"] and e["autenticato"] and e["radice_presente"]


# ------------------------------------------------- cio' che deve NON funzionare

def test_password_sbagliata_non_passa(nas):
    url, _ = nas
    sbagliato = Ponte(url, "r3", "non-questa", radice="/R3")
    assert sbagliato.check()["autenticato"] is False
    with pytest.raises(ErrorePonte) as e:
        sbagliato.preleva("qualsiasi")
    assert "401" in str(e.value)


def test_fuori_dalla_radice_e_rifiutato_dal_ponte(ponte, nas):
    """Il rifiuto arriva prima della rete: e' la condizione per usare un
    account che vede solo la cartella R3. Se il controllo fosse sul NAS,
    dipenderebbe dai permessi di quell'account, cioe' da una configurazione
    che nessuno rivede."""
    _, archivio = nas
    for brutto in ["../fuori.json", "a/../../fuga.json", "/R3/../../x"]:
        with pytest.raises(ErrorePonte):
            ponte.deposita(brutto, b"x")
    assert not any(p.startswith("/fuori") or "fuga" in p for p in archivio)


def test_non_cancella_la_propria_radice(ponte):
    with pytest.raises(ErrorePonte):
        ponte.rimuovi("")


def test_senza_url_non_finge(ponte):
    with pytest.raises(ErrorePonte):
        Ponte("", "r3", "prova")


def test_porta_chiusa_dice_non_raggiungibile():
    muto = Ponte("http://127.0.0.1:9", "r3", "prova", radice="/R3")
    with pytest.raises(ErrorePonte) as e:
        muto.check()
    assert "non raggiungibile" in str(e.value)


def test_deposita_vuole_byte(ponte):
    with pytest.raises(ErrorePonte):
        ponte.deposita("x.txt", "una stringa")


# ------------------------------------------------------------- normalizzazione

@pytest.mark.parametrize("dentro,fuori", [
    ("/R3//capsule/", "/R3/capsule"),
    ("R3/./capsule", "/R3/capsule"),
    ("/R3/a/../b", "/R3/b"),
    ("/R3/../fuori", "/fuori"),
])
def test_normalizza(dentro, fuori):
    assert _normalizza(dentro) == fuori


# -------------------------------------------------------------- QuickConnect

RISPOSTA_TIPO = {
    "serverID": "casa",
    "server": {
        "ddns": "casa.synology.me",
        "fqdn": "NULL",
        "external": {"ip": "93.1.2.3"},
        "interface": [{"ip": "192.168.1.10", "ipv6": [{"address": "fe80::1"}]}],
    },
    "service": {"port": 5001, "ext_port": 5001},
    "env": {"relay_region": "eu"},
    "errno": 0,
}


def test_candidati_in_ordine_di_utilita():
    c = candidati_da(RISPOSTA_TIPO)
    assert [x.come for x in c] == ["ddns", "wan", "lan", "lan", "relay"]
    assert c[0].host == "casa.synology.me"
    assert c[-1].host == "casa.eu.quickconnect.to"


def test_campi_nulli_ignorati():
    assert candidati_da({"server": {"ddns": "NULL", "fqdn": ""}}) == []


def test_risposta_vuota_non_solleva():
    assert candidati_da({}) == []


def test_ipv6_fra_parentesi():
    assert Candidato("fe80::1", "lan").url_webdav(5006) == "https://[fe80::1]:5006"
    assert Candidato("casa.synology.me", "ddns").url_webdav(5006) == \
        "https://casa.synology.me:5006"


# ------------------------------------------------------------- configurazione

def test_config_dice_cosa_manca(monkeypatch):
    for v in (cfg.ENV_URL, cfg.ENV_UTENTE, cfg.ENV_PASSWORD):
        monkeypatch.delenv(v, raising=False)
    assert cfg.Config.da_ambiente().mancanti() == \
        [cfg.ENV_URL, cfg.ENV_UTENTE, cfg.ENV_PASSWORD]


def test_config_avverte_su_http_e_su_tls_disattivato():
    c = cfg.Config(url="http://nas:5005", utente="r3", password="x", insicuro=True)
    note = " ".join(c.avvertenze())
    assert "in chiaro" in note and "certificato" in note


def test_carica_env_non_sovrascrive_ambiente(tmp_path, monkeypatch):
    f = tmp_path / "webdav.env"
    f.write_text(f"{cfg.ENV_URL}=https://dal-file:5006\n"
                 f"{cfg.ENV_UTENTE}=\"dal-file\"\n", encoding="utf-8")
    monkeypatch.setenv(cfg.ENV_URL, "https://gia-impostato:5006")
    monkeypatch.delenv(cfg.ENV_UTENTE, raising=False)
    assert cfg.carica_env(f) == [str(f)]
    c = cfg.Config.da_ambiente()
    assert c.url == "https://gia-impostato:5006"   # l'ambiente vince
    assert c.utente == "dal-file"                  # le virgolette non entrano


def test_nessuna_opzione_password_nella_riga_di_comando():
    """Se qualcuno la aggiungesse, finirebbe nella cronologia della shell."""
    from ponte.__main__ import main
    with pytest.raises(SystemExit):
        main(["--password", "segreta"])


# ------------------------------------------------------- la riga di comando

def test_cli_giro_completo(nas, monkeypatch, tmp_path, capsys):
    from ponte.__main__ import main

    url, _ = nas
    monkeypatch.setenv(cfg.ENV_URL, url)
    monkeypatch.setenv(cfg.ENV_UTENTE, "r3")
    monkeypatch.setenv(cfg.ENV_PASSWORD, "prova")
    monkeypatch.setenv(cfg.ENV_RADICE, "/R3")

    sorgente = tmp_path / "stato.json"
    sorgente.write_text('{"h2": "aperta"}', encoding="utf-8")

    assert main(["--check"]) == 0
    assert "IL PONTE REGGE" in capsys.readouterr().out

    assert main(["--deposita", str(sorgente), "--come", "capsule/stato.json"]) == 0
    assert "riletto dal NAS" in capsys.readouterr().out

    assert main(["--elenca", "capsule"]) == 0
    assert "stato.json" in capsys.readouterr().out

    ripreso = tmp_path / "ripreso.json"
    assert main(["--preleva", "capsule/stato.json", "--in", str(ripreso)]) == 0
    assert ripreso.read_text(encoding="utf-8") == '{"h2": "aperta"}'


def test_cli_senza_configurazione_esce_2(monkeypatch, capsys):
    from ponte.__main__ import main

    for v in (cfg.ENV_URL, cfg.ENV_UTENTE, cfg.ENV_PASSWORD, cfg.ENV_QUICKCONNECT):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(cfg, "FILE_FUORI_REPO", __import__("pathlib").Path("/non/esiste"))
    assert main(["--check"]) == 2
    assert "NON E' CONFIGURATO" in capsys.readouterr().out


def test_cli_prova_locale_dichiara_cosa_non_prova(capsys):
    from ponte.__main__ import main

    assert main(["--prova-locale"]) == 0
    uscita = capsys.readouterr().out
    assert "il client parla WebDAV" in uscita
    assert "NON PROVA" in uscita
