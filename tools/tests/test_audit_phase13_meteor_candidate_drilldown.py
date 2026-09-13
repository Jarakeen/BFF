from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from tools.audit_phase13_meteor_candidate_drilldown import audit


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
        ("R", 1, 5, 4800, "damage", 7, 20, 121090, 91, "{}"),
    ]
    db.executemany("INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    db.commit()
    db.close()
    return path


def test_audit_prints_candidate_topology(tmp_path: Path, capsys) -> None:
    result = audit(_database(tmp_path), ability_ids=(121090,))
    text = capsys.readouterr().out

    assert result == 0
    assert "Candidate 121090" in text
    assert "segmented runs: 1" in text
    assert "runs with same-track prior cast: 1/1" in text
    assert "Mystery Ultimate" in text
    assert "occurrence counts from the anonymous scanner were timestamps, not cast counts" in text
