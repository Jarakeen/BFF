from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_action_selection import AbilityActionEligibility
from minmax.rotation_decision_pipeline import evaluate_priority_decision
from minmax.rotation_decision_progression import (
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
            AbilityPriorityEntry("front", 1, "Budding Seeds", 3),
            AbilityPriorityEntry("back", 4, "Illustrious Healing", 0),
        ),
    )


def _eligibility(*, back_ready: bool = True) -> tuple[AbilityActionEligibility, ...]:
    return (
        AbilityActionEligibility(
            bar="front",
            slot=1,
            skill_name="Budding Seeds",
            timing_ready=True,
            resource_safe=True,
            encounter_allowed=True,
        ),
        AbilityActionEligibility(
            bar="back",
            slot=4,
            skill_name="Illustrious Healing",
            timing_ready=back_ready,
            resource_safe=True,
            encounter_allowed=True,
        ),
    )


def test_pipeline_builds_matching_action_and_bar_swap_selections() -> None:
    result = evaluate_priority_decision(
        priorities=_priorities(),
        current_bar="front",
        eligibility=_eligibility(),
    )

    assert result.action_selection.current_bar == "front"
    assert result.action_selection.selected is not None
    assert result.action_selection.selected.priority.entry.skill_name == "Budding Seeds"
    assert result.bar_swap_selection.should_swap is True
    assert result.bar_swap_selection.destination_bar == "back"
    assert result.evaluation.action_selection is result.action_selection
    assert result.evaluation.bar_swap_selection is result.bar_swap_selection


def test_pipeline_drives_progression_with_carried_bar_state() -> None:
    priorities = _priorities()

    def evaluate(current_bar: str, index: int, point: RotationDecisionPoint):
        result = evaluate_priority_decision(
            priorities=priorities,
            current_bar=current_bar,
            eligibility=_eligibility(),
        )
        return result.evaluation

    progression = build_rotation_plan_from_decisions(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=5.0,
        initial_bar="front",
        decision_points=(
            RotationDecisionPoint(1.0, 0),
            RotationDecisionPoint(2.0, 1),
        ),
        evaluate_decision=evaluate,
    )

    assert progression.final_bar == "back"
    assert [(action.kind, action.bar, action.name) for action in progression.plan.actions] == [
        (RotationActionKind.BAR_SWAP, "back", None),
        (RotationActionKind.SKILL, "back", "Illustrious Healing"),
    ]


def test_pipeline_does_not_swap_to_unready_inactive_ability() -> None:
    result = evaluate_priority_decision(
        priorities=_priorities(),
        current_bar="front",
        eligibility=_eligibility(back_ready=False),
    )

    assert result.bar_swap_selection.should_swap is False
    assert result.action_selection.selected is not None
    assert result.action_selection.selected.priority.entry.skill_name == "Budding Seeds"
