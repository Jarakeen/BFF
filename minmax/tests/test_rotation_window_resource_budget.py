import pytest

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import (
    AppliedResourceTimelineEvent,
    ResourceTimelineEventKind,
    ResourceTimelineResult,
)
from minmax.rotation_window_resource_budget import (
    RequiredRotationSpend,
    derive_rotation_window_resource_budget,
)


def _event(
    time_seconds: float,
    kind: ResourceTimelineEventKind,
    source: str,
    *,
    before: int,
    attempted_change: int,
    applied_change: int,
    after: int,
    shortfall: int = 0,
) -> AppliedResourceTimelineEvent:
    return AppliedResourceTimelineEvent(
        time_seconds=time_seconds,
        kind=kind,
        source=source,
        before=before,
        attempted_change=attempted_change,
        applied_change=applied_change,
        after=after,
        shortfall=shortfall,
    )


def test_paired_burst_budget_derives_entry_amount_across_both_windows() -> None:
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=20000,
        ending_amount=11000,
        events=(
            _event(10.0, ResourceTimelineEventKind.ACTION_COST, "Cage 1 Heal A", before=20000, attempted_change=-3000, applied_change=-3000, after=17000),
            _event(12.0, ResourceTimelineEventKind.ACTION_COST, "Cage 1 Heal B", before=17000, attempted_change=-3000, applied_change=-3000, after=14000),
            _event(13.0, ResourceTimelineEventKind.ACTION_COST, "Optional Support", before=14000, attempted_change=-2500, applied_change=-2500, after=11500),
            _event(14.0, ResourceTimelineEventKind.RECOVERY_TICK, "In-combat recovery tick", before=11500, attempted_change=2000, applied_change=2000, after=13500),
            _event(15.0, ResourceTimelineEventKind.ACTION_COST, "Cage 2 Heal A", before=13500, attempted_change=-3500, applied_change=-3500, after=10000),
            _event(18.0, ResourceTimelineEventKind.ACTION_COST, "Cage 2 Heal B", before=10000, attempted_change=-3500, applied_change=-3500, after=6500),
            _event(20.0, ResourceTimelineEventKind.RECOVERY_TICK, "In-combat recovery tick", before=6500, attempted_change=2000, applied_change=2000, after=8500),
        ),
    )

    budget = derive_rotation_window_resource_budget(
        timeline=timeline,
        start_seconds=10.0,
        end_seconds=21.0,
        required_spends=(
            RequiredRotationSpend(10.0, "Cage 1 Heal A"),
            RequiredRotationSpend(12.0, "Cage 1 Heal B"),
            RequiredRotationSpend(15.0, "Cage 2 Heal A"),
            RequiredRotationSpend(18.0, "Cage 2 Heal B"),
        ),
        minimum_ending_amount=3000,
    )

    assert budget.required_spend_amount == 13000
    assert budget.verified_gain_amount == 4000
    assert budget.minimum_entry_amount == 12000
    assert budget.ending_amount_from_minimum_entry == 3000


def test_budget_ignores_discretionary_action_costs_not_declared_required() -> None:
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=10000,
        ending_amount=3000,
        events=(
            _event(10.0, ResourceTimelineEventKind.ACTION_COST, "Required Heal", before=10000, attempted_change=-3000, applied_change=-3000, after=7000),
            _event(11.0, ResourceTimelineEventKind.ACTION_COST, "Discretionary Filler", before=7000, attempted_change=-4000, applied_change=-4000, after=3000),
        ),
    )

    budget = derive_rotation_window_resource_budget(
        timeline=timeline,
        start_seconds=10.0,
        end_seconds=15.0,
        required_spends=(RequiredRotationSpend(10.0, "Required Heal"),),
    )

    assert budget.required_spend_amount == 3000
    assert budget.minimum_entry_amount == 3000


def test_late_recovery_cannot_hide_earlier_required_resource_need() -> None:
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=5000,
        ending_amount=5000,
        events=(
            _event(10.0, ResourceTimelineEventKind.ACTION_COST, "Immediate Heal", before=5000, attempted_change=-5000, applied_change=-5000, after=0),
            _event(20.0, ResourceTimelineEventKind.RESTORATION, "Verified Restore", before=0, attempted_change=5000, applied_change=5000, after=5000),
        ),
    )

    budget = derive_rotation_window_resource_budget(
        timeline=timeline,
        start_seconds=10.0,
        end_seconds=21.0,
        required_spends=(RequiredRotationSpend(10.0, "Immediate Heal"),),
    )

    assert budget.required_spend_amount == 5000
    assert budget.verified_gain_amount == 5000
    assert budget.minimum_entry_amount == 5000
    assert budget.ending_amount_from_minimum_entry == 5000


def test_budget_uses_attempted_cost_when_existing_timeline_shortfalls() -> None:
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=1000,
        ending_amount=0,
        events=(
            _event(
                10.0,
                ResourceTimelineEventKind.ACTION_COST,
                "Required Heal",
                before=1000,
                attempted_change=-3000,
                applied_change=-1000,
                after=0,
                shortfall=2000,
            ),
        ),
    )

    budget = derive_rotation_window_resource_budget(
        timeline=timeline,
        start_seconds=10.0,
        end_seconds=17.0,
        required_spends=(RequiredRotationSpend(10.0, "Required Heal"),),
    )

    assert budget.required_spend_amount == 3000
    assert budget.minimum_entry_amount == 3000


def test_budget_rejects_required_spend_outside_window() -> None:
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=10000,
        ending_amount=10000,
        events=(),
    )

    with pytest.raises(ValueError, match="outside resource budget window"):
        derive_rotation_window_resource_budget(
            timeline=timeline,
            start_seconds=10.0,
            end_seconds=17.0,
            required_spends=(RequiredRotationSpend(17.0, "Too Late"),),
        )
