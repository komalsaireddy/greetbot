"""
GreetBot Search Skill
======================
Web search using DuckDuckGo Instant Answer API.
No API key required. Returns a brief text snippet.
"""

import requests
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)

_DDG_URL = "https://api.duckduckgo.com/"


def search(query: str, max_len: int = 300) -> Optional[str]:
    """
    Perform a DuckDuckGo instant answer search.

    Uses the DuckDuckGo instant answers API which is free and requires
    no API key. Best for factual questions, definitions, and quick lookups.

    Parameters
    ----------
    query:
        Search query string.
    max_len:
        Maximum character length of the returned snippet.

    Returns
    -------
    str or None
        Text snippet from the top result, or None if nothing found.
    """
    try:
        resp = requests.get(
            _DDG_URL,
            params={
                "q":      query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
            },
            timeout=5,
            headers={"User-Agent": "GreetBot/2.0"},
        )
        resp.raise_for_status()
        data = resp.json()

        # Try AbstractText first (best factual answer)
        text = data.get("AbstractText", "").strip()

        if not text:
            # Fallback to Answer field
            text = data.get("Answer", "").strip()

        if not text:
            # Fallback to Definition
            text = data.get("Definition", "").strip()

        if not text:
            # Try Related Topics
            topics = data.get("RelatedTopics", [])
            for topic in topics:
                if isinstance(topic, dict) and topic.get("Text"):
                    text = topic["Text"].strip()
                    break

        if text:
            from utils.helpers import truncate
            return truncate(text, max_len)

        log.debug(f"No result for query: {query!r}")
        return None

    except requests.exceptions.Timeout:
        log.warning("DuckDuckGo search timed out")
        return None
    except Exception as exc:
        log.error(f"Search error: {exc}")
        return None


def format_search_result(query: str, result: Optional[str]) -> str:
    """
    Format a search result as a TTS-ready spoken response.

    Parameters
    ----------
    query:
        Original query (for fallback message).
    result:
        Text snippet from ``search()``.

    Returns
    -------
    str
        Natural-language response ready for speech.
    """
    if result:
        return f"Here's what I found: {result}"
    return (
        f"I searched for '{query}' but couldn't find a quick answer. "
        "You might want to check online for more details."
    )


def is_search_query(text: str) -> bool:
    """
    Detect if a user message is requesting an internet search.

    Parameters
    ----------
    text:
        User's message.

    Returns
    -------
    bool
        True if the message appears to be a search/lookup query.
    """
    triggers = [
        "search for", "look up", "google", "find out",
        "what is", "who is", "who was", "what are",
        "tell me about", "do you know about", "explain",
        "define", "definition of", "meaning of",
    ]
    lower = text.lower()
    return any(t in lower for t in triggers)


def extract_search_query(text: str) -> str:
    """
    Clean a user message into a concise search query string.

    Parameters
    ----------
    text:
        User's raw message.

    Returns
    -------
    str
        Cleaned search query.
    """
    import re

    # Remove common trigger phrases
    removals = [
        r"^(please |can you |could you )?(search for|look up|google|find out|"
        r"tell me about|do you know about|explain|define|"
        r"what is|who is|who was|what are|meaning of|definition of)\s+",
    ]
    cleaned = text.strip()
    for pattern in removals:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned
