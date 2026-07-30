"""
GreetBot Wikipedia Skill
========================
Uses the `wikipedia` python package to retrieve summaries.
"""

import wikipedia
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)


def search_wikipedia(query: str, sentences: int = 2) -> Optional[str]:
    """
    Search Wikipedia and return a short summary.
    """
    try:
        # Avoid extremely ambiguous searches
        results = wikipedia.search(query)
        if not results:
            log.debug(f"Wikipedia: No results for '{query}'")
            return None
        
        # Take the top result
        page = wikipedia.page(results[0], auto_suggest=False)
        summary = wikipedia.summary(title=page.title, sentences=sentences)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        # If ambiguous, just pick the first option
        try:
            summary = wikipedia.summary(e.options[0], sentences=sentences)
            return summary
        except Exception:
            return None
    except wikipedia.exceptions.PageError:
        return None
    except Exception as exc:
        log.error(f"Wikipedia error: {exc}")
        return None


def is_wikipedia_query(text: str) -> bool:
    """
    Detect if the user is explicitly asking to check Wikipedia or lookup an entity.
    """
    lower = text.lower()
    return "wikipedia" in lower or "who is" in lower or "what is" in lower


def extract_wikipedia_query(text: str) -> str:
    """
    Extract the topic from the user's query.
    """
    import re
    cleaned = text.strip()
    removals = [
        r"^(please )?search wikipedia for\s+",
        r"^(please )?check wikipedia for\s+",
        r"^(please )?tell me who is\s+",
        r"^(please )?tell me what is\s+",
        r"^who is\s+",
        r"^what is\s+",
        r"\s+on wikipedia\b",
    ]
    for pattern in removals:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def format_wikipedia_result(query: str, result: Optional[str]) -> str:
    if result:
        return result
    return f"I couldn't find a Wikipedia page for {query}."
