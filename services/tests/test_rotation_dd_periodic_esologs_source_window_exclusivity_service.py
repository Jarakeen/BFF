import json
import sqlite3
from types import SimpleNamespace

import pytest

from services.rotation_dd_periodic_esologs_source_window_exclusivity_service import (
    RotationDDPeriodicEsoLogsSourceWindowExclusivityService,
)


class _Coefficients:
    def resolve_entity_id(self, entity_id):
        assert entity_id == "skeletal_archer"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_id=8, morph=1, base_ability_id=500),
            unresolved=(),
        )


def _canonical(path):
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, skill_id INTEGER, ability_id INTEGER, morph INTEGER)"
        )
        db.execute("INSERT INTO skill_rank VALUES (1,8,500,1)")
        db.commit()


def _logs(path):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT, fight_id INTEGER, event_index INTEGER,
                timestamp REAL, event_type TEXT, source_id INTEGER,
                ability_game_id INTEGER, raw_json TEXT
            )
            """
        )
        db.commit()


def _event(path, *, index, timestamp, event_type, source_id, ability_id, name=""):
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?)",
            (
                "R", 1, index, timestamp, event_type, source_id, ability_id,
                json.dumps({"ability": {"name": name}}) if name else "{}",
            ),
        )
        db.commit()


def _service(canonical, logs):
    service = RotationDDPeriodicEsoLogsSourceWindowExclusivityService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )
    service.coefficients = _Coefficients()
    return service


def test_exposure_normalized_rates_distinguish_active_window_concentration(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=0, event_type="damage", source_id=1, ability_id=999)
    _event(logs, index=2, timestamp=10000, event_type="cast", source_id=1, ability_id=500, name="Skeletal Archer")
    _event(logs, index=3, timestamp=12000, event_type="damage", source_id=1, ability_id=21929)
    _event(logs, index=4, timestamp=14000, event_type="damage", source_id=1, ability_id=21929)
    _event(logs, index=5, timestamp=16000, event_type="damage", source_id=1, ability_id=21929)
    _event(logs, index=6, timestamp=50000, event_type="damage", source_id=1, ability_id=21929)
    _event(logs, index=7, timestamp=60000, event_type="damage", source_id=1, ability_id=999)

    report = _service(canonical, logs).inspect(
        "skeletal_archer",
        candidate_ability_id=21929,
        active_window_seconds=10.0,
    )

    assert report.cast_count == 1
    assert report.caster_source_groups == 1
    assert report.active_exposure_seconds == pytest.approx(10.0)
    assert report.inactive_exposure_seconds == pytest.approx(50.0)
    assert report.candidate_events_inside_windows == 3
    assert report.candidate_events_outside_windows == 1
    assert report.inside_rate_per_minute == pytest.approx(18.0)
    assert report.outside_rate_per_minute == pytest.approx(1.2)
    assert report.inside_outside_rate_ratio == pytest.approx(15.0)
    assert report.unresolved == ()


def test_merges_recast_windows_and_reports_candidate_on_noncaster_groups(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=0, event_type="damage", source_id=1, ability_id=999)
    _event(logs, index=2, timestamp=1000, event_type="cast", source_id=1, ability_id=500, name="Skeletal Archer")
    _event(logs, index=3, timestamp=10000, event_type="cast", source_id=1, ability_id=500, name="Skeletal Archer")
    _event(logs, index=4, timestamp=5000, event_type="damage", source_id=1, ability_id=21929)
    _event(logs, index=5, timestamp=25000, event_type="damage", source_id=1, ability_id=21929)
    _event(logs, index=6, timestamp=30000, event_type="damage", source_id=1, ability_id=999)

    _event(logs, index=7, timestamp=0, event_type="damage", source_id=2, ability_id=999)
    _event(logs, index=8, timestamp=7000, event_type="damage", source_id=2, ability_id=21929)
    _event(logs, index=9, timestamp=30000, event_type="damage", source_id=2, ability_id=999)

    report = _service(canonical, logs).inspect(
        "skeletal_archer",
        candidate_ability_id=21929,
        active_window_seconds=10.0,
    )

    # [1s,11s] and [10s,20s] merge into one 19-second exposure.
    assert report.cast_count == 2
    assert report.active_exposure_seconds == pytest.approx(19.0)
    assert report.inactive_exposure_seconds == pytest.approx(11.0)
    assert report.candidate_events_inside_windows == 1
    assert report.candidate_events_outside_windows == 1
    assert report.noncaster_source_groups_with_candidate == 1
    assert report.noncaster_candidate_events == 1


def test_no_matching_casts_fail_closed(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)
    _event(logs, index=1, timestamp=1000, event_type="damage", source_id=1, ability_id=21929)

    report = _service(canonical, logs).inspect(
        "skeletal_archer",
        candidate_ability_id=21929,
        active_window_seconds=20.0,
    )

    assert report.cast_count == 0
    assert report.candidate_events_inside_windows == 0
    assert any("no matching cast observations" in message for message in report.unresolved)
