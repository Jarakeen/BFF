# services/eso_db/schema.py
"""
Schema for eso.db - a relational reshaping of the JSON records under
data/uesp/. One table per top-level record type (content, bosses),
plus child tables for their list-valued fields, keyed by the parent's
stable id.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = 1


DDL = """
CREATE TABLE IF NOT EXISTS content (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    content_type   TEXT NOT NULL CHECK (content_type IN ('trial', 'dungeon', 'arena')),
    summary        TEXT DEFAULT '',
    location       TEXT DEFAULT '',
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


def connect(db_path: Path) -> sqlite3.Connection:
    """Open (creating if needed) the database and ensure its schema
    is up to date."""

    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.executescript(DDL)
    connection.commit()

    return connection
