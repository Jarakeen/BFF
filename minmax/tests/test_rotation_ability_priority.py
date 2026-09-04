import pytest

from minmax.rotation_ability_priority import (
    AbilityPriorityEntry,
    AbilityPriorityList,
    AbilityPriorityOverride,
)
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)


def _cage() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def test_ability_priority_list_applies_exact_demand_overrides() -> None:
    priorities = AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Budding Seeds", 3),
            AbilityPriorityEntry("front", 3, "Combat Prayer", 2),
            AbilityPriorityEntry("front", 4, "Illustrious Healing", 4),
            AbilityPriorityEntry("back", 1, "Elemental Ring", 7),
        ),
        overrides=(
            AbilityPriorityOverride(
                demand_name="Ice Cage 1",
                bar="front",
                slot=4,
                skill_name="Illustrious Healing",
                priority=0,
                reason="example burst rescue override",
            ),
            AbilityPriorityOverride(
                demand_name="Ice Cage 1",
                bar="front",
                slot=1,
                skill_name="Budding Seeds",
                priority=1,
                reason="example pre-heal override",
            ),
        ),
    )

    base = priorities.resolve()
    assert [(item.entry.skill_name, item.effective_priority) for item in base] == [
        ("Combat Prayer", 2),
        ("Budding Seeds", 3),
        ("Illustrious Healing", 4),
        ("Elemental Ring", 7),
    ]

    cage = priorities.resolve(_cage())
    assert [(item.entry.skill_name, item.effective_priority) for item in cage] == [
        ("Illustrious Healing", 0),
        ("Budding Seeds", 1),
        ("Combat Prayer", 2),
        ("Elemental Ring", 7),
    ]
    assert cage[0].override is not None
    assert cage[0].override.reason == "example burst rescue override"


def test_equal_ability_priorities_remain_one_tier_with_stable_presentation() -> None:
    priorities = AbilityPriorityList(
        character_name="Example DD",
        build_name="Corpsebuster",
        role="Damage Dealer",
        entries=(
            AbilityPriorityEntry("back", 2, "Back Bar Skill", 3),
            AbilityPriorityEntry("front", 4, "Front Four", 3),
            AbilityPriorityEntry("front", 1, "Front One", 3),
        ),
    )

    resolved = priorities.resolve()
    assert [item.effective_priority for item in resolved] == [3, 3, 3]
    assert [item.entry.skill_name for item in resolved] == [
        "Front One",
        "Front Four",
        "Back Bar Skill",
    ]


def test_ability_priority_override_must_match_exact_base_skill() -> None:
    with pytest.raises(ValueError, match="does not match base entry"):
        AbilityPriorityList(
            character_name="Magrat",
            build_name="DF Healer",
            role="Healer",
            entries=(AbilityPriorityEntry("front", 1, "Budding Seeds", 3),),
            overrides=(
                AbilityPriorityOverride(
                    demand_name="Ice Cage 1",
                    bar="front",
                    slot=1,
                    skill_name="Different Skill",
                    priority=0,
                ),
            ),
        )


def test_duplicate_ability_priority_saved_slot_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate ability priority entry"):
        AbilityPriorityList(
            character_name="Magrat",
            build_name="DF Healer",
            role="Healer",
            entries=(
                AbilityPriorityEntry("front", 1, "Budding Seeds", 1),
                AbilityPriorityEntry("front", 1, "Other Skill", 2),
            ),
        )
