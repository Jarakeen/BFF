from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_action_selection import (
    AbilityActionEligibility,
    select_priority_ability_action,
)
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)


def _priorities() -> AbilityPriorityList:
    return AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Budding Seeds", 0),
            AbilityPriorityEntry("front", 2, "Combat Prayer", 2),
            AbilityPriorityEntry("back", 1, "Illustrious Healing", 0),
        ),
    )


def _eligibility(*, seeds_safe=True, prayer_safe=True, illustrious_safe=True):
    return (
        AbilityActionEligibility("front", 1, "Budding Seeds", resource_safe=seeds_safe),
        AbilityActionEligibility("front", 2, "Combat Prayer", resource_safe=prayer_safe),
        AbilityActionEligibility("back", 1, "Illustrious Healing", resource_safe=illustrious_safe),
    )


def test_selects_highest_priority_legal_ability_on_active_bar() -> None:
    result = select_priority_ability_action(
        priorities=_priorities(),
        current_bar="front",
        eligibility=_eligibility(),
    )

    assert result.selected is not None
    assert result.selected.priority.entry.skill_name == "Budding Seeds"
    assert result.selected.priority.effective_priority == 0


def test_skips_higher_priority_action_when_resource_safety_rejects_it() -> None:
    result = select_priority_ability_action(
        priorities=_priorities(),
        current_bar="front",
        eligibility=_eligibility(seeds_safe=False),
    )

    assert result.selected is not None
    assert result.selected.priority.entry.skill_name == "Combat Prayer"
    assert [item.priority.entry.skill_name for item in result.rejected] == ["Budding Seeds"]


def test_does_not_silently_choose_inactive_bar_ability() -> None:
    result = select_priority_ability_action(
        priorities=_priorities(),
        current_bar="front",
        eligibility=_eligibility(seeds_safe=False, prayer_safe=False),
    )

    assert result.selected is None
    assert all(item.priority.entry.bar == "front" for item in result.ranked_candidates)


def test_demand_specific_priority_resolution_is_used() -> None:
    demand = RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    priorities = AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Budding Seeds", 3),
            AbilityPriorityEntry("front", 2, "Combat Prayer", 1),
        ),
        overrides=(),
    )

    result = select_priority_ability_action(
        priorities=priorities,
        current_bar="front",
        eligibility=(
            AbilityActionEligibility("front", 1, "Budding Seeds"),
            AbilityActionEligibility("front", 2, "Combat Prayer"),
        ),
        demand=demand,
    )

    assert result.selected is not None
    assert result.selected.priority.entry.skill_name == "Combat Prayer"
