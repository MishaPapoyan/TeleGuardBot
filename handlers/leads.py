"""
Module 1 — Business Lead Capture
Flow: Get a Quote → Service → Budget → Contact → Save + Notify Admin
"""

import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import config
from handlers.constants import CANCEL_KEYBOARD, MAIN_MENU_KEYBOARD, WELCOME_TEXT
from utils.sheets import save_lead

logger = logging.getLogger(__name__)

# Conversation states
LEAD_SERVICE, LEAD_BUDGET, LEAD_CONTACT = range(3)

BUDGET_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Under $200", callback_data="budget_under200"),
        InlineKeyboardButton("$200 – $500", callback_data="budget_200_500"),
    ],
    [
        InlineKeyboardButton("$500 – $1,000", callback_data="budget_500_1000"),
        InlineKeyboardButton("$1,000+", callback_data="budget_1000plus"),
    ],
    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_flow")],
])

BUDGET_LABELS = {
    "budget_under200": "Under $200",
    "budget_200_500": "$200 – $500",
    "budget_500_1000": "$500 – $1,000",
    "budget_1000plus": "$1,000+",
}


# ─────────────────────────── entry point ───────────────────────────

async def get_quote_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "📋 *Get a Quote — Step 1 of 3*\n\n"
        "🔧 *What service do you need?*\n"
        "_e.g. Telegram bot, website, automation, API integration..._",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return LEAD_SERVICE


# ─────────────────────────── step 1: service ───────────────────────

async def lead_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["lead_service"] = update.message.text.strip()
    await update.message.reply_text(
        "📋 *Get a Quote — Step 2 of 3*\n\n"
        "💰 *What is your budget range?*\n"
        "_Select below or type your own:_",
        parse_mode="Markdown",
        reply_markup=BUDGET_KEYBOARD,
    )
    return LEAD_BUDGET


# ─────────────────────────── step 2: budget ────────────────────────

async def lead_budget_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["lead_budget"] = BUDGET_LABELS.get(query.data, query.data)
    await query.edit_message_text(
        "📋 *Get a Quote — Step 3 of 3*\n\n"
        "📬 *What is your email or contact number?*\n"
        "_We'll use this to send your quote._",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return LEAD_CONTACT


async def lead_budget_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fallback for users who type a budget instead of tapping a button."""
    context.user_data["lead_budget"] = update.message.text.strip()
    await update.message.reply_text(
        "📋 *Get a Quote — Step 3 of 3*\n\n"
        "📬 *What is your email or contact number?*\n"
        "_We'll use this to send your quote._",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return LEAD_CONTACT


# ─────────────────────────── step 3: contact ───────────────────────

async def lead_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    name = user.full_name
    service = context.user_data.get("lead_service", "Not provided")
    budget = context.user_data.get("lead_budget", "Not provided")
    contact = update.message.text.strip()
    timestamp = datetime.now().strftime("%d %b %Y %H:%M")

    save_lead(name, service, budget, contact)

    admin_msg = (
        f"🔔 *New Lead!*\n\n"
        f"👤 Name: {name}\n"
        f"🔧 Service: {service}\n"
        f"💰 Budget: {budget}\n"
        f"📬 Contact: {contact}\n"
        f"⏰ Time: {timestamp}"
    )
    try:
        await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=admin_msg,
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.warning(f"Admin notification failed: {exc}")

    await update.message.reply_text(
        "✅ *Quote request received!*\n\n"
        "Thanks! We'll review your request and get back to you within *24 hours*.\n\n"
        "Use /start to return to the main menu.",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────── shared cancel ─────────────────────────

async def cancel_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=MAIN_MENU_KEYBOARD,
    )
    return ConversationHandler.END


async def cancel_via_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=MAIN_MENU_KEYBOARD,
    )
    return ConversationHandler.END


# ─────────────────────────── factory ───────────────────────────────

def build_leads_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(get_quote_start, pattern="^get_quote$")],
        states={
            LEAD_SERVICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lead_service),
            ],
            LEAD_BUDGET: [
                CallbackQueryHandler(lead_budget_button, pattern="^budget_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lead_budget_text),
            ],
            LEAD_CONTACT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lead_contact),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_flow, pattern="^cancel_flow$"),
            CommandHandler("start", cancel_via_command),
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
