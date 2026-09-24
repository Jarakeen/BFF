from models.raid_plan import RaidPlan, RaidPlanMember, RaidPlanTriggeredResponsibility
from ui.raid_plan_assignment_page import (
    merge_plan_assignment_values,
    raid_plan_assignment_choices,
)
from ui.roster_page import _assignment_choice_rows


def test_raid_plan_assignment_choices_include_roster_and_full_coverage_vocabulary() -> None:
    expected = tuple(label for label, _identity in _assignment_choice_rows() if label.strip())
    choices = raid_plan_assignment_choices()

    assert set(expected) <= set(choices)
    assert "Boss Positioning / Add Control" in choices
    assert "Portal / Backup Control" in choices
    assert "Major Courage" in choices
    assert "Minor Heroism" in choices
    assert "Xoryn's Masterpiece" in choices
    assert "Ozezan's Plating" in choices


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
    assert "merge_plan_assignment_values" in source
    assert "QCompleter.CompletionMode.PopupCompletion" in source
    assert "Qt.MatchFlag.MatchContains" in source
    assert "Type to find assignment" in source


def test_raid_engine_registers_current_assignment_aware_raid_plan_workspace() -> None:
    from pathlib import Path

    route_source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")
    workspace_source = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")
    assignment_source = Path("ui/city_raid_assignments_page.py").read_text(encoding="utf-8")

    assert "from ui.city_raid_plan_workspace_page import CityRaidPlanWorkspacePage" in route_source
    assert "raid_plans = CityRaidPlanWorkspacePage()" in route_source
    assert "from ui.city_raid_assignments_page import CityRaidAssignmentsPage" in route_source
    assert "assignments = CityRaidAssignmentsPage()" in route_source
    assert "class CityRaidAssignmentsPage(RaidPlanAssignmentPage):" in assignment_source


def test_raid_plan_member_persists_utility_assignments_separately() -> None:
    member = RaidPlanMember(
        seat_id="healer-1",
        gamertag="Jarakeen",
        primary_assignment="Major Courage",
        secondary_assignment="Major Slayer",
        utility_assignments=("Kite", "Interrupts"),
        notes="Watch the left edge.",
    )

    assert member.primary_assignment == "Major Courage"
    assert member.secondary_assignment == "Major Slayer"
    assert member.utility_assignments == ("Kite", "Interrupts")
    assert member.notes == "Watch the left edge."


def test_city_assignments_uses_separate_support_and_utility_surfaces() -> None:
    from pathlib import Path

    source = Path("ui/city_raid_assignments_page.py").read_text(encoding="utf-8")

    assert "raid_plan_assignment_choices" in source
    assert "UTILITY_CHOICES" in source
    assert "self._utility_by_seat" in source
    assert "utility_assignments=tuple(utilities)" in source
    assert 'FoundryCard("Plan Snapshot", "compass")' in source
    assert 'FoundryCard("Mechanic Coverage", "shield")' not in source


def test_raid_plan_workspace_exposes_crit_and_pen_calculator() -> None:
    from pathlib import Path

    source = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")

    assert "RaidPlanOffensiveStatsService" in source
    assert 'FoundryCard("Critical Damage & Penetration", "crosshair")' in source
    assert '"PERSONAL CRIT"' in source
    assert '"RAID CRIT"' in source
    assert '"PHYS PEN"' in source
    assert '"SPELL PEN"' in source
    assert '"RAID ARMOR ↓"' in source
    assert '"EFFECTIVE P / S"' in source
    assert "self._refresh_offensive_stats(plan)" in source
    assert "18,200" in source
