import pytest

from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_action_selection import (
    AbilityActionEligibility,
    select_priority_ability_action,
)
from minmax.rotation_bar_swap_selection import select_priority_bar_swap
from minmax.rotation_decision_scheduling import schedule_priority_decision
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationActionKind


def _priorities() -> AbilityPriorityList:
    return AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Budding Seeds", 2),
            AbilityPriorityEntry("front", 4, "Illustrious Healing", 1),
            AbilityPriorityEntry("back", 3, "Winter's Revenge", 3),
        ),
    )


def _eligibility(*, front_heal_safe: bool = True) -> tuple[AbilityActionEligibility, ...]:
    return (
        AbilityActionEligibility("front", 1, "Budding Seeds"),
        AbilityActionEligibility(
            "front",
            4,
            "Illustrious Healing",
            resource_safe=front_heal_safe,
        ),
        AbilityActionEligibility("back", 3, "Winter's Revenge"),
    )


def _selections(*, current_bar: str, front_heal_safe: bool = True, demand=None):
    eligibility = _eligibility(front_heal_safe=front_heal_safe)
    action = select_priority_ability_action(
        priorities=_priorities(),
        current_bar=current_bar,
        eligibility=eligibility,
        demand=demand,
    )
    swap = select_priority_bar_swap(
        priorities=_priorities(),
        current_bar=current_bar,
        eligibility=eligibility,
        demand=demand,
    )
    return action, swap


def test_schedules_selected_current_bar_skill() -> None:
    action_selection, swap_selection = _selections(current_bar="front")

    result = schedule_priority_decision(
        time_seconds=12.5,
        sequence=4,
        action_selection=action_selection,
        bar_swap_selection=swap_selection,
    )

    assert result.action is not None
    assert result.action.kind is RotationActionKind.SKILL
    assert result.action.name == "Illustrious Healing"
    assert result.action.bar == "front"
    assert result.action.time_seconds == 12.5
    assert result.action.sequence == 4


def test_schedules_explicit_bar_swap_without_same_tick_skill_cast() -> None:
    action_selection, swap_selection = _selections(
        current_bar="back",
        front_heal_safe=True,
    )
    assert swap_selection.should_swap is True

    result = schedule_priority_decision(
        time_seconds=8.0,
        sequence=2,
        action_selection=action_selection,
        bar_swap_selection=swap_selection,
    )

    assert result.action is not None
    assert result.action.kind is RotationActionKind.BAR_SWAP
    assert result.action.bar == "front"
    assert result.action.name is None


def test_schedules_nothing_when_no_current_skill_and_no_swap() -> None:
    priorities = AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(AbilityPriorityEntry("front", 1, "Budding Seeds", 1),),
    )
    eligibility = (
        AbilityActionEligibility(
            "front",
            1,
            "Budding Seeds",
            timing_ready=False,
        ),
    )
    action_selection = select_priority_ability_action(
        priorities=priorities,
        current_bar="front",
        eligibility=eligibility,
    )
    swap_selection = select_priority_bar_swap(
        priorities=priorities,
        current_bar="front",
        eligibility=eligibility,
    )

    result = schedule_priority_decision(
        time_seconds=3.0,
        sequence=0,
        action_selection=action_selection,
        bar_swap_selection=swap_selection,
    )

    assert result.action is None


def test_rejects_mixed_current_bar_decisions() -> None:
    front_action, _ = _selections(current_bar="front")
    _, back_swap = _selections(current_bar="back")

    with pytest.raises(ValueError, match="same current bar"):
        schedule_priority_decision(
            time_seconds=1.0,
            sequence=0,
            action_selection=front_action,
            bar_swap_selection=back_swap,
        )


def test_rejects_mixed_demand_contexts() -> None:
    ice = RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    bahsei = RotationDemandWindow(
        name="Bahsei Tank Bleed",
        start_seconds=0.0,
        end_seconds=180.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.SUSTAINED,
    )
    action_selection, _ = _selections(current_bar="front", demand=ice)
    _, swap_selection = _selections(current_bar="front", demand=bahsei)

    with pytest.raises(ValueError, match="same demand context"):
        schedule_priority_decision(
            time_seconds=11.0,
            sequence=1,
            action_selection=action_selection,
            bar_swap_selection=swap_selection,
        )
