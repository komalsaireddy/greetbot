"""
GreetBot Profile Manager
========================
Manages per-person profiles backed by the SQLite database.
Provides a high-level API for creating, loading, and updating person profiles.
"""

from datetime import datetime
from typing import Optional

from memory.database import Database
from utils.logger import get_logger
from utils.helpers import normalize_name, generate_id

log = get_logger(__name__)


class ProfileManager:
    """
    High-level API for managing person profiles in the database.

    Parameters
    ----------
    db:
        Shared Database instance. If None, a new one is created.
    """

    def __init__(self, db: Optional[Database] = None) -> None:
        self._db = db or Database()

    # ── Core Operations ───────────────────────────────────────────────────────

    def exists(self, person_id: str) -> bool:
        """Check if a person exists in the database."""
        return self._db.get_person(person_id) is not None

    def exists_by_name(self, name: str) -> bool:
        """Check if a person with the given name exists."""
        return self._db.get_person_by_name(name) is not None

    def get_or_create(self, name: str) -> dict:
        """
        Return an existing person by name or create a new one.

        This is the primary way to obtain a profile. Person IDs are derived
        from the normalized name so that "Komal" and "komal" map to the same
        profile.

        Parameters
        ----------
        name:
            The person's display name.

        Returns
        -------
        dict
            The person's profile record.
        """
        clean = normalize_name(name)
        person_id = clean.lower().replace(" ", "_")

        existing = self._db.get_person(person_id)
        if existing:
            log.debug(f"Profile found: {person_id}")
            return existing

        # Create new profile
        self._db.upsert_person(person_id=person_id, name=clean)
        log.info(f"Created new profile: {clean} ({person_id})")
        return self._db.get_person(person_id)  # type: ignore[return-value]

    def load(self, person_id: str) -> Optional[dict]:
        """Load a profile by ID."""
        return self._db.get_person(person_id)

    def load_by_name(self, name: str) -> Optional[dict]:
        """Load a profile by name (case-insensitive)."""
        return self._db.get_person_by_name(name)

    def create(self, person_id: str, name: Optional[str] = None) -> dict:
        """
        Explicitly create a profile with a given ID.

        Used for legacy ``person_001`` style IDs from the face database.

        Parameters
        ----------
        person_id:
            Raw ID string (e.g. ``"person_001"``).
        name:
            Display name (defaults to person_id).

        Returns
        -------
        dict
            Newly created profile.
        """
        display_name = normalize_name(name) if name else person_id
        self._db.upsert_person(person_id=person_id, name=display_name)
        log.info(f"Created profile: {display_name} ({person_id})")
        return self._db.get_person(person_id)  # type: ignore[return-value]

    # ── Updates ───────────────────────────────────────────────────────────────

    def update_last_seen(self, person_id: str) -> None:
        """Touch the last_seen timestamp (also increments visit_count)."""
        self._db.touch_person(person_id)

    def increment_visit(self, person_id: str) -> None:
        """Alias for update_last_seen (increments visit count)."""
        self._db.touch_person(person_id)

    def update_field(self, person_id: str, key: str, value: str) -> None:
        """
        Update a fact or profile field for a person.

        Simple fields (name, age, profession, city) are stored in the
        persons table. Everything else goes to the facts table.

        Parameters
        ----------
        person_id:
            Target person.
        key:
            Field name.
        value:
            New value.
        """
        simple_fields = {"name", "age", "profession", "city"}
        if key in simple_fields:
            self._db.conn.execute(
                f"UPDATE persons SET {key} = ? WHERE id = ?",
                (value, person_id),
            )
            self._db.conn.commit()
        else:
            self._db.set_fact(person_id, key, value)
        log.debug(f"[{person_id}] Updated {key} = {value}")

    def save_fact(self, person_id: str, key: str, value: str) -> None:
        """Store an arbitrary fact about a person."""
        self._db.set_fact(person_id, key, value)

    def get_facts(self, person_id: str) -> dict[str, str]:
        """Return all stored facts for a person."""
        return self._db.get_facts(person_id)

    # ── Listing ───────────────────────────────────────────────────────────────

    def list_all(self) -> list[dict]:
        """Return all known persons."""
        return self._db.list_persons()

    def count(self) -> int:
        """Return the total number of known persons."""
        return len(self._db.list_persons())

    # ── Deletion ──────────────────────────────────────────────────────────────

    def delete(self, person_id: str) -> None:
        """Delete a person and all their data."""
        self._db.delete_person(person_id)
        log.info(f"Deleted profile: {person_id}")

    def rename(self, person_id: str, new_name: str) -> None:
        """
        Rename a person (updates display name only, ID stays the same).

        Parameters
        ----------
        person_id:
            Person to rename.
        new_name:
            New display name.
        """
        clean = normalize_name(new_name)
        self._db.conn.execute(
            "UPDATE persons SET name = ? WHERE id = ?",
            (clean, person_id),
        )
        self._db.conn.commit()
        log.info(f"Renamed {person_id} → {clean}")
