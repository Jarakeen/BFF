from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_action_selection import AbilityActionEligibility
from minmax.rotation_bar_swap_selection import select_priority_bar_swap


def _priorities() -> AbilityPriorityList:
    return AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Budding Seeds", 2),
            AbilityPriorityEntry("front", 3, "Combat Prayer", 4),
            AbilityPriorityEntry("back", 4, "Expansive Frost Cloak", 1),
            AbilityPriorityEntry("back", 5, "Overflowing Altar", 5),
        ),
    )


def _eligibility(
    *,
    front_ready: bool = True,
    back_ready: bool = True,
) -> tuple[AbilityActionEligibility, ...]:
    return (
        AbilityActionEligibility("front", 1, "Budding Seeds", timing_ready=front_ready),
        AbilityActionEligibility("front", 3, "Combat Prayer"),
        AbilityActionEligibility("back", 4, "Expansive Frost Cloak", timing_ready=back_ready),
        AbilityActionEligibility("back", 5, "Overflowing Altar"),
    )


def test_swap_when_inactive_bar_has_strictly_higher_priority_legal_ability() -> None:
    result = select_priority_bar_swap(
        priorities=_priorities(),
        current_bar="front",
        eligibility=_eligibility(),
    )

    assert result.should_swap is True
    assert result.destination_bar == "back"
    assert result.inactive_bar_best is not None
    assert result.inactive_bar_best.priority.entry.skill_name == "Expansive Frost Cloak"
    assert result.current_bar_best is not None
    assert result.current_bar_best.priority.entry.skill_name == "Budding Seeds"


def test_equal_or_lower_inactive_priority_does_not_force_swap() -> None:
    priorities = AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Budding Seeds", 1),
            AbilityPriorityEntry("back", 4, "Expansive Frost Cloak", 1),
        ),
    )
    eligibility = (
        AbilityActionEligibility("front", 1, "Budding Seeds"),
        AbilityActionEligibility("back", 4, "Expansive Frost Cloak"),
    )

    result = select_priority_bar_swap(
        priorities=priorities,
        current_bar="front",
        eligibility=eligibility,
    )

    assert result.should_swap is False
    assert result.destination_bar is None
    assert result.reason == "current bar retains equal or higher legal priority"


def test_swap_when_current_bar_has_no_legal_ability() -> None:
    result = select_priority_bar_swap(
        priorities=_priorities(),
        current_bar="front",
        eligibility=_eligibility(front_ready=False),
    )

    # Combat Prayer remains legal on front, so first make it illegal too.
    eligibility = tuple(
        AbilityActionEligibility(
            item.bar,
            item.slot,
            item.skill_name,
            timing_ready=False if item.bar == "front" else item.timing_ready,
        )
        for item in _eligibility(front_ready=False)
    )
    result = select_priority_bar_swap(
        priorities=_priorities(),
        current_bar="front",
        eligibility=eligibility,
    )

    assert result.should_swap is True
    assert result.destination_bar == "back"
    assert result.current_bar_best is None
    assert result.reason == "inactive bar has a legal ability while current bar has none"


def test_no_swap_when_inactive_bar_has_no_legal_ability() -> None:
    eligibility = tuple(
        AbilityActionEligibility(
            item.bar,
            item.slot,
            item.skill_name,
            timing_ready=False if item.bar == "back" else item.timing_ready,
        )
        for item in _eligibility(back_ready=False)
    )

    result = select_priority_bar_swap(
        priorities=_priorities(),
        current_bar="front",
        eligibility=eligibility,
    )

    assert result.should_swap is False
    assert result.destination_bar is None
    assert result.inactive_bar_best is None
    assert result.reason == "inactive bar has no legal priority ability"
