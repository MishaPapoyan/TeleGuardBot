"""
TeleGuard Bot — Entry Point
Dual-purpose Telegram bot: Business Lead Capture + Community Moderation
"""

import asyncio
import logging
import os
import warnings

from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore", category=PTBUserWarning)

# Fix: PostgreSQL installation sets REQUESTS_CA_BUNDLE to its own cert path,
# which breaks gspread/requests. Override with certifi's trusted bundle.
try:
    import certifi
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
    os.environ["SSL_CERT_FILE"] = certifi.where()
except ImportError:
    pass

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import config
from utils.logger import setup_logging
from utils.sheets import ensure_sheets_exist
from utils.health import start_health_server

from handlers.start import back_to_menu_callback, start_command, view_services_callback
from handlers.leads import build_leads_conversation
from handlers.booking import build_booking_conversation
from handlers.faq import (
    ask_question_callback,
    build_faq_conversation,
    faq_answer_callback,
)
from handlers.moderation import handle_group_message, welcome_new_member
from handlers.admin import (
    ban_command,
    mute_command,
    rules_command,
    setrules_command,
    stats_command,
    unban_command,
    warn_command,
)

setup_logging()
logger = logging.getLogger(__name__)


def build_app() -> Application:
    app = Application.builder().token(config.BOT_TOKEN).build()

    # ── Conversations (registered first — highest priority) ──────────
    app.add_handler(build_leads_conversation())
    app.add_handler(build_booking_conversation())
    app.add_handler(build_faq_conversation())

    # ── Private chat commands ────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))

    # ── Main menu inline buttons ─────────────────────────────────────
    app.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(view_services_callback, pattern="^view_services$"))

    # ── FAQ inline buttons ───────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(ask_question_callback, pattern="^ask_question$"))
    app.add_handler(CallbackQueryHandler(faq_answer_callback, pattern=r"^faq_\d+$"))

    # ── Group moderation ─────────────────────────────────────────────
    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member)
    )
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & (filters.TEXT | filters.CAPTION),
            handle_group_message,
        )
    )

    # ── Admin commands ───────────────────────────────────────────────
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("warn", warn_command))
    app.add_handler(CommandHandler("mute", mute_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("setrules", setrules_command))

    return app


def main() -> None:
    config.validate()
    start_health_server()
    logger.info("TeleGuard starting up...")

    # Best-effort: create missing Google Sheets tabs at startup
    if config.GOOGLE_SHEET_ID:
        ensure_sheets_exist()

    app = build_app()

    if config.WEBHOOK_URL:
        logger.info(f"Webhook mode → {config.WEBHOOK_URL} (port {config.PORT})")
        # url_path must match the path in WEBHOOK_URL so PTB listens on /TOKEN
        from urllib.parse import urlparse
        url_path = urlparse(config.WEBHOOK_URL).path.lstrip("/")
        app.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path=url_path,
            webhook_url=config.WEBHOOK_URL,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        logger.info("Polling mode (local development)")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    # Python 3.12+ removed auto event-loop creation. Python 3.14 made it stricter.
    # Explicitly create and set a loop before PTB touches asyncio.
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    main()
