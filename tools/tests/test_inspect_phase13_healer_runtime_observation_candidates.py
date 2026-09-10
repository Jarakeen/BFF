import json
import sqlite3

from tools.inspect_phase13_healer_runtime_observation_candidates import inspect_samples


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER NOT NULL,
                name TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                raw_name TEXT,
                rank INTEGER,
                morph INTEGER
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                coef_description TEXT,
                duration REAL
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
        db.execute("INSERT INTO skill VALUES (1, 101, 'Illustrious Healing')")
        db.execute("INSERT INTO skill_rank VALUES (10, 1, 101, 'Illustrious Healing', 4, 1)")
        db.execute(
            "INSERT INTO ability VALUES (?, ?, ?, ?)",
            (
                101,
                "Illustrious Healing",
                "Summon restoring spirits, healing for $1 Health over 15 seconds.",
                15000,
            ),
        )
        db.execute(
            "INSERT INTO skill_coefficient VALUES (10, 1, '8', 0.1, 1.0, 0.0, 1.0, NULL)"
        )
    return path


def _candidate(tmp_path):
    path = tmp_path / "candidate.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "review_status": "candidate",
                "game_version": "U50",
                "samples": [
                    {
                        "source_name": "Illustrious Healing",
                        "coefficient_number": 1,
                        "activation_time_seconds": 10.0,
                        "observed_tick_times_seconds": [
                            11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0,
                            19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0,
                        ],
                        "observation_end_seconds": 25.02,
                        "provenance": ["fixture"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_inspector_reports_canonical_cadence_and_expiry_boundary(tmp_path):
    rows = inspect_samples(
        _candidate(tmp_path),
        database_path=_database(tmp_path),
        tolerance_seconds=0.05,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["ready"]
    assert row["canonical_duration_seconds"] == 15.0
    assert row["canonical_cadence_seconds"] == 1.0
    assert row["observed_tick_count"] == 15
    assert row["first_tick_offset_seconds"] == 1.0
    assert row["last_tick_offset_seconds"] == 15.0
    assert row["max_cadence_error_seconds"] == 0.0
    assert row["observation_reaches_expiry"]
    assert row["tick_on_expiry_boundary"] is True
    assert row["last_tick_to_expiry_seconds"] == 0.0


def test_default_runtime_tolerance_does_not_treat_eighteen_ms_late_tick_as_boundary(tmp_path):
    candidate = tmp_path / "candidate_late.json"
    candidate.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "review_status": "candidate",
                "game_version": "U50",
                "samples": [
                    {
                        "source_name": "Illustrious Healing",
                        "coefficient_number": 1,
                        "activation_time_seconds": 10.0,
                        "observed_tick_times_seconds": [25.018],
                        "observation_end_seconds": 25.02,
                        "provenance": ["fixture"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    row = inspect_samples(candidate, database_path=_database(tmp_path))[0]

    assert row["observation_reaches_expiry"]
    assert row["tick_on_expiry_boundary"] is False
    assert row["last_tick_to_expiry_seconds"] == 0.018
