"""
GreetBot Telegram Notifier Skill
==================================
Sends photos and files directly to a Telegram chat via the Bot API.
No OpenClaw or gateway needed — uses requests directly.

Setup:
    1. Create a bot with @BotFather on Telegram → get TELEGRAM_BOT_TOKEN
    2. Send any message to your bot → get TELEGRAM_CHAT_ID via:
       curl https://api.telegram.org/bot<TOKEN>/getUpdates
    3. Add both to your .env file
"""

import os
import io
import glob
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.logger import get_logger

log = get_logger(__name__)

_BASE_URL = "https://api.telegram.org/bot{token}/{method}"

# Throttle: don't send more than 1 unknown-face alert per N seconds
_ALERT_COOLDOWN = 120  # 2 minutes
_last_alert_time: float = 0.0
_alert_lock = threading.Lock()


def _is_configured() -> bool:
    """Return True if Telegram credentials are set."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False
    return True


def send_message(text: str) -> bool:
    """Send a plain text message to the configured chat."""
    if not _is_configured():
        return False
    try:
        url = _BASE_URL.format(token=TELEGRAM_BOT_TOKEN, method="sendMessage")
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }, timeout=10)
        resp.raise_for_status()
        log.info("Telegram message sent.")
        return True
    except Exception as e:
        log.error(f"Telegram sendMessage error: {e}")
        return False


def send_photo_frame(frame, caption: str = "Unknown visitor detected!") -> bool:
    """
    Send an OpenCV frame (numpy array) as a photo to Telegram.
    Used to alert when an unknown face is detected by the camera.
    """
    if not _is_configured():
        return False

    global _last_alert_time
    with _alert_lock:
        now = time.time()
        if now - _last_alert_time < _ALERT_COOLDOWN:
            log.debug("Telegram alert on cooldown, skipping.")
            return False
        _last_alert_time = now

    try:
        # Encode the OpenCV frame as JPEG in memory
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            log.error("Failed to encode frame as JPEG.")
            return False

        url = _BASE_URL.format(token=TELEGRAM_BOT_TOKEN, method="sendPhoto")
        photo_bytes = io.BytesIO(buffer.tobytes())
        photo_bytes.name = "visitor.jpg"

        resp = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption,
        }, files={"photo": photo_bytes}, timeout=15)
        resp.raise_for_status()
        log.info("Telegram visitor photo sent.")
        return True
    except Exception as e:
        log.error(f"Telegram sendPhoto error: {e}")
        return False


def send_file(file_path: str, caption: str = "") -> bool:
    """Send a local file (document/image) to the Telegram chat."""
    if not _is_configured():
        return False

    path = Path(file_path)
    if not path.exists():
        log.error(f"File not found: {file_path}")
        return False

    try:
        url = _BASE_URL.format(token=TELEGRAM_BOT_TOKEN, method="sendDocument")
        with open(path, "rb") as f:
            resp = requests.post(url, data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption or f"📎 {path.name}",
            }, files={"document": (path.name, f)}, timeout=30)
        resp.raise_for_status()
        log.info(f"Telegram file sent: {path.name}")
        return True
    except Exception as e:
        log.error(f"Telegram sendDocument error: {e}")
        return False


# ── File Search ────────────────────────────────────────────────────────────────

_SEARCH_DIRS = [
    Path.home(),
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / "greetbot",
]


def find_file(query: str) -> Optional[str]:
    """
    Fuzzy search for a file by name keywords across common directories.

    Example:
        find_file("timetable")  → "/home/pi/Documents/timetable_monday.pdf"
    """
    keywords = query.lower().split()
    candidates: list[tuple[int, str]] = []

    for search_dir in _SEARCH_DIRS:
        if not search_dir.exists():
            continue
        for f in search_dir.rglob("*"):
            if f.is_file():
                name_lower = f.name.lower()
                score = sum(1 for kw in keywords if kw in name_lower)
                if score > 0:
                    candidates.append((score, str(f)))

    if not candidates:
        return None

    # Return the best match
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


# ── Voice Command Detection ────────────────────────────────────────────────────

_SEND_PATTERNS = [
    r"send (?:me |the |my )?(.+?) (?:to telegram|on telegram|via telegram|through telegram)",
    r"(?:send|forward|share) (.+?) to (?:telegram|my phone|my chat)",
    r"telegram (.+)",
    r"(?:can you |please )?send (?:me |the |my )?(.+?)(?:\s+to telegram)?$",
]


def is_file_send_query(text: str) -> bool:
    """Detect if user is asking to send a file to Telegram."""
    lower = text.lower()
    triggers = ["send", "telegram", "forward", "share", "send me"]
    file_hints = ["file", "photo", "image", "document", "pdf", "doc",
                  "timetable", "schedule", "notes", "report", "sheet"]
    has_trigger = any(t in lower for t in triggers)
    has_file_hint = any(h in lower for h in file_hints)
    return has_trigger and (has_file_hint or "telegram" in lower)


def extract_file_query(text: str) -> str:
    """Extract the file name/description from the user's voice command."""
    import re
    for pattern in _SEND_PATTERNS:
        m = re.search(pattern, text.lower())
        if m:
            return m.group(1).strip()
    # Fallback: remove common words and use what remains
    lower = text.lower()
    for word in ["send", "me", "the", "my", "to", "telegram", "please", "can", "you", "forward", "share", "via", "on"]:
        lower = lower.replace(word, " ")
    return lower.strip()
