import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.constants import MAIN_MENU_KEYBOARD, WELCOME_TEXT

logger = logging.getLogger(__name__)

SERVICES_TEXT = (
    "🛠 *Our Services*\n\n"
    "• 🤖 Telegram Bot Development\n"
    "• 🌐 Web Development & Design\n"
    "• 📊 Google Sheets Automation\n"
    "• 📣 Community Management Bots\n"
    "• 🔗 API Integration & Webhooks\n"
    "• 🛒 E-commerce Solutions\n\n"
    "_Ready to start? Use *Get a Quote* for a personalised estimate!_"
)

BACK_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]
])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point — works in both private chat and groups."""
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


async def view_services_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        SERVICES_TEXT,
        parse_mode="Markdown",
        reply_markup=BACK_KEYBOARD,
    )
