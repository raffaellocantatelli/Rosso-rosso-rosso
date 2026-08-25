"""Il verificatore deve poter dire di no, e non deve poter dire di sì troppo.

Il test che conta più di tutti è `test_verifica_fallita_non_diventa_regge`:
è la differenza fra «non ho potuto controllare» e «va tutto bene», cioè fra
un contraddittorio e un timbro.
"""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import registro_ipotesi as registro  # noqa: E402
import verificatore  # noqa: E402


def falsificatore_finto(cartella: Path, nome: str, codice: int) -> dict:
    """Uno script che esce con il codice richiesto, e lo dice."""
    percorso = cartella / f"{nome}.py"
    percorso.write_text(
        f"import sys\nprint('falsificatore {nome}: esco con {codice}')\n"
        f"sys.exit({codice})\n",
        encoding="utf-8",
    )
    return {"comando": [sys.executable, str(percorso)], "descrizione": nome}


class BaseVerificatore(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.cartella = Path(self.dir.name)

        self.registro_originale = registro.REGISTRO_PATH
        self.verifiche_originale = verificatore.VERIFICHE_PATH
        registro.REGISTRO_PATH = str(self.cartella / "registro.json")
        verificatore.VERIFICHE_PATH = str(self.cartella / "verifiche.jsonl")

    def tearDown(self) -> None:
        registro.REGISTRO_PATH = self.registro_originale
        verificatore.VERIFICHE_PATH = self.verifiche_originale
        self.dir.cleanup()

    def scrivi_registro(self, voci: list[dict]) -> None:
        for voce in voci:
            voce.setdefault("criterio_falsificazione", "criterio di prova")
            voce.setdefault("falsificatore", None)
            voce.setdefault("scadenza", None)
            voce.setdefault("verifiche", dict(registro.CAMPI_DEFAULT["verifiche"]))
        Path(registro.REGISTRO_PATH).write_text(
            json.dumps(voci, ensure_ascii=False), encoding="utf-8"
        )

    def stato(self, id_: str) -> str:
        for h in registro.carica():
            if h["id"] == id_:
                return h["stato"]
        raise KeyError(id_)


class TestEsiti(BaseVerificatore):
    def test_exit_zero_fa_cadere_l_ipotesi(self):
        self.scrivi_registro([{
            "id": "X1", "testo": "cade", "stato": registro.APERTA,
            "falsificatore": falsificatore_finto(self.cartella, "cade", 0),
        }])
        risultati = verificatore.verifica()
        self.assertEqual(risultati[0]["esito"], "caduta")
        self.assertEqual(self.stato("X1"), registro.FALSIFICATA)

    def test_exit_uno_la_fa_reggere_ma_non_confermare(self):
        self.scrivi_registro([{
            "id": "X2", "testo": "regge", "stato": registro.APERTA,
            "falsificatore": falsificatore_finto(self.cartella, "regge", 1),
        }])
        risultati = verificatore.verifica()
        self.assertEqual(risultati[0]["esito"], "regge")
        self.assertEqual(self.stato("X2"), registro.RETTA)
        self.assertNotEqual(self.stato("X2"), registro.CONFERMATA)

    def test_verifica_fallita_non_diventa_regge(self):
        """Il test centrale: un controllo che non conclude non è un sì."""
        self.scrivi_registro([{
            "id": "X3", "testo": "boh", "stato": registro.APERTA,
            "falsificatore": falsificatore_finto(self.cartella, "boh", 2),
        }])
        risultati = verificatore.verifica()
        self.assertEqual(risultati[0]["esito"], "verifica_fallita")
        self.assertEqual(self.stato("X3"), registro.APERTA)

    def test_comando_inesistente_non_conclude(self):
        self.scrivi_registro([{
            "id": "X4", "testo": "rotto", "stato": registro.APERTA,
            "falsificatore": {"comando": ["/non/esiste/affatto"], "descrizione": "rotto"},
        }])
        risultati = verificatore.verifica()
        self.assertEqual(risultati[0]["esito"], "verifica_fallita")
        self.assertIn("comando non trovato", risultati[0]["output"])
        self.assertEqual(self.stato("X4"), registro.APERTA)

    def test_senza_falsificatore_diventa_non_verificabile(self):
        self.scrivi_registro([{
            "id": "X5", "testo": "indecidibile", "stato": registro.APERTA,
            "falsificatore": None,
        }])
        risultati = verificatore.verifica()
        self.assertEqual(risultati[0]["esito"], "non_verificabile")
        self.assertEqual(self.stato("X5"), registro.NON_VERIFICABILE)

    def test_contatore_delle_verifiche(self):
        self.scrivi_registro([{
            "id": "X6", "testo": "regge", "stato": registro.APERTA,
            "falsificatore": falsificatore_finto(self.cartella, "regge", 1),
        }])
        verificatore.verifica()
        verificatore.verifica()
        voce = [h for h in registro.carica() if h["id"] == "X6"][0]
        self.assertEqual(voce["verifiche"]["eseguite"], 2)
        self.assertEqual(voce["verifiche"]["cadute"], 0)


class TestDeclassamento(BaseVerificatore):
    def test_confermata_senza_prova_esterna_viene_declassata(self):
        self.scrivi_registro([{
            "id": "X7", "testo": "confermata da sola", "stato": registro.CONFERMATA,
            "falsificatore": falsificatore_finto(self.cartella, "regge", 1),
        }])
        risultati = verificatore.verifica()
        self.assertTrue(risultati[0]["declassamento"])
        self.assertEqual(self.stato("X7"), registro.RETTA)
        self.assertIn("[P5]", risultati[0]["output"])

    def test_il_declassamento_finisce_nel_deposito(self):
        self.scrivi_registro([{
            "id": "X8", "testo": "x", "stato": registro.CONFERMATA,
            "falsificatore": falsificatore_finto(self.cartella, "regge", 1),
        }])
        verificatore.verifica()
        righe = Path(verificatore.VERIFICHE_PATH).read_text(encoding="utf-8").splitlines()
        voce = json.loads(righe[0])
        self.assertTrue(voce["declassamento"])
        self.assertEqual(voce["stato_prima"], registro.CONFERMATA)
        self.assertEqual(voce["stato_dopo"], registro.RETTA)
        self.assertIn("output_sha256", voce)


class TestSolaLettura(BaseVerificatore):
    def test_prova_non_scrive_niente(self):
        self.scrivi_registro([{
            "id": "X9", "testo": "x", "stato": registro.APERTA,
            "falsificatore": falsificatore_finto(self.cartella, "cade", 0),
        }])
        verificatore.verifica(scrivi=False)
        self.assertEqual(self.stato("X9"), registro.APERTA)
        self.assertFalse(os.path.exists(verificatore.VERIFICHE_PATH))

    def test_filtro_per_id(self):
        self.scrivi_registro([
            {"id": "A", "testo": "a", "stato": registro.APERTA,
             "falsificatore": falsificatore_finto(self.cartella, "regge", 1)},
            {"id": "B", "testo": "b", "stato": registro.APERTA,
             "falsificatore": falsificatore_finto(self.cartella, "cade", 0)},
        ])
        risultati = verificatore.verifica(ids=["A"])
        self.assertEqual([r["ipotesi"] for r in risultati], ["A"])
        self.assertEqual(self.stato("B"), registro.APERTA)


class TestPorteChiuse(BaseVerificatore):
    """Gli stati che l'esecuzione assegna non si possono dichiarare a mano."""

    def setUp(self) -> None:
        super().setUp()
        self.scrivi_registro([{"id": "Y", "testo": "y", "stato": registro.APERTA}])

    def test_retta_a_mano_e_vietata(self):
        with self.assertRaises(ValueError) as errore:
            registro.aggiorna_stato("Y", registro.RETTA)
        self.assertIn("P5", str(errore.exception))

    def test_falsificata_a_mano_e_sempre_permessa(self):
        """L'asimmetria: P6 blocca la conferma, mai la smentita.

        Una macchina deve dire «ha retto»; chiunque può dire «è caduta».
        """
        registro.aggiorna_stato("Y", registro.FALSIFICATA)
        self.assertEqual(
            [h for h in registro.carica() if h["id"] == "Y"][0]["stato"],
            registro.FALSIFICATA,
        )

    def test_confermata_richiede_una_fonte_esterna(self):
        with self.assertRaises(ValueError) as errore:
            registro.aggiorna_stato("Y", registro.CONFERMATA)
        self.assertIn("fonte esterna", str(errore.exception))

    def test_confermata_con_prova_esterna_passa(self):
        registro.aggiorna_stato("Y", registro.CONFERMATA, prova_esterna="lettera di X, 2026-09-01")
        voce = [h for h in registro.carica() if h["id"] == "Y"][0]
        self.assertEqual(voce["stato"], registro.CONFERMATA)
        self.assertEqual(voce["prova_esterna"], "lettera di X, 2026-09-01")

    def test_stato_sconosciuto_rifiutato(self):
        with self.assertRaises(ValueError):
            registro.aggiorna_stato("Y", "QUASI_VERA")

    def test_ipotesi_senza_criterio_rifiutata(self):
        with self.assertRaises(ValueError) as errore:
            registro.aggiungi("Z", "senza criterio", "   ")
        self.assertIn("P6", str(errore.exception))


class TestFalsificatoriReali(unittest.TestCase):
    """I tre falsificatori del repo rispettano il contratto degli exit code."""

    def test_exit_code_ammessi(self):
        radice = Path(__file__).resolve().parent.parent
        import subprocess
        for nome in ("h2_battito_e_contatto", "h3_italiano", "h4_contraddittorio"):
            with self.subTest(falsificatore=nome):
                esito = subprocess.run(
                    [sys.executable, f"falsificatori/{nome}.py"],
                    cwd=radice, capture_output=True, text=True, timeout=60,
                )
                self.assertIn(esito.returncode, (0, 1, 2),
                              f"{nome} esce con {esito.returncode}")


if __name__ == "__main__":
    unittest.main()
