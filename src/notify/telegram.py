import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import requests


class PushDecision(str, Enum):
    NONE = "none"
    GREEN_WINDOW = "green_window"
    RATE_LIMITED = "rate_limited"


@dataclass(frozen=True)
class Decision:
    kind: PushDecision
    reason: str = ""


RATE_LIMIT_HOURS = 12


def _green_block_of_2(days: list[dict]) -> bool:
    """Return True iff any two adjacent days both have stufe='gruen'."""
    for a, b in zip(days, days[1:]):
        if a.get("stufe") == "gruen" and b.get("stufe") == "gruen":
            return True
    return False


def should_push(current: Path, previous: Path, last_push_ts: datetime | None,
                now: datetime) -> Decision:
    """Decide whether to send a push based on transition into Grün.

    Triggers:
      (a) today was not Grün before and is now
      (b) a 2-day Grün block appears in the forecast that wasn't there before
    Rate-limited to at most one push per RATE_LIMIT_HOURS.
    """
    if not current.exists():
        return Decision(PushDecision.NONE, "no current status")
    cur = json.loads(current.read_text())
    prv = json.loads(previous.read_text()) if previous.exists() else {"days": []}

    cur_days = cur.get("days", [])
    prv_days = prv.get("days", [])

    today_green = bool(cur_days) and cur_days[0].get("stufe") == "gruen"
    was_green = bool(prv_days) and prv_days[0].get("stufe") == "gruen"
    transition = today_green and not was_green
    new_window = _green_block_of_2(cur_days) and not _green_block_of_2(prv_days)

    if not (transition or new_window):
        return Decision(PushDecision.NONE, "no positive transition")

    if last_push_ts is not None and (now - last_push_ts) < timedelta(hours=RATE_LIMIT_HOURS):
        return Decision(PushDecision.RATE_LIMITED, f"last push {now - last_push_ts} ago")

    return Decision(PushDecision.GREEN_WINDOW, "transition or new green block")


def compose_message(status: dict) -> str:
    """Compose a short Telegram message from a status dict."""
    level = status.get("latest_level_cm")
    days = status.get("days", [])
    day_str = " · ".join(f"{d.get('day', '—')[-5:]} {d.get('emoji', '?')}" for d in days[:5])
    level_part = f"{level:.0f} cm" if level is not None else "—"
    return f"🛶 Jagst Dörzbach: {level_part}\n{day_str}\nhttps://joerglohrer.github.io/kanu-hohenlohe/"


def send_push(text: str) -> None:
    """Send a Telegram message using env-loaded credentials. Raises on missing creds or HTTP error."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text,
                                 "disable_web_page_preview": False},
                      timeout=20)
    r.raise_for_status()
