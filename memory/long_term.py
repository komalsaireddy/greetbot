"""
GreetBot Long-Term Memory
=========================
SQLite-backed persistent fact and conversation storage per person.
Survives restarts and grows richer with every interaction.
"""

from typing import Any, Optional

from memory.database import Database
from utils.logger import get_logger

log = get_logger(__name__)


class LongTermMemory:
    """
    Persistent memory for a specific person.

    Wraps the Database to provide a clean, person-scoped API for
    storing and retrieving facts, preferences, and conversation summaries.

    Parameters
    ----------
    person_id:
        Unique identifier for the person (e.g. ``"Komal"`` or ``"person_001"``).
    db:
        Shared Database instance. If None, a new one is created.
    """

    def __init__(self, person_id: str, db: Optional[Database] = None) -> None:
        self.person_id = person_id
        self._db = db or Database()

    # ── Facts ─────────────────────────────────────────────────────────────────

    def remember(self, key: str, value: Any) -> None:
        """
        Store or update a fact.

        Parameters
        ----------
        key:
            Fact name (e.g. ``"college"``, ``"hobby"``).
        value:
            Fact value (converted to string for storage).
        """
        self._db.set_fact(self.person_id, key, value)
        log.debug(f"[{self.person_id}] Remembered: {key} = {value}")

    def recall(self, key: str, default: Any = None) -> Optional[str]:
        """
        Recall a specific fact.

        Parameters
        ----------
        key:
            Fact name to look up.
        default:
            Returned if the fact is not found.

        Returns
        -------
        str or None
            Stored value string, or *default*.
        """
        facts = self._db.get_facts(self.person_id)
        return facts.get(key, default)

    def get_all_facts(self) -> dict[str, str]:
        """Return all stored facts for this person."""
        return self._db.get_facts(self.person_id)

    def forget(self, key: str) -> None:
        """Remove a specific fact."""
        self._db.delete_fact(self.person_id, key)
        log.debug(f"[{self.person_id}] Forgot: {key}")

    def get_summary(self) -> str:
        """
        Format all known facts as a compact text block for LLM injection.

        Returns
        -------
        str
            Multi-line summary, or ``"No stored information."`` if empty.
        """
        facts = self.get_all_facts()
        if not facts:
            return "No stored information."

        lines = [f"- {k.replace('_', ' ').title()}: {v}" for k, v in facts.items()]
        return "\n".join(lines)

    # ── Conversation History ──────────────────────────────────────────────────

    def save_turn(
        self,
        role: str,
        content: str,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Persist a conversation turn to the database.

        Parameters
        ----------
        role:
            ``"user"`` or ``"assistant"``.
        content:
            Text of the turn.
        session_id:
            Optional session grouping key.
        """
        self._db.add_conversation_turn(
            self.person_id, role, content, session_id
        )

    def get_recent_turns(self, n: int = 10) -> list[dict]:
        """Return the *n* most recent conversation turns."""
        return self._db.get_last_n_turns(self.person_id, n)

    def get_history_text(self, n: int = 5) -> str:
        """
        Format recent conversation turns as readable text for LLM context.

        Parameters
        ----------
        n:
            Number of most-recent turns to include.

        Returns
        -------
        str
            Formatted conversation history block.
        """
        turns = self.get_recent_turns(n)
        if not turns:
            return "No previous conversations."

        lines = []
        for t in turns:
            label = "User" if t["role"] == "user" else "GreetBot"
            lines.append(f"{label}: {t['content']}")
        return "\n".join(lines)

    # ── Person Profile ────────────────────────────────────────────────────────

    def get_profile(self) -> Optional[dict]:
        """Return this person's profile record from the database."""
        return self._db.get_person(self.person_id)

    def __repr__(self) -> str:
        facts = self._db.get_facts(self.person_id)
        return f"LongTermMemory(person={self.person_id!r}, facts={len(facts)})"
