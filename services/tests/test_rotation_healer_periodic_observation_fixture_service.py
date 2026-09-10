import json
import sqlite3

from services.rotation_healer_periodic_observation_fixture_service import (
    RotationHealerPeriodicObservationFixtureService,
)


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
        db.execute(
            "INSERT INTO skill(id, base_ability_id, name) VALUES (1, 93807, 'Budding Seeds')"
        )
        db.execute(
            """
            INSERT INTO skill_rank(id, skill_id, ability_id, raw_name, rank, morph)
            VALUES (6910, 1, 93807, 'Budding Seeds', 4, 1)
            """
        )
        description = (
            "Summon a field which blooms after 6 seconds, healing for $1 Health. "
            "While the field grows, you and allies are healed for $2 Health every 1 second."
        )
        db.execute(
            """
            INSERT INTO ability(ability_id, name, coef_description, duration)
            VALUES (?, ?, ?, ?)
            """,
            (93807, "Budding Seeds", description, 6000),
        )
        db.execute(
            """
            INSERT INTO skill_coefficient(
                skill_rank_id, coefficient_number, type, a, b, c, r, avg
            ) VALUES (6910, 2, '8', 0.1, 1.0, 0.0, 1.0, NULL)
            """
        )
    return path


def _fixture(tmp_path, payload):
    path = tmp_path / "observations.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _payload(**sample_overrides):
    sample = {
        "source_name": "Budding Seeds",
        "coefficient_number": 2,
        "activation_time_seconds": 10.0,
        "observed_tick_times_seconds": [11.0, 12.0, 13.0, 14.0, 15.0, 16.0],
        "observation_end_seconds": 16.1,
        "provenance": ["reviewed combat-log sample A"],
    }
    sample.update(sample_overrides)
    return {
        "schema_version": 1,
        "game_version": "U50",
        "samples": [sample],
    }


def test_loads_fixture_and_derives_reviewed_runtime_observation(tmp_path):
    report = RotationHealerPeriodicObservationFixtureService(_database(tmp_path)).load(
        _fixture(tmp_path, _payload())
    )

    assert report.unresolved == ()
    assert len(report.entries) == 1
    assert len(report.reviewed_sample_observations) == 1
    assert len(report.reviewed_observations) == 1
    observation = report.reviewed_observations[0]
    assert observation.first_tick_offset_seconds == 1.0
    assert observation.tick_on_expiry_boundary is True
    assert observation.game_version == "U50"


def test_reviewed_observations_collapse_repeated_samples_to_consensus(tmp_path):
    samples = []
    for label, activation, offset in (
        ("A", 10.0, 0.04),
        ("B", 20.0, 0.06),
        ("C", 30.0, 0.05),
    ):
        samples.append(
            {
                "source_name": "Budding Seeds",
                "coefficient_number": 2,
                "activation_time_seconds": activation,
                "observed_tick_times_seconds": [
                    activation + offset + step for step in range(6)
                ],
                "observation_end_seconds": activation + 6.1,
                "provenance": [f"reviewed combat-log sample {label}"],
            }
        )
    payload = {
        "schema_version": 1,
        "game_version": "U50",
        "samples": samples,
    }

    report = RotationHealerPeriodicObservationFixtureService(_database(tmp_path)).load(
        _fixture(tmp_path, payload)
    )

    assert report.unresolved == ()
    assert len(report.reviewed_sample_observations) == 3
    assert len(report.reviewed_observations) == 1
    observation = report.reviewed_observations[0]
    assert abs(observation.first_tick_offset_seconds - 0.05) < 1e-9
    assert observation.tick_on_expiry_boundary is False
    assert any("consensus from 3 explicitly reviewed" in item for item in observation.provenance)


def test_fixture_uses_canonical_cadence_and_reports_conflict(tmp_path):
    report = RotationHealerPeriodicObservationFixtureService(_database(tmp_path)).load(
        _fixture(
            tmp_path,
            _payload(
                observed_tick_times_seconds=[11.0, 12.25, 13.25, 14.25, 15.25, 16.0]
            ),
        )
    )

    assert any("conflicts with canonical cadence" in item for item in report.unresolved)
    assert report.entries[0].canonical.cadence_seconds == 1.0


def test_fixture_requires_supported_schema_version(tmp_path):
    path = _fixture(tmp_path, {"schema_version": 2, "samples": []})

    try:
        RotationHealerPeriodicObservationFixtureService(_database(tmp_path)).load(path)
    except ValueError as exc:
        assert "unsupported healer runtime observation schema_version" in str(exc)
    else:
        raise AssertionError("expected unsupported schema version to fail")


def test_invalid_sample_is_reported_without_discarding_other_samples(tmp_path):
    payload = _payload()
    payload["samples"].insert(0, {"source_name": "Budding Seeds"})

    report = RotationHealerPeriodicObservationFixtureService(_database(tmp_path)).load(
        _fixture(tmp_path, payload)
    )

    assert len(report.entries) == 1
    assert len(report.reviewed_observations) == 1
    assert any(item.startswith("sample 1:") for item in report.unresolved)


def test_short_observation_does_not_promote_expiry_rule(tmp_path):
    report = RotationHealerPeriodicObservationFixtureService(_database(tmp_path)).load(
        _fixture(
            tmp_path,
            _payload(
                observed_tick_times_seconds=[11.0, 12.0, 13.0],
                observation_end_seconds=13.2,
            ),
        )
    )

    assert report.reviewed_observations == ()
    assert any("does not extend through canonical expiry" in item for item in report.unresolved)
