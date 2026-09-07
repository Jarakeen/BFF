import pytest

from minmax.demand_aware_priority_duration_scheduler import (
    DemandAwarePriorityDurationRotationScheduler,
)
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
from minmax.rotation_plan import RotationActionKind


def _priorities() -> AbilityPriorityList:
    return AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Sustained Heal", 2),
            AbilityPriorityEntry("front", 2, "Burst Prep", 4),
        ),
        overrides=(
            AbilityPriorityOverride(
                demand_name="Ice Cage 1",
                bar="front",
                slot=2,
                skill_name="Burst Prep",
                priority=0,
                reason="burst rescue window",
            ),
        ),
    )


def _demand(name="Ice Cage 1", start=10.0, end=20.0):
    return RotationDemandWindow(
        name=name,
        start_seconds=start,
        end_seconds=end,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _due(scheduler, time_seconds):
    return scheduler._due_refresh(
        time_seconds=time_seconds,
        bar="front",
        next_due={
            ("sustained heal", "front"): 9.0,
            ("burst prep", "front"): 9.0,
        },
        rule_order={
            ("sustained heal", "front"): 0,
            ("burst prep", "front"): 1,
        },
        action_kind_by_key={
            ("sustained heal", "front"): RotationActionKind.SKILL,
            ("burst prep", "front"): RotationActionKind.SKILL,
        },
    )


def test_base_priority_wins_outside_demand_window() -> None:
    scheduler = DemandAwarePriorityDurationRotationScheduler(
        _priorities(),
        (_demand(),),
    )

    assert _due(scheduler, 9.5) == ("sustained heal", "front")


def test_demand_override_changes_due_refresh_order_inside_window() -> None:
    scheduler = DemandAwarePriorityDurationRotationScheduler(
        _priorities(),
        (_demand(),),
    )

    assert _due(scheduler, 10.0) == ("burst prep", "front")
    assert _due(scheduler, 19.999) == ("burst prep", "front")
    assert _due(scheduler, 20.0) == ("sustained heal", "front")


def test_overlapping_demands_require_explicit_precedence() -> None:
    scheduler = DemandAwarePriorityDurationRotationScheduler(
        _priorities(),
        (
            _demand("Ice Cage 1", 10.0, 20.0),
            _demand("Ice Cage 2", 12.0, 22.0),
        ),
    )

    with pytest.raises(ValueError, match="multiple rotation demand windows"):
        _due(scheduler, 15.0)
