from minmax.resource_costs import ResourceType
from minmax.resource_timeline import (
    AppliedResourceTimelineEvent,
    ResourceTimelineEventKind,
    ResourceTimelineResult,
)
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
    create_staggered_burst_demands,
)
from minmax.rotation_resource_reserve import (
    RotationResourceReserveRequirement,
    assess_rotation_resource_reserve,
    assess_rotation_resource_reserves,
    resource_amount_before,
    resource_maximum_before,
)


def _timeline() -> ResourceTimelineResult:
    return ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=20_000,
        ending_amount=8_000,
        events=(
            AppliedResourceTimelineEvent(
                time_seconds=4.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="maintenance",
                before=20_000,
                attempted_change=-4_000,
                applied_change=-4_000,
                after=16_000,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=10.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="cage one burst",
                before=16_000,
                attempted_change=-6_000,
                applied_change=-6_000,
                after=10_000,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=13.0,
                kind=ResourceTimelineEventKind.RECOVERY_TICK,
                source="In-combat recovery tick",
                before=10_000,
                attempted_change=2_000,
                applied_change=2_000,
                after=12_000,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=14.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="cage two burst",
                before=12_000,
                attempted_change=-4_000,
                applied_change=-4_000,
                after=8_000,
            ),
        ),
    )


def _bar_sensitive_timeline() -> ResourceTimelineResult:
    return ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=24_000,
        ending_amount=12_000,
        starting_maximum=30_000,
        ending_maximum=36_000,
        events=(
            AppliedResourceTimelineEvent(
                time_seconds=4.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="maintenance",
                before=24_000,
                attempted_change=-6_000,
                applied_change=-6_000,
                after=18_000,
                maximum_before=30_000,
                maximum_after=30_000,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=8.0,
                kind=ResourceTimelineEventKind.RESOURCE_MAXIMUM,
                source="bar swap to back",
                before=18_000,
                attempted_change=0,
                applied_change=0,
                after=18_000,
                maximum_before=30_000,
                maximum_after=36_000,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=12.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="burst prep",
                before=18_000,
                attempted_change=-6_000,
                applied_change=-6_000,
                after=12_000,
                maximum_before=36_000,
                maximum_after=36_000,
            ),
        ),
    )


def test_resource_amount_before_uses_strict_demand_entry_boundary() -> None:
    timeline = _timeline()

    assert resource_amount_before(timeline, 0.0) == 20_000
    assert resource_amount_before(timeline, 10.0) == 16_000
    assert resource_amount_before(timeline, 14.0) == 12_000


def test_resource_maximum_before_uses_strict_demand_entry_boundary() -> None:
    timeline = _bar_sensitive_timeline()

    assert resource_maximum_before(timeline, 0.0) == 30_000
    assert resource_maximum_before(timeline, 8.0) == 30_000
    assert resource_maximum_before(timeline, 8.001) == 36_000
    assert resource_maximum_before(_timeline(), 10.0) is None


def test_staggered_healer_demands_can_require_independent_reserves() -> None:
    first, second = create_staggered_burst_demands(
        name="Ice Cage",
        first_start_seconds=10.0,
        second_start_seconds=14.0,
        deadline_seconds=7.0,
    )
    assessments = assess_rotation_resource_reserves(
        timeline=_timeline(),
        demands=(first, second),
        requirements=(
            RotationResourceReserveRequirement(
                demand_name="Ice Cage 1",
                resource=ResourceType.MAGICKA,
                minimum_amount=15_000,
            ),
            RotationResourceReserveRequirement(
                demand_name="Ice Cage 2",
                resource=ResourceType.MAGICKA,
                minimum_amount=13_000,
            ),
        ),
    )

    assert [(item.demand.name, item.available_before_start) for item in assessments] == [
        ("Ice Cage 1", 16_000),
        ("Ice Cage 2", 12_000),
    ]
    assert assessments[0].satisfied is True
    assert assessments[0].shortfall == 0
    assert assessments[0].available_fraction_before_start is None
    assert assessments[1].satisfied is False
    assert assessments[1].shortfall == 1_000


def test_bar_sensitive_reserve_assessment_exposes_normalized_entry_state() -> None:
    demand = RotationDemandWindow(
        name="Burst window",
        start_seconds=12.0,
        end_seconds=16.0,
        kind=RotationDemandKind.DAMAGE,
        pattern=RotationDemandPattern.BURST,
    )
    assessment = assess_rotation_resource_reserve(
        timeline=_bar_sensitive_timeline(),
        demand=demand,
        requirement=RotationResourceReserveRequirement(
            demand_name="Burst window",
            resource=ResourceType.MAGICKA,
            minimum_amount=17_000,
        ),
    )

    assert assessment.available_before_start == 18_000
    assert assessment.maximum_before_start == 36_000
    assert assessment.available_fraction_before_start == 0.5
    assert assessment.satisfied is True


def test_sustained_pressure_uses_same_role_neutral_reserve_contract() -> None:
    demand = RotationDemandWindow(
        name="Bahsei bleed phase",
        start_seconds=10.0,
        end_seconds=190.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.SUSTAINED,
        target_count=2,
    )
    assessment = assess_rotation_resource_reserve(
        timeline=_timeline(),
        demand=demand,
        requirement=RotationResourceReserveRequirement(
            demand_name="Bahsei bleed phase",
            resource=ResourceType.MAGICKA,
            minimum_amount=17_000,
        ),
    )

    assert assessment.available_before_start == 16_000
    assert assessment.satisfied is False
    assert assessment.shortfall == 1_000


def test_missing_reserve_requirement_is_not_silently_treated_as_zero() -> None:
    first, second = create_staggered_burst_demands(
        name="Ice Cage",
        first_start_seconds=10.0,
        second_start_seconds=14.0,
        deadline_seconds=7.0,
    )
    assessments = assess_rotation_resource_reserves(
        timeline=_timeline(),
        demands=(first, second),
        requirements=(
            RotationResourceReserveRequirement(
                demand_name="Ice Cage 2",
                resource="magicka",
                minimum_amount=11_000,
            ),
        ),
    )

    assert [item.demand.name for item in assessments] == ["Ice Cage 2"]
    assert assessments[0].satisfied is True


def test_reserve_assessment_rejects_mismatched_or_duplicate_requirements() -> None:
    demand = RotationDemandWindow(
        name="Damage burst",
        start_seconds=10.0,
        end_seconds=15.0,
        kind=RotationDemandKind.DAMAGE,
        pattern=RotationDemandPattern.BURST,
    )

    try:
        assess_rotation_resource_reserve(
            timeline=_timeline(),
            demand=demand,
            requirement=RotationResourceReserveRequirement(
                demand_name="Damage burst",
                resource=ResourceType.STAMINA,
                minimum_amount=1,
            ),
        )
    except ValueError as exc:
        assert "does not match timeline" in str(exc)
    else:
        raise AssertionError("Expected mismatched reserve resource to fail")

    duplicate = RotationResourceReserveRequirement(
        demand_name="Damage burst",
        resource=ResourceType.MAGICKA,
        minimum_amount=1,
    )
    try:
        assess_rotation_resource_reserves(
            timeline=_timeline(),
            demands=(demand,),
            requirements=(duplicate, duplicate),
        )
    except ValueError as exc:
        assert "duplicate resource reserve requirement" in str(exc)
    else:
        raise AssertionError("Expected duplicate demand reserve requirements to fail")
