"""Entry point.

    python -m bot.main            # avvia il bot in long polling
    python -m bot.main --check    # dice se il bot puo' partire, e cosa manca

--check esiste per la stessa ragione di 'python -m sdq1 --check': un
sistema che non puo' funzionare deve dirlo subito e uscire con codice 2,
non fingere di essere acceso. Senza token qui non si avvia niente.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.error import InvalidToken, TelegramError
from telegram.ext import Application, ApplicationBuilder

from . import db, handlers

TOKEN_ENV = "TELEGRAM_BOT_TOKEN"

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=os.getenv("PROTOCOLLO_LOG", "INFO").upper(),
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("protocollo")


def leggi_token() -> str | None:
    load_dotenv()
    token = (os.getenv(TOKEN_ENV) or "").strip()
    return token or None


async def _pubblica_comandi(app: Application) -> None:
    await app.bot.set_my_commands(
        [BotCommand(nome, descrizione) for nome, descrizione in handlers.COMANDI]
    )


async def _verifica() -> int:
    """Controlla token, database e raggiungibilita' di Telegram.

    Stampa ogni riga con la sua etichetta: RECUPERATO cio' che e' stato
    osservato eseguendolo, UNKNOWN cio' che da qui non si puo' sapere.
    """
    esito = 0

    token = leggi_token()
    if token:
        print(f"RECUPERATO  {TOKEN_ENV}: presente ({len(token)} caratteri)")
    else:
        print(f"RECUPERATO  {TOKEN_ENV}: assente")
        print("            -> copia .env.example in .env e incolla il token "
              "di @BotFather")
        esito = 2

    percorso = db.db_path()
    try:
        db.init_db()
        print(f"RECUPERATO  database: scrivibile ({percorso})")
    except Exception as errore:  # pragma: no cover - dipende dal filesystem
        print(f"RECUPERATO  database: NON scrivibile ({percorso}) — {errore}")
        esito = 2

    if not token:
        print("UNKNOWN     identita' del bot: non verificabile senza token")
        return esito

    try:
        app = ApplicationBuilder().token(token).build()
        async with app.bot:
            io = await app.bot.get_me()
        print(f"RECUPERATO  Telegram risponde: @{io.username} (id {io.id})")
    except InvalidToken:
        # Il messaggio di PTB contiene il token: non va stampato ne' loggato.
        print("RECUPERATO  Telegram rifiuta il token: non e' un token valido")
        esito = 2
    except TelegramError as errore:
        print(f"RECUPERATO  Telegram non risponde: {errore}")
        esito = 2

    return esito


def check() -> int:
    return asyncio.run(_verifica())


def avvia(token: str) -> None:
    db.init_db()
    app = (
        ApplicationBuilder()
        .token(token)
        .post_init(_pubblica_comandi)
        .build()
    )
    handlers.registra(app)
    log.info("Protocollo Rosso Rosso Rosso — bot avviato (long polling).")
    log.info("Database: %s", db.db_path())
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bot.main",
        description="Bot Telegram del Protocollo Rosso Rosso Rosso.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="verifica token, database e risposta di Telegram, poi esce",
    )
    argomenti = parser.parse_args(argv)

    if argomenti.check:
        return check()

    token = leggi_token()
    if not token:
        print(
            f"{TOKEN_ENV} non impostato: il bot non parte.\n"
            "Copia .env.example in .env e incolla il token di @BotFather.\n"
            "Poi: python -m bot.main --check",
            file=sys.stderr,
        )
        return 2

    avvia(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
