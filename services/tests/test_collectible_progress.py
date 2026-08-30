from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from services.eso_collectible_database_service import EsoCollectibleDatabaseService


def _database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE entity (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL
            );

            CREATE TABLE entity_source (
                id INTEGER PRIMARY KEY,
                entity_id TEXT NOT NULL,
                raw_json TEXT
            );

            CREATE TABLE collectible (
                id INTEGER PRIMARY KEY,
                entity_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                hint TEXT,
                icon TEXT,
                source_category_type TEXT,
                source_category_name TEXT,
                source_subcategory_name TEXT,
                category_index INTEGER,
                subcategory_index INTEGER,
                collectible_index INTEGER,
                canonical_type_key TEXT,
                sidebar_category_key TEXT,
                normalization_status TEXT NOT NULL DEFAULT 'unmapped',
                mapping_id INTEGER,
                audit_reason TEXT,
                is_unlocked INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                is_slottable INTEGER DEFAULT 0,
                is_usable INTEGER DEFAULT 0,
                is_renameable INTEGER DEFAULT 0,
                is_placeholder INTEGER DEFAULT 0,
                is_hidden INTEGER DEFAULT 0,
                has_appearance INTEGER DEFAULT 0,
                source_raw_json TEXT NOT NULL
            );
            """
        )
        db.execute(
            """
            INSERT INTO collectible (
                id, entity_id, name, canonical_type_key,
                sidebar_category_key, source_raw_json
            ) VALUES (101, 'collectible:101', 'Test Mount', 'mount', 'Mounts', '{}')
            """
        )
        db.commit()


def test_collection_progress_is_separate_from_source_unlock_flag(tmp_path):
    db_path = tmp_path / "eso.db"
    _database(db_path)

    service = EsoCollectibleDatabaseService(db_path)
    service.set_progress(
        101,
        owned=True,
        acquired_on="2026-08-29",
        notes="Finally dropped.",
    )

    row = service.collectible(101)
    assert row is not None
    assert row["owned"] == 1
    assert row["acquired_on"] == "2026-08-29"
    assert row["notes"] == "Finally dropped."
    assert row["is_unlocked"] == 0

    owned, total = service.progress_summary("Mounts")
    assert (owned, total) == (1, 1)


def test_collection_progress_exports_full_catalog_csv(tmp_path):
    db_path = tmp_path / "eso.db"
    _database(db_path)

    service = EsoCollectibleDatabaseService(db_path)
    service.set_progress(101, owned=True, notes="Backup me")

    target = tmp_path / "backup.csv"
    result = service.export_progress_csv(target)

    assert result == target
    with target.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["Collectible ID"] == "101"
    assert rows[0]["Name"] == "Test Mount"
    assert rows[0]["Collected"] == "Yes"
    assert rows[0]["Notes"] == "Backup me"


def test_expanded_collections_groups_existing_normalized_types(tmp_path):
    db_path = tmp_path / "eso.db"
    _database(db_path)

    grouped_types = [
        (201, "weapon_style", "Weapon Styles"),
        (202, "armor_style", "Armor Styles"),
        (203, "furnishing", "Furnishings"),
        (204, "fragment", "Fragments"),
        (205, "combination_fragment", "Fragments"),
        (206, "patron", "Fragments"),
        (207, "account_upgrade", "Tools & Upgrades"),
        (208, "tool", "Tools & Upgrades"),
        (209, "story", "Tools & Upgrades"),
        (210, "skill_style", "Tools & Upgrades"),
    ]

    with sqlite3.connect(db_path) as db:
        for collectible_id, type_key, _expected in grouped_types:
            db.execute(
                """
                INSERT INTO collectible (
                    id, entity_id, name, canonical_type_key,
                    sidebar_category_key, normalization_status,
                    audit_reason, source_raw_json
                ) VALUES (?, ?, ?, ?, NULL, 'contextual', 'outside_sidebar', '{}')
                """,
                (
                    collectible_id,
                    f"collectible:{collectible_id}",
                    f"Test {type_key}",
                    type_key,
                ),
            )
        db.commit()

    service = EsoCollectibleDatabaseService(db_path)

    for collectible_id, _type_key, expected_category in grouped_types:
        row = service.collectible(collectible_id)
        assert row is not None
        assert row["sidebar_category_key"] == expected_category
        assert row["audit_reason"] is None

    assert service.category_count("Weapon Styles") == 1
    assert service.category_count("Armor Styles") == 1
    assert service.category_count("Furnishings") == 1
    assert service.category_count("Fragments") == 3
    assert service.category_count("Tools & Upgrades") == 4
