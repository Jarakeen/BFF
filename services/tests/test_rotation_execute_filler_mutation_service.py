from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_execute_filler_damage_comparison_service import (
    RotationExecuteFillerDamageComparison,
)
from services.rotation_execute_filler_mutation_service import (
    RotationExecuteFillerMutationService,
)
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteFillerOpportunity,
)


def _candidate() -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Tester",
            build_name="DD Build",
            duration_seconds=10.0,
            actions=(
                RotationAction(1.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
                RotationAction(1.0, 1, RotationActionKind.SKILL, name="Filler", bar="front"),
                RotationAction(2.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
                RotationAction(2.0, 1, RotationActionKind.SKILL, name="Other", bar="front"),
            ),
            assumptions=("baseline assumption",),
            unresolved=("baseline unresolved",),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _opportunity(execute: str, *, time_seconds: float = 1.0, current: str = "Filler"):
    return RotationExecuteFillerOpportunity(
        time_seconds=time_seconds,
        bar="front",
        current_skill_name=current,
        execute_skill_name=execute,
        current_priority=1,
        execute_priority=5,
        target_identity="boss",
        active_thresholds=(0.25,),
    )


class _ComparisonService:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def compare(self, *, candidate, opportunity):
        self.calls.append((candidate, opportunity))
        current, execute, replace, unresolved = self.rows[opportunity.execute_skill_name]
        return RotationExecuteFillerDamageComparison(
            opportunity=opportunity,
            current_damage=current,
            execute_damage=execute,
            replace_with_execute=replace,
            unresolved=unresolved,
        )


def test_strict_damage_win_replaces_only_exact_filler_skill() -> None:
    candidate = _candidate()
    comparison = _ComparisonService({"Execute": (100.0, 150.0, True, ())})
    result = RotationExecuteFillerMutationService(
        comparison_service=comparison,  # type: ignore[arg-type]
    ).apply(candidate=candidate, opportunities=(_opportunity("Execute"),))

    skills = [action for action in result.candidate.plan.actions if action.kind is RotationActionKind.SKILL]
    assert [(action.time_seconds, action.name) for action in skills] == [
        (1.0, "Execute"),
        (2.0, "Other"),
    ]
    assert len(result.mutations) == 1
    assert result.mutations[0].replaced_skill_name == "Filler"
    assert result.mutations[0].execute_skill_name == "Execute"
    assert result.mutations[0].current_damage == 100.0
    assert result.mutations[0].execute_damage == 150.0
    assert result.candidate.plan.unresolved == ("baseline unresolved",)
    assert "baseline assumption" in result.candidate.plan.assumptions
    assert any("canonical exact-slot damage was strictly greater" in value for value in result.candidate.plan.assumptions)


def test_unresolved_or_nonwinning_comparison_leaves_candidate_unchanged() -> None:
    candidate = _candidate()
    opportunities = (_opportunity("Unknown"), _opportunity("Weak"))
    comparison = _ComparisonService(
        {
            "Unknown": (100.0, None, False, ("execute damage unresolved",)),
            "Weak": (100.0, 90.0, False, ()),
        }
    )
    result = RotationExecuteFillerMutationService(
        comparison_service=comparison,  # type: ignore[arg-type]
    ).apply(candidate=candidate, opportunities=opportunities)

    assert result.candidate is candidate
    assert result.mutations == ()
    assert result.unresolved == ("execute damage unresolved",)


def test_highest_resolved_execute_damage_wins_same_slot() -> None:
    candidate = _candidate()
    opportunities = (_opportunity("Execute A"), _opportunity("Execute B"))
    comparison = _ComparisonService(
        {
            "Execute A": (100.0, 140.0, True, ()),
            "Execute B": (100.0, 175.0, True, ()),
        }
    )
    result = RotationExecuteFillerMutationService(
        comparison_service=comparison,  # type: ignore[arg-type]
    ).apply(candidate=candidate, opportunities=opportunities)

    skill = next(
        action
        for action in result.candidate.plan.actions
        if action.kind is RotationActionKind.SKILL and action.time_seconds == 1.0
    )
    assert skill.name == "Execute B"
    assert result.mutations[0].execute_damage == 175.0


def test_equal_best_execute_damage_fails_closed_without_hidden_tiebreak() -> None:
    candidate = _candidate()
    opportunities = (_opportunity("Execute A"), _opportunity("Execute B"))
    comparison = _ComparisonService(
        {
            "Execute A": (100.0, 150.0, True, ()),
            "Execute B": (100.0, 150.0, True, ()),
        }
    )
    result = RotationExecuteFillerMutationService(
        comparison_service=comparison,  # type: ignore[arg-type]
    ).apply(candidate=candidate, opportunities=opportunities)

    assert result.candidate is candidate
    assert result.mutations == ()
    assert len(result.unresolved) == 1
    assert "equal-damage tie" in result.unresolved[0]
    assert "Execute A" in result.unresolved[0]
    assert "Execute B" in result.unresolved[0]


def test_mutation_preserves_light_attack_and_action_identity() -> None:
    candidate = _candidate()
    comparison = _ComparisonService({"Execute": (100.0, 150.0, True, ())})
    result = RotationExecuteFillerMutationService(
        comparison_service=comparison,  # type: ignore[arg-type]
    ).apply(candidate=candidate, opportunities=(_opportunity("Execute"),))

    same_time = [action for action in result.candidate.plan.actions if action.time_seconds == 1.0]
    assert [(action.sequence, action.kind, action.name, action.bar) for action in same_time] == [
        (0, RotationActionKind.LIGHT_ATTACK, None, "front"),
        (1, RotationActionKind.SKILL, "Execute", "front"),
    ]
