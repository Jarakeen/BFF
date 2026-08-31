from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools.audit_phase4_action_cost_timing import audit_database


def _create_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE ability (
                ability_id INTEGER,
                name TEXT,
                rank INTEGER,
                morph INTEGER,
                base_cost REAL,
                base_mechanic INTEGER,
                raw_json TEXT
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO ability (
                ability_id, name, rank, morph, base_cost, base_mechanic, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    1,
                    "Ordinary Skill",
                    4,
                    0,
                    2700.0,
                    1,
                    json.dumps({"baseIsCostTime": "false", "chargeFreq": "0"}),
                ),
                (
                    2,
                    "Recurring Skill",
                    4,
                    0,
                    700.0,
                    32,
                    json.dumps({"baseIsCostTime": "true", "chargeFreq": "2000"}),
                ),
                (
                    3,
                    "Compound Recurring Skill",
                    4,
                    0,
                    459.0,
                    5,
                    json.dumps({"baseIsCostTime": "true", "chargeFreq": "2000,2000"}),
                ),
                (
                    4,
                    "Zero Cost",
                    4,
                    0,
                    0.0,
                    0,
                    json.dumps({"baseIsCostTime": "false"}),
                ),
            ),
        )


def test_audit_classifies_activation_and_recurring_rows(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _create_database(database)

    report = audit_database(database)

    assert report["positive_cost_rows"] == 3
    assert report["activation_rows"] == 1
    assert report["recurring_rows"] == 2
    assert report["unresolved_rows"] == 0
    assert report["interval_counts"] == {2.0: 2}


def test_audit_reports_divergent_recurring_intervals(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _create_database(database)

    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO ability (
                ability_id, name, rank, morph, base_cost, base_mechanic, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                5,
                "Unsupported Timing",
                1,
                0,
                500.0,
                5,
                json.dumps({"baseIsCostTime": "true", "chargeFreq": "2000,3000"}),
            ),
        )

    report = audit_database(database)

    assert report["unresolved_rows"] == 1
    assert report["unresolved"][0]["ability_id"] == 5
    assert "divergent intervals" in report["unresolved"][0]["reason"]
