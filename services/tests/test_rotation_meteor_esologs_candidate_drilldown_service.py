from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.rotation_meteor_esologs_candidate_drilldown_service import (
    RotationMeteorEsoLogsCandidateDrilldownService,
)


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "logs.db"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE log_event (report_code TEXT, fight_id INTEGER, event_index INTEGER, "
        "timestamp REAL, event_type TEXT, source_id INTEGER, target_id INTEGER, "
        "ability_game_id INTEGER, cast_track_id INTEGER, raw_json TEXT)"
    )
    rows = [
        ("R", 1, 1, 1000, "cast", 7, 20, 500, 91, json.dumps({"ability": {"name": "Mystery Ultimate"}})),
        ("R", 1, 2, 1800, "damage", 7, 20, 121090, 91, "{}"),
        ("R", 1, 3, 2800, "damage", 7, 20, 121090, 91, "{}"),
        ("R", 1, 4, 3800, "damage", 7, 20, 121090, 91, "{}"),
        ("R", 1, 5, 4800, "damage", 7, 21, 121090, 91, "{}"),
        ("R", 1, 6, 9000, "cast", 7, 30, 600, 92, json.dumps({"ability": {"name": "Other Cast"}})),
        ("R", 1, 7, 9600, "damage", 7, 30, 121090, 92, "{}"),
        ("R", 1, 8, 10600, "damage", 7, 30, 121090, 92, "{}"),
        ("R", 1, 9, 11600, "damage", 7, 30, 121090, 92, "{}"),
    ]
    db.executemany("INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.commit()
    db.close()
    return path


def test_drilldown_segments_runs_and_links_prior_casts(tmp_path: Path) -> None:
    report = RotationMeteorEsoLogsCandidateDrilldownService(_database(tmp_path)).inspect(
        ability_ids=(121090,),
    )

    candidate = report.candidates[0]
    assert candidate.ability_game_id == 121090
    assert candidate.damage_event_count == 7
    assert candidate.run_count == 2
    assert candidate.source_actor_count == 1
    assert candidate.runs_with_prior_cast == 2
    assert candidate.runs_with_same_track_prior_cast == 2
    assert candidate.nearest_prior_cast_id_counts == ((500, 1), (600, 1))
    assert candidate.nearest_prior_cast_name_counts == (("Mystery Ultimate", 1), ("Other Cast", 1))

    first = candidate.runs[0]
    assert first.damage_event_count == 4
    assert first.distinct_target_count == 2
    assert first.median_interval_seconds == 1.0
    assert first.cast_track_ids == (91,)
    assert first.nearby_casts[0].ability_game_id == 500
    assert first.nearby_casts[0].ability_name == "Mystery Ultimate"
    assert first.nearby_casts[0].offset_seconds == 0.8
    assert first.nearby_casts[0].shares_damage_cast_track is True


def test_drilldown_reports_missing_candidate_without_inference(tmp_path: Path) -> None:
    report = RotationMeteorEsoLogsCandidateDrilldownService(_database(tmp_path)).inspect(
        ability_ids=(999999,),
    )

    assert report.candidates == ()
    assert report.unresolved == ("candidate 999999: no damage rows found",)
