from __future__ import annotations

import sqlite3
from pathlib import Path

from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_repository import RaidPlanRepository
from tools.restore_raid_plan_revision import find_recovery_candidate, restore_candidate


def _plan(*, aces_everywhere: bool) -> RaidPlan:
    members = [
        RaidPlanMember(seat_id="tank-1", gamertag="Rik", character_name="Rik Necro Tank"),
        RaidPlanMember(seat_id="tank-2", gamertag="Spithis", character_name="Spithis"),
    ]
    for index in range(1, 9):
        members.append(
            RaidPlanMember(
                seat_id=f"dd-{index}",
                gamertag="AAA Aces" if aces_everywhere or index == 1 else f"DD {index}",
                character_name="Aces" if aces_everywhere or index == 1 else f"Character {index}",
            )
        )
    return RaidPlan(
        plan_id="godslayer-performance-mode",
        trial_id="sunspire",
        name="Godslayer Performance Mode",
        team_name="Performance Mode",
        members=tuple(members),
    )


def test_restore_tool_finds_latest_revision_with_rik_tank_and_one_aces(tmp_path: Path) -> None:
    database = tmp_path / "foundrydock.db"
    repository = RaidPlanRepository(database)
    good = _plan(aces_everywhere=False)
    bad = _plan(aces_everywhere=True)

    repository.save(good)
    repository.save(bad)

    candidate = find_recovery_candidate(
        database,
        plan_hint="Performance Mode",
        tank_name="Rik",
        unique_player="Aces",
    )

    assert candidate is not None
    assert candidate.source == "revision"
    assert candidate.payload["members"][0]["gamertag"] == "Rik"
    assert sum(
        1
        for member in candidate.payload["members"]
        if "aces" in str(member.get("gamertag", "")).casefold()
    ) == 1


def test_restore_tool_restores_only_matching_raid_plan(tmp_path: Path) -> None:
    database = tmp_path / "foundrydock.db"
    repository = RaidPlanRepository(database)
    good = _plan(aces_everywhere=False)
    bad = _plan(aces_everywhere=True)
    repository.save(good)
    repository.save(bad)

    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE marker(value TEXT NOT NULL)")
        db.execute("INSERT INTO marker(value) VALUES ('keep me')")
        db.commit()

    candidate = find_recovery_candidate(
        database,
        plan_hint="Performance Mode",
        tank_name="Rik",
        unique_player="Aces",
    )
    assert candidate is not None

    restore_candidate(database, candidate)

    restored = repository.get(good.plan_id)
    assert restored == good
    with sqlite3.connect(database) as db:
        row = db.execute("SELECT value FROM marker").fetchone()
    assert row == ("keep me",)
