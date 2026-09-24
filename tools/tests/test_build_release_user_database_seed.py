from __future__ import annotations

import json
import sqlite3

from tools.build_release_user_database_seed import (
    PLAN_ID,
    PLAN_NAME,
    TEAM_NAME,
    create_seed,
)


def test_release_user_seed_populates_raid_planning_surfaces(tmp_path) -> None:
    path = create_seed(tmp_path / "foundrydock.db")

    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM roster_member").fetchone()[0] == 12
        assert db.execute("SELECT COUNT(*) FROM team").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM team_member").fetchone()[0] == 12
        assert db.execute("SELECT COUNT(*) FROM roster_member_assignment").fetchone()[0] == 12

        team = db.execute("SELECT name FROM team").fetchone()[0]
        assert team == TEAM_NAME

        row = db.execute(
            "SELECT payload_json FROM raid_plan WHERE plan_id = ?",
            (PLAN_ID,),
        ).fetchone()
        assert row is not None
        plan = json.loads(row[0])
        assert plan["name"] == PLAN_NAME
        assert plan["team_name"] == TEAM_NAME
        assert len(plan["members"]) == 12
        assert any(member["primary_assignment"] == "Major Courage" for member in plan["members"])
        assert any("Roaring Opportunist" in member["planned_gear_sets"] for member in plan["members"])

        catalog_row = db.execute(
            "SELECT payload_json FROM build_catalog WHERE singleton_id = 1"
        ).fetchone()
        assert catalog_row is not None
        catalog = json.loads(catalog_row[0])
        assert len(catalog["players"]) == 12
        assert len(catalog["characters"]) == 12
        assert len(catalog["builds"]) == 12
