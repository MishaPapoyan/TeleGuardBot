"""
Module 2 — Admin Commands

Commands (group only, admin-only unless noted):
  /ban @user [reason]    — Ban user and log
  /warn @user [reason]   — Manual warning
  /mute @user [minutes]  — Mute for N minutes (default 10)
  /unban @user           — Remove ban
  /stats                 — Show moderation stats
  /rules                 — Show group rules (all members)
  /setrules [text]       — Update group rules
"""

import logging
from datetime import datetime, timezone, timedelta

from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

from config import config
from handlers.moderation import RESTRICTED, ALL_ALLOWED
from utils.sheets import get_moderation_stats, log_moderation
from utils.spam_filter import spam_filter

logger = logging.getLogger(__name__)


# ─────────────────────── shared helpers ────────────────────────────

async def _is_admin(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id == config.ADMIN_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def _check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Reply with an error and return False if caller is not an admin."""
    user = update.effective_user
    chat = update.effective_chat
    if not await _is_admin(chat.id, user.id, context):
        await update.message.reply_text("⛔ This command is for admins only.")
        return False
    return True


def _parse_target(context) -> tuple[str | None, str]:
    """
    Extract @username (or replied-to user) and optional reason from args.
    Returns (username_or_none, reason).
    """
    args = context.args or []
    if not args:
        return None, ""
    target = args[0].lstrip("@")
    reason = " ".join(args[1:]) if len(args) > 1 else "No reason given"
    return target, reason


async def _resolve_user_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    username: str | None,
) -> int | None:
    """Resolve a username to a user_id via reply or args."""
    # If the command is a reply, use the replied-to user
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    if username:
        try:
            chat = await context.bot.get_chat(f"@{username}")
            return chat.id
        except Exception:
            return None
    return None


# ─────────────────────── /ban ──────────────────────────────────────

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin(update, context):
        return

    username, reason = _parse_target(context)
    user_id = await _resolve_user_id(update, context, username)

    if not user_id:
        await update.message.reply_text(
            "Usage: /ban @username [reason] — or reply to a message."
        )
        return

    chat = update.effective_chat
    admin = update.effective_user

    try:
        await context.bot.ban_chat_member(chat_id=chat.id, user_id=user_id)
        await update.message.reply_text(
            f"🚫 User `{username or user_id}` has been banned.\n_Reason: {reason}_",
            parse_mode="Markdown",
        )
        log_moderation(
            user=f"@{username or user_id}",
            action="Ban",
            reason=reason,
            admin=f"@{admin.username or admin.id}",
        )
        spam_filter.reset_warnings(user_id)
    except Exception as exc:
        await update.message.reply_text(f"❌ Could not ban user: {exc}")


# ─────────────────────── /warn ─────────────────────────────────────

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin(update, context):
        return

    username, reason = _parse_target(context)
    user_id = await _resolve_user_id(update, context, username)

    if not user_id:
        await update.message.reply_text(
            "Usage: /warn @username [reason] — or reply to a message."
        )
        return

    chat = update.effective_chat
    admin = update.effective_user
    count = spam_filter.add_warning(user_id)

    await update.message.reply_text(
        f"⚠️ Warning issued to `{username or user_id}` ({count}/2).\n_Reason: {reason}_",
        parse_mode="Markdown",
    )
    log_moderation(
        user=f"@{username or user_id}",
        action=f"Warn {count}",
        reason=reason,
        admin=f"@{admin.username or admin.id}",
    )

    if count >= 3:
        try:
            await context.bot.ban_chat_member(chat_id=chat.id, user_id=user_id)
            await update.message.reply_text(
                f"🚫 `{username or user_id}` reached 3 warnings and has been auto-banned.",
                parse_mode="Markdown",
            )
            log_moderation(
                user=f"@{username or user_id}",
                action="Ban",
                reason="3 warnings reached",
                admin=f"@{admin.username or admin.id}",
            )
            spam_filter.reset_warnings(user_id)
        except Exception as exc:
            logger.warning(f"Auto-ban after 3 warns failed: {exc}")


# ─────────────────────── /mute ─────────────────────────────────────

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin(update, context):
        return

    args = context.args or []
    username = args[0].lstrip("@") if args else None
    minutes = 10  # default

    # Allow: /mute @user 30  or  /mute @user  or reply with /mute 30
    if len(args) >= 2:
        try:
            minutes = int(args[1])
        except ValueError:
            pass
    elif len(args) == 1:
        try:
            minutes = int(args[0])
            username = None
        except ValueError:
            pass

    user_id = await _resolve_user_id(update, context, username)

    if not user_id:
        await update.message.reply_text(
            "Usage: /mute @username [minutes] — or reply to a message."
        )
        return

    chat = update.effective_chat
    admin = update.effective_user
    until = datetime.now(tz=timezone.utc) + timedelta(minutes=minutes)

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user_id,
            permissions=RESTRICTED,
            until_date=until,
        )
        await update.message.reply_text(
            f"🔇 `{username or user_id}` muted for *{minutes} minute(s)*.",
            parse_mode="Markdown",
        )
        log_moderation(
            user=f"@{username or user_id}",
            action=f"Mute {minutes}min",
            reason="Manual mute",
            admin=f"@{admin.username or admin.id}",
        )
    except Exception as exc:
        await update.message.reply_text(f"❌ Could not mute user: {exc}")


# ─────────────────────── /unban ────────────────────────────────────

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin(update, context):
        return

    username, _ = _parse_target(context)
    user_id = await _resolve_user_id(update, context, username)

    if not user_id:
        await update.message.reply_text("Usage: /unban @username")
        return

    chat = update.effective_chat
    admin = update.effective_user

    try:
        await context.bot.unban_chat_member(
            chat_id=chat.id, user_id=user_id, only_if_banned=True
        )
        await update.message.reply_text(
            f"✅ `{username or user_id}` has been unbanned.",
            parse_mode="Markdown",
        )
        log_moderation(
            user=f"@{username or user_id}",
            action="Unban",
            reason="Manual unban",
            admin=f"@{admin.username or admin.id}",
        )
        spam_filter.reset_warnings(user_id)
    except Exception as exc:
        await update.message.reply_text(f"❌ Could not unban user: {exc}")


# ─────────────────────── /stats ────────────────────────────────────

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin(update, context):
        return

    stats = get_moderation_stats()
    if not stats:
        await update.message.reply_text("📊 No moderation data yet.")
        return

    await update.message.reply_text(
        f"📊 *Moderation Stats*\n\n"
        f"🚫 Bans:     {stats.get('bans', 0)}\n"
        f"⚠️  Warnings: {stats.get('warns', 0)}\n"
        f"🔇 Mutes:    {stats.get('mutes', 0)}\n"
        f"📋 Total:    {stats.get('total', 0)}",
        parse_mode="Markdown",
    )


# ─────────────────────── /rules ────────────────────────────────────

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    rules = spam_filter.group_rules.get(chat.id)
    if rules:
        await update.message.reply_text(
            f"📜 *Group Rules*\n\n{rules}",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "ℹ️ No rules have been set yet. Admins can use /setrules to add them."
        )


# ─────────────────────── /setrules ─────────────────────────────────

async def setrules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_admin(update, context):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /setrules [rules text]\n"
            "Example: /setrules No spam. No links. Be respectful."
        )
        return

    chat = update.effective_chat
    rules_text = " ".join(context.args)
    spam_filter.group_rules[chat.id] = rules_text

    await update.message.reply_text(
        f"✅ *Group rules updated!*\n\n{rules_text}",
        parse_mode="Markdown",
    )
