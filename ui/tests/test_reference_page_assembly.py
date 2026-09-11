import json
import sqlite3
from pathlib import Path

from ui.reference_data_model import ReferenceEntry
from ui.reference_page_assembly import finalize_reference_entries


def _seed_database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_bonus (
                id INTEGER PRIMARY KEY,
                set_id INTEGER NOT NULL,
                piece_count INTEGER NOT NULL,
                description TEXT
            );
            INSERT INTO gear_set VALUES (1, 'History Test Set', 'Trial', 5);
            INSERT INTO gear_set_bonus VALUES (1, 1, 5, 'Current five-piece bonus.');

            CREATE TABLE skill (
                id TEXT PRIMARY KEY,
                base_ability_id INTEGER,
                name TEXT,
                index_name TEXT,
                description TEXT,
                texture TEXT,
                class_type TEXT,
                skill_line TEXT,
                target TEXT,
                skill_type TEXT,
                is_passive INTEGER,
                is_player INTEGER,
                is_crafted INTEGER,
                crafted_id INTEGER
            );
            CREATE TABLE skill_rank (
                skill_id TEXT,
                ability_id INTEGER,
                display_id INTEGER,
                rank INTEGER,
                morph INTEGER,
                skill_index INTEGER,
                learned_level INTEGER
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                base_ability_id INTEGER,
                name TEXT,
                index_name TEXT,
                description TEXT,
                texture TEXT,
                target TEXT,
                skill_type TEXT,
                base_mechanic TEXT,
                cost INTEGER,
                buff_type TEXT
            );
            CREATE TABLE champion_point (
                id INTEGER PRIMARY KEY,
                name TEXT,
                discipline_id INTEGER,
                description TEXT,
                min_description TEXT,
                max_description TEXT,
                max_points INTEGER,
                jump_points TEXT,
                skill_type TEXT
            );
            """
        )


def test_final_assembly_adds_catalog_history_and_related_content(tmp_path: Path):
    database = tmp_path / "eso.db"
    _seed_database(database)

    boss_root = tmp_path / "eso_info" / "bosses"
    boss_root.mkdir(parents=True)
    (boss_root / "garvin_the_tracker.json").write_text(
        json.dumps(
            {
                "id": "garvin_the_tracker",
                "name": "Garvin the Tracker",
                "content_name": "Lep Seclusa",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "reference_version_history.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "events": [
                    {
                        "entity_type": "Gear Set",
                        "name": "History Test Set",
                        "update": "U34",
                        "year": 2022,
                        "change_type": "released",
                        "summary": "Original five-piece bonus was different.",
                        "source": "Reviewed source",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    starting = ReferenceEntry(
        name="Example",
        entry_type="Mechanic Evidence",
        source_scope="Trial",
        tags=("REFERENCE",),
        summary="Example",
        details=(),
        related=("Garvin the Tracker",),
    )

    entries = finalize_reference_entries(
        (starting,),
        data_root=tmp_path,
        database_path=database,
    )
    by_name = {entry.name: entry for entry in entries}

    assert by_name["Example"].related == ("Garvin the Tracker — Lep Seclusa",)
    assert "History / Legacy" in dict(by_name["History Test Set"].details)


def test_final_assembly_removes_eso_color_markup_from_display_text(tmp_path: Path):
    database = tmp_path / "eso.db"
    _seed_database(database)

    starting = ReferenceEntry(
        name="|cFFAA00Colored Name|r",
        entry_type="Mechanic Evidence",
        source_scope="Trial",
        tags=("|cFFFFFFREFERENCE|r",),
        summary="Avoid |cFF0000the red circle|r.",
        details=(("|c00FF00Handling|r", "Use |c12345678the safe area|r."),),
        related=("|cABCDEFRelated Boss|r",),
        death_note="Do not stand in |cFF0000bad|r.",
        field_note="Source text may contain |cffffffmarkup|r.",
        used_by=("|cffffffEncounter Guide|r",),
        evidence=("|cffffffReviewed source|r",),
        mitigation_note="Move to |c00ff00safety|r.",
    )

    entries = finalize_reference_entries(
        (starting,),
        data_root=tmp_path,
        database_path=database,
    )
    cleaned = next(entry for entry in entries if entry.name == "Colored Name")

    rendered_fields = " ".join(
        (
            cleaned.name,
            *cleaned.tags,
            cleaned.summary,
            *(part for detail in cleaned.details for part in detail),
            *cleaned.related,
            cleaned.death_note,
            cleaned.field_note,
            *cleaned.used_by,
            *cleaned.evidence,
            cleaned.mitigation_note,
        )
    )
    assert "|c" not in rendered_fields
    assert "|r" not in rendered_fields
    assert "the red circle" in cleaned.summary
    assert dict(cleaned.details)["Handling"] == "Use the safe area."
