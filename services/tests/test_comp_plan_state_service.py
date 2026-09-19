from dataclasses import replace

from models.comp_plan_state import CompChairState
from models.raid_plan import (
    RaidPlan,
    RaidPlanMember,
    RaidPlanTriggeredResponsibility,
)
from services.comp_plan_state_service import CompPlanStateService
from services.raid_plan_repository import RaidPlanRepository


def _plan() -> RaidPlan:
    return RaidPlan(
        plan_id="pm-gs",
        trial_id="sunspire",
        name="Performance Mode GS",
        team_name="Performance Mode",
        difficulty="Veteran Hardmode",
        status="planning",
        plan_note="Do not stand in anything expensive.",
        members=(
            RaidPlanMember(
                seat_id="tank-1",
                gamertag="TankPlayer",
                character_name="Tank Toon",
                role="Tank",
                eso_class="Dragonknight",
                planned_gear_sets=("Lucent Echoes", "Pearlescent Ward"),
                primary_assignment="Major Vulnerability",
                utility_assignments=("Boss Positioning",),
                comp_locked_fields=("player", "class"),
                notes="Main boss",
            ),
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                character_name="Magrat",
                role="Healer",
                eso_class="Warden",
                selected_build_name="DF Healer",
                planned_gear_sets=("Spell Power Cure", "Ozezan the Inferno"),
                planned_skills=("Combat Prayer", "Energy Orb"),
                planned_mundus="The Ritual",
                primary_assignment="Major Courage",
                secondary_assignment="Minor Courage",
                utility_assignments=("Raid Healing/Support",),
                comp_locked_fields=("player", "gear"),
                notes="Locked healer package",
            ),
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="",
                role="Damage",
                eso_class="Necromancer",
                planned_gear_sets=("Elemental Catalyst",),
                comp_locked_fields=("class",),
            ),
        ),
        triggered_responsibilities=(
            RaidPlanTriggeredResponsibility(
                responsibility_id="tank-1-breath",
                seat_id="tank-1",
                encounter_id="nahviintaas",
                trigger_key="breath",
                directive="Turn boss away from group",
                source="Raid Plan",
            ),
        ),
    )


def test_raid_plan_to_comp_state_preserves_partial_roster_and_locked_choices() -> None:
    plan = _plan()

    state = CompPlanStateService.from_raid_plan(
        plan,
        achievement_goal="Godslayer",
    )

    assert state.raid_plan_id == plan.plan_id
    assert state.raid_plan_name == plan.name
    assert state.achievement_goal == "Godslayer"
    assert len(state.chairs) == 3

    healer = state.chair("healer-1")
    assert healer is not None
    assert healer.player_name == "Jarakeen"
    assert healer.planned_gear_sets == ("Spell Power Cure", "Ozezan the Inferno")
    assert healer.is_locked("gear")
    assert healer.primary_assignment == "Major Courage"

    recruit = state.chair("dd-1")
    assert recruit is not None
    assert recruit.is_open_player is True
    assert recruit.eso_class == "Necromancer"
    assert recruit.planned_gear_sets == ("Elemental Catalyst",)


def test_comp_state_round_trip_preserves_raid_plan_fields_comp_does_not_own() -> None:
    plan = _plan()
    state = CompPlanStateService.from_raid_plan(plan)

    rebuilt = CompPlanStateService.to_raid_plan(state, base_plan=plan)

    assert rebuilt == plan
    assert rebuilt.triggered_responsibilities == plan.triggered_responsibilities
    assert rebuilt.plan_note == plan.plan_note
    assert rebuilt.team_name == plan.team_name


def test_comp_state_can_change_one_unlocked_chair_without_touching_others() -> None:
    plan = _plan()
    state = CompPlanStateService.from_raid_plan(plan)
    recruit = state.chair("dd-1")
    assert recruit is not None

    state = state.with_chair(
        recruit.with_changes(
            player_name="NewDD",
            character_name="New DD Toon",
            planned_gear_sets=("Elemental Catalyst", "Pillar of Nirn"),
        )
    )
    rebuilt = CompPlanStateService.to_raid_plan(state, base_plan=plan)

    dd = rebuilt.member("dd-1")
    assert dd is not None
    assert dd.gamertag == "NewDD"
    assert dd.planned_gear_sets == ("Elemental Catalyst", "Pillar of Nirn")
    assert rebuilt.member("healer-1") == plan.member("healer-1")
    assert rebuilt.triggered_responsibilities == plan.triggered_responsibilities


def test_lock_service_persists_lock_metadata_back_to_raid_plan() -> None:
    plan = _plan()
    state = CompPlanStateService.from_raid_plan(plan)

    state = CompPlanStateService.lock(
        state,
        seat_id="dd-1",
        field_name="gear",
        locked=True,
    )
    rebuilt = CompPlanStateService.to_raid_plan(state, base_plan=plan)

    dd = rebuilt.member("dd-1")
    assert dd is not None
    assert dd.comp_locked_fields == ("class", "gear")


def test_raid_plan_repository_round_trips_comp_locks_additively(tmp_path) -> None:
    path = tmp_path / "raid_plans.json"
    repository = RaidPlanRepository(path)
    plan = _plan()

    repository.save(plan)
    loaded = repository.get(plan.plan_id)

    assert loaded == plan
    assert loaded is not None
    healer = loaded.member("healer-1")
    assert healer is not None
    assert healer.comp_locked_fields == ("player", "gear")


def test_comp_state_rejects_unknown_lock_field() -> None:
    try:
        CompChairState(seat_id="tank-1", locked_fields=("mystery",))
    except ValueError as exc:
        assert "unknown Comp chair lock field" in str(exc)
    else:
        raise AssertionError("unknown lock field should be rejected")


def test_comp_state_requires_matching_base_raid_plan() -> None:
    plan = _plan()
    state = CompPlanStateService.from_raid_plan(plan)
    other = replace(plan, plan_id="other")

    try:
        CompPlanStateService.to_raid_plan(state, base_plan=other)
    except ValueError as exc:
        assert "does not belong" in str(exc)
    else:
        raise AssertionError("mismatched Raid Plan should be rejected")
