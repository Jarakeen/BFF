import pytest

from minmax.demand_action_claim_anticipatory_duration_scheduler import (
    DemandActionClaimAnticipatoryPriorityDurationRotationScheduler,
)
from minmax.demand_action_claim_duration_scheduler import DemandActionClaim
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
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


def _scheduler() -> DemandActionClaimAnticipatoryPriorityDurationRotationScheduler:
    return DemandActionClaimAnticipatoryPriorityDurationRotationScheduler(
        _priorities(),
        (_demand(),),
        (
            DemandActionClaim(
                demand_name=DEMAND_NAME,
                bar="front",
                skill_name="Budding Seeds",
            ),
        ),
        (
            DemandRefreshLead(
                demand_name=DEMAND_NAME,
                bar="front",
                skill_name="Combat Prayer",
                lead_seconds=2.0,
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


def test_mechanic_claim_precedes_eligible_anticipatory_refresh() -> None:
    scheduler = _scheduler()

    # Prayer is eligible two seconds early at 30s, but Seeds would otherwise miss
    # the mechanic window entirely. The explicit mechanic claim therefore wins.
    assert _due(
        scheduler,
        time_seconds=30.0,
        seeds_due=36.0,
        prayer_due=32.0,
    ) == ("budding seeds", "front")


def test_anticipatory_refresh_runs_when_no_action_claim_is_needed() -> None:
    scheduler = _scheduler()

    # Seeds is already due inside the demand, so its hard claim is unnecessary.
    # Prayer may still use the caller-proven two-second early-refresh permission.
    assert _due(
        scheduler,
        time_seconds=30.0,
        seeds_due=33.0,
        prayer_due=32.0,
    ) == ("combat prayer", "front")


def test_combined_scheduler_validates_refresh_lead_duration_rule() -> None:
    scheduler = _scheduler()
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
            RotationAction(1.0, 1, RotationActionKind.SKILL, "Combat Prayer", "front"),
        ),
    )
    rules = (
        RotationRecastRule("Budding Seeds", 11.0, bar="front"),
    )

    with pytest.raises(ValueError, match="requires a verified duration rule"):
        scheduler.refine(plan, rules)


def test_combined_scheduler_validates_action_claim_duration_rule() -> None:
    scheduler = _scheduler()
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
            RotationAction(1.0, 1, RotationActionKind.SKILL, "Combat Prayer", "front"),
        ),
    )
    rules = (
        RotationRecastRule("Combat Prayer", 8.0, bar="front"),
    )

    with pytest.raises(ValueError, match="requires a verified duration rule"):
        scheduler.refine(plan, rules)
