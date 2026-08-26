"""Il backup è opzionale: la sua assenza non deve mai fermare il sistema."""

import json

from usa_backup_rosso import BackupSistemaRosso


def scrivi(tmp_path, dati, nome="backup.json"):
    percorso = tmp_path / nome
    percorso.write_text(json.dumps(dati, ensure_ascii=False), encoding="utf-8")
    return str(percorso)


def test_backup_assente_non_solleva(tmp_path):
    backup = BackupSistemaRosso(str(tmp_path / "non-esiste.json"))
    assert backup.chunks == []
    assert not backup
    assert "assente" in backup.errore


def test_backup_illeggibile_non_solleva(tmp_path):
    rotto = tmp_path / "rotto.json"
    rotto.write_text("{{{", encoding="utf-8")
    backup = BackupSistemaRosso(str(rotto))
    assert backup.chunks == []
    assert "illeggibile" in backup.errore


def test_formato_con_chiave_chunks(tmp_path):
    percorso = scrivi(tmp_path, {"chunks": [{"id": "a", "tag": ["scacchiera"]}]})
    assert len(BackupSistemaRosso(percorso)) == 1


def test_formato_lista_nuda(tmp_path):
    percorso = scrivi(tmp_path, [{"id": "a", "tag": ["scacchiera"]}])
    assert len(BackupSistemaRosso(percorso)) == 1


def test_voci_non_dict_scartate(tmp_path):
    percorso = scrivi(tmp_path, {"chunks": [{"id": "a"}, "spazzatura", 42]})
    backup = BackupSistemaRosso(percorso)
    assert len(backup) == 1
    assert "scartate" in backup.errore


def test_cerca_per_tag_case_insensitive(tmp_path):
    percorso = scrivi(tmp_path, {"chunks": [
        {"id": "a", "tag": ["Scacchiera"]},
        {"id": "b", "tag": "scacchiera"},
        {"id": "c", "tag": ["altro"]},
    ]})
    backup = BackupSistemaRosso(percorso)
    assert {c["id"] for c in backup.cerca_per_tag("SCACCHIERA")} == {"a", "b"}


def test_tag_multipli_senza_duplicati(tmp_path):
    percorso = scrivi(tmp_path, {"chunks": [
        {"id": "a", "tag": ["protocollo_rosso", "R³∞"]},
        {"id": "b", "tag": ["R³∞"]},
    ]})
    backup = BackupSistemaRosso(percorso)
    risultati = backup.cerca_per_tag_multipli(["protocollo_rosso", "R³∞"])
    assert [c["id"] for c in risultati] == ["a", "b"]


def test_cerca_testo_e_tag_disponibili(tmp_path):
    percorso = scrivi(tmp_path, {"chunks": [
        {"id": "a", "testo": "Tunnel sottomarino", "tag": ["infra"]},
    ]})
    backup = BackupSistemaRosso(percorso)
    assert len(backup.cerca_testo("TUNNEL")) == 1
    assert backup.tag_disponibili() == ["infra"]
