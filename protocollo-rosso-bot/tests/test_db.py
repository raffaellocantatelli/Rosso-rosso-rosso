"""Il database fa quello che dice, e non fa quello che non deve."""

import os
import tempfile
import unittest
from pathlib import Path

from bot import db


class TestDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.percorso = Path(self.dir.name) / "prova.db"
        os.environ["PROTOCOLLO_DB"] = str(self.percorso)
        db.init_db()

    def tearDown(self) -> None:
        os.environ.pop("PROTOCOLLO_DB", None)
        self.dir.cleanup()

    def test_init_idempotente(self):
        db.init_db()
        db.init_db()
        self.assertTrue(self.percorso.exists())

    def test_utente_non_duplicato(self):
        db.registra_utente(7, "Claudio")
        db.registra_utente(7, "Claudio")
        with db.connect() as conn:
            n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        self.assertEqual(n, 1)

    def test_possibilita_sempre_ipotesi(self):
        db.aggiungi_possibilita(7, "il campo del già", "esperimento X")
        db.aggiungi_possibilita(7, "senza criterio", None)
        righe = db.elenca_possibilita(7)
        self.assertEqual([r["etichetta"] for r in righe], ["IPOTESI", "IPOTESI"])

    def test_nessuna_funzione_chiude_una_possibilita(self):
        """P6 vale anche sul codice: qui non esiste il modo di chiudere."""
        vietate = {"chiudi_possibilita", "conferma_possibilita",
                   "promuovi_possibilita", "elimina_possibilita"}
        self.assertEqual(vietate & set(dir(db)), set())

    def test_falsificazione_mancante_resta_none(self):
        db.aggiungi_possibilita(7, "x", None)
        self.assertIsNone(db.elenca_possibilita(7)[0]["falsificazione"])

    def test_azioni_contate_separatamente_da_quelle_verificabili(self):
        db.registra_azione(7, "scritta una riga", "commit abc123")
        db.registra_azione(7, "pensato molto", None)
        db.registra_azione(7, "pensato ancora", "")
        self.assertEqual(db.conta_azioni(7), 3)
        self.assertEqual(db.conta_azioni_verificabili(7), 1)

    def test_azioni_di_utenti_diversi_non_si_mescolano(self):
        db.registra_azione(1, "mia", "prova")
        db.registra_azione(2, "tua", "prova")
        self.assertEqual(len(db.elenca_azioni(1)), 1)
        self.assertEqual(len(db.elenca_azioni(2)), 1)

    def test_visita_registra_la_durata_reale(self):
        visita = db.inizia_visita(7)
        db.concludi_visita(visita, 3.2, False)
        riga = db.elenca_visite(7)[0]
        self.assertEqual(riga["durata_gesto"], 3.2)
        self.assertEqual(riga["gesto_lento"], 0)


if __name__ == "__main__":
    unittest.main()
