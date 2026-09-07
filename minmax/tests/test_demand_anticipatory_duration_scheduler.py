import pytest

from minmax.demand_anticipatory_duration_scheduler import (
    DemandAnticipatoryPriorityDurationRotationScheduler,
    DemandRefreshLead,
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
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule


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
                demand_name="Phase 2 healing prep",
                bar="front",
                slot=2,
                skill_name="Burst Prep",
                priority=0,
                reason="prepare burst healing before threshold",
            ),
        ),
    )


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Phase 2 healing prep",
        start_seconds=27.0,
        end_seconds=32.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _scheduler(lead_seconds: float = 3.0):
    return DemandAnticipatoryPriorityDurationRotationScheduler(
        _priorities(),
        (_demand(),),
        (
            DemandRefreshLead(
                demand_name="Phase 2 healing prep",
                bar="front",
                skill_name="Burst Prep",
                lead_seconds=lead_seconds,
            ),
        ),
    )


def _due(scheduler, time_seconds: float):
    return scheduler._due_refresh(
        time_seconds=time_seconds,
        bar="front",
        next_due={
            ("sustained heal", "front"): 31.0,
            ("burst prep", "front"): 30.0,
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


def test_named_demand_can_make_explicit_burst_prep_refresh_due_early() -> None:
    scheduler = _scheduler(3.0)

    assert _due(scheduler, 26.999) is None
    assert _due(scheduler, 27.0) == ("burst prep", "front")


def test_early_refresh_permission_does_not_apply_outside_named_demand() -> None:
    scheduler = _scheduler(3.0)

    # Once the demand window closes, ordinary base priority applies again.
    assert _due(scheduler, 32.0) == ("sustained heal", "front")


def test_refresh_lead_cannot_make_skill_immediately_eligible_after_each_cast() -> None:
    scheduler = _scheduler(10.0)
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Burst Prep", "front"),
        ),
    )
    rules = (
        RotationRecastRule("Burst Prep", 10.0, bar="front"),
    )

    with pytest.raises(ValueError, match="shorter than the verified ordinary refresh span"):
        scheduler.refine(plan, rules)


def test_refresh_lead_requires_verified_duration_rule() -> None:
    scheduler = _scheduler(3.0)
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Burst Prep", "front"),
        ),
    )

    with pytest.raises(ValueError, match="requires a verified duration rule"):
        scheduler.refine(plan, ())
