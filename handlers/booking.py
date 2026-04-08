"""
Module 1 — Booking Flow
Flow: Book a Call → Name → Email → Time Preference → Save + Notify Admin
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
from utils.sheets import save_booking

logger = logging.getLogger(__name__)

# Conversation states
BOOK_NAME, BOOK_EMAIL, BOOK_TIME = range(3)

TIME_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🌅 Morning", callback_data="time_morning"),
        InlineKeyboardButton("☀️ Afternoon", callback_data="time_afternoon"),
        InlineKeyboardButton("🌙 Evening", callback_data="time_evening"),
    ],
    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_flow")],
])

TIME_LABELS = {
    "time_morning": "Morning",
    "time_afternoon": "Afternoon",
    "time_evening": "Evening",
}


# ─────────────────────────── entry point ───────────────────────────

async def book_call_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "📅 *Book a Call — Step 1 of 3*\n\n"
        "👤 *What is your full name?*",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return BOOK_NAME


# ─────────────────────────── step 1: name ──────────────────────────

async def book_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["book_name"] = update.message.text.strip()
    await update.message.reply_text(
        "📅 *Book a Call — Step 2 of 3*\n\n"
        "📧 *What is your email address?*",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return BOOK_EMAIL


# ─────────────────────────── step 2: email ─────────────────────────

async def book_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["book_email"] = update.message.text.strip()
    await update.message.reply_text(
        "📅 *Book a Call — Step 3 of 3*\n\n"
        "🕐 *Pick a preferred time slot:*",
        parse_mode="Markdown",
        reply_markup=TIME_KEYBOARD,
    )
    return BOOK_TIME


# ─────────────────────────── step 3: time ──────────────────────────

async def book_time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    name = context.user_data.get("book_name", "Not provided")
    email = context.user_data.get("book_email", "Not provided")
    time_pref = TIME_LABELS.get(query.data, query.data)
    timestamp = datetime.now().strftime("%d %b %Y %H:%M")

    save_booking(name, email, time_pref)

    admin_msg = (
        f"📅 *New Booking!*\n\n"
        f"👤 Name: {name}\n"
        f"📧 Email: {email}\n"
        f"🕐 Time: {time_pref}\n"
        f"⏰ Submitted: {timestamp}"
    )
    try:
        await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=admin_msg,
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.warning(f"Admin notification failed: {exc}")

    await query.edit_message_text(
        "✅ *Booking confirmed!*\n\n"
        f"Thanks, *{name}*! We've scheduled a call for the *{time_pref}*.\n"
        "We'll email you shortly to confirm the exact time.\n\n"
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

def build_booking_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(book_call_start, pattern="^book_call$")],
        states={
            BOOK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_name),
            ],
            BOOK_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_email),
            ],
            BOOK_TIME: [
                CallbackQueryHandler(book_time_selected, pattern="^time_"),
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
