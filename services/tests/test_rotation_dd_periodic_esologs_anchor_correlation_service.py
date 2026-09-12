from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

import pytest

from services.rotation_dd_periodic_esologs_anchor_correlation_service import (
    RotationDDPeriodicEsoLogsAnchorCorrelationService,
)


class _Coefficients:
    def resolve_entity_id(self, entity_id):
        assert entity_id == "stampede"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_id=7, morph=1, base_ability_id=39807),
            unresolved=(),
        )


def _logs(path):
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
                ability_game_id INTEGER,
                cast_track_id INTEGER,
                raw_json TEXT
            )
            """
        )


def _event(path, index, time, event_type, ability_id, *, track=10, name=None):
    raw = {} if name is None else {"ability": {"name": name}}
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "R",
                1,
                index,
                time,
                event_type,
                42,
                ability_id,
                track,
                json.dumps(raw),
            ),
        )


def _service(canonical, logs):
    canonical.touch()
    service = RotationDDPeriodicEsoLogsAnchorCorrelationService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )
    service.coefficients = _Coefficients()
    service._numeric_aliases = lambda skill_id, morph, base_ability_id: (39807,)
    return service


def test_correlates_cast_impact_and_clustered_periodic_occurrences(tmp_path) -> None:
    canonical = tmp_path / "canonical.db"
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(logs, 1, 1000, "cast", 39807, track=10, name="Stampede")
    _event(logs, 2, 1150, "damage", 38792, track=10)
    _event(logs, 3, 2150, "damage", 126474, track=10)
    _event(logs, 4, 2160, "damage", 126474, track=10)
    _event(logs, 5, 3155, "damage", 126474, track=10)
    _event(logs, 6, 4150, "damage", 126474, track=10)

    report = _service(canonical, logs).inspect(
        "stampede",
        impact_ability_id=38792,
        periodic_ability_id=126474,
        active_window_seconds=15.0,
    )

    assert report.unresolved == ()
    assert report.cast_count == 1
    assert report.impact_observation_count == 1
    assert report.periodic_observation_count == 1
    assert report.cast_track_linked_impact_count == 1
    assert report.cast_track_linked_periodic_count == 4
    assert report.cast_to_impact_seconds == pytest.approx((0.15,))
    assert report.impact_to_first_periodic_seconds == pytest.approx((1.0,))
    assert report.periodic_intervals_seconds == pytest.approx((1.005, 0.995))
    assert report.median_cast_to_impact_seconds == pytest.approx(0.15)
    assert report.median_impact_to_first_periodic_seconds == pytest.approx(1.0)


def test_prefers_cast_track_linked_effect_rows(tmp_path) -> None:
    canonical = tmp_path / "canonical.db"
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(logs, 1, 1000, "cast", 39807, track=10, name="Stampede")
    _event(logs, 2, 1050, "damage", 38792, track=99)
    _event(logs, 3, 1200, "damage", 38792, track=10)
    _event(logs, 4, 1700, "damage", 126474, track=99)
    _event(logs, 5, 2200, "damage", 126474, track=10)
    _event(logs, 6, 3200, "damage", 126474, track=10)

    report = _service(canonical, logs).inspect(
        "stampede",
        impact_ability_id=38792,
        periodic_ability_id=126474,
        active_window_seconds=15.0,
    )

    assert report.cast_to_impact_seconds == pytest.approx((0.2,))
    assert report.impact_to_first_periodic_seconds == pytest.approx((1.0,))
    assert report.periodic_intervals_seconds == pytest.approx((1.0,))


def test_missing_effect_rows_fail_closed(tmp_path) -> None:
    canonical = tmp_path / "canonical.db"
    logs = tmp_path / "logs.db"
    _logs(logs)
    _event(logs, 1, 1000, "cast", 39807, track=10, name="Stampede")

    report = _service(canonical, logs).inspect(
        "stampede",
        impact_ability_id=38792,
        periodic_ability_id=126474,
        active_window_seconds=15.0,
    )

    assert report.impact_observation_count == 0
    assert report.periodic_observation_count == 0
    assert any("no impact ability 38792" in item for item in report.unresolved)
    assert any("no periodic ability 126474" in item for item in report.unresolved)
