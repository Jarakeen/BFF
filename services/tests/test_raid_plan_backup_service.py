from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_backup_service import (
    BACKUP_KIND,
    RaidPlanBackupError,
    export_raid_plan_backup,
    load_raid_plan_backup,
)
from services.raid_plan_repository import RaidPlanRepository


def _plan() -> RaidPlan:
    return RaidPlan(
        plan_id="sunspire-performance-mode-gs",
        trial_id="sunspire",
        name="Core Team",
        team_name="Performance Mode",
        difficulty="Hard Mode",
        plan_note="backup test",
        members=(
            RaidPlanMember(
                seat_id="tank-1",
                gamertag="Rik",
                character_name="Rik Tank",
                eso_class="Sorcerer",
                role="Tank",
            ),
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="AAA Aces",
                character_name="Aces",
                eso_class="Nightblade",
                role="DD",
            ),
        ),
    )


def test_raid_plan_backup_round_trips_exactly(tmp_path: Path) -> None:
    plan = _plan()
    path = export_raid_plan_backup(plan, tmp_path / "core-team.raidplan.json")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["kind"] == BACKUP_KIND
    assert payload["schema_version"] == 1
    assert payload["plan"]["plan_id"] == plan.plan_id
    assert load_raid_plan_backup(path) == plan


def test_raid_plan_backup_rejects_unrelated_json(tmp_path: Path) -> None:
    path = tmp_path / "not-a-backup.json"
    path.write_text('{"kind": "something_else"}', encoding="utf-8")

    with pytest.raises(RaidPlanBackupError):
        load_raid_plan_backup(path)


def test_restoring_backup_through_repository_changes_only_raid_plan(tmp_path: Path) -> None:
    database = tmp_path / "foundrydock.db"
    repository = RaidPlanRepository(database)
    bad = RaidPlan(
        plan_id="sunspire-performance-mode-gs",
        trial_id="sunspire",
        name="Core Team",
        members=(
            RaidPlanMember(seat_id="tank-1", gamertag="AAA Aces"),
            RaidPlanMember(seat_id="tank-2", gamertag="AAA Aces"),
        ),
    )
    repository.save(bad)

    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE marker(value TEXT NOT NULL)")
        db.execute("INSERT INTO marker(value) VALUES ('leave this alone')")
        db.commit()

    backup_path = export_raid_plan_backup(_plan(), tmp_path / "good.json")
    restored = load_raid_plan_backup(backup_path)
    repository.save(restored)

    assert repository.get(restored.plan_id) == restored
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT value FROM marker").fetchone() == ("leave this alone",)


def test_raid_plan_backup_accepts_early_phase14_safety_export(tmp_path: Path) -> None:
    plan = _plan()
    path = tmp_path / "raid-plan-sunspire-performance-mode-gs.json"
    path.write_text(
        json.dumps(
            {
                "payload": {
                    "kind": "raid_plan",
                    "plan": {
                        "plan_id": plan.plan_id,
                        "trial_id": plan.trial_id,
                        "name": plan.name,
                        "team_name": plan.team_name,
                        "difficulty": plan.difficulty,
                        "plan_note": plan.plan_note,
                        "status": plan.status,
                        "members": [
                            {
                                "seat_id": row.seat_id,
                                "gamertag": row.gamertag,
                                "character_name": row.character_name,
                                "eso_class": row.eso_class,
                                "role": row.role,
                            }
                            for row in plan.members
                        ],
                        "triggered_responsibilities": [],
                    },
                },
                "saved_at": "2026-09-25T01:55:17+00:00",
            }
        ),
        encoding="utf-8",
    )

    restored = load_raid_plan_backup(path)

    assert restored.plan_id == plan.plan_id
    assert restored.team_name == "Performance Mode"
    assert tuple(member.gamertag for member in restored.members) == ("Rik", "AAA Aces")
