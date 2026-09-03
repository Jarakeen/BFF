from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.encounter_repository import EncounterRepository
from services.encounter_schema import ensure_encounter_schema


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


def _add_canonical_fact(database: Path) -> None:
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
                json.dumps(
                    {
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
                    },
                    sort_keys=True,
                ),
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


def test_fixture_without_database_preserves_raw_projection_behavior(tmp_path: Path) -> None:
    data_root = _data_root(tmp_path)

    encounter = EncounterRepository.from_data_root(data_root).get("boss")

    assert [row.name for row in encounter.mechanics] == [
        "Literal Mechanic",
        "Accepted Inference",
        "Rejected Inference",
    ]
