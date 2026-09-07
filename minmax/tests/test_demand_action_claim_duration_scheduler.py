import pytest

from minmax.demand_action_claim_duration_scheduler import (
    DemandActionClaim,
    DemandActionClaimPriorityDurationRotationScheduler,
)
from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule


DEMAND_NAME = "Phase 2 healing prep"


def _priorities() -> AbilityPriorityList:
    return AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Budding Seeds", 1),
            AbilityPriorityEntry("front", 2, "Combat Prayer", 2),
        ),
    )


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name=DEMAND_NAME,
        start_seconds=29.0,
        end_seconds=34.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _scheduler() -> DemandActionClaimPriorityDurationRotationScheduler:
    return DemandActionClaimPriorityDurationRotationScheduler(
        _priorities(),
        (_demand(),),
        (
            DemandActionClaim(
                demand_name=DEMAND_NAME,
                bar="front",
                skill_name="Budding Seeds",
            ),
        ),
    )


def _due(scheduler, *, time_seconds: float, seeds_due: float, prayer_due: float):
    return scheduler._due_refresh(
        time_seconds=time_seconds,
        bar="front",
        next_due={
            ("budding seeds", "front"): seeds_due,
            ("combat prayer", "front"): prayer_due,
        },
        rule_order={
            ("budding seeds", "front"): 0,
            ("combat prayer", "front"): 1,
        },
        action_kind_by_key={
            ("budding seeds", "front"): RotationActionKind.SKILL,
            ("combat prayer", "front"): RotationActionKind.SKILL,
        },
    )


def test_claim_takes_priority_when_ordinary_target_refresh_would_miss_demand() -> None:
    scheduler = _scheduler()

    # Combat Prayer is already ordinarily due, but the explicit hard demand claim
    # wins because Seeds would otherwise refresh after the mechanic window closes.
    assert _due(scheduler, time_seconds=30.0, seeds_due=36.0, prayer_due=29.0) == (
        "budding seeds",
        "front",
    )


def test_claim_does_not_fire_when_ordinary_target_refresh_is_already_inside_demand() -> None:
    scheduler = _scheduler()

    assert _due(scheduler, time_seconds=30.0, seeds_due=33.0, prayer_due=29.0) == (
        "combat prayer",
        "front",
    )


def test_claim_is_consumed_after_one_mechanic_driven_cast() -> None:
    scheduler = _scheduler()

    assert _due(scheduler, time_seconds=30.0, seeds_due=36.0, prayer_due=40.0) == (
        "budding seeds",
        "front",
    )
    assert _due(scheduler, time_seconds=31.0, seeds_due=37.0, prayer_due=40.0) is None


def test_claim_requires_verified_duration_rule() -> None:
    scheduler = _scheduler()
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
        ),
    )

    with pytest.raises(ValueError, match="requires a verified duration rule"):
        scheduler.refine(plan, ())


def test_claim_refine_displaces_due_skill_and_restarts_target_duration() -> None:
    scheduler = _scheduler()
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            RotationAction(25.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
            RotationAction(30.0, 1, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(31.0, 2, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(36.0, 3, RotationActionKind.SKILL, "Budding Seeds", "front"),
        ),
    )
    rules = (
        RotationRecastRule("Budding Seeds", 11.0, bar="front"),
        RotationRecastRule("Combat Prayer", 1.0, bar="front"),
    )

    refined = scheduler.refine(plan, rules)
    skill_rows = tuple(
        (action.time_seconds, action.name)
        for action in refined.actions
        if action.kind is RotationActionKind.SKILL
    )

    assert (30.0, "Budding Seeds") in skill_rows
    assert any(
        "refresh obligation for 'Budding Seeds' claimed the 30s front-bar slot"
        in message
        for message in refined.unresolved
    )
