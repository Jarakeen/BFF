import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    RotationResourceReserveRequirement,
)
from minmax.rotation_reserve_priority import (
    ReserveProtectionPriority,
    plan_rotation_reserve_protection,
)
from minmax.rotation_reserve_protection import (
    ReserveProtectionCandidate,
    RotationReserveProtectionAnalysis,
)


def _analysis(*, available: int, required: int, amounts: tuple[int, ...]) -> RotationReserveProtectionAnalysis:
    demand = RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    requirement = RotationResourceReserveRequirement(
        demand_name=demand.name,
        resource=ResourceType.MAGICKA,
        minimum_amount=required,
    )
    reserve = RotationResourceReserveAssessment(
        demand=demand,
        requirement=requirement,
        available_before_start=available,
    )
    candidates = tuple(
        ReserveProtectionCandidate(
            time_seconds=float(index + 1),
            source=f"Optional {index + 1}",
            resource=ResourceType.MAGICKA,
            amount=amount,
        )
        for index, amount in enumerate(amounts)
    )
    return RotationReserveProtectionAnalysis(
        demand=demand,
        reserve_assessment=reserve,
        candidates=candidates,
        recoverable_amount=sum(amounts),
        projected_available_if_all_withheld=available + sum(amounts),
    )


def test_priority_plan_withholds_only_first_action_when_that_repairs_reserve() -> None:
    analysis = _analysis(available=14500, required=16000, amounts=(2500, 3000))

    plan = plan_rotation_reserve_protection(
        analysis=analysis,
        priorities=(
            ReserveProtectionPriority(time_seconds=1.0, source="Optional 1", delay_order=0),
            ReserveProtectionPriority(time_seconds=2.0, source="Optional 2", delay_order=1),
        ),
    )

    assert [item.candidate.source for item in plan.ranked_candidates] == [
        "Optional 1",
        "Optional 2",
    ]
    assert [item.candidate.source for item in plan.selected_to_withhold] == ["Optional 1"]
    assert plan.projected_available_after_selected == 17000
    assert plan.projected_shortfall_after_selected == 0
    assert plan.reserve_repaired is True


def test_priority_plan_uses_multiple_actions_when_policy_prefix_is_required() -> None:
    analysis = _analysis(available=10000, required=16000, amounts=(2500, 3000, 2000))

    plan = plan_rotation_reserve_protection(
        analysis=analysis,
        priorities=(
            ReserveProtectionPriority(time_seconds=3.0, source="Optional 3", delay_order=2),
            ReserveProtectionPriority(time_seconds=1.0, source="Optional 1", delay_order=0),
            ReserveProtectionPriority(time_seconds=2.0, source="Optional 2", delay_order=1),
        ),
    )

    assert [item.candidate.source for item in plan.selected_to_withhold] == [
        "Optional 1",
        "Optional 2",
        "Optional 3",
    ]
    assert plan.projected_available_after_selected == 17500
    assert plan.reserve_repaired is True


def test_priority_plan_reports_unrepaired_when_all_policy_actions_are_insufficient() -> None:
    analysis = _analysis(available=10000, required=18000, amounts=(2500, 3000))

    plan = plan_rotation_reserve_protection(
        analysis=analysis,
        priorities=(
            ReserveProtectionPriority(time_seconds=1.0, source="Optional 1", delay_order=0),
            ReserveProtectionPriority(time_seconds=2.0, source="Optional 2", delay_order=1),
        ),
    )

    assert plan.projected_available_after_selected == 15500
    assert plan.projected_shortfall_after_selected == 2500
    assert plan.reserve_repaired is False


def test_priority_plan_requires_explicit_priority_for_every_candidate() -> None:
    analysis = _analysis(available=14500, required=16000, amounts=(2500, 3000))

    with pytest.raises(ValueError, match="missing explicit priority"):
        plan_rotation_reserve_protection(
            analysis=analysis,
            priorities=(
                ReserveProtectionPriority(time_seconds=1.0, source="Optional 1", delay_order=0),
            ),
        )


def test_priority_plan_rejects_duplicate_delay_orders() -> None:
    analysis = _analysis(available=14500, required=16000, amounts=(2500, 3000))

    with pytest.raises(ValueError, match="duplicate reserve protection delay order"):
        plan_rotation_reserve_protection(
            analysis=analysis,
            priorities=(
                ReserveProtectionPriority(time_seconds=1.0, source="Optional 1", delay_order=0),
                ReserveProtectionPriority(time_seconds=2.0, source="Optional 2", delay_order=0),
            ),
        )
