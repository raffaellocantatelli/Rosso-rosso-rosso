"""Test della memoria di SDQ-1 (MEMO-002 / VectorStore).

Solo unittest della stdlib: il resto di sdq1 non ha dipendenze esterne
e i test non sono una buona ragione per introdurne.

    python -m unittest discover -s tests -t .
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdq1.memory.vector_store import REDACTED_MARKER, VectorStore  # noqa: E402


def store_con(voci):
    """Scrive uno store con contenuto noto e restituisce (VectorStore, path).

    Costruire il file a mano invece di usare add() tiene i test
    deterministici: id e timestamp sono fissati, non dipendono
    dall'orologio o dall'ordine di inserimento.
    """
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(voci, f, ensure_ascii=False)
    return VectorStore(path=path), path


def leggi(path):
    """Rilegge lo store da disco — quello che conta è cosa è stato salvato."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestRedazionePrivacy(unittest.TestCase):
    def setUp(self):
        self.store, self.path = store_con([])

    def tearDown(self):
        os.unlink(self.path)

    def test_blocco_private_non_finisce_su_disco(self):
        self.store.add("la chiave è <private>segreto-123</private> ok", "risposta")
        salvato = leggi(self.path)
        self.assertNotIn("segreto-123", json.dumps(salvato))
        self.assertIn(REDACTED_MARKER, salvato[0]["input"])

    def test_redazione_anche_nella_risposta(self):
        self.store.add("domanda", "eccolo: <private>token-abc</private>")
        salvato = leggi(self.path)
        self.assertNotIn("token-abc", json.dumps(salvato))

    def test_tag_case_insensitive_e_multilinea(self):
        self.store.add("prima <PRIVATE>riga uno\nriga due</PRIVATE> dopo", "r")
        salvato = leggi(self.path)
        self.assertNotIn("riga uno", salvato[0]["input"])
        self.assertNotIn("riga due", salvato[0]["input"])

    def test_piu_blocchi_nello_stesso_testo(self):
        self.store.add("<private>uno</private> in mezzo <private>due</private>", "r")
        salvato = leggi(self.path)
        self.assertNotIn("uno", salvato[0]["input"])
        self.assertNotIn("due", salvato[0]["input"])
        self.assertIn("in mezzo", salvato[0]["input"])

    def test_voce_interamente_privata_resta_un_marcatore(self):
        voce = self.store.add("<private>tutto quanto</private>", "r")
        self.assertEqual(voce["input"], REDACTED_MARKER)
        self.assertNotIn("tutto quanto", voce["input"])

    def test_testo_senza_tag_resta_intatto(self):
        voce = self.store.add("nessun tag qui", "risposta normale")
        self.assertEqual(voce["input"], "nessun tag qui")
        self.assertEqual(voce["response"], "risposta normale")


class TestIdCitabili(unittest.TestCase):
    def test_retrieve_espone_id_per_citazione(self):
        store, path = store_con([
            {"id": 7, "input": "memoria persistente del sistema", "response": "r", "timestamp": 1.0},
        ])
        try:
            hits = store.retrieve("memoria persistente")
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["id"], 7)
        finally:
            os.unlink(path)

    def test_id_non_collide_dopo_una_rimozione(self):
        """len()+1 riassegnava id già usati: mem#2 avrebbe indicato due voci."""
        store, path = store_con([
            {"id": 1, "input": "prima voce", "response": "r", "timestamp": 1.0},
            {"id": 2, "input": "seconda voce", "response": "r", "timestamp": 2.0},
        ])
        try:
            del store._entries[0]
            nuova = store.add("terza voce", "r")
            self.assertEqual(nuova["id"], 3)
            ids = [e["id"] for e in store._entries]
            self.assertEqual(len(ids), len(set(ids)))
        finally:
            os.unlink(path)


class TestRecuperoConfigurabile(unittest.TestCase):
    def setUp(self):
        self.store, self.path = store_con([
            {"id": 1, "input": "sistema di quadranti multi agente", "response": "r1", "timestamp": 1.0},
            {"id": 2, "input": "ridondanza documentale fra tre nodi", "response": "r2", "timestamp": 2.0},
            {"id": 3, "input": "sistema di backup universale", "response": "r3", "timestamp": 3.0},
        ])

    def tearDown(self):
        os.unlink(self.path)

    def test_top_k_limita_i_risultati(self):
        self.assertLessEqual(len(self.store.retrieve("sistema", top_k=1)), 1)

    def test_ordinamento_per_score_decrescente(self):
        hits = self.store.retrieve("sistema di quadranti", top_k=3)
        punteggi = [h["score"] for h in hits]
        self.assertEqual(punteggi, sorted(punteggi, reverse=True))

    def test_min_score_esclude_le_voci_deboli(self):
        larghi = self.store.retrieve("sistema", top_k=10, min_score=0.0)
        stretti = self.store.retrieve("sistema", top_k=10, min_score=0.9)
        self.assertGreater(len(larghi), len(stretti))
        for h in stretti:
            self.assertGreater(h["score"], 0.9)

    def test_query_senza_corrispondenze_non_restituisce_nulla(self):
        self.assertEqual(self.store.retrieve("xilofono krypton"), [])


class TestDeduplicazione(unittest.TestCase):
    """Il run giornaliero ripete lo stesso prompt: senza dedup il contesto
    si riempie di copie identiche e il sistema si autocita (P5)."""

    def setUp(self):
        self.store, self.path = store_con([
            {"id": 1, "input": "riflessione giornaliera del sistema", "response": "vecchia", "timestamp": 1.0},
            {"id": 2, "input": "riflessione giornaliera del sistema", "response": "intermedia", "timestamp": 2.0},
            {"id": 3, "input": "riflessione giornaliera del sistema", "response": "recente", "timestamp": 3.0},
            {"id": 4, "input": "ridondanza documentale fra nodi", "response": "altro", "timestamp": 4.0},
        ])

    def tearDown(self):
        os.unlink(self.path)

    def test_le_copie_identiche_collassano_in_una(self):
        hits = self.store.retrieve("riflessione giornaliera del sistema", top_k=3)
        self.assertEqual(len(hits), 1)

    def test_fra_le_copie_sopravvive_la_piu_recente(self):
        hits = self.store.retrieve("riflessione giornaliera del sistema", top_k=3)
        self.assertEqual(hits[0]["id"], 3)
        self.assertEqual(hits[0]["response"], "recente")

    def test_il_dedup_non_scarta_le_voci_diverse(self):
        hits = self.store.retrieve("riflessione giornaliera ridondanza nodi", top_k=10)
        self.assertEqual(len({h["input"] for h in hits}), 2)

    def test_dedup_normalizza_spazi_e_maiuscole(self):
        store, path = store_con([
            {"id": 1, "input": "Riflessione  Giornaliera", "response": "a", "timestamp": 1.0},
            {"id": 2, "input": "riflessione giornaliera", "response": "b", "timestamp": 2.0},
        ])
        try:
            self.assertEqual(len(store.retrieve("riflessione giornaliera")), 1)
        finally:
            os.unlink(path)

    def test_dedup_disattivabile_per_ispezione(self):
        hits = self.store.retrieve("riflessione giornaliera del sistema", top_k=10, dedup=False)
        self.assertEqual(len(hits), 3)


class TestPersistenza(unittest.TestCase):
    def test_lo_store_sopravvive_alla_riapertura(self):
        store, path = store_con([])
        try:
            store.add("voce da ritrovare dopo il riavvio", "r")
            riaperto = VectorStore(path=path)
            self.assertEqual(len(riaperto), 1)
            self.assertEqual(len(riaperto.retrieve("voce da ritrovare")), 1)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
