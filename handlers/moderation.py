"""
Module 2 — Community Moderation

Features:
  • Auto-welcome new members (message deleted after 5 minutes)
  • Spam detection: links from new accounts, mass mentions, duplicates, keywords
  • Warning system: warn on 1st/2nd offense, auto-ban on 3rd
  • Anti-flood: mute 5 min if 5+ messages in 10 seconds
"""

import logging
from datetime import datetime, timezone, timedelta

from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

from config import config
from utils.sheets import log_moderation
from utils.spam_filter import spam_filter

logger = logging.getLogger(__name__)

# Mute duration for flood violations (seconds)
FLOOD_MUTE_SECONDS = 300  # 5 minutes
# Welcome message auto-delete delay (seconds)
WELCOME_DELETE_DELAY = 300  # 5 minutes
# Warnings before auto-ban
MAX_WARNINGS = 3


# ─────────────────────── permission helpers ─────────────────────────

RESTRICTED = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
)

ALL_ALLOWED = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


async def _is_admin(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if user is a group admin/creator or the configured ADMIN_ID."""
    if user_id == config.ADMIN_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


# ─────────────────────── auto-welcome ──────────────────────────────

async def _delete_message_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    try:
        await context.bot.delete_message(
            chat_id=data["chat_id"],
            message_id=data["message_id"],
        )
    except Exception:
        pass  # message may already be deleted


async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message for each new member; auto-delete after 5 minutes."""
    message = update.effective_message
    if not message or not message.new_chat_members:
        return

    chat = update.effective_chat
    rules_text = spam_filter.group_rules.get(chat.id, "")
    rules_line = f"\n\n📜 Please read the [group rules]({rules_text})." if rules_text else ""

    for new_member in message.new_chat_members:
        if new_member.is_bot:
            continue

        name = new_member.full_name
        welcome = await message.reply_text(
            f"👋 Welcome, *{name}*! Glad to have you here.\n"
            f"Say hi and introduce yourself!{rules_line}",
            parse_mode="Markdown",
        )

        # Schedule auto-delete after 5 minutes
        context.job_queue.run_once(
            _delete_message_job,
            when=WELCOME_DELETE_DELAY,
            data={"chat_id": chat.id, "message_id": welcome.message_id},
        )


# ─────────────────────── spam & flood ──────────────────────────────

async def _mute_user(
    chat_id: int,
    user_id: int,
    duration_seconds: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    until = datetime.now(tz=timezone.utc) + timedelta(seconds=duration_seconds)
    await context.bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user_id,
        permissions=RESTRICTED,
        until_date=until,
    )


async def _ban_user(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)


async def _handle_flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    try:
        await message.delete()
    except Exception:
        pass

    try:
        await _mute_user(chat.id, user.id, FLOOD_MUTE_SECONDS, context)
    except Exception as exc:
        logger.warning(f"Could not mute {user.id}: {exc}")
        return

    warning = await chat.send_message(
        f"⚠️ *{user.full_name}* has been muted for *5 minutes* due to flood.\n"
        "_Please slow down!_",
        parse_mode="Markdown",
    )
    log_moderation(
        user=f"@{user.username or user.id}",
        action="Mute 5min",
        reason="Anti-flood triggered",
        admin="Auto",
    )
    # Auto-delete the warning after 30 seconds
    context.job_queue.run_once(
        _delete_message_job,
        when=30,
        data={"chat_id": chat.id, "message_id": warning.message_id},
    )


async def _handle_spam(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    reason: str,
) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    try:
        await message.delete()
    except Exception:
        pass

    warning_count = spam_filter.add_warning(user.id)

    if warning_count >= MAX_WARNINGS:
        try:
            await _ban_user(chat.id, user.id, context)
        except Exception as exc:
            logger.warning(f"Could not ban {user.id}: {exc}")
            return
        await chat.send_message(
            f"🚫 *{user.full_name}* has been *banned* after {MAX_WARNINGS} warnings.\n"
            f"_Reason: {reason}_",
            parse_mode="Markdown",
        )
        log_moderation(
            user=f"@{user.username or user.id}",
            action="Ban",
            reason=f"Auto: {reason} (3rd offense)",
            admin="Auto",
        )
        spam_filter.reset_warnings(user.id)
    else:
        warning = await chat.send_message(
            f"⚠️ *{user.full_name}*, warning {warning_count}/{MAX_WARNINGS - 1}.\n"
            f"_Reason: {reason}._\n"
            f"Next violation may result in a ban.",
            parse_mode="Markdown",
        )
        log_moderation(
            user=f"@{user.username or user.id}",
            action=f"Warn {warning_count}",
            reason=f"Auto: {reason}",
            admin="Auto",
        )
        context.job_queue.run_once(
            _delete_message_job,
            when=30,
            data={"chat_id": chat.id, "message_id": warning.message_id},
        )


# ─────────────────────── main group message handler ─────────────────

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user or not chat:
        return

    # Never moderate admins
    if await _is_admin(chat.id, user.id, context):
        return

    text = message.text or message.caption or ""

    # 1. Flood check
    if spam_filter.check_flood(user.id):
        await _handle_flood(update, context)
        return

    # 2. Mass mentions
    if spam_filter.check_mass_mention(text):
        await _handle_spam(update, context, "mass user mentions")
        return

    # 3. Duplicate messages
    if spam_filter.check_duplicate(user.id, text):
        await _handle_spam(update, context, "duplicate messages")
        return

    # 4. Keyword blocklist
    matched_kw = spam_filter.check_keywords(text)
    if matched_kw:
        await _handle_spam(update, context, f"blocked keyword: '{matched_kw}'")
        return

    # 5. Links from recently-joined members
    if text:
        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            since = getattr(member, "since", None) or getattr(member, "joined_date", None)
            if since:
                days_in_group = (datetime.now(tz=timezone.utc) - since).days
                if spam_filter.check_link_new_account(text, days_in_group):
                    await _handle_spam(update, context, "link posted by new member")
        except Exception:
            pass
