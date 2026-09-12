from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_magnitude_observation_service import (
    RotationDDPeriodicEsoLogsMagnitudeObservationService,
)


class _Coefficients:
    def resolve_entity_id(self, entity_id):
        assert entity_id == "stampede"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_id=7, morph=1, base_ability_id=39807),
            unresolved=(),
        )


def _logs(path) -> None:
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT,
                fight_id INTEGER,
                event_index INTEGER,
                timestamp REAL,
                event_type TEXT,
                source_id INTEGER,
                target_id INTEGER,
                ability_game_id INTEGER,
                amount REAL,
                hit_type INTEGER,
                cast_track_id INTEGER,
                raw_json TEXT
            )
            """
        )


def _event(
    path,
    index,
    timestamp,
    event_type,
    ability_id,
    *,
    track=10,
    target=99,
    amount=None,
    hit_type=1,
    name=None,
) -> None:
    raw = {} if name is None else {"ability": {"name": name}}
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "R",
                1,
                index,
                timestamp,
                event_type,
                42,
                target,
                ability_id,
                amount,
                hit_type,
                track,
                json.dumps(raw),
            ),
        )


def _service(canonical, logs):
    canonical.touch()
    service = RotationDDPeriodicEsoLogsMagnitudeObservationService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )
    service.coefficients = _Coefficients()
    service._numeric_aliases = lambda skill_id, morph, base_ability_id: (39807,)
    return service


def test_groups_same_cast_target_and_hit_type_into_amount_sequence(tmp_path) -> None:
    canonical = tmp_path / "canonical.db"
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(logs, 1, 1000, "cast", 39807, track=10, name="Stampede")
    _event(logs, 2, 2100, "damage", 126474, track=10, amount=1000, hit_type=1)
    _event(logs, 3, 3100, "damage", 126474, track=10, amount=1000, hit_type=1)
    _event(logs, 4, 4100, "damage", 126474, track=10, amount=1200, hit_type=1)

    report = _service(canonical, logs).inspect(
        "stampede",
        periodic_ability_id=126474,
    )

    assert report.unresolved == ()
    assert report.cast_anchor_count == 1
    assert len(report.sequences) == 1
    sequence = report.sequences[0]
    assert sequence.target_id == 99
    assert sequence.hit_type == 1
    assert sequence.amounts == (1000.0, 1000.0, 1200.0)
    assert sequence.offsets_seconds == (1.1, 2.1, 3.1)
    assert sequence.distinct_amount_count == 2
    assert sequence.amount_is_constant is False
    assert report.varying_sequence_count == 1
    assert report.constant_sequence_count == 0


def test_separates_target_and_hit_type_to_avoid_obvious_magnitude_confounders(tmp_path) -> None:
    canonical = tmp_path / "canonical.db"
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(logs, 1, 1000, "cast", 39807, track=10, name="Stampede")
    _event(logs, 2, 2100, "damage", 126474, track=10, target=99, amount=1000, hit_type=1)
    _event(logs, 3, 3100, "damage", 126474, track=10, target=99, amount=1000, hit_type=1)
    _event(logs, 4, 2200, "damage", 126474, track=10, target=100, amount=1500, hit_type=1)
    _event(logs, 5, 3200, "damage", 126474, track=10, target=100, amount=1500, hit_type=1)
    _event(logs, 6, 2300, "damage", 126474, track=10, target=99, amount=2000, hit_type=2)
    _event(logs, 7, 3300, "damage", 126474, track=10, target=99, amount=2000, hit_type=2)

    report = _service(canonical, logs).inspect(
        "stampede",
        periodic_ability_id=126474,
    )

    assert len(report.sequences) == 3
    assert report.constant_sequence_count == 3
    assert report.varying_sequence_count == 0


def test_single_occurrence_rows_do_not_nominate_magnitude_behavior(tmp_path) -> None:
    canonical = tmp_path / "canonical.db"
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(logs, 1, 1000, "cast", 39807, track=10, name="Stampede")
    _event(logs, 2, 2100, "damage", 126474, track=10, amount=1000)

    report = _service(canonical, logs).inspect(
        "stampede",
        periodic_ability_id=126474,
    )

    assert report.sequences == ()
    assert any("at least 2 occurrences" in item for item in report.unresolved)
