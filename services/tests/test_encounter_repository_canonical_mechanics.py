from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from services.encounter_repository import EncounterRepository, EncounterSourceError
from services.encounter_schema import ensure_encounter_schema
from services.encounter_service import EncounterService


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _data_root(tmp_path: Path) -> Path:
    data_root = tmp_path / "data"
    bosses = data_root / "eso_info" / "bosses"
    evidence = data_root / "encounter_evidence"
    bosses.mkdir(parents=True)
    evidence.mkdir(parents=True)
    _write(
        bosses / "boss.json",
        {
            "id": "boss",
            "content_id": "trial",
            "name": "Boss",
            "health": {},
            "phases": [],
            "mechanics": [
                {
                    "name": "Literal Mechanic",
                    "description": "Source-declared mechanic.",
                    "interpretation_status": "source",
                    "mechanic_type": "movement",
                    "requires_movement": True,
                },
                {
                    "name": "Accepted Inference",
                    "description": "Raw inferred version.",
                    "interpretation_status": "inferred",
                    "mechanic_type": "targeted_hazard",
                    "target_count": 2,
                },
                {
                    "name": "Rejected Inference",
                    "description": "Must not reach downstream evaluation.",
                    "interpretation_status": "inferred",
                    "mechanic_type": "interrupt",
                    "interruptible": True,
                },
            ],
        },
    )
    return data_root


def _canonical_payload(**updates) -> dict:
    payload = {
        "name": "Accepted Inference",
        "description": "Reviewed canonical version.",
        "mechanic_type": "targeted_hazard",
        "damage_type": None,
        "target_count": 2,
        "requires_movement": None,
        "requires_positioning": None,
        "requires_cleanse": None,
        "persistent_hazard": None,
        "failure_is_fatal": None,
        "interruptible": None,
    }
    payload.update(updates)
    return payload


def _add_canonical_fact(database: Path, payload: dict | None = None) -> None:
    con = sqlite3.connect(database)
    try:
        ensure_encounter_schema(con)
        con.execute(
            "INSERT INTO content(id, name, slug, content_type) VALUES ('trial', 'Trial', 'trial', 'trial')"
        )
        con.execute(
            "INSERT INTO encounter(id, content_id, name, slug) VALUES ('boss', 'trial', 'Boss', 'boss')"
        )
        con.execute(
            """
            INSERT INTO encounter_canonical_fact(
                encounter_id, canonical_kind, fact_type, fact_key,
                payload_json, review_status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "boss",
                "mechanic_detail",
                "mechanic_detail",
                "accepted_inference",
                json.dumps(payload or _canonical_payload(), sort_keys=True),
                "reviewed_single_source",
            ),
        )
        con.commit()
    finally:
        con.close()


def test_database_backed_repository_excludes_unreviewed_inferred_mechanics(tmp_path: Path) -> None:
    data_root = _data_root(tmp_path)
    database = data_root / "eso.db"
    _add_canonical_fact(database)

    encounter = EncounterRepository.from_data_root(data_root).get("boss")

    assert [row.name for row in encounter.mechanics] == [
        "Literal Mechanic",
        "Accepted Inference",
    ]
    accepted = encounter.mechanics[1]
    assert accepted.description == "Reviewed canonical version."
    assert accepted.interpretation_status == "reviewed_single_source"
    assert accepted.mechanic_id == "boss:canonical:accepted_inference"
    assert accepted.requirement_subjects == ()


def test_fixture_without_database_preserves_raw_projection_behavior(tmp_path: Path) -> None:
    data_root = _data_root(tmp_path)

    encounter = EncounterRepository.from_data_root(data_root).get("boss")

    assert [row.name for row in encounter.mechanics] == [
        "Literal Mechanic",
        "Accepted Inference",
        "Rejected Inference",
    ]
    assert all(row.requirement_subjects == () for row in encounter.mechanics)


def test_boss_owned_canonical_movement_is_not_a_player_requirement(tmp_path: Path) -> None:
    data_root = _data_root(tmp_path)
    database = data_root / "eso.db"
    _add_canonical_fact(
        database,
        _canonical_payload(
            name="Boss Roll",
            mechanic_type="movement",
            target_count=None,
            requires_movement=True,
            requirement_subjects={"movement": "boss"},
        ),
    )

    service = EncounterService(EncounterRepository.from_data_root(data_root))
    encounter = service.get("boss")

    canonical = next(row for row in encounter.mechanics if row.name == "Boss Roll")
    assert canonical.requirement_subject("movement") == "boss"
    assert [
        (row.mechanic_name, row.requirement_type)
        for row in service.requirements("boss")
    ] == [("Literal Mechanic", "movement")]


def test_explicit_player_positioning_remains_a_player_requirement(tmp_path: Path) -> None:
    data_root = _data_root(tmp_path)
    database = data_root / "eso.db"
    _add_canonical_fact(
        database,
        _canonical_payload(
            name="Range Check",
            mechanic_type="positioning",
            target_count=None,
            requires_positioning=True,
            requirement_subjects={"positioning": "player"},
        ),
    )

    service = EncounterService(EncounterRepository.from_data_root(data_root))

    requirements = [
        (row.mechanic_name, row.requirement_type)
        for row in service.requirements("boss")
    ]
    assert ("Range Check", "positioning") in requirements
    assert [row.mechanic_name for row in service.positioning_constraints("boss")] == [
        "Range Check"
    ]


def test_invalid_canonical_requirement_subject_is_rejected(tmp_path: Path) -> None:
    data_root = _data_root(tmp_path)
    database = data_root / "eso.db"
    _add_canonical_fact(
        database,
        _canonical_payload(
            requires_movement=True,
            requirement_subjects={"movement": "everyone-ish"},
        ),
    )

    with pytest.raises(EncounterSourceError, match="Unsupported canonical mechanic requirement subject"):
        EncounterRepository.from_data_root(data_root).get("boss")
