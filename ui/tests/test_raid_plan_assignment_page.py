from models.raid_plan import RaidPlan, RaidPlanMember, RaidPlanTriggeredResponsibility
from ui.raid_plan_assignment_page import (
    merge_plan_assignment_values,
    raid_plan_assignment_choices,
)
from ui.roster_page import _assignment_choice_rows


def test_raid_plan_assignment_choices_reuse_roster_assignment_vocabulary() -> None:
    expected = tuple(label for label, _identity in _assignment_choice_rows() if label.strip())

    assert raid_plan_assignment_choices() == expected
    assert "Boss Positioning / Add Control" in expected
    assert "Portal / Backup Control" in expected


def test_assignment_values_update_only_existing_plan_members() -> None:
    triggered = RaidPlanTriggeredResponsibility(
        responsibility_id="portal-response",
        seat_id="healer-1",
        encounter_id="xalvakka-hm",
        trigger_key="portal_active",
        directive="Cover portal group",
    )
    plan = RaidPlan(
        plan_id="rockgrove-plan",
        trial_id="rockgrove",
        name="Rockgrove Plan",
        team_name="Performance Mode",
        status="active",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                roster_member_id=7,
                character_id="magrat-id",
                character_name="Magrat",
                role="Healer",
                eso_class="Warden",
                selected_build_name="DF Healer",
                notes="Top-left pool",
            ),
        ),
        triggered_responsibilities=(triggered,),
    )

    updated = merge_plan_assignment_values(
        plan,
        {
            "healer-1": ("Raid Healing / Support", "Portal / Backup Control"),
            "dd-8": ("Imaginary Chair Job", ""),
        },
    )

    member = updated.member("healer-1")
    assert member is not None
    assert member.primary_assignment == "Raid Healing / Support"
    assert member.secondary_assignment == "Portal / Backup Control"
    assert member.roster_member_id == 7
    assert member.character_id == "magrat-id"
    assert member.selected_build_name == "DF Healer"
    assert member.notes == "Top-left pool"
    assert updated.team_name == "Performance Mode"
    assert updated.status == "active"
    assert updated.triggered_responsibilities == (triggered,)
    assert updated.member("dd-8") is None


def test_empty_visible_assignment_clears_plan_owned_assignment() -> None:
    plan = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Friend",
                primary_assignment="Old Primary",
                secondary_assignment="Old Secondary",
            ),
        ),
    )

    updated = merge_plan_assignment_values(plan, {"dd-1": ("", "")})

    member = updated.member("dd-1")
    assert member is not None
    assert member.primary_assignment is None
    assert member.secondary_assignment is None


def test_assignment_page_does_not_depend_on_roster_assignment_context_service() -> None:
    from pathlib import Path

    source = Path("ui/raid_plan_assignment_page.py").read_text(encoding="utf-8")

    assert "RosterAssignmentContextService" not in source
    assert "roster_assignment_context" not in source
    assert "primary_assignment=self._assignment_text" not in source
    assert "merge_plan_assignment_values" in source
    assert "QCompleter.CompletionMode.PopupCompletion" in source
    assert "Qt.MatchFlag.MatchContains" in source
    assert "Type to find assignment" in source
