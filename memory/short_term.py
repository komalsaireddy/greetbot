"""
GreetBot Short-Term Memory
==========================
In-memory conversation buffer for the current session.
Holds recent dialogue turns per person so the LLM has context
without hitting the database on every query.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from config import SHORT_TERM_MAX_TURNS
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class Turn:
    """A single conversation turn."""
    role: str        # "user" | "assistant" | "system"
    content: str


class ShortTermMemory:
    """
    Circular buffer of recent conversation turns.

    One instance per active conversation session. Automatically discards
    the oldest turns when *max_turns* is exceeded.

    Parameters
    ----------
    max_turns:
        Maximum number of turns to retain.
    """

    def __init__(self, max_turns: int = SHORT_TERM_MAX_TURNS) -> None:
        self._max_turns = max_turns
        self._buffer: Deque[Turn] = deque(maxlen=max_turns)

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add(self, role: str, content: str) -> None:
        """Append a turn to the buffer.

        Parameters
        ----------
        role:
            ``"user"`` or ``"assistant"``.
        content:
            Text content of the turn.
        """
        self._buffer.append(Turn(role=role, content=content))

    def add_user(self, content: str) -> None:
        """Shorthand for ``add("user", content)``."""
        self.add("user", content)

    def add_assistant(self, content: str) -> None:
        """Shorthand for ``add("assistant", content)``."""
        self.add("assistant", content)

    def clear(self) -> None:
        """Clear all stored turns."""
        self._buffer.clear()

    # ── Access ────────────────────────────────────────────────────────────────

    def get_history(self) -> list[Turn]:
        """Return all stored turns in chronological order."""
        return list(self._buffer)

    def to_messages(self) -> list[dict[str, str]]:
        """
        Convert history to the OpenAI / Groq message format.

        Returns
        -------
        list[dict]
            List of ``{"role": ..., "content": ...}`` dicts.
        """
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self._buffer
        ]

    def to_prompt_text(self) -> str:
        """
        Format history as a readable text block for injection into prompts.

        Returns
        -------
        str
            Multi-line string of recent conversation turns.
        """
        if not self._buffer:
            return "No conversation history yet."

        lines = []
        for turn in self._buffer:
            label = "You" if turn.role == "user" else "GreetBot"
            lines.append(f"{label}: {turn.content}")
        return "\n".join(lines)

    def last_user_message(self) -> str:
        """Return the most recent user message, or empty string."""
        for turn in reversed(self._buffer):
            if turn.role == "user":
                return turn.content
        return ""

    def last_bot_message(self) -> str:
        """Return the most recent assistant message, or empty string."""
        for turn in reversed(self._buffer):
            if turn.role == "assistant":
                return turn.content
        return ""

    def __len__(self) -> int:
        return len(self._buffer)

    def __repr__(self) -> str:
        return f"ShortTermMemory(turns={len(self._buffer)}, max={self._max_turns})"
