"""
Spam detection and flood tracking for TeleGuard.

Checks performed per message:
  1. Flood       — 5+ messages within 10 seconds
  2. Mass mention — 5+ @mentions in one message
  3. Duplicate   — same text sent 3+ times
  4. Keyword     — message matches blocklist
  5. Link + new  — link from user who joined < 7 days ago
"""

import re
import time
from collections import defaultdict, deque
from typing import Optional

URL_PATTERN = re.compile(
    r"(https?://|www\.|t\.me/)",
    re.IGNORECASE,
)
MENTION_PATTERN = re.compile(r"@\w+")

DEFAULT_KEYWORDS: list[str] = [
    "buy crypto",
    "investment opportunity",
    "guaranteed profit",
    "earn $",
    "make money fast",
    "free money",
    "click here to earn",
    "passive income",
]

# Thresholds
FLOOD_MESSAGES = 5       # messages
FLOOD_WINDOW = 10        # seconds
DUPLICATE_THRESHOLD = 3  # occurrences before action
MASS_MENTION_THRESHOLD = 5
NEW_ACCOUNT_DAYS = 7


class SpamFilter:
    def __init__(self) -> None:
        # {user_id: deque of message timestamps}
        self._flood: dict[int, deque] = defaultdict(lambda: deque(maxlen=20))
        # {user_id: list of recent message texts}
        self._history: dict[int, list[str]] = defaultdict(list)
        # {user_id: warning count}
        self._warnings: dict[int, int] = defaultdict(int)
        # {chat_id: rules text}
        self.group_rules: dict[int, str] = {}
        # Mutable keyword list (admin can extend)
        self.keywords: list[str] = list(DEFAULT_KEYWORDS)

    # ------------------------------------------------------------------ flood

    def check_flood(self, user_id: int) -> bool:
        """True if user sent FLOOD_MESSAGES or more within FLOOD_WINDOW seconds."""
        now = time.monotonic()
        dq = self._flood[user_id]
        dq.append(now)
        recent = sum(1 for t in dq if now - t <= FLOOD_WINDOW)
        return recent >= FLOOD_MESSAGES

    # --------------------------------------------------------------- duplicate

    def check_duplicate(self, user_id: int, text: str) -> bool:
        """True if this exact text has been sent DUPLICATE_THRESHOLD times."""
        history = self._history[user_id]
        count = history.count(text)
        history.append(text)
        if len(history) > 30:
            self._history[user_id] = history[-30:]
        return count + 1 >= DUPLICATE_THRESHOLD

    # ---------------------------------------------------------- mass mentions

    def check_mass_mention(self, text: str) -> bool:
        return len(MENTION_PATTERN.findall(text)) >= MASS_MENTION_THRESHOLD

    # --------------------------------------------------------------- keywords

    def check_keywords(self, text: str) -> Optional[str]:
        """Returns the matched keyword string, or None."""
        lower = text.lower()
        for kw in self.keywords:
            if kw.lower() in lower:
                return kw
        return None

    # -------------------------------------------------- link + new account

    def check_link_new_account(self, text: str, days_in_group: int) -> bool:
        """True if user joined < NEW_ACCOUNT_DAYS days ago and sent a link."""
        return days_in_group < NEW_ACCOUNT_DAYS and bool(URL_PATTERN.search(text))

    # ------------------------------------------------------------ warnings

    def add_warning(self, user_id: int) -> int:
        """Increment warning count and return the new total."""
        self._warnings[user_id] += 1
        return self._warnings[user_id]

    def get_warnings(self, user_id: int) -> int:
        return self._warnings[user_id]

    def reset_warnings(self, user_id: int) -> None:
        self._warnings[user_id] = 0


# Module-level singleton shared across all handlers
spam_filter = SpamFilter()
