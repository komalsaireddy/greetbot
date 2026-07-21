"""
GreetBot Memory Database
========================
SQLite-backed persistent storage for persons, conversations, and facts.
This is the single source of truth for all long-term data.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config import DATABASE_PATH
from utils.logger import get_logger

log = get_logger(__name__)


class Database:
    """
    SQLite wrapper for GreetBot persistent storage.

    Tables
    ------
    persons
        One row per known person (name, metadata, visit count).
    facts
        Key-value facts about a person (e.g. "college = JNTU").
    conversations
        Individual conversation turns (role + content per person).
    preferences
        User preferences key-value store.
    global_memory
        Global robot memory (not person-specific).
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else DATABASE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._migrate()
        log.info(f"Database ready at {self.path}")

    # ── Connection ────────────────────────────────────────────────────────────

    def _connect(self) -> None:
        self._conn = sqlite3.connect(
            str(self.path),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._connect()
        return self._conn  # type: ignore[return-value]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Schema Migration ──────────────────────────────────────────────────────

    def _migrate(self) -> None:
        """Create tables if they don't exist (idempotent)."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS persons (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                age         TEXT,
                profession  TEXT,
                city        TEXT,
                first_seen  TEXT NOT NULL,
                last_seen   TEXT NOT NULL,
                visit_count INTEGER DEFAULT 1,
                extra       TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id   TEXT NOT NULL,
                key         TEXT NOT NULL,
                value       TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE,
                UNIQUE(person_id, key)
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id   TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                session_id  TEXT,
                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS global_memory (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_facts_person
                ON facts(person_id);
            CREATE INDEX IF NOT EXISTS idx_conv_person
                ON conversations(person_id, timestamp DESC);
        """)
        self.conn.commit()

    # ── Persons ───────────────────────────────────────────────────────────────

    def get_person(self, person_id: str) -> Optional[dict]:
        """Fetch a person by their ID."""
        row = self.conn.execute(
            "SELECT * FROM persons WHERE id = ?", (person_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_person_by_name(self, name: str) -> Optional[dict]:
        """Fetch a person by name (case-insensitive)."""
        row = self.conn.execute(
            "SELECT * FROM persons WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        return dict(row) if row else None

    def list_persons(self) -> list[dict]:
        """Return all known persons."""
        rows = self.conn.execute(
            "SELECT * FROM persons ORDER BY last_seen DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_person(
        self,
        person_id: str,
        name: str,
        age: str = "",
        profession: str = "",
        city: str = "",
        extra: Optional[dict] = None,
    ) -> None:
        """Insert or update a person record."""
        now = datetime.now().isoformat()
        extra_json = json.dumps(extra or {})
        self.conn.execute(
            """
            INSERT INTO persons (id, name, age, profession, city, first_seen, last_seen, extra)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name        = excluded.name,
                last_seen   = excluded.last_seen,
                extra       = excluded.extra
            """,
            (person_id, name, age, profession, city, now, now, extra_json),
        )
        self.conn.commit()

    def touch_person(self, person_id: str) -> None:
        """Update last_seen and increment visit_count."""
        now = datetime.now().isoformat()
        self.conn.execute(
            """
            UPDATE persons
            SET last_seen = ?, visit_count = visit_count + 1
            WHERE id = ?
            """,
            (now, person_id),
        )
        self.conn.commit()

    def delete_person(self, person_id: str) -> None:
        """Delete a person and all their data (cascades)."""
        self.conn.execute("DELETE FROM persons WHERE id = ?", (person_id,))
        self.conn.commit()

    # ── Facts ─────────────────────────────────────────────────────────────────

    def set_fact(self, person_id: str, key: str, value: Any) -> None:
        """Store or update a fact about a person."""
        now = datetime.now().isoformat()
        value_str = str(value)
        self.conn.execute(
            """
            INSERT INTO facts (person_id, key, value, updated_at)
                VALUES (?, ?, ?, ?)
            ON CONFLICT(person_id, key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (person_id, key, value_str, now),
        )
        self.conn.commit()

    def get_facts(self, person_id: str) -> dict[str, str]:
        """Return all facts for a person as a dict."""
        rows = self.conn.execute(
            "SELECT key, value FROM facts WHERE person_id = ?", (person_id,)
        ).fetchall()
        return {r["key"]: r["value"] for r in rows}

    def delete_fact(self, person_id: str, key: str) -> None:
        self.conn.execute(
            "DELETE FROM facts WHERE person_id = ? AND key = ?", (person_id, key)
        )
        self.conn.commit()

    # ── Conversations ─────────────────────────────────────────────────────────

    def add_conversation_turn(
        self,
        person_id: str,
        role: str,
        content: str,
        session_id: Optional[str] = None,
    ) -> None:
        """Append a conversation turn."""
        now = datetime.now().isoformat()
        self.conn.execute(
            """
            INSERT INTO conversations (person_id, role, content, timestamp, session_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (person_id, role, content, now, session_id),
        )
        self.conn.commit()

    def get_conversation_history(
        self,
        person_id: str,
        limit: int = 20,
        session_id: Optional[str] = None,
    ) -> list[dict]:
        """Return recent conversation turns (newest last)."""
        if session_id:
            rows = self.conn.execute(
                """
                SELECT role, content, timestamp FROM conversations
                WHERE person_id = ? AND session_id = ?
                ORDER BY timestamp DESC LIMIT ?
                """,
                (person_id, session_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT role, content, timestamp FROM conversations
                WHERE person_id = ?
                ORDER BY timestamp DESC LIMIT ?
                """,
                (person_id, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def get_last_n_turns(self, person_id: str, n: int = 5) -> list[dict]:
        """Return the last n turns across all sessions."""
        return self.get_conversation_history(person_id, limit=n)

    def clear_conversation(self, person_id: str, session_id: Optional[str] = None) -> None:
        if session_id:
            self.conn.execute(
                "DELETE FROM conversations WHERE person_id = ? AND session_id = ?",
                (person_id, session_id),
            )
        else:
            self.conn.execute(
                "DELETE FROM conversations WHERE person_id = ?", (person_id,)
            )
        self.conn.commit()

    # ── Global Memory ─────────────────────────────────────────────────────────

    def set_global(self, key: str, value: Any) -> None:
        """Store a global key-value pair."""
        now = datetime.now().isoformat()
        self.conn.execute(
            """
            INSERT INTO global_memory (key, value, updated_at)
                VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, str(value), now),
        )
        self.conn.commit()

    def get_global(self, key: str, default: Any = None) -> Optional[str]:
        """Retrieve a global value."""
        row = self.conn.execute(
            "SELECT value FROM global_memory WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def all_global(self) -> dict[str, str]:
        """Return all global memory entries."""
        rows = self.conn.execute("SELECT key, value FROM global_memory").fetchall()
        return {r["key"]: r["value"] for r in rows}
