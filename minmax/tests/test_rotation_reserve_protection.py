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
)
from minmax.rotation_reserve_protection import (
    DiscretionaryRotationSpend,
    analyze_rotation_reserve_protection,
)
from minmax.rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    RotationResourceReserveRequirement,
)


def _timeline() -> ResourceTimelineResult:
    return ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=20000,
        ending_amount=12000,
        events=(
            AppliedResourceTimelineEvent(
                time_seconds=5.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="Optional Filler",
                before=20000,
                attempted_change=-2500,
                applied_change=-2500,
                after=17500,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=8.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="Early Refresh",
                before=17500,
                attempted_change=-3000,
                applied_change=-3000,
                after=14500,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=10.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="Cage Heal",
                before=14500,
                attempted_change=-2500,
                applied_change=-2500,
                after=12000,
            ),
        ),
    )


def _assessment() -> RotationResourceReserveAssessment:
    demand = RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    requirement = RotationResourceReserveRequirement(
        demand_name="Ice Cage 1",
        resource=ResourceType.MAGICKA,
        minimum_amount=16000,
    )
    return RotationResourceReserveAssessment(
        demand=demand,
        requirement=requirement,
        available_before_start=14500,
    )


def test_reserve_protection_quantifies_explicit_discretionary_spend() -> None:
    analysis = analyze_rotation_reserve_protection(
        timeline=_timeline(),
        reserve_assessment=_assessment(),
        discretionary_spends=(
            DiscretionaryRotationSpend(5.0, "Optional Filler"),
            DiscretionaryRotationSpend(8.0, "Early Refresh"),
        ),
    )

    assert [(item.time_seconds, item.source, item.amount) for item in analysis.candidates] == [
        (5.0, "Optional Filler", 2500),
        (8.0, "Early Refresh", 3000),
    ]
    assert analysis.recoverable_amount == 5500
    assert analysis.projected_available_if_all_withheld == 20000
    assert analysis.projected_shortfall_if_all_withheld == 0
    assert analysis.can_repair_shortfall is True


def test_reserve_protection_excludes_actions_at_demand_start() -> None:
    try:
        analyze_rotation_reserve_protection(
            timeline=_timeline(),
            reserve_assessment=_assessment(),
            discretionary_spends=(
                DiscretionaryRotationSpend(10.0, "Cage Heal"),
            ),
        )
    except ValueError as exc:
        assert "pre-demand action cost" in str(exc)
    else:
        raise AssertionError("Expected demand-start response action to be excluded")


def test_reserve_protection_reports_when_discretionary_spend_cannot_close_gap() -> None:
    assessment = RotationResourceReserveAssessment(
        demand=_assessment().demand,
        requirement=RotationResourceReserveRequirement(
            demand_name="Ice Cage 1",
            resource=ResourceType.MAGICKA,
            minimum_amount=18000,
        ),
        available_before_start=14500,
    )
    analysis = analyze_rotation_reserve_protection(
        timeline=_timeline(),
        reserve_assessment=assessment,
        discretionary_spends=(
            DiscretionaryRotationSpend(5.0, "Optional Filler"),
        ),
    )

    assert analysis.recoverable_amount == 2500
    assert analysis.projected_available_if_all_withheld == 17000
    assert analysis.projected_shortfall_if_all_withheld == 1000
    assert analysis.can_repair_shortfall is False


def test_reserve_protection_requires_explicit_unambiguous_declarations() -> None:
    duplicate = (
        DiscretionaryRotationSpend(5.0, "Optional Filler"),
        DiscretionaryRotationSpend(5.0, "Optional Filler"),
    )

    try:
        analyze_rotation_reserve_protection(
            timeline=_timeline(),
            reserve_assessment=_assessment(),
            discretionary_spends=duplicate,
        )
    except ValueError as exc:
        assert "duplicate discretionary spend declaration" in str(exc)
    else:
        raise AssertionError("Expected duplicate discretionary declaration to be rejected")
