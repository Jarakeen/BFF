from __future__ import annotations

import json
import sqlite3
import pytest

from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_repository import RaidPlanConflictError, RaidPlanRepository


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


def test_stale_screen_cannot_replace_newer_plan_and_noop_creates_no_revision(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "foundrydock.db")
    original = RaidPlan(plan_id="shared", trial_id="sunspire", name="First")
    newer = RaidPlan(plan_id="shared", trial_id="sunspire", name="Second")
    stale = RaidPlan(plan_id="shared", trial_id="sunspire", name="Stale")
    repository.save(original)
    repository.save(newer, expected=original)

    with pytest.raises(RaidPlanConflictError, match="another screen"):
        repository.save(stale, expected=original)
    assert repository.get("shared") == newer
    repository.save(newer, expected=newer)
    with sqlite3.connect(repository.path) as db:
        count = db.execute("SELECT COUNT(*) FROM raid_plan_revision").fetchone()[0]
    assert count == 1

    with pytest.raises(RaidPlanConflictError, match="already exists"):
        repository.save(original, must_be_new=True)
    assert repository.get("shared") == newer
