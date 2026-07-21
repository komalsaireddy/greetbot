"""
GreetBot Emotion Detector
==========================
Lightweight text-based sentiment analysis that determines the emotional
tone of user messages to drive avatar expressions and personality tone.

No heavy ML required — uses keyword patterns and simple heuristics.
"""

import re
from enum import Enum
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)


class Emotion(str, Enum):
    """Supported emotion states for the avatar and personality."""
    NEUTRAL    = "NEUTRAL"
    HAPPY      = "HAPPY"
    CURIOUS    = "CURIOUS"
    THOUGHTFUL = "THOUGHTFUL"
    SURPRISED  = "SURPRISED"
    SAD        = "SAD"
    FRUSTRATED = "FRUSTRATED"


# ── Keyword patterns ──────────────────────────────────────────────────────────
# Each entry: (emotion, list of patterns)

_PATTERNS: list[tuple[Emotion, list[str]]] = [
    (Emotion.HAPPY, [
        r"\b(great|amazing|awesome|fantastic|wonderful|love|happy|joy|excited|"
        r"thank you|thanks|grateful|perfect|excellent|brilliant)\b",
    ]),
    (Emotion.SAD, [
        r"\b(sad|unhappy|depressed|miserable|upset|crying|miss|lonely|heartbroken|"
        r"terrible|awful|horrible|bad day)\b",
    ]),
    (Emotion.FRUSTRATED, [
        r"\b(frustrated|annoyed|angry|mad|furious|irritated|stupid|useless|"
        r"broken|doesn't work|not working|why won't|stop|quit|ugh|argh)\b",
    ]),
    (Emotion.SURPRISED, [
        r"\b(wow|really|seriously|what|no way|oh my|unbelievable|incredible|"
        r"didn't know|never knew|i had no idea|fascinating)\b",
    ]),
    (Emotion.CURIOUS, [
        r"\b(how|why|what is|tell me|explain|curious|interesting|wonder|"
        r"can you|could you|would you|please tell)\b",
    ]),
    (Emotion.THOUGHTFUL, [
        r"\b(think|believe|maybe|perhaps|probably|i suppose|i wonder|let me see|"
        r"it seems|as far as|in my opinion|i feel like)\b",
    ]),
]


class EmotionDetector:
    """
    Detects the emotional tone from text using rule-based pattern matching.

    The detector checks the user's message against keyword patterns in
    priority order. If multiple emotions match, the highest-priority one wins.
    Falls back to NEUTRAL if nothing matches.
    """

    def detect(self, text: str) -> Emotion:
        """
        Analyze text and return the detected emotion.

        Parameters
        ----------
        text:
            User's spoken or typed message.

        Returns
        -------
        Emotion
            Detected emotion enum value.
        """
        if not text:
            return Emotion.NEUTRAL

        lower = text.lower()

        for emotion, patterns in _PATTERNS:
            for pattern in patterns:
                if re.search(pattern, lower):
                    log.debug(f"Emotion detected: {emotion.value} (pattern: {pattern[:30]})")
                    return emotion

        return Emotion.NEUTRAL

    def detect_from_reply(self, reply: str) -> Emotion:
        """
        Analyze the *bot's* reply to set appropriate avatar expression.

        Uses a slightly different set of heuristics tuned for bot output.

        Parameters
        ----------
        reply:
            GreetBot's response text.

        Returns
        -------
        Emotion
            Expression the avatar should show.
        """
        if not reply:
            return Emotion.NEUTRAL

        lower = reply.lower()

        # Happy/warm response indicators
        if re.search(r"\b(great|wonderful|love|happy|welcome|pleasure|glad)\b", lower):
            return Emotion.HAPPY

        # Curious / questioning
        if reply.strip().endswith("?"):
            return Emotion.CURIOUS

        # Thoughtful / long responses
        if len(reply.split()) > 40:
            return Emotion.THOUGHTFUL

        # Surprised
        if re.search(r"\b(wow|amazing|incredible|fascinating|interesting)\b", lower):
            return Emotion.SURPRISED

        return Emotion.NEUTRAL
