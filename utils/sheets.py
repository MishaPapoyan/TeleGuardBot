"""
Google Sheets integration for TeleGuard.

Sheet layout expected:
  Sheet 1 — "Leads"         : Timestamp | Name | Service | Budget | Contact | Status
  Sheet 2 — "Bookings"      : Timestamp | Name | Email | Time Preference | Status
  Sheet 3 — "FAQ Questions" : Timestamp | Username | Question
  Sheet 4 — "Moderation Log": Timestamp | User | Action | Reason | Admin
"""

import logging
from datetime import datetime
from functools import lru_cache

import gspread
from google.oauth2.service_account import Credentials

from config import config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_REQUIRED_SHEETS = ["Leads", "Bookings", "FAQ Questions", "Moderation Log"]


def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_JSON, scopes=SCOPES
    )
    return gspread.authorize(creds)


def _get_worksheet(name: str) -> gspread.Worksheet:
    client = _get_client()
    spreadsheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    return spreadsheet.worksheet(name)


def ensure_sheets_exist() -> bool:
    """Create missing sheets with headers. Called once at startup."""
    try:
        client = _get_client()
        spreadsheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        existing = {ws.title for ws in spreadsheet.worksheets()}

        headers = {
            "Leads": ["Timestamp", "Name", "Service", "Budget", "Contact", "Status"],
            "Bookings": ["Timestamp", "Name", "Email", "Time Preference", "Status"],
            "FAQ Questions": ["Timestamp", "Username", "Question"],
            "Moderation Log": ["Timestamp", "User", "Action", "Reason", "Admin"],
        }

        for sheet_name, header_row in headers.items():
            if sheet_name not in existing:
                ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                ws.append_row(header_row)
                logger.info(f"Created sheet: {sheet_name}")

        return True
    except Exception as exc:
        logger.error(f"Could not ensure sheets exist: {exc}")
        return False


def save_lead(name: str, service: str, budget: str, contact: str) -> bool:
    try:
        ws = _get_worksheet("Leads")
        ws.append_row([_now(), name, service, budget, contact, "New"])
        return True
    except Exception as exc:
        logger.error(f"save_lead failed: {exc}")
        return False


def save_booking(name: str, email: str, time_pref: str) -> bool:
    try:
        ws = _get_worksheet("Bookings")
        ws.append_row([_now(), name, email, time_pref, "Pending"])
        return True
    except Exception as exc:
        logger.error(f"save_booking failed: {exc}")
        return False


def save_faq_question(username: str, question: str) -> bool:
    try:
        ws = _get_worksheet("FAQ Questions")
        ws.append_row([_now(), username, question])
        return True
    except Exception as exc:
        logger.error(f"save_faq_question failed: {exc}")
        return False


def log_moderation(user: str, action: str, reason: str, admin: str) -> bool:
    try:
        ws = _get_worksheet("Moderation Log")
        ws.append_row([_now(), user, action, reason, admin])
        return True
    except Exception as exc:
        logger.error(f"log_moderation failed: {exc}")
        return False


def get_moderation_stats() -> dict[str, int]:
    try:
        ws = _get_worksheet("Moderation Log")
        records = ws.get_all_records()
        stats: dict[str, int] = {"bans": 0, "warns": 0, "mutes": 0, "total": len(records)}
        for r in records:
            action = str(r.get("Action", "")).lower()
            if action.startswith("ban"):
                stats["bans"] += 1
            elif action.startswith("warn"):
                stats["warns"] += 1
            elif action.startswith("mute"):
                stats["mutes"] += 1
        return stats
    except Exception as exc:
        logger.error(f"get_moderation_stats failed: {exc}")
        return {}
