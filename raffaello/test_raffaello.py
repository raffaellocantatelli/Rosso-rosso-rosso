"""Test del companion Raffaello.  Esecuzione: python -m raffaello.test_raffaello"""

import unittest
from datetime import datetime, timezone

from raffaello.companion import MemoriaEpisodica, Raffaello
from raffaello.identita import carica


OGGI = datetime.now(timezone.utc).date().isoformat()


class ClientFinto:
    """Sta al posto di ClaudeClient: stessa forma, nessuna rete."""

    def __init__(self, testo="lettura, significato, azione", via_api=True, disponibile=True):
        self.testo, self.via_api, self._disponibile = testo, via_api, disponibile
        self.chiamate = []

    def disponibile(self):
        return self._disponibile

    def completa(self, sistema, utente):
        self.chiamate.append({"sistema": sistema, "utente": utente})
        return type("R", (), {
            "testo": self.testo, "via_api": self.via_api, "provider": "finto",
        })()


class TestIdentita(unittest.TestCase):
    def test_il_master_e_la_fonte(self):
        self.assertTrue(carica().da_master, "sdq1_master.json non è stato letto")

    def test_tratti_canonici(self):
        for tratto in ("empatico", "diretto", "protettivo"):
            self.assertIn(tratto, carica().tratti)

    def test_prompt_contiene_stile_e_struttura(self):
        prompt = carica().prompt_sistema()
        self.assertIn("Raffaello", prompt)
        self.assertIn("italiano", prompt)
        self.assertIn("una sola azione concreta", prompt)

    def test_fallback_se_il_master_manca(self):
        ident = carica(percorso="/percorso/che/non/esiste.json")
        self.assertFalse(ident.da_master)
        self.assertIn("empatico", ident.tratti)


class TestRisposta(unittest.TestCase):
    def test_usa_il_client_quando_c_e(self):
        client = ClientFinto("Ecco cosa vedo.")
        r = Raffaello(client=client).rispondi("come sto andando")
        self.assertEqual(r.testo, "Ecco cosa vedo.")
        self.assertFalse(r.offline)
        self.assertEqual(r.provider, "finto")

    def test_l_identita_arriva_nel_prompt_di_sistema(self):
        client = ClientFinto()
        Raffaello(client=client).rispondi("ciao")
        self.assertIn("Raffaello", client.chiamate[0]["sistema"])

    def test_senza_client_si_dichiara_offline(self):
        r = Raffaello(client=None).rispondi("come sto andando")
        self.assertTrue(r.offline)
        self.assertIn("offline", r.testo)
        self.assertIn("non è output di un modello", r.testo)

    def test_client_non_disponibile_equivale_a_offline(self):
        r = Raffaello(client=ClientFinto(disponibile=False)).rispondi("ciao")
        self.assertTrue(r.offline)

    def test_risposta_vuota_non_viene_spacciata(self):
        """Un provider che risponde stringa vuota non deve produrre una
        risposta vuota apparentemente legittima."""
        r = Raffaello(client=ClientFinto(testo="   ")).rispondi("ciao")
        self.assertTrue(r.offline)
        self.assertIn("offline", r.testo)

    def test_messaggio_vuoto_non_esplode(self):
        r = Raffaello(client=ClientFinto()).rispondi("   ")
        self.assertTrue(r.offline)
        self.assertIn("Non mi hai chiesto niente", r.testo)


class TestMemoriaEpisodica(unittest.TestCase):
    def setUp(self):
        self.raffaello = Raffaello(client=ClientFinto(), memoria=MemoriaEpisodica(backend=None))

    def test_ogni_scambio_diventa_episodio(self):
        self.raffaello.rispondi("parliamo del protocollo rosso")
        self.assertEqual(len(self.raffaello.memoria), 1)

    def test_l_episodio_porta_la_data(self):
        self.raffaello.rispondi("primo messaggio")
        self.assertEqual(self.raffaello.memoria.esporta()[0]["data"], OGGI)

    def test_richiama_gli_episodi_affini(self):
        self.raffaello.rispondi("parliamo del protocollo rosso rosso rosso")
        r = self.raffaello.rispondi("dimmi del protocollo rosso rosso rosso")
        self.assertGreaterEqual(len(r.episodi_richiamati), 1)

    def test_non_richiama_episodi_estranei(self):
        self.raffaello.rispondi("ricetta della carbonara")
        r = self.raffaello.rispondi("configurazione dei nodi r3")
        self.assertEqual(r.episodi_richiamati, [])

    def test_gli_episodi_finiscono_nel_prompt(self):
        client = ClientFinto()
        r = Raffaello(client=client, memoria=MemoriaEpisodica(backend=None))
        r.rispondi("il protocollo rosso rosso rosso")
        r.rispondi("ancora il protocollo rosso rosso rosso")
        self.assertIn("Episodi precedenti", client.chiamate[1]["utente"])

    def test_episodi_per_giorno(self):
        self.raffaello.rispondi("uno")
        self.assertEqual(len(self.raffaello.memoria.del_giorno(OGGI)), 1)
        self.assertEqual(self.raffaello.memoria.del_giorno("2020-01-01"), [])

    def test_esporta_e_serializzabile(self):
        self.raffaello.rispondi("uno")
        voce = self.raffaello.memoria.esporta()[0]
        self.assertEqual(set(voce), {"messaggio", "risposta", "data", "provider"})

    def test_memoria_vuota_non_richiama_nulla(self):
        self.assertEqual(MemoriaEpisodica(backend=None).cerca("qualsiasi cosa"), [])


class TestContesto(unittest.TestCase):
    def test_il_contesto_arriva_nel_prompt(self):
        client = ClientFinto()
        Raffaello(client=client).rispondi("come va", contesto={"zona": "recupero"})
        self.assertIn("zona: recupero", client.chiamate[0]["utente"])

    def test_senza_contesto_nessuna_sezione_dati(self):
        client = ClientFinto()
        Raffaello(client=client).rispondi("come va")
        self.assertNotIn("Dati di contesto", client.chiamate[0]["utente"])


if __name__ == "__main__":
    unittest.main()
