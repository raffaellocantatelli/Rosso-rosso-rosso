"""I testi non possono mentire su cosa sono.

Questi test non giudicano lo stile: controllano le due regole del
Capitolo 3 che un'interfaccia puo' violare senza accorgersene.
"""

import re
import unittest
from pathlib import Path

from bot import handlers, texts

TESI_GRANDE = "esiste già"


class TestTesti(unittest.TestCase):
    def test_la_tesi_porta_sempre_la_sua_etichetta(self):
        for nome, valore in vars(texts).items():
            if not isinstance(valore, str) or TESI_GRANDE not in valore:
                continue
            self.assertIn("IPOTESI", valore,
                          f"{nome} enuncia la tesi senza etichetta")

    def test_la_tesi_dichiara_come_potrebbe_cadere(self):
        self.assertIn("P6", texts.TESI)
        self.assertIn("UNKNOWN", texts.TESI)

    def test_nessun_testo_dichiara_dimostrato(self):
        vietate = ("è dimostrato", "è provato", "è certo", "prova definitiva")
        for nome, valore in vars(texts).items():
            if not isinstance(valore, str):
                continue
            for frase in vietate:
                self.assertNotIn(frase, valore.lower(), f"{nome}: «{frase}»")

    def test_le_quattro_etichette_ci_sono_tutte(self):
        self.assertEqual(
            set(texts.ETICHETTA_RISPOSTE),
            {"RECUPERATO", "INFERITO", "IPOTESI", "UNKNOWN"},
        )

    def test_tre_veli(self):
        self.assertEqual(set(texts.VELI), {"1", "2", "3"})

    def test_origine_dichiarata(self):
        self.assertIn("Claudio Terzi", texts.ORIGINE)
        self.assertIn("CT-LGAI-001", texts.ORIGINE)
        self.assertIn("Claudio Terzi", texts.START)

    def test_i_segnaposto_delle_format_sono_quelli_attesi(self):
        attesi = {
            "SANTUARIO_TROPPO_VELOCE": {"secondi"},
            "SANTUARIO_USCITA_LENTA": {"secondi"},
            "SANTUARIO_USCITA_VELOCE": {"secondi"},
            "POSSIBILITA_SALVATA_CON_CRITERIO": {"numero", "testo",
                                                 "falsificazione"},
            "POSSIBILITA_SALVATA_UNKNOWN": {"numero", "testo"},
            "AZIONE_SALVATA": {"numero", "quando", "descrizione", "verifica",
                               "totale"},
            "AZIONE_SALVATA_NON_VERIFICABILE": {"numero", "quando",
                                                "descrizione", "totale"},
            "ETICHETTA_SCEGLI": {"testo"},
        }
        for nome, campi in attesi.items():
            testo = getattr(texts, nome)
            trovati = set(re.findall(r"{(\w+)}", testo))
            self.assertEqual(trovati, campi, nome)


class TestReadme(unittest.TestCase):
    """Il README elenca i comandi: che siano quelli veri."""

    def test_i_comandi_del_readme_esistono(self):
        readme = (Path(__file__).resolve().parent.parent / "README.md").read_text()
        dichiarati = set(re.findall(r"^\| `/(\w+)`", readme, re.MULTILINE))
        implementati = {nome for nome, _ in handlers.COMANDI}
        self.assertTrue(dichiarati, "nessun comando trovato nel README")
        self.assertEqual(dichiarati - implementati, set(),
                         "il README promette comandi che non esistono")


if __name__ == "__main__":
    unittest.main()
