from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.rotation_unnerving_boneyard_refresh_anomaly_service import (
    RotationUnnervingBoneyardRefreshAnomalyService,
)


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "logs.db"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE log_event (report_code TEXT,fight_id INTEGER,event_index INTEGER,"
            "timestamp REAL,event_type TEXT,source_id INTEGER,ability_game_id INTEGER,"
            "cast_track_id INTEGER,raw_json TEXT)"
        )
    return path


def _event(path: Path, index: int, ts: float, kind: str, ability: int, track: int, name: str | None = None) -> None:
    raw = json.dumps({"ability": {"name": name}}) if name else "{}"
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?)",
            ("R", 1, index, ts, kind, 7, ability, track, raw),
        )


def test_reports_old_event_between_recast_and_first_new_event(tmp_path: Path) -> None:
    path = _db(tmp_path)
    _event(path, 1, 1000, "cast", 1, 10, "Unnerving Boneyard")
    _event(path, 2, 9000, "damage", 117809, 10)
    _event(path, 3, 10000, "cast", 1, 20, "Unnerving Boneyard")
    _event(path, 4, 10100, "damage", 117809, 10)
    _event(path, 5, 10350, "damage", 117809, 20)

    report = RotationUnnervingBoneyardRefreshAnomalyService(path).inspect_anomalies()

    assert len(report.anomalies) == 1
    item = report.anomalies[0]
    assert item.old_event_after_new_cast_seconds == 0.1
    assert item.old_event_before_first_new_seconds == 0.25
