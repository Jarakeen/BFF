from __future__ import annotations

from pathlib import Path
import sqlite3

from services.rotation_unnerving_boneyard_cadence_stability_service import (
    RotationUnnervingBoneyardCadenceStabilityService,
)


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "logs.db"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE log_event (report_code TEXT, fight_id INTEGER, event_index INTEGER, "
        "timestamp REAL, event_type TEXT, source_id INTEGER, ability_game_id INTEGER, "
        "cast_track_id INTEGER)"
    )
    db.commit()
    db.close()
    return path


def _event(path: Path, index: int, timestamp: float, track: int) -> None:
    db = sqlite3.connect(path)
    db.execute(
        "INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("R", 1, index, timestamp, "damage", 7, 117809, track),
    )
    db.commit()
    db.close()


def test_collapses_near_duplicate_rows_before_measuring_cadence(tmp_path: Path) -> None:
    path = _database(tmp_path)
    for index, timestamp in enumerate((1000, 1001, 2000, 2002, 3001), start=1):
        _event(path, index, timestamp, 10)

    report = RotationUnnervingBoneyardCadenceStabilityService(path).inspect()

    assert report.track_count == 1
    assert report.occurrence_count == 3
    assert report.interval_count == 2
    assert 0.99 <= report.median_interval_seconds <= 1.01
    assert report.near_one_second_count == 2
    assert report.near_one_second_fraction == 1.0


def test_keeps_large_gap_as_real_interval(tmp_path: Path) -> None:
    path = _database(tmp_path)
    for index, timestamp in enumerate((1000, 2000, 5000), start=1):
        _event(path, index, timestamp, 10)

    report = RotationUnnervingBoneyardCadenceStabilityService(path).inspect()

    assert report.interval_count == 2
    assert report.maximum_interval_seconds == 3.0
    assert report.near_one_second_count == 1


def test_fails_closed_without_intervals(tmp_path: Path) -> None:
    path = _database(tmp_path)
    _event(path, 1, 1000, 10)

    report = RotationUnnervingBoneyardCadenceStabilityService(path).inspect()

    assert report.interval_count == 0
    assert report.unresolved
