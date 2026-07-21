"""
GreetBot Helpers
================
General-purpose utility functions used throughout the project.
"""

import re
import uuid
from datetime import datetime
from typing import Any


def clean_text(text: str) -> str:
    """
    Normalize text for TTS output.

    Removes markdown formatting, excess whitespace, and special characters
    that sound bad when read aloud.

    Parameters
    ----------
    text:
        Raw text, possibly containing markdown.

    Returns
    -------
    str
        Clean, TTS-friendly text.
    """
    if not text:
        return ""

    # Remove markdown bold/italic
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)

    # Remove markdown headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Remove markdown links [text](url)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)

    # Remove inline code
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Remove bullet points
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)

    # Collapse multiple whitespace / newlines
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


def truncate(text: str, max_len: int = 200, suffix: str = "...") -> str:
    """
    Safely truncate text to *max_len* characters.

    Breaks at a word boundary where possible.

    Parameters
    ----------
    text:
        Text to truncate.
    max_len:
        Maximum allowed character count (including suffix).
    suffix:
        Appended when truncation occurs.

    Returns
    -------
    str
        Truncated text.
    """
    if len(text) <= max_len:
        return text

    cutoff = max_len - len(suffix)
    truncated = text[:cutoff].rsplit(" ", 1)[0]
    return truncated + suffix


def format_duration(seconds: float) -> str:
    """
    Convert seconds to a human-readable duration string.

    Examples::

        format_duration(90)    → "1 minute 30 seconds"
        format_duration(3700)  → "1 hour 1 minute"

    Parameters
    ----------
    seconds:
        Duration in seconds.

    Returns
    -------
    str
        Human-readable duration.
    """
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"

    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        parts = [f"{minutes} minute{'s' if minutes != 1 else ''}"]
        if secs:
            parts.append(f"{secs} second{'s' if secs != 1 else ''}")
        return " ".join(parts)

    hours, mins = divmod(minutes, 60)
    parts = [f"{hours} hour{'s' if hours != 1 else ''}"]
    if mins:
        parts.append(f"{mins} minute{'s' if mins != 1 else ''}")
    return " ".join(parts)


def current_time_greeting() -> str:
    """
    Return a time-appropriate greeting phrase.

    Returns
    -------
    str
        "Good morning", "Good afternoon", or "Good evening".
    """
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"


def generate_id() -> str:
    """
    Generate a short unique identifier.

    Returns
    -------
    str
        8-character hex string (e.g. ``"a3f9c12b"``).
    """
    return uuid.uuid4().hex[:8]


def safe_get(obj: Any, *keys: str, default: Any = None) -> Any:
    """
    Safely traverse nested dicts / objects.

    Parameters
    ----------
    obj:
        Root object.
    *keys:
        Keys to traverse.
    default:
        Returned if any key is missing.

    Returns
    -------
    Any
        Value at the nested path, or *default*.
    """
    current = obj
    for key in keys:
        try:
            if isinstance(current, dict):
                current = current[key]
            else:
                current = getattr(current, key)
        except (KeyError, AttributeError, TypeError):
            return default
    return current


def normalize_name(name: str) -> str:
    """
    Normalize a person's name to Title Case, stripping extra whitespace.

    Parameters
    ----------
    name:
        Raw name string.

    Returns
    -------
    str
        Normalized name (e.g. ``"  komal  "`` → ``"Komal"``).
    """
    return " ".join(
        word.capitalize()
        for word in name.strip().split()
        if word.isalpha()
    )
