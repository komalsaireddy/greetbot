"""
GreetBot Context Manager
=========================
Maintains the current session state: who is present, the active speaker,
environment details, and any transient flags needed across modules.
"""

from datetime import datetime
from typing import Optional

from utils.helpers import current_time_greeting
from utils.logger import get_logger

log = get_logger(__name__)


class ContextManager:
    """
    Session-level context state shared between vision, brain, and speech.

    This is the single source of truth for "what is happening right now":
    who the robot sees, who it's talking to, how long the session has been
    running, etc.

    This object is passed around (or injected) rather than using globals.
    """

    def __init__(self) -> None:
        self._active_person: Optional[str] = None
        self._active_person_id: Optional[str] = None
        self._person_count: int = 0
        self._known_count: int = 0
        self._unknown_count: int = 0
        self._session_start: datetime = datetime.now()
        self._conversation_count: int = 0
        self._is_speaking: bool = False
        self._is_listening: bool = False
        self._last_interaction: Optional[datetime] = None

    # ── Active Person ─────────────────────────────────────────────────────────

    def set_person(self, name: Optional[str], person_id: Optional[str] = None) -> None:
        """
        Set the currently active conversation partner.

        Parameters
        ----------
        name:
            Display name of the person, or None if unknown.
        person_id:
            Database ID of the person.
        """
        if name != self._active_person:
            log.info(f"Active person: {name or 'Unknown'}")
            self._active_person = name
            self._active_person_id = person_id

    def clear_person(self) -> None:
        """Clear the active person (no one is being spoken to)."""
        self._active_person = None
        self._active_person_id = None

    @property
    def active_person(self) -> Optional[str]:
        """Name of the current conversation partner."""
        return self._active_person

    @property
    def active_person_id(self) -> Optional[str]:
        """Database ID of the current conversation partner."""
        return self._active_person_id

    # ── Scene State ───────────────────────────────────────────────────────────

    def update_scene(
        self,
        person_count: int,
        known_count: int,
        unknown_count: int,
    ) -> None:
        """
        Update person counts from the vision system.

        Parameters
        ----------
        person_count:
            Total visible faces.
        known_count:
            Recognized known persons.
        unknown_count:
            Unrecognized persons.
        """
        self._person_count = person_count
        self._known_count = known_count
        self._unknown_count = unknown_count

    @property
    def person_count(self) -> int:
        """Total number of visible persons."""
        return self._person_count

    @property
    def known_count(self) -> int:
        """Number of recognized known persons visible."""
        return self._known_count

    @property
    def unknown_count(self) -> int:
        """Number of unrecognized persons visible."""
        return self._unknown_count

    @property
    def someone_present(self) -> bool:
        """True if at least one person is visible."""
        return self._person_count > 0

    # ── Robot State ───────────────────────────────────────────────────────────

    def set_speaking(self, value: bool) -> None:
        """Mark whether the robot is currently speaking."""
        self._is_speaking = value

    def set_listening(self, value: bool) -> None:
        """Mark whether the robot is actively listening."""
        self._is_listening = value

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    def record_interaction(self) -> None:
        """Record that an interaction just occurred."""
        self._last_interaction = datetime.now()
        self._conversation_count += 1

    @property
    def conversation_count(self) -> int:
        """Total number of conversation turns this session."""
        return self._conversation_count

    @property
    def session_uptime(self) -> float:
        """Session uptime in seconds."""
        return (datetime.now() - self._session_start).total_seconds()

    # ── Context String ────────────────────────────────────────────────────────

    def get_context_string(self) -> str:
        """
        Return a human-readable summary of the current context.

        Useful for debugging and for injecting into prompts as needed.

        Returns
        -------
        str
            Formatted context summary.
        """
        lines = [
            f"Greeting:        {current_time_greeting()}",
            f"Active person:   {self._active_person or 'None'}",
            f"Visible persons: {self._person_count} "
            f"({self._known_count} known, {self._unknown_count} unknown)",
            f"Session uptime:  {self.session_uptime:.0f}s",
            f"Interactions:    {self._conversation_count}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"ContextManager("
            f"person={self._active_person!r}, "
            f"visible={self._person_count}, "
            f"uptime={self.session_uptime:.0f}s)"
        )
