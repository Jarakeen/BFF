import pytest

from models.raid_plan import (
    RaidPlan,
    RaidPlanMember,
    RaidPlanTriggeredResponsibility,
)


def test_raid_plan_allows_gamertag_before_character_role_or_build() -> None:
    member = RaidPlanMember(
        seat_id="dd-1",
        gamertag="FriendOne",
    )
    plan = RaidPlan(
        plan_id="performance-mode-rockgrove",
        trial_id="rockgrove",
        name="Performance Mode - Rockgrove",
        team_name="Performance Mode",
        members=(member,),
    )

    resolved = plan.member("DD-1")
    assert resolved is not None
    assert resolved.gamertag == "FriendOne"
    assert resolved.character_selected is False
    assert resolved.build_selected is False
    assert resolved.role is None
    assert resolved.eso_class is None


def test_stable_build_id_counts_as_selected_and_is_normalized() -> None:
    member = RaidPlanMember(
        seat_id="healer-1",
        gamertag="Jarakeen",
        selected_build_id="  build-123  ",
    )

    assert member.selected_build_id == "build-123"
    assert member.selected_build_name is None
    assert member.build_selected is True


def test_same_character_can_be_referenced_by_multiple_trial_plans() -> None:
    magrat_rg = RaidPlanMember(
        seat_id="healer-1",
        gamertag="Jarakeen",
        character_id="magrat-id",
        character_name="Magrat",
        role="Healer",
        selected_build_id="df-healer-id",
        selected_build_name="DF Healer",
    )
    magrat_dsr = magrat_rg.with_selection(
        selected_build_id="spc-pillager-id",
        selected_build_name="SPC Pillager",
        primary_assignment="Group Healer",
    )

    rockgrove = RaidPlan(
        plan_id="rg-plan",
        trial_id="rockgrove",
        name="Performance Mode - Rockgrove",
        team_name="Performance Mode",
        members=(magrat_rg,),
    )
    dreadsail = RaidPlan(
        plan_id="dsr-plan",
        trial_id="dreadsail_reef",
        name="Performance Mode - Dreadsail Reef",
        team_name="Performance Mode",
        members=(magrat_dsr,),
    )

    assert rockgrove.member("healer-1").character_id == "magrat-id"
    assert dreadsail.member("healer-1").character_id == "magrat-id"
    assert rockgrove.member("healer-1").selected_build_id == "df-healer-id"
    assert dreadsail.member("healer-1").selected_build_id == "spc-pillager-id"
    assert rockgrove.member("healer-1").selected_build_name == "DF Healer"
    assert dreadsail.member("healer-1").selected_build_name == "SPC Pillager"


def test_plan_member_replacement_changes_plan_not_original_member() -> None:
    original = RaidPlanMember(
        seat_id="healer-1",
        gamertag="Jarakeen",
        character_name="Magrat",
    )
    plan = RaidPlan(
        plan_id="rg-plan",
        trial_id="rockgrove",
        name="Rockgrove Plan",
        members=(original,),
    )

    selected = original.with_selection(
        role="Healer",
        selected_build_id="df-healer-id",
        selected_build_name="DF Healer",
    )
    updated = plan.with_member(selected)

    assert plan.member("healer-1").selected_build_id is None
    assert plan.member("healer-1").selected_build_name is None
    assert updated.member("healer-1").selected_build_id == "df-healer-id"
    assert updated.member("healer-1").selected_build_name == "DF Healer"
    assert original.selected_build_id is None
    assert original.selected_build_name is None


def test_ad_hoc_plan_does_not_require_persistent_team() -> None:
    plan = RaidPlan(
        plan_id="friends-run-rg",
        trial_id="rockgrove",
        name="Friends Run",
    )

    assert plan.team_name is None
    assert plan.status == "planning"


def test_duplicate_seat_ids_are_rejected_case_insensitively() -> None:
    with pytest.raises(ValueError, match="seat_id values must be unique"):
        RaidPlan(
            plan_id="bad-plan",
            trial_id="rockgrove",
            name="Bad Plan",
            members=(
                RaidPlanMember(seat_id="DD-1", gamertag="One"),
                RaidPlanMember(seat_id="dd-1", gamertag="Two"),
            ),
        )


def test_raid_plan_can_own_runtime_triggered_responsibility_without_timestamp() -> None:
    off_tank = RaidPlanMember(
        seat_id="off-tank",
        gamertag="TankTwo",
        role="Tank",
    )
    responsibility = RaidPlanTriggeredResponsibility(
        responsibility_id="xalvakka-iron-atronach-pickup",
        seat_id="off-tank",
        encounter_id="xalvakka",
        trigger_key="iron_atronach_active",
        directive="acquire_and_maintain_owned_add_when_active",
        target_key="Iron Atronach",
        required_capability_type="TAUNT",
        source="reviewed add-activity boundary",
    )

    plan = RaidPlan(
        plan_id="rg-plan",
        trial_id="rockgrove",
        name="Rockgrove Plan",
        members=(off_tank,),
        triggered_responsibilities=(responsibility,),
    )

    rows = plan.triggered_for_seat("OFF-TANK", encounter_id="XALVAKKA")
    assert rows == (responsibility,)
    assert rows[0].trigger_key == "iron_atronach_active"
    assert rows[0].required_capability_type == "taunt"
    assert not hasattr(rows[0], "time_seconds")


def test_triggered_responsibility_cannot_reference_unknown_seat() -> None:
    responsibility = RaidPlanTriggeredResponsibility(
        responsibility_id="orphaned-add-pickup",
        seat_id="off-tank",
        encounter_id="xalvakka",
        trigger_key="iron_atronach_active",
        directive="acquire_add",
    )

    with pytest.raises(ValueError, match="references unknown seat_id"):
        RaidPlan(
            plan_id="rg-plan",
            trial_id="rockgrove",
            name="Rockgrove Plan",
            triggered_responsibilities=(responsibility,),
        )


def test_triggered_responsibility_ids_are_unique_case_insensitively() -> None:
    tank = RaidPlanMember(seat_id="off-tank", gamertag="TankTwo")
    first = RaidPlanTriggeredResponsibility(
        responsibility_id="Iron-Pickup",
        seat_id="off-tank",
        encounter_id="xalvakka",
        trigger_key="iron_atronach_active",
        directive="acquire_add",
    )
    duplicate = RaidPlanTriggeredResponsibility(
        responsibility_id="iron-pickup",
        seat_id="off-tank",
        encounter_id="xalvakka",
        trigger_key="iron_atronach_active",
        directive="maintain_add",
    )

    with pytest.raises(ValueError, match="responsibility_id values must be unique"):
        RaidPlan(
            plan_id="rg-plan",
            trial_id="rockgrove",
            name="Rockgrove Plan",
            members=(tank,),
            triggered_responsibilities=(first, duplicate),
        )


def test_member_with_triggered_responsibility_cannot_be_removed_until_unassigned() -> None:
    tank = RaidPlanMember(seat_id="off-tank", gamertag="TankTwo")
    responsibility = RaidPlanTriggeredResponsibility(
        responsibility_id="iron-pickup",
        seat_id="off-tank",
        encounter_id="xalvakka",
        trigger_key="iron_atronach_active",
        directive="acquire_add",
    )
    plan = RaidPlan(
        plan_id="rg-plan",
        trial_id="rockgrove",
        name="Rockgrove Plan",
        members=(tank,),
        triggered_responsibilities=(responsibility,),
    )

    with pytest.raises(ValueError, match="triggered responsibilities still reference"):
        plan.without_member("OFF-TANK")
