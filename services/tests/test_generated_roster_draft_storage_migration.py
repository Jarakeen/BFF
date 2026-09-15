from __future__ import annotations

from services.eso_database import EsoDatabase
from services.generated_roster_draft_service import (
    GENERATED_ROSTER_DRAFT_STORAGE,
    LEGACY_GENERATED_ROSTER_PLAN_READ_MIGRATION_ONLY,
    GeneratedRosterDraftService,
    GeneratedRosterDraftSlot,
)


def _table_names(db: EsoDatabase) -> set[str]:
    return {
        str(row["name"])
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }


def test_fresh_generated_draft_storage_does_not_create_legacy_plan_tables(tmp_path) -> None:
    db = EsoDatabase(tmp_path / "eso.db")

    service = GeneratedRosterDraftService(db)

    tables = _table_names(db)
    assert GENERATED_ROSTER_DRAFT_STORAGE == "generated_roster_draft"
    assert LEGACY_GENERATED_ROSTER_PLAN_READ_MIGRATION_ONLY is True
    assert "generated_roster_draft" in tables
    assert "generated_roster_draft_slot" in tables
    assert "generated_roster_plan" not in tables
    assert "generated_roster_plan_slot" not in tables
    assert service.list_plan_names() == ()


def test_legacy_generated_plan_rows_migrate_forward_without_legacy_rewrite(tmp_path) -> None:
    db = EsoDatabase(tmp_path / "eso.db")
    db.execute(
        """
        CREATE TABLE generated_roster_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            goal TEXT NOT NULL,
            difficulty TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE generated_roster_plan_slot (
            plan_id INTEGER NOT NULL,
            slot_index INTEGER NOT NULL,
            slot_name TEXT NOT NULL,
            kind TEXT NOT NULL,
            player_name TEXT NOT NULL DEFAULT '',
            character_name TEXT NOT NULL DEFAULT '',
            eso_class TEXT NOT NULL DEFAULT '',
            build_name TEXT NOT NULL DEFAULT '',
            gear_summary TEXT NOT NULL DEFAULT '',
            unresolved TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (plan_id, slot_index)
        )
        """
    )
    db.execute(
        "INSERT INTO generated_roster_plan (id, name, goal, difficulty) VALUES (7, ?, ?, ?)",
        ("Legacy Draft", "Godslayer", "Veteran"),
    )
    db.execute(
        """
        INSERT INTO generated_roster_plan_slot (
            plan_id, slot_index, slot_name, kind, player_name,
            character_name, eso_class, build_name, gear_summary, unresolved
        ) VALUES (7, 0, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Healer 1",
            "open_recruit",
            "Recruitment Needed",
            "",
            "Warden",
            "Support Healer",
            "Pillager's Profit",
            "traits unresolved",
        ),
    )
    db.commit()

    service = GeneratedRosterDraftService(db)
    migrated = service.load_plan("legacy draft")

    assert migrated is not None
    assert migrated.draft_id == 7
    assert migrated.name == "Legacy Draft"
    assert migrated.goal == "Godslayer"
    assert migrated.slots[0].slot_name == "Healer 1"
    assert migrated.slots[0].gear_sets == ()
    assert migrated.slots[0].skills == ()

    service.save_plan(
        name="Legacy Draft",
        goal="Gryphon Heart",
        difficulty="Veteran Hardmode",
        slots=(
            GeneratedRosterDraftSlot(
                slot_name="Healer 1",
                kind="saved",
                player_name="Player",
                character_name="Character",
                eso_class="Warden",
                build_name="GH Healer",
            ),
        ),
    )

    canonical = db.execute(
        "SELECT goal, difficulty FROM generated_roster_draft WHERE id = 7"
    ).fetchone()
    legacy = db.execute(
        "SELECT goal, difficulty FROM generated_roster_plan WHERE id = 7"
    ).fetchone()
    assert canonical is not None
    assert canonical["goal"] == "Gryphon Heart"
    assert canonical["difficulty"] == "Veteran Hardmode"
    assert legacy is not None
    assert legacy["goal"] == "Godslayer"
    assert legacy["difficulty"] == "Veteran"
