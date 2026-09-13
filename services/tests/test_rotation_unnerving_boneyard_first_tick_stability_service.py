from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.rotation_unnerving_boneyard_first_tick_stability_service import (
    RotationUnnervingBoneyardFirstTickStabilityService,
)


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "logs.db"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE log_event (report_code TEXT,fight_id INTEGER,event_index INTEGER,"
        "timestamp REAL,event_type TEXT,source_id INTEGER,ability_game_id INTEGER,"
        "cast_track_id INTEGER,raw_json TEXT)"
    )
    db.commit()
    db.close()
    return path


def _event(path: Path, *, index: int, timestamp: float, event_type: str, ability_id: int, track: int, name: str | None = None) -> None:
    raw = json.dumps({"ability": {"name": name}}) if name else "{}"
    db = sqlite3.connect(path)
    db.execute(
        "INSERT INTO log_event VALUES ('R',1,?,?,?,?,?,?,?)",
        (index, timestamp, event_type, 7, ability_id, track, raw),
    )
    db.commit()
    db.close()


def test_reports_first_tick_distribution_by_cast_track(tmp_path: Path) -> None:
    path = _db(tmp_path)
    for n, offset in enumerate((300.0, 350.0, 400.0), start=0):
        base = 1000.0 + n * 2000.0
        track = 10 + n
        _event(path, index=n * 2 + 1, timestamp=base, event_type="cast", ability_id=1, track=track, name="Unnerving Boneyard")
        _event(path, index=n * 2 + 2, timestamp=base + offset, event_type="damage", ability_id=117809, track=track)

    report = RotationUnnervingBoneyardFirstTickStabilityService(path).inspect()

    assert report.sample_count == 3
    assert report.median_offset_seconds == 0.35
    assert report.minimum_offset_seconds == 0.3
    assert report.maximum_offset_seconds == 0.4
    assert len(report.groups) == 1
    assert report.groups[0].sample_count == 3


def test_ignores_damage_without_matching_cast_track(tmp_path: Path) -> None:
    path = _db(tmp_path)
    _event(path, index=1, timestamp=1000, event_type="cast", ability_id=1, track=10, name="Unnerving Boneyard")
    _event(path, index=2, timestamp=1350, event_type="damage", ability_id=117809, track=99)

    report = RotationUnnervingBoneyardFirstTickStabilityService(path).inspect()

    assert report.sample_count == 0
    assert report.unresolved
