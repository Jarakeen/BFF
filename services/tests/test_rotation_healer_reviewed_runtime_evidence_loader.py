from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerPeriodicRefreshPolicy,
)
from services.rotation_healer_reviewed_runtime_evidence_loader import (
    RotationHealerReviewedRuntimeEvidenceLoader,
)


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER NOT NULL,
                name TEXT
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                index_name TEXT,
                duration INTEGER,
                channeled INTEGER,
                coef_description TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                raw_name TEXT,
                rank INTEGER,
                morph INTEGER
            );
            CREATE TABLE skill_coefficient (
                skill_rank_id INTEGER NOT NULL,
                coefficient_number INTEGER NOT NULL,
                type TEXT,
                a REAL,
                b REAL,
                c REAL,
                r REAL,
                avg REAL
            );
            """
        )
        connection.execute(
            "INSERT INTO skill(id,base_ability_id,name) VALUES (?,?,?)",
            (1, 61505, "Echoing Vigor"),
        )
        connection.execute(
            "INSERT INTO ability(ability_id,name,index_name,duration,channeled,coef_description) VALUES (?,?,?,?,?,?)",
            (61505, "Echoing Vigor", "echoing vigor", 16000, 0, "Heals every 2 seconds for 16 seconds."),
        )
        connection.execute(
            "INSERT INTO skill_rank(id,skill_id,ability_id,raw_name,rank,morph) VALUES (?,?,?,?,?,?)",
            (1, 1, 61505, "Echoing Vigor", 4, 1),
        )
        connection.execute(
            "INSERT INTO skill_coefficient(skill_rank_id,coefficient_number,type,a,b,c,r,avg) VALUES (?,?,?,?,?,?,?,?)",
            (1, 1, "heal", 0.0, 0.0, 0.0, 1.0, None),
        )
        connection.commit()
    finally:
        connection.close()
    return path


def _timing_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "timing.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "review_status": "reviewed",
                "game_version": "U50",
                "samples": [
                    {
                        "source_name": "Echoing Vigor",
                        "coefficient_number": 1,
                        "activation_time_seconds": 10.0,
                        "observed_tick_times_seconds": [10.02, 12.02, 14.02, 16.02, 18.02, 20.02, 22.02, 24.02],
                        "observation_end_seconds": 26.1,
                        "provenance": ["reviewed isolated sample"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _refresh_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "refresh.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "review_status": "reviewed",
                "game_version": "U50",
                "policies": [
                    {
                        "source_name": "Echoing Vigor",
                        "coefficient_number": 1,
                        "refresh_policy": "restart",
                        "provenance": ["reviewed recipient-aware recast evidence"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_loader_composes_reviewed_refresh_policy_into_reviewed_timing(tmp_path):
    result = RotationHealerReviewedRuntimeEvidenceLoader(_database(tmp_path)).load(
        _timing_fixture(tmp_path),
        refresh_fixture_path=_refresh_fixture(tmp_path),
    )

    assert result.unresolved == ()
    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.source_name == "Echoing Vigor"
    assert observation.refresh_policy is RotationHealerPeriodicRefreshPolicy.RESTART
    assert "reviewed refresh/recast policy: restart" in observation.provenance


def test_loader_keeps_refresh_unresolved_when_no_refresh_fixture_is_supplied(tmp_path):
    result = RotationHealerReviewedRuntimeEvidenceLoader(_database(tmp_path)).load(
        _timing_fixture(tmp_path)
    )

    assert result.unresolved == ()
    assert len(result.observations) == 1
    assert result.observations[0].refresh_policy is None


def test_loader_fails_closed_when_refresh_fixture_has_no_timing_fixture(tmp_path):
    result = RotationHealerReviewedRuntimeEvidenceLoader(_database(tmp_path)).load(
        None,
        refresh_fixture_path=_refresh_fixture(tmp_path),
    )

    assert result.observations == ()
    assert result.unresolved == (
        "reviewed healer refresh policies were supplied without reviewed periodic timing evidence",
    )
