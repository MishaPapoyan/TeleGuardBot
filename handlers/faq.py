"""
Module 1 — FAQ System
Shows top 5 FAQ buttons from faq.json.
Unanswered / custom questions are saved to Google Sheets.
"""

import json
import logging
import os
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from handlers.constants import MAIN_MENU_KEYBOARD, WELCOME_TEXT
from utils.sheets import save_faq_question

logger = logging.getLogger(__name__)

FAQ_FILE = Path(__file__).parent.parent / "data" / "faq.json"

# Conversation state for custom question
AWAITING_CUSTOM_Q = 0

BACK_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("⬅️ Back to FAQ", callback_data="ask_question")],
    [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")],
])


# ──────────────────────────── helpers ──────────────────────────────

def _load_faqs() -> list[dict]:
    try:
        with open(FAQ_FILE, encoding="utf-8") as f:
            return json.load(f).get("faqs", [])
    except Exception as exc:
        logger.error(f"Failed to load faq.json: {exc}")
        return []


def _faq_keyboard() -> InlineKeyboardMarkup:
    faqs = _load_faqs()
    rows = [
        [InlineKeyboardButton(faq["question"], callback_data=f"faq_{faq['id']}")]
        for faq in faqs[:5]
    ]
    rows.append([InlineKeyboardButton("✏️ Ask Your Own Question", callback_data="faq_custom")])
    rows.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(rows)


# ─────────────────────── FAQ menu callback ──────────────────────────

async def ask_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "❓ *Frequently Asked Questions*\n\nSelect a question or ask your own:",
        parse_mode="Markdown",
        reply_markup=_faq_keyboard(),
    )


# ────────────────────── individual FAQ answer ───────────────────────

async def faq_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    try:
        faq_id = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.answer("Invalid FAQ.", show_alert=True)
        return

    faqs = _load_faqs()
    faq = next((f for f in faqs if f["id"] == faq_id), None)

    if not faq:
        await query.edit_message_text("Sorry, that question wasn't found.")
        return

    await query.edit_message_text(
        f"❓ *{faq['question']}*\n\n{faq['answer']}",
        parse_mode="Markdown",
        reply_markup=BACK_KEYBOARD,
    )


# ───────────────────── custom question conversation ─────────────────

async def faq_custom_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✏️ *Ask Your Own Question*\n\n"
        "Type your question below and we'll get back to you!\n\n"
        "_Send /cancel to go back._",
        parse_mode="Markdown",
    )
    return AWAITING_CUSTOM_Q


async def faq_custom_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name
    question = update.message.text.strip()

    save_faq_question(username, question)

    await update.message.reply_text(
        "✅ *Question submitted!*\n\n"
        "Thanks! We've logged your question and will add it to our FAQ or reply directly.\n\n"
        "Use /start to return to the main menu.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def faq_custom_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=MAIN_MENU_KEYBOARD,
    )
    return ConversationHandler.END


# ─────────────────────────── factory ───────────────────────────────

def build_faq_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(faq_custom_start, pattern="^faq_custom$")],
        states={
            AWAITING_CUSTOM_Q: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, faq_custom_receive),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", faq_custom_cancel),
            CommandHandler("start", faq_custom_cancel),
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )
