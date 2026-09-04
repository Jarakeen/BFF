import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    RotationResourceReserveRequirement,
)
from minmax.rotation_reserve_adjustment import (
    ReserveProtectionActionBinding,
    propose_rotation_reserve_adjustment,
)
from minmax.rotation_reserve_priority import (
    ReserveProtectionPriority,
    plan_rotation_reserve_protection,
)
from minmax.rotation_reserve_protection import (
    ReserveProtectionCandidate,
    RotationReserveProtectionAnalysis,
)


def _protection_plan(*, available: int = 14000, required: int = 16000):
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
    candidates = (
        ReserveProtectionCandidate(
            time_seconds=7.0,
            source="Optional Filler",
            resource=ResourceType.MAGICKA,
            amount=2500,
        ),
        ReserveProtectionCandidate(
            time_seconds=8.0,
            source="Early Refresh",
            resource=ResourceType.MAGICKA,
            amount=3000,
        ),
    )
    analysis = RotationReserveProtectionAnalysis(
        demand=demand,
        reserve_assessment=reserve,
        candidates=candidates,
        recoverable_amount=5500,
        projected_available_if_all_withheld=available + 5500,
    )
    return plan_rotation_reserve_protection(
        analysis=analysis,
        priorities=(
            ReserveProtectionPriority(
                time_seconds=7.0,
                source="Optional Filler",
                delay_order=0,
            ),
            ReserveProtectionPriority(
                time_seconds=8.0,
                source="Early Refresh",
                delay_order=1,
            ),
        ),
    )


def _rotation_plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(
                time_seconds=7.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
            RotationAction(
                time_seconds=8.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Budding Seeds",
                bar="front",
            ),
            RotationAction(
                time_seconds=10.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Illustrious Healing",
                bar="front",
            ),
        ),
    )


def test_adjustment_withholds_only_selected_bound_action_and_preserves_original() -> None:
    protection = _protection_plan()
    original = _rotation_plan()

    proposal = propose_rotation_reserve_adjustment(
        plan=original,
        protection_plan=protection,
        bindings=(
            ReserveProtectionActionBinding(
                candidate_time_seconds=7.0,
                candidate_source="Optional Filler",
                action_time_seconds=7.0,
                action_sequence=0,
            ),
        ),
    )

    assert [action.name for action in original.actions] == [
        "Combat Prayer",
        "Budding Seeds",
        "Illustrious Healing",
    ]
    assert [action.name for action in proposal.adjusted_plan.actions] == [
        "Budding Seeds",
        "Illustrious Healing",
    ]
    assert proposal.withheld_actions[0].action.name == "Combat Prayer"
    assert proposal.withheld_actions[0].candidate_source == "Optional Filler"
    assert proposal.withheld_actions[0].recovered_amount == 2500
    assert "no replacement timing is inferred" in proposal.adjusted_plan.assumptions[-1]


def test_adjustment_requires_binding_for_every_selected_candidate() -> None:
    protection = _protection_plan(available=10000, required=16000)

    with pytest.raises(ValueError, match="missing an action binding"):
        propose_rotation_reserve_adjustment(
            plan=_rotation_plan(),
            protection_plan=protection,
            bindings=(
                ReserveProtectionActionBinding(
                    candidate_time_seconds=7.0,
                    candidate_source="Optional Filler",
                    action_time_seconds=7.0,
                    action_sequence=0,
                ),
            ),
        )


def test_adjustment_rejects_binding_for_unselected_candidate() -> None:
    protection = _protection_plan()

    with pytest.raises(ValueError, match="does not match a selected candidate"):
        propose_rotation_reserve_adjustment(
            plan=_rotation_plan(),
            protection_plan=protection,
            bindings=(
                ReserveProtectionActionBinding(
                    candidate_time_seconds=8.0,
                    candidate_source="Early Refresh",
                    action_time_seconds=8.0,
                    action_sequence=0,
                ),
            ),
        )


def test_adjustment_rejects_binding_that_does_not_match_schedule_action() -> None:
    protection = _protection_plan()

    with pytest.raises(ValueError, match="does not match a rotation action"):
        propose_rotation_reserve_adjustment(
            plan=_rotation_plan(),
            protection_plan=protection,
            bindings=(
                ReserveProtectionActionBinding(
                    candidate_time_seconds=7.0,
                    candidate_source="Optional Filler",
                    action_time_seconds=7.0,
                    action_sequence=99,
                ),
            ),
        )
