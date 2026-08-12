from __future__ import annotations

"""SQLite schema for FoundryDock's ESO encounter knowledge layer."""

from pathlib import Path
import sqlite3

SCHEMA_VERSION = 2

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS content (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL,
    summary TEXT DEFAULT '',
    location TEXT DEFAULT '',
    source_url TEXT,
    source_page_title TEXT,
    source_revision_id TEXT,
    retrieved_at TEXT,
    source_license TEXT
);

CREATE TABLE IF NOT EXISTS encounter (
    id TEXT PRIMARY KEY,
    content_id TEXT NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    summary TEXT DEFAULT '',
    location TEXT DEFAULT '',
    species TEXT DEFAULT '',
    reaction TEXT DEFAULT '',
    source_url TEXT,
    source_page_title TEXT,
    source_revision_id TEXT,
    retrieved_at TEXT,
    source_license TEXT,
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
    UNIQUE(content_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_encounter_content ON encounter(content_id);

CREATE TABLE IF NOT EXISTS encounter_health (
    encounter_id TEXT PRIMARY KEY,
    normal TEXT,
    veteran TEXT,
    hardmode TEXT,
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS encounter_ability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    source_section TEXT DEFAULT '',
    source_url TEXT,
    source_revision_id TEXT,
    existing_ability_id INTEGER,
    interruptible INTEGER,
    interrupt_note TEXT DEFAULT '',
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE,
    FOREIGN KEY (existing_ability_id) REFERENCES ability(id) ON DELETE SET NULL,
    UNIQUE(encounter_id, name)
);

CREATE INDEX IF NOT EXISTS idx_encounter_ability_encounter ON encounter_ability(encounter_id);

CREATE TABLE IF NOT EXISTS encounter_mechanic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    mechanic_type TEXT,
    damage_type TEXT,
    target_count INTEGER,
    requires_movement INTEGER,
    requires_positioning INTEGER,
    requires_cleanse INTEGER,
    persistent_hazard INTEGER,
    failure_is_fatal INTEGER,
    interruptible INTEGER,
    interrupt_note TEXT DEFAULT '',
    interpretation_status TEXT NOT NULL DEFAULT 'unclassified',
    source_section TEXT DEFAULT '',
    source_url TEXT,
    source_revision_id TEXT,
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE,
    UNIQUE(encounter_id, name)
);

CREATE INDEX IF NOT EXISTS idx_encounter_mechanic_encounter ON encounter_mechanic(encounter_id);

CREATE TABLE IF NOT EXISTS encounter_phase (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id TEXT NOT NULL,
    label TEXT DEFAULT '',
    threshold TEXT DEFAULT '',
    description TEXT DEFAULT '',
    source_section TEXT DEFAULT '',
    source_url TEXT,
    source_revision_id TEXT,
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_encounter_phase_encounter ON encounter_phase(encounter_id);

CREATE TABLE IF NOT EXISTS encounter_dialogue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id TEXT NOT NULL,
    trigger TEXT NOT NULL,
    speaker TEXT DEFAULT '',
    line TEXT NOT NULL,
    matched_ability_id INTEGER,
    source_section TEXT DEFAULT '',
    source_url TEXT,
    source_revision_id TEXT,
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE,
    FOREIGN KEY (matched_ability_id) REFERENCES encounter_ability(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_encounter_dialogue_encounter_trigger ON encounter_dialogue(encounter_id, trigger);

CREATE TABLE IF NOT EXISTS encounter_strategy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id TEXT NOT NULL,
    mechanic_id INTEGER,
    strategy TEXT NOT NULL,
    recommended_role TEXT,
    priority TEXT,
    rationale TEXT DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'manual',
    source_url TEXT,
    source_revision_id TEXT,
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE,
    FOREIGN KEY (mechanic_id) REFERENCES encounter_mechanic(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_encounter_strategy_encounter ON encounter_strategy(encounter_id);

CREATE TABLE IF NOT EXISTS content_achievement (
    content_id TEXT NOT NULL,
    achievement_id INTEGER NOT NULL,
    source_url TEXT,
    source_revision_id TEXT,
    PRIMARY KEY (content_id, achievement_id),
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievement(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS encounter_achievement (
    encounter_id TEXT NOT NULL,
    achievement_id INTEGER NOT NULL,
    source_url TEXT,
    source_revision_id TEXT,
    PRIMARY KEY (encounter_id, achievement_id),
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievement(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS content_npc (
    content_id TEXT NOT NULL,
    npc_entity_id TEXT NOT NULL,
    source_url TEXT,
    source_revision_id TEXT,
    PRIMARY KEY (content_id, npc_entity_id),
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS encounter_npc (
    encounter_id TEXT NOT NULL,
    npc_entity_id TEXT NOT NULL,
    source_url TEXT,
    source_revision_id TEXT,
    PRIMARY KEY (encounter_id, npc_entity_id),
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS content_quest (
    content_id TEXT NOT NULL,
    quest_id TEXT NOT NULL,
    source_url TEXT,
    source_revision_id TEXT,
    PRIMARY KEY (content_id, quest_id),
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS encounter_quest (
    encounter_id TEXT NOT NULL,
    quest_id TEXT NOT NULL,
    source_url TEXT,
    source_revision_id TEXT,
    PRIMARY KEY (encounter_id, quest_id),
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS encounter_section (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id TEXT NOT NULL,
    section_name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    source_url TEXT,
    source_revision_id TEXT,
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE,
    UNIQUE(encounter_id, section_name)
);

CREATE TABLE IF NOT EXISTS content_section (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id TEXT NOT NULL,
    section_name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    source_url TEXT,
    source_revision_id TEXT,
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
    UNIQUE(content_id, section_name)
);

CREATE TABLE IF NOT EXISTS encounter_schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def ensure_encounter_schema(connection: sqlite3.Connection) -> None:
    """Create the encounter layer without deleting or replacing existing data."""
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA_SQL)
    connection.execute(
        "INSERT OR REPLACE INTO encounter_schema_meta(key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    connection.commit()


def ensure_encounter_schema_file(database: Path) -> None:
    connection = sqlite3.connect(Path(database))
    try:
        ensure_encounter_schema(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create the FoundryDock encounter schema")
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    ensure_encounter_schema_file(args.database)
    print(f"Encounter schema ready: {args.database}")
