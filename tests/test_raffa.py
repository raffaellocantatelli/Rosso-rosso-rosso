"""Test di RAFFA-001 (analisi semantica).

    python -m unittest discover -s tests -t .
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdq1.agents import raffa  # noqa: E402
from sdq1.context import Context  # noqa: E402


def analizza(testo):
    return raffa.run(Context(testo)).intent


class TestClassificazione(unittest.TestCase):
    def test_punto_interrogativo_fa_domanda(self):
        self.assertEqual(analizza("Il sistema funziona?")["tipo"], "domanda")

    def test_interrogativo_iniziale_senza_punto(self):
        intent = analizza("come funziona la cascata dei provider")
        self.assertEqual(intent["tipo"], "domanda")
        self.assertEqual(intent["interrogativo"], "come")

    def test_interrogativo_riconosciuto_anche_con_punto(self):
        self.assertEqual(analizza("Quando parte il run?")["interrogativo"], "quando")

    def test_domanda_senza_interrogativo_esplicito(self):
        self.assertIsNone(analizza("Il backup e' andato a buon fine?")["interrogativo"])

    def test_verbo_imperativo_iniziale_fa_comando(self):
        self.assertEqual(analizza("crea un backup completo")["tipo"], "comando")

    def test_punteggiatura_attaccata_al_verbo(self):
        """lower.split() lasciava 'crea,' attaccato e il comando sfuggiva."""
        self.assertEqual(analizza("Crea, subito, un backup")["tipo"], "comando")

    def test_affermazione_come_default(self):
        self.assertEqual(analizza("Il sistema gira in locale")["tipo"], "affermazione")

    def test_la_domanda_prevale_sul_verbo_di_comando(self):
        self.assertEqual(analizza("Come si crea un backup?")["tipo"], "domanda")

    def test_input_vuoto_non_esplode(self):
        intent = analizza("   ")
        self.assertEqual(intent["tipo"], "affermazione")
        self.assertEqual(intent["parole_chiave"], [])


class TestParoleChiave(unittest.TestCase):
    def test_ordina_per_frequenza_non_per_alfabeto(self):
        """Regressione: sorted(set(...))[:8] sceglieva in base all'iniziale.

        Qui 'sistema' compare tre volte ma in fondo all'alfabeto: con il
        vecchio ordinamento veniva tagliato dalle otto parole che lo
        precedevano, per quanto fosse il tema della frase.
        """
        testo = ("analisi backup cache database elenco firma grafico indice "
                 "logica sistema sistema sistema")
        chiave = analizza(testo)["parole_chiave"]
        self.assertEqual(chiave[0], "sistema")

    def test_a_parita_di_frequenza_vince_la_piu_lunga(self):
        chiave = analizza("dato ridondanza")["parole_chiave"]
        self.assertEqual(chiave, ["ridondanza", "dato"])

    def test_esclude_le_stopword(self):
        chiave = analizza("questo sistema senza quello")["parole_chiave"]
        self.assertEqual(chiave, ["sistema"])

    def test_esclude_gli_interrogativi(self):
        chiave = analizza("cosa fa questo sistema?")["parole_chiave"]
        self.assertNotIn("cosa", chiave)
        self.assertIn("sistema", chiave)

    def test_scarta_le_parole_troppo_corte(self):
        self.assertEqual(analizza("il re va su")["parole_chiave"], [])

    def test_elisione_conserva_la_parola_piena(self):
        self.assertIn("emergenza", analizza("e' un'emergenza vera")["parole_chiave"])

    def test_non_supera_il_tetto(self):
        # Niente cifre nei nomi: il tokenizer le scarta e "parola1"/"parola2"
        # collasserebbero in un'unica parola, svuotando il test.
        testo = " ".join("parola" + chr(97 + i) * 2 for i in range(20))
        chiave = analizza(testo)["parole_chiave"]
        self.assertEqual(len(set(chiave)), raffa.MAX_PAROLE_CHIAVE)

    def test_risultato_deterministico(self):
        testo = "alfa beta gamma delta alfa beta"
        self.assertEqual(analizza(testo)["parole_chiave"], analizza(testo)["parole_chiave"])

    def test_maiuscole_normalizzate(self):
        self.assertEqual(analizza("SISTEMA Sistema sistema")["parole_chiave"], ["sistema"])


class TestCompatibilita(unittest.TestCase):
    """GEN-006 legge ctx.intent['tipo'] e ['parole_chiave']: le chiavi
    storiche devono restare, o il prompt si rompe in silenzio."""

    def test_chiavi_storiche_presenti(self):
        intent = analizza("Analizza il sistema")
        for chiave in ("tipo", "parole_chiave", "lunghezza"):
            self.assertIn(chiave, intent)

    def test_lunghezza_e_quella_del_testo_ripulito(self):
        self.assertEqual(analizza("  ciao  ")["lunghezza"], len("ciao"))

    def test_parole_chiave_e_una_lista(self):
        self.assertIsInstance(analizza("il sistema gira")["parole_chiave"], list)


if __name__ == "__main__":
    unittest.main()
