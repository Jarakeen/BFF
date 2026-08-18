# services/eso_db/schema.py
"""
Schema for eso.db - a relational reshaping of the JSON records under
data/uesp/.

The schema is versioned so existing databases can be upgraded safely
without destroying imported data.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = 2


DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS content (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    content_type   TEXT NOT NULL CHECK (content_type IN ('trial', 'dungeon', 'arena')),
    summary        TEXT DEFAULT '',
    location       TEXT DEFAULT '',
    group_size     INTEGER,
    source_url     TEXT DEFAULT '',
    source_title   TEXT DEFAULT '',
    revision_id    INTEGER,
    retrieved_at   TEXT DEFAULT '',
    license        TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS content_bosses (
    content_id  TEXT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    boss_id     TEXT NOT NULL,
    position    INTEGER NOT NULL,
    PRIMARY KEY (content_id, boss_id)
);

CREATE TABLE IF NOT EXISTS content_sets (
    content_id TEXT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    set_id     TEXT NOT NULL,
    position   INTEGER NOT NULL,
    PRIMARY KEY (content_id, set_id)
);

CREATE TABLE IF NOT EXISTS content_notes (
    content_id  TEXT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    note        TEXT NOT NULL,
    PRIMARY KEY (content_id, position)
);

CREATE TABLE IF NOT EXISTS content_related_npcs (
    content_id  TEXT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    npc_name    TEXT NOT NULL,
    PRIMARY KEY (content_id, position)
);

CREATE TABLE IF NOT EXISTS content_achievements (
    content_id     TEXT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    achievement_id TEXT NOT NULL,
    position       INTEGER NOT NULL,
    name           TEXT NOT NULL,
    description    TEXT DEFAULT '',
    points         INTEGER,
    PRIMARY KEY (content_id, achievement_id)
);

CREATE TABLE IF NOT EXISTS bosses (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    content_id     TEXT REFERENCES content(id) ON DELETE SET NULL,
    content_name   TEXT DEFAULT '',
    location       TEXT DEFAULT '',
    species        TEXT DEFAULT '',
    reaction       TEXT DEFAULT '',
    health_normal  TEXT DEFAULT '',
    health_veteran TEXT DEFAULT '',
    health_hardmode TEXT DEFAULT '',
    summary        TEXT DEFAULT '',
    source_url     TEXT DEFAULT '',
    source_title   TEXT DEFAULT '',
    revision_id    INTEGER,
    retrieved_at   TEXT DEFAULT '',
    license        TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS boss_abilities (
    boss_id     TEXT NOT NULL REFERENCES bosses(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    PRIMARY KEY (boss_id, position)
);

CREATE TABLE IF NOT EXISTS boss_phases (
    boss_id     TEXT NOT NULL REFERENCES bosses(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    label       TEXT NOT NULL,
    threshold   TEXT DEFAULT '',
    description TEXT DEFAULT '',
    PRIMARY KEY (boss_id, position)
);

CREATE TABLE IF NOT EXISTS boss_dialogue (
    boss_id     TEXT NOT NULL REFERENCES bosses(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    speaker     TEXT NOT NULL,
    line        TEXT NOT NULL,
    trigger_context TEXT DEFAULT '',
    PRIMARY KEY (boss_id, position)
);

CREATE TABLE IF NOT EXISTS boss_notes (
    boss_id     TEXT NOT NULL REFERENCES bosses(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    note        TEXT NOT NULL,
    PRIMARY KEY (boss_id, position)
);

CREATE TABLE IF NOT EXISTS boss_related_npcs (
    boss_id     TEXT NOT NULL REFERENCES bosses(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    npc_name    TEXT NOT NULL,
    PRIMARY KEY (boss_id, position)
);

CREATE TABLE IF NOT EXISTS boss_related_quests (
    boss_id     TEXT NOT NULL REFERENCES bosses(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    quest       TEXT NOT NULL,
    PRIMARY KEY (boss_id, position)
);

CREATE TABLE IF NOT EXISTS boss_achievements (
    boss_id        TEXT NOT NULL REFERENCES bosses(id) ON DELETE CASCADE,
    achievement_id TEXT NOT NULL,
    position       INTEGER NOT NULL,
    name           TEXT NOT NULL,
    description    TEXT DEFAULT '',
    points         INTEGER,
    PRIMARY KEY (boss_id, achievement_id)
);

CREATE TABLE IF NOT EXISTS boss_difficulty_notes (
    boss_id     TEXT NOT NULL REFERENCES bosses(id) ON DELETE CASCADE,
    category    TEXT NOT NULL CHECK (category IN ('normal_veteran', 'hardmode')),
    position    INTEGER NOT NULL,
    note        TEXT NOT NULL,
    PRIMARY KEY (boss_id, category, position)
);

CREATE INDEX IF NOT EXISTS idx_bosses_content_id ON bosses(content_id);
"""


def _get_schema_version(connection: sqlite3.Connection) -> int:
    """Return the current database schema version.

    Databases created before schema_version existed are treated as
    version 1 because that was the previous schema.
    """
    table_exists = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'schema_version'
        """
    ).fetchone()

    if not table_exists:
        return 1

    row = connection.execute(
        "SELECT version FROM schema_version LIMIT 1"
    ).fetchone()

    return int(row[0]) if row else 1


def _set_schema_version(
    connection: sqlite3.Connection,
    version: int,
) -> None:
    connection.execute("DELETE FROM schema_version")
    connection.execute(
        "INSERT INTO schema_version (version) VALUES (?)",
        (version,),
    )


def _column_exists(
    connection: sqlite3.Connection,
    table: str,
    column: str,
) -> bool:
    columns = connection.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(row[1] == column for row in columns)


def _migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
    """Upgrade the original schema to version 2.

    Version 2 adds:
      - content.group_size
      - content_sets
    """
    if not _column_exists(connection, "content", "group_size"):
        connection.execute(
            "ALTER TABLE content ADD COLUMN group_size INTEGER"
        )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS content_sets (
            content_id TEXT NOT NULL
                REFERENCES content(id) ON DELETE CASCADE,
            set_id     TEXT NOT NULL,
            position   INTEGER NOT NULL,
            PRIMARY KEY (content_id, set_id)
        )
        """
    )


def _migrate(connection: sqlite3.Connection) -> None:
    """Apply all migrations required to reach SCHEMA_VERSION."""
    current_version = _get_schema_version(connection)

    if current_version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {current_version} is newer than "
            f"supported version {SCHEMA_VERSION}."
        )

    if current_version < 1:
        raise RuntimeError(
            f"Unsupported database schema version: {current_version}"
        )

    if current_version == 1:
        _migrate_v1_to_v2(connection)
        _set_schema_version(connection, 2)
        current_version = 2

    if current_version != SCHEMA_VERSION:
        raise RuntimeError(
            f"Database migration stopped at version {current_version}; "
            f"expected {SCHEMA_VERSION}."
        )


def connect(db_path: Path) -> sqlite3.Connection:
    """Open the database and ensure its schema is current."""

    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON;")

    try:
        connection.executescript(DDL)
        _migrate(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        raise

    return connection