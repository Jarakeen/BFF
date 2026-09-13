from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.rotation_meteor_esologs_timing_signature_candidate_service import (
    RotationMeteorEsoLogsTimingSignatureCandidateService,
)


def _db(path: Path) -> Path:
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE log_event ("
            "report_code TEXT, fight_id INTEGER, event_index INTEGER, timestamp REAL, "
            "event_type TEXT, source_id INTEGER, ability_game_id INTEGER, raw_json TEXT)"
        )
    return path


def _event(path: Path, *, index: int, timestamp: float, ability_id: int, name: str, source_id: int = 7) -> None:
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?)",
            (
                "R",
                1,
                index,
                timestamp,
                "damage",
                source_id,
                ability_id,
                json.dumps({"ability": {"name": name}}),
            ),
        )


def test_finds_repeating_one_second_stream_inside_eleven_second_window(tmp_path: Path) -> None:
    logs = _db(tmp_path / "logs.db")
    for i, timestamp in enumerate((1000, 2000, 3000, 4000, 5000), start=1):
        _event(logs, index=i, timestamp=timestamp, ability_id=9001, name="Unknown Ultimate Dot")

    report = RotationMeteorEsoLogsTimingSignatureCandidateService(logs).inspect()

    assert len(report.candidates) == 1
    candidate = report.candidates[0]
    assert candidate.ability_game_id == 9001
    assert candidate.ability_names == ("Unknown Ultimate Dot",)
    assert candidate.one_second_interval_matches == 4
    assert candidate.median_interval_seconds == 1.0
    assert candidate.median_run_span_seconds == 4.0
    assert not report.unresolved


def test_rejects_long_running_one_second_stream(tmp_path: Path) -> None:
    logs = _db(tmp_path / "logs.db")
    for i in range(14):
        _event(logs, index=i + 1, timestamp=1000 + i * 1000, ability_id=42, name="Long Dot")

    report = RotationMeteorEsoLogsTimingSignatureCandidateService(logs).inspect()

    assert report.candidates == ()
    assert report.unresolved


def test_rejects_stream_without_enough_one_second_matches(tmp_path: Path) -> None:
    logs = _db(tmp_path / "logs.db")
    for i, timestamp in enumerate((1000, 2600, 4200, 5800), start=1):
        _event(logs, index=i, timestamp=timestamp, ability_id=77, name="Slow Dot")

    report = RotationMeteorEsoLogsTimingSignatureCandidateService(logs).inspect()

    assert report.candidates == ()
