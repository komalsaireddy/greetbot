"""
GreetBot Memory
===============
Simple global key-value memory store backed by SQLite.
Use for robot-wide state that isn't tied to a specific person.
"""

from typing import Any, Optional

from memory.database import Database
from utils.logger import get_logger

log = get_logger(__name__)


class Memory:
    """
    Global robot memory — key-value store persisted in SQLite.

    This replaces the old JSON-based memory.  All values are stored
    as strings internally; retrieve and cast as needed.

    Parameters
    ----------
    db:
        Shared Database instance. If None, a new one is created.
    """

    def __init__(self, db: Optional[Database] = None) -> None:
        self._db = db or Database()

    def remember(self, key: str, value: Any) -> None:
        """
        Store a value in global memory.

        Parameters
        ----------
        key:
            Memory key.
        value:
            Value to store (converted to string).
        """
        self._db.set_global(key, value)
        log.debug(f"Global memory set: {key} = {value}")

    def recall(self, key: str, default: Any = None) -> Optional[str]:
        """
        Retrieve a value from global memory.

        Parameters
        ----------
        key:
            Memory key to look up.
        default:
            Returned if key is not found.

        Returns
        -------
        str or None
            Stored value, or *default*.
        """
        return self._db.get_global(key, default)

    def forget(self, key: str) -> None:
        """Remove a key from global memory."""
        self._db.conn.execute(
            "DELETE FROM global_memory WHERE key = ?", (key,)
        )
        self._db.conn.commit()

    def all(self) -> dict[str, str]:
        """Return all global memory entries as a dict."""
        return self._db.all_global()

    def __repr__(self) -> str:
        entries = self._db.all_global()
        return f"Memory(entries={len(entries)})"
