import pytest

from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_action_selection import (
    AbilityActionEligibility,
    select_priority_ability_action,
)
from minmax.rotation_bar_swap_selection import select_priority_bar_swap
from minmax.rotation_decision_progression import (
    RotationDecisionEvaluation,
    RotationDecisionPoint,
    build_rotation_plan_from_decisions,
)
from minmax.rotation_plan import RotationActionKind


def _priorities() -> AbilityPriorityList:
    return AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry(
                bar="front",
                slot=1,
                skill_name="Budding Seeds",
                priority=2,
            ),
            AbilityPriorityEntry(
                bar="back",
                slot=4,
                skill_name="Illustrious Healing",
                priority=0,
            ),
        ),
    )


def _eligibility() -> tuple[AbilityActionEligibility, ...]:
    return (
        AbilityActionEligibility(
            bar="front",
            slot=1,
            skill_name="Budding Seeds",
        ),
        AbilityActionEligibility(
            bar="back",
            slot=4,
            skill_name="Illustrious Healing",
        ),
    )


def _evaluation(current_bar: str) -> RotationDecisionEvaluation:
    priorities = _priorities()
    eligibility = _eligibility()
    return RotationDecisionEvaluation(
        action_selection=select_priority_ability_action(
            priorities=priorities,
            current_bar=current_bar,
            eligibility=eligibility,
        ),
        bar_swap_selection=select_priority_bar_swap(
            priorities=priorities,
            current_bar=current_bar,
            eligibility=eligibility,
        ),
    )


def test_progression_carries_bar_state_from_swap_into_next_decision() -> None:
    observed_bars: list[str] = []

    def evaluate(current_bar: str, index: int, point: RotationDecisionPoint):
        observed_bars.append(current_bar)
        return _evaluation(current_bar)

    result = build_rotation_plan_from_decisions(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=5.0,
        initial_bar="front",
        decision_points=(
            RotationDecisionPoint(time_seconds=1.0, sequence=0),
            RotationDecisionPoint(time_seconds=2.0, sequence=1),
        ),
        evaluate_decision=evaluate,
    )

    assert observed_bars == ["front", "back"]
    assert result.initial_bar == "front"
    assert result.final_bar == "back"
    assert [(step.bar_before, step.bar_after) for step in result.steps] == [
        ("front", "back"),
        ("back", "back"),
    ]
    assert [action.kind for action in result.plan.actions] == [
        RotationActionKind.BAR_SWAP,
        RotationActionKind.SKILL,
    ]
    assert result.plan.actions[0].bar == "back"
    assert result.plan.actions[1].name == "Illustrious Healing"
    assert result.plan.actions[1].bar == "back"


def test_progression_rejects_same_timestamp_follow_up_decision() -> None:
    with pytest.raises(ValueError, match="strictly increase"):
        build_rotation_plan_from_decisions(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=5.0,
            initial_bar="front",
            decision_points=(
                RotationDecisionPoint(time_seconds=1.0, sequence=0),
                RotationDecisionPoint(time_seconds=1.0, sequence=1),
            ),
            evaluate_decision=lambda current_bar, index, point: _evaluation(current_bar),
        )


def test_progression_rejects_evaluator_state_from_wrong_active_bar() -> None:
    with pytest.raises(ValueError, match="does not match active bar"):
        build_rotation_plan_from_decisions(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=5.0,
            initial_bar="front",
            decision_points=(RotationDecisionPoint(time_seconds=1.0, sequence=0),),
            evaluate_decision=lambda current_bar, index, point: _evaluation("back"),
        )
