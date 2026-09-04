from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.encounter_schema import ensure_encounter_schema
from ui.mechanics_boss_map_support import PAIR_ID
from ui.mechanics_search_support import searchable_encounter_ids


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE ability(id INTEGER PRIMARY KEY)")
        ensure_encounter_schema(connection)
        connection.execute(
            """
            INSERT INTO content(id, name, slug, content_type)
            VALUES ('rockgrove', 'Rockgrove', 'rockgrove', 'trial')
            """
        )
        connection.execute(
            """
            INSERT INTO encounter(id, content_id, name, slug, summary, location)
            VALUES ('oaxiltso', 'rockgrove', 'Oaxiltso', 'oaxiltso',
                    'A Havocrel boss.', 'Rockgrove')
            """
        )
        connection.execute(
            """
            INSERT INTO encounter_ability(
                encounter_id, name, description, interrupt_note, source_section
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "oaxiltso",
                "Noxious Sludge",
                "Targets players with sludge that must be handled correctly.",
                "",
                "Skills and Abilities",
            ),
        )
        connection.execute(
            """
            INSERT INTO encounter_canonical_fact(
                encounter_id, canonical_kind, fact_type, fact_key,
                payload_json, review_status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "oaxiltso",
                "mechanic_detail",
                "mechanic_detail",
                "summon_havocrel_annihilators",
                json.dumps({
                    "name": "Summon Havocrel Annihilators",
                    "description": "Oaxiltso summons Havocrel Annihilators.",
                    "requires_positioning": True,
                }),
                "reviewed_single_source",
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return path


def test_search_finds_boss_by_name(tmp_path: Path) -> None:
    database = _database(tmp_path)
    assert searchable_encounter_ids(database, "oax") == {"oaxiltso"}


def test_search_finds_boss_by_ability_text(tmp_path: Path) -> None:
    database = _database(tmp_path)
    assert searchable_encounter_ids(database, "sludge") == {"oaxiltso"}


def test_search_finds_reviewed_canonical_mechanic_payload(tmp_path: Path) -> None:
    database = _database(tmp_path)
    assert searchable_encounter_ids(database, "annihilators") == {"oaxiltso"}


def test_search_maps_dreadsail_pair_member_hit_to_combined_selector(tmp_path: Path) -> None:
    database = _database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "INSERT INTO content(id, name, slug, content_type) VALUES (?, ?, ?, ?)",
            ("dreadsail_reef", "Dreadsail Reef", "dreadsail-reef", "trial"),
        )
        connection.execute(
            "INSERT INTO encounter(id, content_id, name, slug) VALUES (?, ?, ?, ?)",
            ("lylanar", "dreadsail_reef", "Lylanar", "lylanar"),
        )
        connection.execute(
            """
            INSERT INTO encounter_ability(encounter_id, name, description)
            VALUES (?, ?, ?)
            """,
            ("lylanar", "Fire Brand", "Applies the fire brand mechanic."),
        )
        connection.commit()
    finally:
        connection.close()

    matches = searchable_encounter_ids(database, "fire brand")
    assert "lylanar" in matches
    assert PAIR_ID in matches
