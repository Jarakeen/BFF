from services.performance_focus_service import (
    PerformanceBuildEvidence,
    likely_responsibilities,
)
from services.performance_role_focus import desired_uptime, role_profile


def test_role_profiles_keep_dps_and_tank_focus_distinct() -> None:
    dps = role_profile("DPS")
    tank = role_profile("Tank")

    assert dps.CardTitle == "Damage Focus"
    assert "Minor Force" in dps.TrackedEffects
    assert "Major Breach" not in dps.TrackedEffects

    assert tank.CardTitle == "Tank Focus"
    assert "Major Breach" in tank.TrackedEffects
    assert "Major Resolve" in tank.TrackedEffects
    assert "Minor Force" not in tank.TrackedEffects


def test_bff_calibrated_targets_are_rounded_working_values() -> None:
    assert desired_uptime("Major Berserk") == 95.0
    assert desired_uptime("Major Slayer") == 90.0
    assert desired_uptime("Major Vulnerability") == 55.0
    assert desired_uptime("Off Balance") == 30.0
    assert desired_uptime("Major Resolve") is None


def test_dps_minor_force_requires_build_source_evidence() -> None:
    evidence = PerformanceBuildEvidence(
        ClassName="Nightblade",
        Role="DPS",
        Abilities=("Barbed Trap", "Incapacitating Strike"),
    )

    suggestions = dict(likely_responsibilities(evidence))

    assert "Minor Force" in suggestions
    assert "Major Slayer" not in suggestions
    assert "Major Courage" not in suggestions


def test_tank_pierce_armor_suggests_breach_but_not_unrelated_debuffs() -> None:
    evidence = PerformanceBuildEvidence(
        ClassName="Dragonknight",
        Role="Tank",
        Abilities=("Pierce Armor", "Hardened Armor"),
    )

    suggestions = dict(likely_responsibilities(evidence))

    assert "Major Breach" in suggestions
    assert "Minor Breach" in suggestions
    assert "Major Resolve" in suggestions
    assert "Major Vulnerability" not in suggestions


def test_tank_set_and_horn_evidence_can_add_assigned_group_utility() -> None:
    evidence = PerformanceBuildEvidence(
        ClassName="Necromancer",
        Role="Tank",
        GearSets=("Turning Tide",),
        Abilities=("Aggressive Horn", "Beckoning Armor"),
    )

    suggestions = dict(likely_responsibilities(evidence))

    assert "Major Vulnerability" in suggestions
    assert "Major Force" in suggestions
    assert "Major Resolve" in suggestions
