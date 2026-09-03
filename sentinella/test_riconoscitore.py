# -*- coding: utf-8 -*-
"""Le guardie del riconoscitore.

Ogni test qui sotto difende una regola che, se saltasse in silenzio, farebbe
dire alla mappa qualcosa che non sa. Non verificano che il codice giri:
verificano che non menta.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""
import unittest

from . import fonti
from . import riconoscitore as ric


def _inv(chiave, items, **extra):
    return fonti.inviluppo(chiave, items=items, total=len(items), **extra)


class Inviluppo(unittest.TestCase):
    def test_fuori_da_ok_i_conteggi_sono_null_mai_zero(self):
        e = fonti.inviluppo("sismi", status=fonti.ERRORE, error="caduta")
        self.assertIsNone(e["total"])
        self.assertIsNone(e["returned"])
        self.assertNotEqual(e["total"], 0)
        self.assertFalse(e["truncated"])

    def test_troncato_dichiara_il_valore_vero(self):
        e = fonti.inviluppo("sismi", items=[{}] * 5, total=40, cap=5)
        self.assertTrue(e["truncated"])
        self.assertEqual(e["returned"], 5)
        self.assertEqual(e["total"], 40)


class Diametro(unittest.TestCase):
    def test_relazione_standard(self):
        # H=22 corrisponde a circa 140 m con albedo 0.14: valore di riferimento
        self.assertAlmostEqual(ric.diametro_da_magnitudine(22), 140, delta=6)

    def test_albedo_scuro_da_un_oggetto_piu_grande(self):
        self.assertGreater(ric.diametro_da_magnitudine(22, albedo=0.05),
                           ric.diametro_da_magnitudine(22, albedo=0.25))

    def test_senza_h_non_si_inventa_un_diametro(self):
        self.assertIsNone(ric.diametro_da_magnitudine(None))


class Incertezza(unittest.TestCase):
    def test_giorni_ore_minuti(self):
        self.assertAlmostEqual(ric._sigma_in_ore("9_15:50"), 9 * 24 + 15 + 50 / 60, places=3)

    def test_solo_minuti(self):
        self.assertAlmostEqual(ric._sigma_in_ore("00:09"), 0.15, places=3)

    def test_campo_illeggibile_non_diventa_zero(self):
        self.assertIsNone(ric._sigma_in_ore("boh"))


class Passaggi(unittest.TestCase):
    def _oggetto(self, **kw):
        base = {"designazione": "TEST", "quando_utc": "2026-Sep-30 12:00", "dist_au": 0.05,
                "dist_ld": 20.0, "dist_km": 7_400_000, "dist_min_au": 0.049, "dist_max_au": 0.051,
                "v_rel_kms": 8.0, "h": 18.0, "sigma_tempo": "00:05"}
        base.update(kw)
        return _inv("passaggi", [base])

    def test_grande_ma_lontano_resta_informativo(self):
        s = ric.da_passaggi(self._oggetto(h=15.0, dist_ld=12.0))[0]
        self.assertEqual(s["livello"], ric.INFORMATIVO)

    def test_un_passaggio_che_manca_la_terra_non_e_mai_allerta(self):
        s = ric.da_passaggi(self._oggetto(h=17.0, dist_ld=0.3, dist_min_au=0.0007))[0]
        self.assertNotEqual(s["livello"], ric.ALLERTA)
        self.assertEqual(s["tetto_applicato"], 69)

    def test_dentro_la_fascia_geostazionaria_il_tetto_cade(self):
        # 30.000 km = sotto i 42.164 km dell'orbita geostazionaria
        s = ric.da_passaggi(self._oggetto(dist_ld=0.08, dist_min_au=30_000 / ric.UA_KM))[0]
        self.assertNotIn("tetto_applicato", s)
        self.assertEqual(s["livello"], ric.ALLERTA)

    def test_orbita_poco_vincolata_abbassa_la_confidenza(self):
        s = ric.da_passaggi(self._oggetto(sigma_tempo="9_15:50", dist_min_au=0.001, dist_max_au=0.09))[0]
        self.assertEqual(s["confidenza"], "bassa")

    def test_ogni_segnalazione_dichiara_come_smentirla(self):
        for s in ric.da_passaggi(self._oggetto()):
            self.assertTrue(s["smentito_se"].strip())
            self.assertTrue(s["riconosciuto_da"])


class Sismi(unittest.TestCase):
    def _sisma(self, **kw):
        base = {"id": "x", "mag": 6.3, "place": "da qualche parte", "time": 1788435482183,
                "url": "", "alert": None, "tsunami": 0, "sig": 100,
                "lon": 1.0, "lat": 2.0, "depth_km": 35}
        base.update(kw)
        return _inv("sismi", [base])

    def test_pager_verde_impedisce_di_alzare_l_allarme(self):
        # Il caso reale che ha fatto nascere questa regola: M6.3 con flag tsunami
        # e PAGER green finiva in "allerta" contro la valutazione di USGS.
        s = ric.da_sismi(self._sisma(mag=6.3, tsunami=1, alert="green"))[0]
        self.assertEqual(s["punteggio"], ric.PAGER["green"])
        self.assertNotEqual(s["livello"], ric.ALLERTA)

    def test_pager_rosso_alza_anche_una_magnitudo_bassa(self):
        s = ric.da_sismi(self._sisma(mag=5.0, alert="red"))[0]
        self.assertEqual(s["livello"], ric.ALLERTA)

    def test_sotto_la_soglia_non_produce_segnalazioni(self):
        self.assertEqual(ric.da_sismi(self._sisma(mag=3.1)), [])


class Ordine(unittest.TestCase):
    def _eventi(self):
        return _inv("sismi", [
            {"id": "piccolo", "mag": 5.4, "place": "a", "time": 1788435482183, "url": "",
             "alert": "green", "tsunami": 0, "sig": 1, "lon": 1.0, "lat": 2.0, "depth_km": 10},
            {"id": "grosso", "mag": 6.3, "place": "b", "time": 1788435482183, "url": "",
             "alert": "green", "tsunami": 1, "sig": 1, "lon": 1.0, "lat": 2.0, "depth_km": 10},
        ])

    def test_sotto_lo_stesso_tetto_ordina_il_punteggio_grezzo(self):
        q = ric.quadro({"sismi": self._eventi()})
        primo, secondo = q["segnalazioni"][0], q["segnalazioni"][1]
        self.assertEqual(primo["punteggio"], secondo["punteggio"])   # stesso PAGER, stesso tetto
        self.assertEqual(primo["id"], "eq:grosso")                   # ma non sono equivalenti
        self.assertGreater(primo["punteggio_grezzo"], secondo["punteggio_grezzo"])

    def test_l_eta_pesa_solo_sull_ordine_mai_sulla_gravita(self):
        vecchio = _inv("bolidi", [{"quando_utc": "2025-01-01 00:00:00", "lat": 0.0, "lon": 0.0,
                                   "energia_kt": 2.4, "radiata_j": 1, "quota_km": 30, "velocita_kms": 20}])
        s = ric.quadro({"bolidi": vecchio})["segnalazioni"][0]
        self.assertGreater(s["punteggio"], 50)      # la gravita' resta quella
        self.assertLess(s["ordine"], 10)            # ma non riguarda piu' adesso
        self.assertGreater(s["giorni_fa"], 300)

    def test_le_date_dei_sismi_sono_leggibili(self):
        """Il formato scritto da da_sismi deve essere quello che _quando sa leggere."""
        q = ric.quadro({"sismi": self._eventi()})
        self.assertIsNotNone(q["segnalazioni"][0].get("giorni_fa"))


class Quadro(unittest.TestCase):
    def test_una_sorgente_caduta_vieta_la_sintesi(self):
        """Se manca una finestra sul cielo, «nessuna allerta» e' una frase che non possiamo dire."""
        q = ric.quadro({
            "sismi": _inv("sismi", []),
            "passaggi": fonti.inviluppo("passaggi", status=fonti.ERRORE, error="caduta"),
        })
        self.assertFalse(q["quadro_completo"])
        self.assertIsNone(q["sintesi"])
        self.assertEqual(q["sorgenti_degradate"][0]["sorgente"], "passaggi")

    def test_con_tutte_le_sorgenti_la_sintesi_esiste(self):
        q = ric.quadro({"sismi": _inv("sismi", [])})
        self.assertTrue(q["quadro_completo"])
        self.assertEqual(q["sintesi"], ric.INFORMATIVO)

    def test_i_fenomeni_passati_non_alzano_la_sintesi(self):
        s = _inv("sismi", [{"id": "x", "mag": 7.8, "place": "p", "time": 1788435482183, "url": "",
                            "alert": "red", "tsunami": 1, "sig": 900, "lon": 1.0, "lat": 2.0, "depth_km": 10}])
        q = ric.quadro({"sismi": s})
        self.assertEqual(q["segnalazioni"][0]["livello"], ric.ALLERTA)
        self.assertEqual(q["sintesi"], ric.INFORMATIVO)  # e' gia' avvenuto: non e' un'allerta in corso

    def test_l_avviso_di_fondo_viaggia_con_i_dati(self):
        q = ric.quadro({"sismi": _inv("sismi", [])})
        self.assertIn("non prevede", q["non_e_una_previsione"])


if __name__ == "__main__":
    unittest.main()
