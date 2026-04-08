"""Shared UI constants — imported by all handlers to avoid circular imports."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

WELCOME_TEXT = (
    "👋 *Welcome to TeleGuard Bot!*\n\n"
    "I'm your 24/7 business assistant. Here's what I can do:\n\n"
    "📋 *Get a Quote* — Tell us about your project\n"
    "📅 *Book a Call* — Schedule a consultation\n"
    "❓ *Ask a Question* — Browse our FAQ\n"
    "🛠 *View Services* — See what we offer\n\n"
    "Choose an option below:"
)

MAIN_MENU_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📋 Get a Quote", callback_data="get_quote"),
        InlineKeyboardButton("📅 Book a Call", callback_data="book_call"),
    ],
    [
        InlineKeyboardButton("❓ Ask a Question", callback_data="ask_question"),
        InlineKeyboardButton("🛠 View Services", callback_data="view_services"),
    ],
])

CANCEL_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_flow")]
])
