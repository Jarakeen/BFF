from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools.build_custom_raid_plan_catalog_seed import build_plan_catalog


def test_plan_catalog_seed_keeps_only_referenced_builds(tmp_path: Path) -> None:
    source = tmp_path / "characters.json"
    seed_db = tmp_path / "foundrydock.db"
    output = tmp_path / "seed-characters.json"

    source.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "players": [
                    {"player_id": "p1", "gamertag": "Rikbacon"},
                    {"player_id": "p2", "gamertag": "SomeoneElse"},
                ],
                "characters": [
                    {"character_id": "c1", "player_id": "p1", "name": "Tanky", "gamertag": "Rikbacon"},
                    {"character_id": "c2", "player_id": "p2", "name": "Other", "gamertag": "SomeoneElse"},
                ],
                "builds": [
                    {"build_id": "b1", "character_id": "c1", "name": "MT", "payload": {"BuildName": "MT"}},
                    {"build_id": "b2", "character_id": "c2", "name": "Other", "payload": {"BuildName": "Other"}},
                ],
                "team_assignments": [
                    {"assignment_id": "a1", "team_name": "Performance Mode", "build_id": "b1"},
                    {"assignment_id": "a2", "team_name": "Other Team", "build_id": "b2"},
                ],
            }
        ),
        encoding="utf-8",
    )

    db = sqlite3.connect(seed_db)
    try:
        db.execute(
            """
            CREATE TABLE raid_plan (
                plan_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.execute(
            "INSERT INTO raid_plan(plan_id, payload_json) VALUES (?, ?)",
            (
                "pm-rg",
                json.dumps(
                    {
                        "plan_id": "pm-rg",
                        "trial_id": "rockgrove",
                        "name": "PM RG",
                        "members": [
                            {
                                "seat_id": "tank-1",
                                "gamertag": "Rikbacon",
                                "player_id": "p1",
                                "character_id": "c1",
                                "selected_build_id": "b1",
                                "selected_build_name": "MT",
                            }
                        ],
                    }
                ),
            ),
        )
        db.commit()
    finally:
        db.close()

    counts = build_plan_catalog(source, seed_db, output, plan_id="pm-rg")

    assert counts == {
        "players": 1,
        "characters": 1,
        "builds": 1,
        "team_assignments": 1,
    }
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert [row["player_id"] for row in payload["players"]] == ["p1"]
    assert [row["character_id"] for row in payload["characters"]] == ["c1"]
    assert [row["build_id"] for row in payload["builds"]] == ["b1"]
    assert [row["build_id"] for row in payload["team_assignments"]] == ["b1"]
