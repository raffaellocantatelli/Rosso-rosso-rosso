"""Comandi e ConversationHandler.

Tre regole che valgono per tutto il file:

1. quello che l'utente scrive viene salvato com'e' e ristampato con
   html.escape: il bot non riformula niente per farlo suonare meglio;
2. nessuna risposta conferma un'ipotesi (P5), nemmeno per gentilezza;
3. quando un dato e' debole -- un gesto veloce, un'azione senza verifica --
   viene scritto che e' debole. E' l'unico modo per cui questo bot non
   diventi la cosa da cui il Capitolo 3 mette in guardia.
"""

from __future__ import annotations

import html
import logging
import os
import time

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from . import db, texts
from .states import Azione, Etichetta, Possibilita, Santuario

log = logging.getLogger(__name__)

#: Sotto questa soglia il gesto della candela non e' un gesto lento.
#: Non e' una prova da superare: e' il confine fra un dato e un altro.
SOGLIA_GESTO_LENTO = float(os.getenv("PROTOCOLLO_GESTO_MIN", "20"))

#: Modi in cui si dice "non lo so" senza doverlo scrivere in un modo solo.
NEGAZIONI = {
    "non lo so", "non so", "nonlosò", "boh", "nessuna", "nessuno", "niente",
    "-", "—", "no", "non saprei", "unknown", "non lo so.", "non so.",
}

TASTI_ETICHETTE = ReplyKeyboardMarkup(
    [["RECUPERATO", "INFERITO"], ["IPOTESI", "UNKNOWN"]],
    one_time_keyboard=True, resize_keyboard=True,
)


# --- utilita' ---------------------------------------------------------------

async def _di(update: Update, testo: str, **kwargs) -> None:
    await update.effective_message.reply_text(
        testo, parse_mode=ParseMode.HTML, **kwargs
    )


def _testo_utente(update: Update) -> str:
    return (update.effective_message.text or "").strip()


def _e_negazione(testo: str) -> bool:
    return testo.strip().lower() in NEGAZIONI


def _mostra(testo: str) -> str:
    """Ristampa quello che ha scritto l'utente, senza toccarlo."""
    return html.escape(testo)


def _tastiera(*etichette: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[e] for e in etichette], one_time_keyboard=True, resize_keyboard=True
    )


def _utente(update: Update) -> int:
    return update.effective_user.id


# --- comandi semplici -------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    u = update.effective_user
    db.registra_utente(u.id, u.full_name)
    await _di(update, texts.START, reply_markup=ReplyKeyboardRemove())


async def aiuto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _di(update, texts.AIUTO)


async def tesi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _di(update, texts.TESI)


async def strati(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _di(update, texts.STRATI)


async def p5p6(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _di(update, texts.P5P6)


async def veli(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tastiera = InlineKeyboardMarkup([
        [InlineKeyboardButton("1 — l'identità separata", callback_data="velo:1")],
        [InlineKeyboardButton("2 — la colpa e il passato", callback_data="velo:2")],
        [InlineKeyboardButton("3 — l'attesa del compimento", callback_data="velo:3")],
    ])
    await _di(update, texts.VELI_INTRO, reply_markup=tastiera)


async def velo_scelto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    numero = query.data.split(":", 1)[1]
    await query.message.reply_text(
        texts.VELI[numero], parse_mode=ParseMode.HTML
    )


async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    righe = db.elenca_possibilita(_utente(update))
    if not righe:
        await _di(update, texts.LISTA_VUOTA)
        return

    pezzi = [texts.LISTA_INTESTAZIONE]
    for numero, riga in enumerate(righe, start=1):
        criterio = riga["falsificazione"]
        cade = _mostra(criterio) if criterio else "<b>UNKNOWN</b>"
        pezzi.append(
            f"\n<b>#{numero}</b> — {riga['creata_il'][:10]}\n"
            f"IPOTESI: {_mostra(riga['testo'])}\n"
            f"Cade se: {cade}"
        )
    deboli = sum(1 for r in righe if not r["falsificazione"])
    if deboli:
        pezzi.append(
            f"\n\n{deboli} su {len(righe)} non dichiara come potrebbe cadere: "
            "per P6 quelle non potranno mai essere confermate. Restano tue "
            "lo stesso."
        )
    await _di(update, "".join(pezzi))


async def annulla(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await _di(update, texts.ANNULLATO, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def sconosciuto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _di(update, texts.NON_CAPITO)


# --- /santuario -------------------------------------------------------------
#
# Gli stati portano il nome del passaggio che deve ancora essere mostrato:
# in Santuario.LUCE il bot ha gia' mostrato la soglia e aspetta l'utente.

async def santuario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    u = update.effective_user
    db.registra_utente(u.id, u.full_name)
    context.user_data["visita_id"] = db.inizia_visita(u.id)
    context.user_data["candela_tentativi"] = 0
    await _di(update, texts.SANTUARIO_INTRO, reply_markup=_tastiera("entro"))
    return Santuario.SOGLIA


async def santuario_soglia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _di(update, texts.SANTUARIO_SOGLIA, reply_markup=_tastiera("continuo"))
    return Santuario.LUCE


async def santuario_luce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _di(update, texts.SANTUARIO_LUCE, reply_markup=_tastiera("continuo"))
    return Santuario.COLONNE


async def santuario_colonne(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _di(update, texts.SANTUARIO_COLONNE, reply_markup=_tastiera("continuo"))
    return Santuario.LIBRO


async def santuario_libro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _di(update, texts.SANTUARIO_LIBRO, reply_markup=_tastiera("l'ho riposato"))
    return Santuario.CANDELA


async def santuario_candela(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["candela_t0"] = time.monotonic()
    await _di(
        update, texts.SANTUARIO_CANDELA,
        reply_markup=_tastiera("il gesto è finito"),
    )
    return Santuario.USCITA


async def santuario_uscita(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t0 = context.user_data.get("candela_t0", time.monotonic())
    durata = time.monotonic() - t0
    lento = durata >= SOGLIA_GESTO_LENTO
    tentativi = context.user_data.get("candela_tentativi", 0) + 1
    context.user_data["candela_tentativi"] = tentativi

    if not lento and tentativi == 1:
        # Una sola volta: l'invito a rifarlo. Insistere sarebbe una
        # missione da completare, ed e' esattamente cio' che il Santuario
        # non e'.
        context.user_data["candela_t0"] = time.monotonic()
        await _di(
            update,
            texts.SANTUARIO_TROPPO_VELOCE.format(secondi=int(durata)),
            reply_markup=_tastiera("il gesto è finito"),
        )
        return Santuario.USCITA

    visita_id = context.user_data.get("visita_id")
    if visita_id is not None:
        db.concludi_visita(visita_id, durata, lento)

    testo = (
        texts.SANTUARIO_USCITA_LENTA if lento else texts.SANTUARIO_USCITA_VELOCE
    )
    await _di(
        update, testo.format(secondi=int(durata)),
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


# --- /tieni_aperto ----------------------------------------------------------

async def possibilita_inizio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    u = update.effective_user
    db.registra_utente(u.id, u.full_name)
    await _di(update, texts.POSSIBILITA_CHIEDI, reply_markup=ReplyKeyboardRemove())
    return Possibilita.TESTO


async def possibilita_testo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["possibilita"] = _testo_utente(update)
    await _di(update, texts.POSSIBILITA_CHIEDI_P6)
    return Possibilita.FALSIFICAZIONE


async def possibilita_falsificazione(update: Update,
                                     context: ContextTypes.DEFAULT_TYPE) -> int:
    testo = context.user_data.pop("possibilita", "")
    risposta = _testo_utente(update)
    criterio = None if _e_negazione(risposta) else risposta

    db.aggiungi_possibilita(_utente(update), testo, criterio)
    numero = len(db.elenca_possibilita(_utente(update)))

    if criterio:
        await _di(update, texts.POSSIBILITA_SALVATA_CON_CRITERIO.format(
            numero=numero, testo=_mostra(testo), falsificazione=_mostra(criterio),
        ))
    else:
        await _di(update, texts.POSSIBILITA_SALVATA_UNKNOWN.format(
            numero=numero, testo=_mostra(testo),
        ))
    context.user_data.clear()
    return ConversationHandler.END


# --- /azione ----------------------------------------------------------------

async def azione_inizio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    u = update.effective_user
    db.registra_utente(u.id, u.full_name)
    await _di(update, texts.AZIONE_CHIEDI, reply_markup=ReplyKeyboardRemove())
    return Azione.DESCRIZIONE


async def azione_descrizione(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["azione"] = _testo_utente(update)
    await _di(update, texts.AZIONE_CHIEDI_VERIFICA)
    return Azione.VERIFICA


async def azione_verifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    descrizione = context.user_data.pop("azione", "")
    risposta = _testo_utente(update)
    verifica = None if _e_negazione(risposta) else risposta

    utente = _utente(update)
    db.registra_azione(utente, descrizione, verifica)
    righe = db.elenca_azioni(utente)
    quando = righe[-1]["registrata_il"][:10] if righe else ""
    totale = db.conta_azioni_verificabili(utente)

    if verifica:
        await _di(update, texts.AZIONE_SALVATA.format(
            numero=len(righe), quando=quando,
            descrizione=_mostra(descrizione), verifica=_mostra(verifica),
            totale=totale,
        ))
    else:
        await _di(update, texts.AZIONE_SALVATA_NON_VERIFICABILE.format(
            numero=len(righe), quando=quando,
            descrizione=_mostra(descrizione), totale=totale,
        ))
    context.user_data.clear()
    return ConversationHandler.END


# --- /etichetta -------------------------------------------------------------

async def etichetta_inizio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _di(update, texts.ETICHETTA_CHIEDI, reply_markup=ReplyKeyboardRemove())
    return Etichetta.AFFERMAZIONE


async def etichetta_affermazione(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE) -> int:
    affermazione = _testo_utente(update)
    context.user_data["affermazione"] = affermazione
    await _di(
        update,
        texts.ETICHETTA_SCEGLI.format(testo=_mostra(affermazione)),
        reply_markup=TASTI_ETICHETTE,
    )
    return Etichetta.SCELTA


async def etichetta_scelta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    scelta = _testo_utente(update).strip().upper()
    if scelta not in texts.ETICHETTA_RISPOSTE:
        await _di(
            update,
            "Non è una delle quattro. Scegli fra RECUPERATO, INFERITO, "
            "IPOTESI e UNKNOWN — o /annulla.",
            reply_markup=TASTI_ETICHETTE,
        )
        return Etichetta.SCELTA

    await _di(update, texts.ETICHETTA_RISPOSTE[scelta],
              reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


# --- registrazione ----------------------------------------------------------

def _testo() -> filters.BaseFilter:
    return filters.TEXT & ~filters.COMMAND


def conversazione_santuario() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("santuario", santuario)],
        states={
            Santuario.SOGLIA: [MessageHandler(_testo(), santuario_soglia)],
            Santuario.LUCE: [MessageHandler(_testo(), santuario_luce)],
            Santuario.COLONNE: [MessageHandler(_testo(), santuario_colonne)],
            Santuario.LIBRO: [MessageHandler(_testo(), santuario_libro)],
            Santuario.CANDELA: [MessageHandler(_testo(), santuario_candela)],
            Santuario.USCITA: [MessageHandler(_testo(), santuario_uscita)],
        },
        fallbacks=[CommandHandler("annulla", annulla)],
        name="santuario",
    )


def conversazione_possibilita() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("tieni_aperto", possibilita_inizio)],
        states={
            Possibilita.TESTO: [MessageHandler(_testo(), possibilita_testo)],
            Possibilita.FALSIFICAZIONE: [
                MessageHandler(_testo(), possibilita_falsificazione)
            ],
        },
        fallbacks=[CommandHandler("annulla", annulla)],
        name="tieni_aperto",
    )


def conversazione_azione() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("azione", azione_inizio)],
        states={
            Azione.DESCRIZIONE: [MessageHandler(_testo(), azione_descrizione)],
            Azione.VERIFICA: [MessageHandler(_testo(), azione_verifica)],
        },
        fallbacks=[CommandHandler("annulla", annulla)],
        name="azione",
    )


def conversazione_etichetta() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("etichetta", etichetta_inizio)],
        states={
            Etichetta.AFFERMAZIONE: [
                MessageHandler(_testo(), etichetta_affermazione)
            ],
            Etichetta.SCELTA: [MessageHandler(_testo(), etichetta_scelta)],
        },
        fallbacks=[CommandHandler("annulla", annulla)],
        name="etichetta",
    )


#: Elenco dei comandi, unico posto in cui vivono. main.py lo usa per
#: registrarli su Telegram, i test per controllare che il README non menta.
COMANDI = [
    ("start", "Ingresso nel protocollo"),
    ("tesi", "La tesi grande, dichiarata come IPOTESI"),
    ("strati", "I due strati e le quattro etichette"),
    ("p5p6", "Le due leggi"),
    ("santuario", "Esperienza guidata del Santuario"),
    ("tieni_aperto", "Deposita una possibilità aperta"),
    ("lista", "Rivedi le tue possibilità aperte"),
    ("azione", "Registra un'azione vera e verificabile"),
    ("veli", "Dissolvi uno dei tre veli finali"),
    ("etichetta", "Colloca un'affermazione nello strato giusto"),
    ("aiuto", "Elenco comandi"),
    ("annulla", "Esce da un percorso senza registrare niente"),
]


def registra(app: Application) -> None:
    """Aggiunge tutti gli handler all'applicazione, nell'ordine che conta."""
    app.add_handler(conversazione_santuario())
    app.add_handler(conversazione_possibilita())
    app.add_handler(conversazione_azione())
    app.add_handler(conversazione_etichetta())

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["aiuto", "help"], aiuto))
    app.add_handler(CommandHandler("tesi", tesi))
    app.add_handler(CommandHandler("strati", strati))
    app.add_handler(CommandHandler("p5p6", p5p6))
    app.add_handler(CommandHandler("veli", veli))
    app.add_handler(CommandHandler("lista", lista))
    # Fuori da una conversazione /annulla non ha niente da annullare, e lo dice.
    app.add_handler(CommandHandler("annulla", annulla))
    app.add_handler(CallbackQueryHandler(velo_scelto, pattern=r"^velo:[123]$"))

    # Ultimo: solo i comandi che nessun altro handler ha raccolto.
    app.add_handler(MessageHandler(filters.COMMAND, sconosciuto))
