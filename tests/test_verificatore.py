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


class TestDailyNonSiRilegge(unittest.TestCase):
    """Il daily non deve tornare domani come «contesto rilevante».

    Il fix del 22/08 fermava solo gli Stub. Il difetto pero' non era lo Stub:
    era il sistema che rilegge le proprie riflessioni. Con un provider vero
    succedeva di nuovo, e senza banner ad avvisare.
    """

    def test_memorizza_false_non_scrive_in_memoria(self):
        from sdq1.agents import pipeline

        class MemoriaFinta:
            def __init__(self):
                self.scritte = []

            def retrieve(self, _testo):
                return []

            def add(self, *args, **kwargs):
                self.scritte.append(args)

        class RouterFinto:
            def generate(self, _prompt, profile="default"):
                return "riflessione di prova, abbastanza lunga da non sembrare debole", "finto"

        memoria = MemoriaFinta()
        pipeline.esegui("prompt del daily", "default", RouterFinto(), memoria,
                        memorizza=False)
        self.assertEqual(memoria.scritte, [], "il daily e' entrato in memoria")

        pipeline.esegui("una domanda vera", "default", RouterFinto(), memoria)
        self.assertEqual(len(memoria.scritte), 1, "una domanda normale deve entrare")

    def test_il_prompt_del_daily_porta_i_fatti(self):
        from sdq1 import daily

        prompt = daily.costruisci_prompt(fatti={"health": {"rilevazioni_totali": 3}})
        self.assertIn("DATI", prompt)
        self.assertIn("rilevazioni_totali", prompt)
        self.assertIn("UNKNOWN", prompt)
        self.assertIn("NON inventare metriche", prompt)


class TestCrashNonEUnSi(BaseVerificatore):
    """Un falsificatore che esplode non ha detto «regge».

    Il 26/08 H5 e' risultata RETTA per un crash su un 429: Python esce con
    codice 1 quando un'eccezione non e' gestita, e 1 significa REGGE. E' la
    stessa confusione — «non ho potuto controllare» letto come «va tutto
    bene» — che l'exit 2 esiste per impedire.
    """

    def falsificatore_che_esplode(self):
        percorso = self.cartella / "esplode.py"
        percorso.write_text(
            "raise RuntimeError('429 Too Many Requests')\n", encoding="utf-8"
        )
        return {"comando": [sys.executable, str(percorso)], "descrizione": "esplode"}

    def test_un_traceback_non_diventa_regge(self):
        self.scrivi_registro([{
            "id": "K1", "testo": "esplode", "stato": registro.APERTA,
            "falsificatore": self.falsificatore_che_esplode(),
        }])
        risultati = verificatore.verifica()
        self.assertEqual(risultati[0]["exit_code"], 1,
                         "il crash deve davvero uscire con 1, o il test non prova niente")
        self.assertEqual(risultati[0]["esito"], "verifica_fallita")
        self.assertEqual(self.stato("K1"), registro.APERTA)

    def test_il_guscio_protetto_restituisce_non_conclusa(self):
        import falsificatori

        def esplode():
            raise RuntimeError("429")

        self.assertEqual(falsificatori.main_protetto(esplode),
                         falsificatori.NON_CONCLUSA)
        self.assertEqual(falsificatori.main_protetto(lambda: falsificatori.REGGE),
                         falsificatori.REGGE)


class TestSegretiOscurati(unittest.TestCase):
    """Una credenziale non deve poter finire in un messaggio d'errore."""

    def test_la_chiave_viene_oscurata(self):
        import os
        from sdq1.llm.router import oscura_segreti

        os.environ["GOOGLE_API_KEY"] = "CHIAVE-SEGRETISSIMA-987654321"
        try:
            sporco = "errore su https://api/x?key=CHIAVE-SEGRETISSIMA-987654321"
            pulito = oscura_segreti(sporco)
            self.assertNotIn("CHIAVE-SEGRETISSIMA-987654321", pulito)
            self.assertIn("oscurata", pulito)
        finally:
            os.environ.pop("GOOGLE_API_KEY", None)

    def test_la_chiave_non_e_piu_nell_url_di_gemini(self):
        from pathlib import Path
        sorgente = Path(__file__).resolve().parent.parent / "sdq1/llm/providers/gemini_provider.py"
        testo = sorgente.read_text(encoding="utf-8")
        self.assertNotIn("?key={key}", testo,
                         "la chiave e' tornata nella query string")
        self.assertIn("x-goog-api-key", testo)


class TestArchivio(unittest.TestCase):
    """L'archivio dà le fonti, mai la voce del sistema."""

    def setUp(self):
        import archivio
        self.archivio = archivio
        self.indice = archivio.costruisci_indice()

    def test_le_fonti_ci_sono(self):
        file_indicizzati = {f["file"] for f in self.indice}
        self.assertIn("testi/PROTOCOLLO_ROSSO_v2_REVISIONE.md", file_indicizzati)
        self.assertIn("CLAUDE.md", file_indicizzati)

    def test_nessun_output_del_sistema_entra_in_contesto(self):
        """Il difetto §4.2 non deve poter rientrare travestito da erudizione."""
        import re
        file_indicizzati = {f["file"] for f in self.indice}
        for nome in file_indicizzati:
            self.assertIsNone(
                re.search(r"CONTRADDITTORIO_|daily_|store\.json|verifiche\.jsonl", nome),
                f"{nome} è un output del sistema e non può essere una fonte",
            )

    def test_ogni_frammento_porta_la_sua_provenienza(self):
        for frammento in self.indice:
            self.assertTrue(frammento["file"])
            self.assertGreaterEqual(frammento["riga"], 1)

    def test_il_contesto_espone_file_e_riga(self):
        contesto = self.archivio.come_contesto("conservare trasmettere archivio",
                                               quanti=2, indice=self.indice)
        self.assertIn("FONTE:", contesto)
        self.assertRegex(contesto, r"FONTE: [^\s:]+:\d+")


class TestArchivioNonMangiaLeCronache(unittest.TestCase):
    """Le cronache degli altri nodi non sono fonti.

    Il 02/09, unendo il ramo di default, in memoria/ sono comparsi 46
    R3_DRIVE_SYNC_REPORT prodotti da un altro modello a cadenza oraria, e
    l'archivio li aveva presi per fonti: 46 su 55. Il Contraddittore avrebbe
    letto la cronaca di un altro modello come se fosse l'archivio dell'autore.
    """

    def test_nessuna_cronaca_di_nodo_fra_le_fonti(self):
        import re
        import archivio
        vietati = re.compile(
            r"R3_DRIVE_SYNC_REPORT|R3_WORK_QUEUE|SYNC_DRIVE_GITHUB"
            r"|CONTRADDITTORIO|daily_|^SESSIONE_|ZZ_SUPERATO"
        )
        for frammento in archivio.costruisci_indice():
            self.assertIsNone(
                vietati.search(frammento["file"]),
                f"{frammento['file']} è una cronaca, non una fonte",
            )

    def test_le_fonti_vere_ci_sono_ancora(self):
        import archivio
        file_indicizzati = {f["file"] for f in archivio.costruisci_indice()}
        self.assertIn("testi/PROTOCOLLO_ROSSO_v2_REVISIONE.md", file_indicizzati)
        self.assertIn("testi/IL_DESTINATARIO.md", file_indicizzati)
