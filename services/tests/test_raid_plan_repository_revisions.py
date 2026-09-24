from __future__ import annotations

import json
import sqlite3

from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_repository import RaidPlanRepository


def test_database_save_keeps_previous_verified_plan_revision(tmp_path) -> None:
    path = tmp_path / "foundrydock.db"
    repository = RaidPlanRepository(path)

    first = RaidPlan(
        plan_id="shared-copy",
        trial_id="sunspire",
        name="Shared Copy",
        members=(
            RaidPlanMember(
                seat_id="tank-1",
                gamertag="Tank",
                eso_class="Dragonknight",
                primary_assignment="Major Breach",
            ),
        ),
    )
    second = RaidPlan(
        plan_id="shared-copy",
        trial_id="sunspire",
        name="Shared Copy",
        members=(
            RaidPlanMember(
                seat_id="tank-1",
                gamertag="Tank",
                eso_class="Dragonknight",
                primary_assignment="Major Vulnerability",
            ),
        ),
    )

    repository.save(first)
    repository.save(second)

    assert repository.get("shared-copy") == second
    with sqlite3.connect(path) as db:
        row = db.execute(
            """
            SELECT payload_json
            FROM raid_plan_revision
            WHERE plan_id = ?
            ORDER BY revision_id DESC
            LIMIT 1
            """,
            ("shared-copy",),
        ).fetchone()
    assert row is not None
    payload = json.loads(row[0])
    assert payload["members"][0]["primary_assignment"] == "Major Breach"
