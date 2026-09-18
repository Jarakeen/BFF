import json

import pytest

from models.raid_plan import (
    RaidPlan,
    RaidPlanMember,
    RaidPlanTriggeredResponsibility,
)
from services.raid_plan_repository import RaidPlanRepository, RaidPlanRepositoryError


def _plan(*, plan_id: str = "performance-mode-rockgrove", name: str = "Performance Mode — Rockgrove") -> RaidPlan:
    return RaidPlan(
        plan_id=plan_id,
        trial_id="rockgrove",
        name=name,
        team_name="Performance Mode",
        difficulty="Veteran Hardmode",
        plan_note="Keep portal group stacked after transition.",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                roster_member_id=7,
                character_name="Magrat",
                role="Healer",
                eso_class="Warden",
                selected_build_id="df-healer-build-id",
                selected_build_name="DF Healer",
                primary_assignment="Group Healer",
                notes="Top-left pool",
            ),
            RaidPlanMember(seat_id="dd-1", gamertag="FriendName"),
        ),
        triggered_responsibilities=(
            RaidPlanTriggeredResponsibility(
                responsibility_id="xalvakka-healer-portal",
                seat_id="healer-1",
                encounter_id="xalvakka-hm",
                trigger_key="portal_active",
                directive="Cover portal group",
                source="reviewed raid plan",
            ),
        ),
    )


def test_repository_round_trips_complete_plan_snapshot(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "raid_plans.json")
    plan = _plan()

    repository.save(plan)

    restored = repository.get(plan.plan_id)
    assert restored == plan
    assert restored.member("healer-1").selected_build_id == "df-healer-build-id"
    assert restored.plan_note == "Keep portal group stacked after transition."
    assert repository.list_plans() == (plan,)


def test_repository_reads_legacy_plan_without_selected_build_id(tmp_path) -> None:
    path = tmp_path / "raid_plans.json"
    payload = {
        "schema_version": 1,
        "plans": [
            {
                "plan_id": "legacy-plan",
                "trial_id": "rockgrove",
                "name": "Legacy Plan",
                "members": [
                    {
                        "seat_id": "healer-1",
                        "gamertag": "Jarakeen",
                        "character_name": "Magrat",
                        "selected_build_name": "DF Healer",
                    }
                ],
                "triggered_responsibilities": [],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    plan = RaidPlanRepository(path).get("legacy-plan")

    assert plan is not None
    member = plan.member("healer-1")
    assert member is not None
    assert member.selected_build_id is None
    assert member.selected_build_name == "DF Healer"
    assert member.build_selected is True


def test_save_replaces_same_plan_id_without_duplicating(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "raid_plans.json")
    repository.save(_plan())
    replacement = _plan(name="Performance Mode — Rockgrove Revised")

    repository.save(replacement)

    assert repository.list_plans() == (replacement,)


def test_repository_supports_multiple_trial_plans(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "raid_plans.json")
    rockgrove = _plan()
    dreadsail = RaidPlan(
        plan_id="performance-mode-dreadsail",
        trial_id="dreadsail-reef",
        name="Performance Mode — Dreadsail",
        team_name="Performance Mode",
        members=(RaidPlanMember(seat_id="healer-1", gamertag="Jarakeen", character_name="Magrat"),),
    )

    repository.save(rockgrove)
    repository.save(dreadsail)

    assert {plan.plan_id for plan in repository.list_plans()} == {
        "performance-mode-rockgrove",
        "performance-mode-dreadsail",
    }


def test_delete_removes_only_requested_plan(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "raid_plans.json")
    first = _plan()
    second = _plan(plan_id="other-plan", name="Other Plan")
    repository.save(first)
    repository.save(second)

    assert repository.delete(first.plan_id) is True
    assert repository.get(first.plan_id) is None
    assert repository.get(second.plan_id) == second
    assert repository.delete("missing") is False


def test_repository_fails_closed_on_unknown_schema(tmp_path) -> None:
    path = tmp_path / "raid_plans.json"
    path.write_text(json.dumps({"schema_version": 99, "plans": []}), encoding="utf-8")

    with pytest.raises(RaidPlanRepositoryError, match="unsupported"):
        RaidPlanRepository(path).list_plans()


def test_repository_round_trips_playerless_class_planning_chair(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "raid_plans.json")
    plan = RaidPlan(
        plan_id="class-only",
        trial_id="rockgrove",
        name="Class Only",
        members=(
            RaidPlanMember(
                seat_id="tank-1",
                gamertag="",
                role="Tank",
                eso_class="Dragonknight",
            ),
        ),
    )

    repository.save(plan)
    restored = repository.get("class-only")

    assert restored == plan
    assert restored.member("tank-1").gamertag == ""
    assert restored.member("tank-1").eso_class == "Dragonknight"


def test_repository_migrates_legacy_main_off_tank_seat_ids(tmp_path) -> None:
    path = tmp_path / "raid_plans.json"
    payload = {
        "schema_version": 1,
        "plans": [
            {
                "plan_id": "legacy-tanks",
                "trial_id": "rockgrove",
                "name": "Legacy Tanks",
                "members": [
                    {"seat_id": "main-tank", "gamertag": "", "role": "Tank", "eso_class": "Dragonknight"},
                    {"seat_id": "off-tank", "gamertag": "Friend", "role": "Tank", "eso_class": "Necromancer"},
                ],
                "triggered_responsibilities": [],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    plan = RaidPlanRepository(path).get("legacy-tanks")

    assert plan is not None
    assert plan.member("tank-1").eso_class == "Dragonknight"
    assert plan.member("tank-2").gamertag == "Friend"
