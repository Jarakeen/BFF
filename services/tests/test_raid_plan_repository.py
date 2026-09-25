import json

import pytest

from models.raid_plan import (
    RaidPlan,
    RaidPlanCoverageProvider,
    RaidPlanMember,
    RaidPlanTriggeredResponsibility,
)
from services.raid_plan_repository import (
    RaidPlanRepository, RaidPlanRepositoryError, duplicate_occupied_player_seats,
)


def test_duplicate_occupied_players_are_detected_without_counting_open_chairs() -> None:
    plan = RaidPlan(
        plan_id="sunspire-team", trial_id="sunspire", name="Team",
        members=(
            RaidPlanMember(seat_id="tank-1", gamertag="AAA Aces", player_id="aces"),
            RaidPlanMember(seat_id="healer-1", gamertag="AAA Aces", player_id="aces"),
            RaidPlanMember(seat_id="dd-1", gamertag="Recruit"),
            RaidPlanMember(seat_id="dd-2", gamertag="Recruit"),
        ),
    )

    assert duplicate_occupied_player_seats(plan) == ("aaa aces: tank-1, healer-1",)


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
                assignment_source="WW",
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
    assert restored.member("healer-1").assignment_source == "WW"
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


def test_repository_round_trips_sqlite_user_database(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "foundrydock.db")
    plan = _plan()

    repository.save(plan)

    restored = repository.get(plan.plan_id)
    assert restored == plan
    assert repository.list_plans() == (plan,)

    replacement = _plan(name="Performance Mode — Rockgrove Revised")
    repository.save(replacement)
    assert repository.list_plans() == (replacement,)

    assert repository.delete(plan.plan_id) is True
    assert repository.get(plan.plan_id) is None


def test_repository_pydantic_round_trips_explained_manual_coverage(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "foundrydock.db")
    plan = _plan()
    plan = plan.with_coverage_provider(
        RaidPlanCoverageProvider(
            effect_name="Minor Berserk",
            seat_id="healer-1",
            source="Combat Prayer",
            note="Raid lead assigned; verify uptime on review.",
        )
    )

    repository.save(plan)
    restored = repository.get(plan.plan_id)

    assert restored == plan
    provider = restored.coverage_for("Minor Berserk")[0]
    assert provider.source == "Combat Prayer"
    assert provider.note == "Raid lead assigned; verify uptime on review."


def test_repository_pydantic_rejects_blank_manual_coverage_source(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "foundrydock.db")
    raw = {
        "plan_id": "bad-coverage",
        "trial_id": "sunspire",
        "name": "Bad Coverage",
        "members": [{"seat_id": "healer-1", "gamertag": "Jarakeen"}],
        "triggered_responsibilities": [],
        "coverage_providers": [{
            "effect_name": "Minor Berserk",
            "seat_id": "healer-1",
            "source": "   ",
            "note": "vibes require at least a label",
        }],
    }
    with repository._connect() as db:
        db.execute(
            "INSERT INTO raid_plan(plan_id, payload_json) VALUES (?, ?)",
            ("bad-coverage", json.dumps(raw)),
        )

    with pytest.raises(RaidPlanRepositoryError, match="source"):
        repository.get("bad-coverage")


def test_repository_pydantic_rejects_unknown_manual_coverage_seat(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "foundrydock.db")
    raw = {
        "plan_id": "bad-seat",
        "trial_id": "sunspire",
        "name": "Bad Seat",
        "members": [{"seat_id": "healer-1", "gamertag": "Jarakeen"}],
        "triggered_responsibilities": [],
        "coverage_providers": [{
            "effect_name": "Minor Berserk",
            "seat_id": "dd-99",
            "source": "vibes",
        }],
    }
    with repository._connect() as db:
        db.execute(
            "INSERT INTO raid_plan(plan_id, payload_json) VALUES (?, ?)",
            ("bad-seat", json.dumps(raw)),
        )

    with pytest.raises(RaidPlanRepositoryError, match="unknown seat_id"):
        repository.get("bad-seat")


def test_repository_pydantic_rejects_extra_manual_coverage_fields(tmp_path) -> None:
    repository = RaidPlanRepository(tmp_path / "foundrydock.db")
    raw = {
        "plan_id": "extra-field",
        "trial_id": "sunspire",
        "name": "Extra Field",
        "members": [{"seat_id": "healer-1", "gamertag": "Jarakeen"}],
        "triggered_responsibilities": [],
        "coverage_providers": [{
            "effect_name": "Minor Berserk",
            "seat_id": "healer-1",
            "source": "Combat Prayer",
            "surprise": "silently accepting schema drift is how civilization ends",
        }],
    }
    with repository._connect() as db:
        db.execute(
            "INSERT INTO raid_plan(plan_id, payload_json) VALUES (?, ?)",
            ("extra-field", json.dumps(raw)),
        )

    with pytest.raises(RaidPlanRepositoryError, match="surprise"):
        repository.get("extra-field")
