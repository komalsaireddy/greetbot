"""
GreetBot Conversation Manager
==============================
Manages per-person conversation sessions, combining short-term (in-memory)
and long-term (SQLite) memory into a unified interface for the LLM.
"""

import uuid
from typing import Optional

from memory.database import Database
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from utils.logger import get_logger

log = get_logger(__name__)


class ConversationSession:
    """
    A single conversation session with one person.

    Holds both the in-memory conversation buffer (short-term) and a
    reference to the person's persistent memory (long-term).

    Parameters
    ----------
    person_id:
        Database ID of the conversation partner.
    person_name:
        Display name of the partner.
    db:
        Shared Database instance.
    """

    def __init__(
        self,
        person_id: str,
        person_name: str,
        db: Database,
    ) -> None:
        self.person_id = person_id
        self.person_name = person_name
        self.session_id: str = uuid.uuid4().hex[:8]

        self._short_term = ShortTermMemory()
        self._long_term = LongTermMemory(person_id=person_id, db=db)

        log.info(f"Conversation session started: {person_name} (session={self.session_id})")

    # ── Turn Management ───────────────────────────────────────────────────────

    def add_turn(self, role: str, content: str) -> None:
        """
        Record a conversation turn in both short-term and long-term memory.

        Parameters
        ----------
        role:
            ``"user"`` or ``"assistant"``.
        content:
            Text of the turn.
        """
        self._short_term.add(role, content)
        self._long_term.save_turn(role, content, session_id=self.session_id)

    def add_user_turn(self, text: str) -> None:
        """Add a user message turn."""
        self.add_turn("user", text)

    def add_assistant_turn(self, text: str) -> None:
        """Add an assistant message turn."""
        self.add_turn("assistant", text)

    # ── Memory Access ─────────────────────────────────────────────────────────

    def get_short_term_messages(self) -> list[dict[str, str]]:
        """
        Return current session turns in Groq-compatible message format.

        Returns
        -------
        list[dict]
            List of ``{"role": ..., "content": ...}`` dicts.
        """
        return self._short_term.to_messages()

    def get_facts_summary(self) -> str:
        """Return formatted long-term facts for LLM injection."""
        return self._long_term.get_summary()

    def get_history_text(self, n: int = 5) -> str:
        """Return recent past conversation as text (from long-term store)."""
        return self._long_term.get_history_text(n)

    def remember_fact(self, key: str, value: str) -> None:
        """Store a fact about this person in long-term memory."""
        self._long_term.remember(key, value)

    def recall_fact(self, key: str) -> Optional[str]:
        """Recall a specific fact about this person."""
        return self._long_term.recall(key)

    def get_all_facts(self) -> dict[str, str]:
        """Return all known facts about this person."""
        return self._long_term.get_all_facts()

    # ── Session Info ──────────────────────────────────────────────────────────

    @property
    def turn_count(self) -> int:
        """Number of turns in the current session buffer."""
        return len(self._short_term)

    def __repr__(self) -> str:
        return (
            f"ConversationSession("
            f"person={self.person_name!r}, "
            f"session={self.session_id}, "
            f"turns={self.turn_count})"
        )


class ConversationManager:
    """
    Factory and registry for conversation sessions.

    One session is created per recognized person. Sessions survive
    as long as the robot is running; the underlying data persists
    in the database across restarts.

    Parameters
    ----------
    db:
        Shared Database instance.
    """

    def __init__(self, db: Optional[Database] = None) -> None:
        self._db = db or Database()
        self._sessions: dict[str, ConversationSession] = {}

    def get_session(
        self,
        person_id: str,
        person_name: str,
    ) -> ConversationSession:
        """
        Return an existing session or create a new one.

        Parameters
        ----------
        person_id:
            Database ID of the person.
        person_name:
            Display name of the person.

        Returns
        -------
        ConversationSession
            The active session for this person.
        """
        if person_id not in self._sessions:
            self._sessions[person_id] = ConversationSession(
                person_id=person_id,
                person_name=person_name,
                db=self._db,
            )
        return self._sessions[person_id]

    def end_session(self, person_id: str) -> None:
        """
        End and discard the session for a person.

        Data has already been persisted turn-by-turn, so nothing is lost.

        Parameters
        ----------
        person_id:
            Person whose session to close.
        """
        if person_id in self._sessions:
            session = self._sessions.pop(person_id)
            log.info(f"Ended session for {session.person_name} "
                     f"({session.turn_count} turns recorded)")

    def active_sessions(self) -> list[str]:
        """Return the list of person IDs with active sessions."""
        return list(self._sessions.keys())

    def end_all(self) -> None:
        """End all active sessions."""
        for pid in list(self._sessions.keys()):
            self.end_session(pid)
