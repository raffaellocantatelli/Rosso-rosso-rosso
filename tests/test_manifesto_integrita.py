"""Regressioni di portabilita del Guardian Layer."""
from pathlib import Path

import manifesto_integrita as mi


def test_hash_logico_ignora_i_terminatori_di_riga(tmp_path):
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    lf.write_bytes(b"uno\ndue\n")
    crlf.write_bytes(b"uno\r\ndue\r\n")
    assert mi.sha256(lf) == mi.sha256(crlf)


def test_chiave_manifesto_e_sempre_posix():
    chiave = mi._chiave(Path("cartella") / "sotto" / "file.py")
    assert chiave == "cartella/sotto/file.py"
