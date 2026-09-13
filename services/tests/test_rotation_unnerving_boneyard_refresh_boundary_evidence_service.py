from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.rotation_unnerving_boneyard_refresh_boundary_evidence_service import (
    RotationUnnervingBoneyardRefreshBoundaryEvidenceService,
)


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "logs.db"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE log_event ("
        "report_code TEXT, fight_id INTEGER, event_index INTEGER, timestamp REAL, "
        "event_type TEXT, source_id INTEGER, ability_game_id INTEGER, cast_track_id INTEGER, raw_json TEXT)"
    )
    db.commit()
    db.close()
    return path


def _event(
    path: Path,
    *,
    index: int,
    timestamp: float,
    event_type: str,
    ability_id: int,
    track: int,
    name: str | None = None,
) -> None:
    raw = json.dumps({"ability": {"name": name}}) if name else "{}"
    db = sqlite3.connect(path)
    db.execute(
        "INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("R", 1, index, timestamp, event_type, 7, ability_id, track, raw),
    )
    db.commit()
    db.close()


def test_reports_cast_time_replacement_when_old_track_stops_before_recast(tmp_path: Path) -> None:
    path = _database(tmp_path)
    _event(path, index=1, timestamp=1000, event_type="cast", ability_id=1, track=10, name="Unnerving Boneyard")
    _event(path, index=2, timestamp=1300, event_type="damage", ability_id=117809, track=10)
    _event(path, index=3, timestamp=9000, event_type="damage", ability_id=117809, track=10)
    _event(path, index=4, timestamp=10000, event_type="cast", ability_id=1, track=20, name="Unnerving Boneyard")
    _event(path, index=5, timestamp=10350, event_type="damage", ability_id=117809, track=20)

    report = RotationUnnervingBoneyardRefreshBoundaryEvidenceService(path).inspect()

    assert report.consecutive_pairs == 1
    assert report.comparable_pairs == 1
    assert report.pairs_with_old_event_after_new_cast == 0
    assert report.pairs_with_old_event_at_or_after_first_new_event == 0
    assert report.median_last_old_before_new_cast_seconds == 1.0
    assert report.median_first_new_after_new_cast_seconds == 0.35


def test_distinguishes_old_tick_after_recast_from_first_new_event_boundary(tmp_path: Path) -> None:
    path = _database(tmp_path)
    _event(path, index=1, timestamp=1000, event_type="cast", ability_id=1, track=10, name="Unnerving Boneyard")
    _event(path, index=2, timestamp=9500, event_type="damage", ability_id=117809, track=10)
    _event(path, index=3, timestamp=10000, event_type="cast", ability_id=1, track=20, name="Unnerving Boneyard")
    _event(path, index=4, timestamp=10100, event_type="damage", ability_id=117809, track=10)
    _event(path, index=5, timestamp=10400, event_type="damage", ability_id=117809, track=20)

    report = RotationUnnervingBoneyardRefreshBoundaryEvidenceService(path).inspect()

    assert report.pairs_with_old_event_after_new_cast == 1
    assert report.pairs_with_old_event_at_or_after_first_new_event == 0


def test_exact_timestamp_old_event_is_reported_separately(tmp_path: Path) -> None:
    path = _database(tmp_path)
    _event(path, index=1, timestamp=1000, event_type="cast", ability_id=1, track=10, name="Unnerving Boneyard")
    _event(path, index=2, timestamp=9000, event_type="damage", ability_id=117809, track=10)
    _event(path, index=4, timestamp=10000, event_type="cast", ability_id=1, track=20, name="Unnerving Boneyard")
    _event(path, index=3, timestamp=10000, event_type="damage", ability_id=117809, track=10)
    _event(path, index=5, timestamp=10350, event_type="damage", ability_id=117809, track=20)

    report = RotationUnnervingBoneyardRefreshBoundaryEvidenceService(path).inspect()

    assert report.pairs_with_old_event_at_new_cast == 1
    assert report.exact_timestamp_old_events_at_new_cast == 1


def test_numeric_alias_matches_cast_when_raw_name_is_missing(tmp_path: Path) -> None:
    path = _database(tmp_path)
    _event(path, index=1, timestamp=1000, event_type="cast", ability_id=115252, track=10)
    _event(path, index=2, timestamp=1300, event_type="damage", ability_id=117809, track=10)
    _event(path, index=3, timestamp=9000, event_type="damage", ability_id=117809, track=10)
    _event(path, index=4, timestamp=10000, event_type="cast", ability_id=115252, track=20)
    _event(path, index=5, timestamp=10350, event_type="damage", ability_id=117809, track=20)

    service = RotationUnnervingBoneyardRefreshBoundaryEvidenceService(path)
    service._cast_aliases = lambda: {115252}  # type: ignore[method-assign]
    report = service.inspect()

    assert report.consecutive_pairs == 1
    assert report.comparable_pairs == 1


def test_fails_closed_without_comparable_pairs(tmp_path: Path) -> None:
    path = _database(tmp_path)
    _event(path, index=1, timestamp=1000, event_type="cast", ability_id=1, track=10, name="Unnerving Boneyard")
    _event(path, index=2, timestamp=10000, event_type="cast", ability_id=1, track=20, name="Unnerving Boneyard")

    report = RotationUnnervingBoneyardRefreshBoundaryEvidenceService(path).inspect()

    assert report.comparable_pairs == 0
    assert report.unresolved
