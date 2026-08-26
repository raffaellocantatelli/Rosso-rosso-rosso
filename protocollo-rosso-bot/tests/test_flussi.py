"""I flussi conversazionali, eseguiti davvero.

Niente rete: gli handler ricevono un Update finto che espone solo cio' che
usano. Quello che questi test verificano non e' che il bot "risponda", ma
che risponda *la verita'* sui dati che scrive.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bot import db, handlers
from bot.states import Azione, Etichetta, Possibilita, Santuario
from telegram.ext import ConversationHandler

FINE = ConversationHandler.END


class FintoMessaggio:
    def __init__(self, testo: str) -> None:
        self.text = testo
        self.risposte: list[str] = []

    async def reply_text(self, testo: str, **kwargs) -> None:
        self.risposte.append(testo)


class FintoUpdate:
    def __init__(self, testo: str = "", utente: int = 7) -> None:
        self.effective_message = FintoMessaggio(testo)
        self.effective_user = SimpleNamespace(id=utente, full_name="Prova")

    @property
    def risposta(self) -> str:
        return "\n".join(self.effective_message.risposte)


def contesto() -> SimpleNamespace:
    return SimpleNamespace(user_data={})


class BaseFlusso(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        os.environ["PROTOCOLLO_DB"] = str(Path(self.dir.name) / "prova.db")
        db.init_db()
        self.ctx = contesto()

    def tearDown(self) -> None:
        os.environ.pop("PROTOCOLLO_DB", None)
        self.dir.cleanup()

    async def passo(self, funzione, testo: str = "avanti"):
        update = FintoUpdate(testo)
        stato = await funzione(update, self.ctx)
        return stato, update


class TestSantuario(BaseFlusso):
    async def attraversa_fino_alla_candela(self):
        stato, _ = await self.passo(handlers.santuario, "/santuario")
        self.assertEqual(stato, Santuario.SOGLIA)
        for funzione, atteso in [
            (handlers.santuario_soglia, Santuario.LUCE),
            (handlers.santuario_luce, Santuario.COLONNE),
            (handlers.santuario_colonne, Santuario.LIBRO),
            (handlers.santuario_libro, Santuario.CANDELA),
            (handlers.santuario_candela, Santuario.USCITA),
        ]:
            stato, _ = await self.passo(funzione)
            self.assertEqual(stato, atteso)

    async def test_ordine_dei_passaggi_del_capitolo_4(self):
        await self.attraversa_fino_alla_candela()
        self.assertIn("candela_t0", self.ctx.user_data)

    async def test_gesto_lento_registrato_come_completo(self):
        soglia = handlers.SOGLIA_GESTO_LENTO
        handlers.SOGLIA_GESTO_LENTO = 0.0
        try:
            await self.attraversa_fino_alla_candela()
            stato, update = await self.passo(handlers.santuario_uscita)
        finally:
            handlers.SOGLIA_GESTO_LENTO = soglia
        self.assertEqual(stato, FINE)
        self.assertIn("completa", update.risposta)
        riga = db.elenca_visite(7)[0]
        self.assertEqual(riga["gesto_lento"], 1)
        self.assertIsNotNone(riga["conclusa_il"])

    async def test_gesto_veloce_invita_una_volta_poi_dice_com_e_andata(self):
        soglia = handlers.SOGLIA_GESTO_LENTO
        handlers.SOGLIA_GESTO_LENTO = 10_000.0
        try:
            await self.attraversa_fino_alla_candela()
            stato, primo = await self.passo(handlers.santuario_uscita)
            self.assertEqual(stato, Santuario.USCITA, "il primo invito manca")
            self.assertIn("Rifallo", primo.risposta)

            stato, secondo = await self.passo(handlers.santuario_uscita)
        finally:
            handlers.SOGLIA_GESTO_LENTO = soglia
        self.assertEqual(stato, FINE, "il secondo tentativo deve chiudere")
        self.assertIn("incompleta", secondo.risposta)
        self.assertNotIn("completa</b>", secondo.risposta.replace("incompleta", ""))
        riga = db.elenca_visite(7)[0]
        self.assertEqual(riga["gesto_lento"], 0,
                         "un gesto veloce non puo' risultare lento nel db")


class TestPossibilita(BaseFlusso):
    async def deposita(self, testo: str, criterio: str):
        stato, _ = await self.passo(handlers.possibilita_inizio, "/tieni_aperto")
        self.assertEqual(stato, Possibilita.TESTO)
        stato, _ = await self.passo(handlers.possibilita_testo, testo)
        self.assertEqual(stato, Possibilita.FALSIFICAZIONE)
        stato, update = await self.passo(
            handlers.possibilita_falsificazione, criterio
        )
        self.assertEqual(stato, FINE)
        return update

    async def test_con_criterio_resta_ipotesi(self):
        update = await self.deposita("la trasmissione arrivera'",
                                     "se a dicembre nessuno ha risposto")
        riga = db.elenca_possibilita(7)[0]
        self.assertEqual(riga["etichetta"], "IPOTESI")
        self.assertEqual(riga["falsificazione"], "se a dicembre nessuno ha risposto")
        self.assertIn("IPOTESI", update.risposta)

    async def test_non_lo_so_diventa_unknown_dichiarato(self):
        update = await self.deposita("il campo del già", "non lo so")
        self.assertIsNone(db.elenca_possibilita(7)[0]["falsificazione"])
        self.assertIn("UNKNOWN", update.risposta)
        self.assertIn("ipotesi debole", update.risposta)

    async def test_il_testo_dell_utente_non_viene_interpretato_come_html(self):
        update = await self.deposita("<b>grassetto</b> & co", "un criterio")
        self.assertIn("&lt;b&gt;grassetto&lt;/b&gt; &amp; co", update.risposta)

    async def test_lista_segnala_le_ipotesi_senza_criterio(self):
        await self.deposita("prima", "un criterio")
        await self.deposita("seconda", "non lo so")
        _, update = await self.passo(handlers.lista, "/lista")
        self.assertIn("UNKNOWN", update.risposta)
        self.assertIn("1 su 2", update.risposta)

    async def test_lista_vuota_non_inventa_niente(self):
        _, update = await self.passo(handlers.lista, "/lista")
        self.assertIn("Non hai ancora depositato", update.risposta)


class TestAzione(BaseFlusso):
    async def registra(self, descrizione: str, verifica: str):
        stato, _ = await self.passo(handlers.azione_inizio, "/azione")
        self.assertEqual(stato, Azione.DESCRIZIONE)
        stato, _ = await self.passo(handlers.azione_descrizione, descrizione)
        self.assertEqual(stato, Azione.VERIFICA)
        stato, update = await self.passo(handlers.azione_verifica, verifica)
        self.assertEqual(stato, FINE)
        return update

    async def test_azione_verificabile(self):
        update = await self.registra("spedita la lettera", "ricevuta postale 44")
        riga = db.elenca_azioni(7)[0]
        self.assertEqual(riga["verifica"], "ricevuta postale 44")
        self.assertIn("ricevuta postale 44", update.risposta)
        self.assertEqual(db.conta_azioni_verificabili(7), 1)

    async def test_azione_senza_verifica_resta_senza_verifica(self):
        update = await self.registra("ci ho pensato molto", "nessuna")
        self.assertIsNone(db.elenca_azioni(7)[0]["verifica"])
        self.assertIn("nessuna verifica esterna dichiarata", update.risposta)
        self.assertEqual(db.conta_azioni_verificabili(7), 0)

    async def test_il_totale_mostrato_conta_solo_le_verificabili(self):
        await self.registra("una", "un testimone")
        update = await self.registra("due", "non lo so")
        self.assertIn("<b>1</b>", update.risposta)


class TestEtichetta(BaseFlusso):
    async def test_scelta_valida(self):
        stato, _ = await self.passo(handlers.etichetta_inizio, "/etichetta")
        self.assertEqual(stato, Etichetta.AFFERMAZIONE)
        stato, _ = await self.passo(handlers.etichetta_affermazione,
                                    "il sistema funziona")
        self.assertEqual(stato, Etichetta.SCELTA)
        stato, update = await self.passo(handlers.etichetta_scelta, "ipotesi")
        self.assertEqual(stato, FINE)
        self.assertIn("P6", update.risposta)

    async def test_scelta_non_valida_richiede_di_nuovo(self):
        await self.passo(handlers.etichetta_inizio, "/etichetta")
        await self.passo(handlers.etichetta_affermazione, "x")
        stato, update = await self.passo(handlers.etichetta_scelta, "forse")
        self.assertEqual(stato, Etichetta.SCELTA)
        self.assertIn("Non è una delle quattro", update.risposta)


class TestAnnulla(BaseFlusso):
    async def test_annulla_non_scrive_niente(self):
        await self.passo(handlers.possibilita_inizio, "/tieni_aperto")
        await self.passo(handlers.possibilita_testo, "una possibilità")
        stato, update = await self.passo(handlers.annulla, "/annulla")
        self.assertEqual(stato, FINE)
        self.assertEqual(db.elenca_possibilita(7), [])
        self.assertIn("Niente è stato registrato", update.risposta)


if __name__ == "__main__":
    unittest.main()
