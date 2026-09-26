from __future__ import annotations

import json

from services.eso_database import EsoDatabase
from services.generated_roster_draft_prescription_service import (
    GENERATED_ROSTER_DRAFT_PRESCRIPTION_STORAGE,
    GeneratedRosterDraftPrescriptionService,
)
from services.generated_roster_draft_service import (
    GeneratedRosterDraftService,
    GeneratedRosterDraftSlot,
)


def _table_exists(db: EsoDatabase, name: str) -> bool:
    return (
        db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        is not None
    )


def test_fresh_prescription_storage_uses_canonical_draft_identity_only(tmp_path) -> None:
    db = EsoDatabase(tmp_path / "eso.db")
    drafts = GeneratedRosterDraftService(db)
    draft = drafts.save_plan(
        name="GH Prog",
        goal="Gryphon Heart",
        difficulty="Veteran",
        slots=(
            GeneratedRosterDraftSlot(
                slot_name="Healer 1",
                kind="prescribed_recruit",
                player_name="Recruitment Needed",
                character_name="",
                eso_class="Warden",
                build_name="Support Healer",
            ),
        ),
    )

    prescriptions = GeneratedRosterDraftPrescriptionService(db)
    payload = {"slot_name": "Healer 1", "eso_class": "Warden"}
    prescriptions.save(
        draft_id=draft.draft_id,
        slot_name="Healer 1",
        prescription=payload,
        adopted_player_name="Keen",
        adopted_character_name="Magrat",
        adopted_build_name="GH Healer",
    )

    assert prescriptions.load(draft.draft_id, "healer 1") == payload
    assert _table_exists(db, GENERATED_ROSTER_DRAFT_PRESCRIPTION_STORAGE)
    assert not _table_exists(db, "generated_roster_recruit_prescription")


def test_legacy_prescription_rows_migrate_forward_without_rewrite(tmp_path) -> None:
    db = EsoDatabase(tmp_path / "eso.db")
    db.execute(
        """
        CREATE TABLE generated_roster_plan (
            id INTEGER PRIMARY KEY,
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
        """
        CREATE TABLE generated_roster_recruit_prescription (
            plan_id INTEGER NOT NULL,
            slot_name TEXT NOT NULL,
            prescription_json TEXT NOT NULL,
            adopted_player_name TEXT NOT NULL DEFAULT '',
            adopted_character_name TEXT NOT NULL DEFAULT '',
            adopted_build_name TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (plan_id, slot_name)
        )
        """
    )
    db.execute(
        "INSERT INTO generated_roster_plan (id, name, goal, difficulty) VALUES (7, 'RG Prog', 'Rockgrove', 'Veteran')"
    )
    db.execute(
        """
        INSERT INTO generated_roster_plan_slot (
            plan_id, slot_index, slot_name, kind, player_name, character_name,
            eso_class, build_name, gear_summary, unresolved
        ) VALUES (7, 0, 'Off Tank', 'prescribed_recruit', 'Recruitment Needed', '',
                  'Dragonknight', 'DK Tank', '', '')
        """
    )
    legacy_payload = {"slot_name": "Off Tank", "eso_class": "Dragonknight"}
    db.execute(
        """
        INSERT INTO generated_roster_recruit_prescription (
            plan_id, slot_name, prescription_json,
            adopted_player_name, adopted_character_name, adopted_build_name
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (7, "Off Tank", json.dumps(legacy_payload), "Tank", "DK", "RG Tank"),
    )
    db.commit()

    drafts = GeneratedRosterDraftService(db)
    migrated_draft = drafts.load_plan("RG Prog")
    assert migrated_draft is not None

    prescriptions = GeneratedRosterDraftPrescriptionService(db)
    assert prescriptions.load(migrated_draft.draft_id, "Off Tank") == legacy_payload

    legacy_row = db.execute(
        """
        SELECT prescription_json, adopted_build_name
        FROM generated_roster_recruit_prescription
        WHERE plan_id = 7 AND slot_name = 'Off Tank'
        """
    ).fetchone()
    assert legacy_row is not None
    assert json.loads(str(legacy_row["prescription_json"])) == legacy_payload
    assert str(legacy_row["adopted_build_name"]) == "RG Tank"


def test_existing_prescription_updates_payload_not_only_adoption_names(tmp_path) -> None:
    db = EsoDatabase(tmp_path / "eso.db")
    drafts = GeneratedRosterDraftService(db)
    draft = drafts.save_plan(
        name="PM",
        goal="Godslayer",
        difficulty="Veteran",
        slots=(GeneratedRosterDraftSlot(
            slot_name="DD 1", kind="prescribed_recruit",
            player_name="Recruitment Needed", character_name="",
            eso_class="Necromancer", build_name="Support DD",
        ),),
    )
    service = GeneratedRosterDraftPrescriptionService(db)
    service.save(
        draft_id=draft.draft_id, slot_name="DD 1",
        prescription={"gear": ["Z'en"]},
        adopted_player_name="", adopted_character_name="", adopted_build_name="",
    )
    service.save(
        draft_id=draft.draft_id, slot_name="DD 1",
        prescription={"gear": ["Alkosh"], "class": "Dragonknight"},
        adopted_player_name="Cobble", adopted_character_name="Cobble DK",
        adopted_build_name="Z'enKosh",
    )

    assert service.load(draft.draft_id, "DD 1") == {
        "gear": ["Alkosh"], "class": "Dragonknight"
    }


def test_prescription_rejects_missing_parent_draft_without_row(tmp_path) -> None:
    db = EsoDatabase(tmp_path / "eso.db")
    GeneratedRosterDraftService(db)
    service = GeneratedRosterDraftPrescriptionService(db)

    import pytest
    with pytest.raises(ValueError, match="does not exist"):
        service.save(
            draft_id=999, slot_name="DD 1", prescription={"role": "DD"},
            adopted_player_name="", adopted_character_name="", adopted_build_name="",
        )

    row = db.execute(
        "SELECT COUNT(*) AS count FROM generated_roster_draft_recruit_prescription"
    ).fetchone()
    assert int(row["count"]) == 0
