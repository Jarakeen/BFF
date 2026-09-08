from pathlib import Path

from services.performance_focus_service import (
    PerformanceBuildEvidence,
    PerformanceFocusGoal,
    PerformanceFocusStore,
    likely_responsibilities,
    suggest_working_target,
)


def test_suggest_working_target_is_incremental_and_capped() -> None:
    assert suggest_working_target(63.3) == 75.0
    assert suggest_working_target(90.1) == 95.0
    assert suggest_working_target(99.0) == 95.0


def test_focus_store_round_trips_and_upserts_by_name(tmp_path: Path) -> None:
    store = PerformanceFocusStore(tmp_path / "performance_focus.json")
    store.upsert(
        PerformanceFocusGoal(
            Name="Major Brittle",
            TargetPercent=80.0,
            CurrentPercent=63.3,
            Source="Suggested",
        )
    )
    store.upsert(
        PerformanceFocusGoal(
            Name="major brittle",
            TargetPercent=85.0,
            CurrentPercent=70.0,
            Source="Custom",
        )
    )

    goals = store.load()
    assert len(goals) == 1
    assert goals[0].TargetPercent == 85.0
    assert goals[0].CurrentPercent == 70.0


def test_custom_goal_is_preserved_without_current_uptime(tmp_path: Path) -> None:
    store = PerformanceFocusStore(tmp_path / "performance_focus.json")
    store.upsert(
        PerformanceFocusGoal(
            Name="Bar swap consistency",
            TargetPercent=90.0,
            CurrentPercent=None,
            Source="Custom",
            EvidenceNote="User-created goal",
        )
    )

    goal = store.load()[0]
    assert goal.Name == "Bar swap consistency"
    assert goal.CurrentPercent is None
    assert goal.Source == "Custom"


def test_warden_healer_suggests_mending_without_claiming_assignment() -> None:
    evidence = PerformanceBuildEvidence(ClassName="Warden", Role="Healer")
    suggestions = dict(likely_responsibilities(evidence))
    assert suggestions["Major Mending"] == "Warden healer class context"


def test_gear_and_ability_evidence_suggests_only_known_sources() -> None:
    evidence = PerformanceBuildEvidence(
        ClassName="Warden",
        Role="Healer",
        GearSets=("Spell Power Cure", "Roaring Opportunist"),
        Abilities=("Combat Prayer", "Aggressive Horn"),
    )
    suggestions = dict(likely_responsibilities(evidence))

    assert "Major Courage" in suggestions
    assert "Major Slayer" in suggestions
    assert "Minor Berserk" in suggestions
    assert "Major Force" in suggestions
    assert "Major Vulnerability" not in suggestions
