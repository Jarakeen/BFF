from __future__ import annotations

"""SQLite schema for FoundryDock's ESO encounter knowledge layer."""

from pathlib import Path
import sqlite3

SCHEMA_VERSION = 3

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

-- Schema v3: reviewed canonical facts are kept separate from their supporting
-- evidence so one fact can retain multiple independent sources losslessly.
CREATE TABLE IF NOT EXISTS encounter_canonical_fact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id TEXT NOT NULL,
    canonical_kind TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    fact_key TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'reviewed',
    valid_from_update TEXT DEFAULT '',
    valid_to_update TEXT DEFAULT '',
    valid_from_patch TEXT DEFAULT '',
    valid_to_patch TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (encounter_id) REFERENCES encounter(id) ON DELETE CASCADE,
    UNIQUE(encounter_id, fact_type, fact_key, valid_from_update, valid_from_patch)
);

CREATE INDEX IF NOT EXISTS idx_encounter_canonical_fact_encounter
    ON encounter_canonical_fact(encounter_id);
CREATE INDEX IF NOT EXISTS idx_encounter_canonical_fact_kind
    ON encounter_canonical_fact(canonical_kind);

CREATE TABLE IF NOT EXISTS encounter_fact_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_fact_id INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_locator TEXT DEFAULT '',
    source_revision TEXT DEFAULT '',
    game_update TEXT DEFAULT '',
    patch_version TEXT DEFAULT '',
    confidence TEXT NOT NULL DEFAULT 'medium',
    source_value_json TEXT NOT NULL,
    notes TEXT DEFAULT '',
    retrieved_at TEXT DEFAULT '',
    FOREIGN KEY (canonical_fact_id) REFERENCES encounter_canonical_fact(id) ON DELETE CASCADE,
    UNIQUE(
        canonical_fact_id,
        source_type,
        source_name,
        source_locator,
        source_revision,
        game_update,
        patch_version
    )
);

CREATE INDEX IF NOT EXISTS idx_encounter_fact_evidence_fact
    ON encounter_fact_evidence(canonical_fact_id);
CREATE INDEX IF NOT EXISTS idx_encounter_fact_evidence_source
    ON encounter_fact_evidence(source_type, source_name);

CREATE TABLE IF NOT EXISTS encounter_schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def ensure_encounter_schema(connection: sqlite3.Connection) -> None:
    """Create or extend the encounter layer without deleting or replacing data."""
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

    parser = argparse.ArgumentParser(description="Create or extend the FoundryDock encounter schema")
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    ensure_encounter_schema_file(args.database)
    print(f"Encounter schema ready: {args.database} (v{SCHEMA_VERSION})")
