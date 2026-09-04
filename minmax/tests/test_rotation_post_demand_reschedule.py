import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_post_demand_reschedule import (
    PostDemandActionDirective,
    PostDemandDisposition,
    propose_post_demand_reschedule,
)
from minmax.rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    RotationResourceReserveRequirement,
)
from minmax.rotation_reserve_adjustment import (
    RotationReserveAdjustmentProposal,
    WithheldRotationAction,
)
from minmax.rotation_reserve_priority import (
    RankedReserveProtectionCandidate,
    RotationReserveProtectionPlan,
)
from minmax.rotation_reserve_protection import (
    ReserveProtectionCandidate,
    RotationReserveProtectionAnalysis,
)


def _proposal() -> RotationReserveAdjustmentProposal:
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
        minimum_amount=16000,
    )
    reserve = RotationResourceReserveAssessment(
        demand=demand,
        requirement=requirement,
        available_before_start=14500,
    )
    candidate = ReserveProtectionCandidate(
        time_seconds=5.0,
        source="Optional Filler",
        resource=ResourceType.MAGICKA,
        amount=2500,
    )
    analysis = RotationReserveProtectionAnalysis(
        demand=demand,
        reserve_assessment=reserve,
        candidates=(candidate,),
        recoverable_amount=2500,
        projected_available_if_all_withheld=17000,
    )
    ranked = RankedReserveProtectionCandidate(candidate=candidate, delay_order=0)
    protection = RotationReserveProtectionPlan(
        analysis=analysis,
        ranked_candidates=(ranked,),
        selected_to_withhold=(ranked,),
        projected_available_after_selected=17000,
    )

    withheld_action = RotationAction(
        time_seconds=5.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Optional Filler",
        bar="front",
    )
    critical_action = RotationAction(
        time_seconds=17.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Critical Heal",
        bar="front",
    )
    original = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(withheld_action, critical_action),
    )
    adjusted = RotationPlan(
        character_name=original.character_name,
        build_name=original.build_name,
        duration_seconds=original.duration_seconds,
        actions=(critical_action,),
        assumptions=("reserve protection applied",),
    )
    return RotationReserveAdjustmentProposal(
        original_plan=original,
        adjusted_plan=adjusted,
        protection_plan=protection,
        withheld_actions=(
            WithheldRotationAction(
                action=withheld_action,
                candidate_source="Optional Filler",
                recovered_amount=2500,
            ),
        ),
    )


def test_post_demand_reschedule_reinserts_action_at_explicit_safe_time() -> None:
    proposal = propose_post_demand_reschedule(
        reserve_adjustment=_proposal(),
        directives=(
            PostDemandActionDirective(
                original_time_seconds=5.0,
                original_sequence=0,
                disposition=PostDemandDisposition.RESCHEDULE,
                new_time_seconds=18.0,
                new_sequence=0,
            ),
        ),
    )

    assert [(a.time_seconds, a.name) for a in proposal.adjusted_plan.actions] == [
        (17.0, "Critical Heal"),
        (18.0, "Optional Filler"),
    ]
    assert proposal.outcomes[0].replacement_action is not None
    assert proposal.outcomes[0].replacement_action.bar == "front"
    assert proposal.outcomes[0].disposition is PostDemandDisposition.RESCHEDULE
    assert "explicit caller-supplied timing" in proposal.adjusted_plan.assumptions[-1]


def test_post_demand_reschedule_allows_explicit_omission() -> None:
    proposal = propose_post_demand_reschedule(
        reserve_adjustment=_proposal(),
        directives=(
            PostDemandActionDirective(
                original_time_seconds=5.0,
                original_sequence=0,
                disposition=PostDemandDisposition.OMIT,
            ),
        ),
    )

    assert [action.name for action in proposal.adjusted_plan.actions] == ["Critical Heal"]
    assert proposal.outcomes[0].replacement_action is None
    assert proposal.outcomes[0].disposition is PostDemandDisposition.OMIT


def test_post_demand_reschedule_requires_disposition_for_every_withheld_action() -> None:
    with pytest.raises(ValueError, match="missing explicit post-demand disposition"):
        propose_post_demand_reschedule(
            reserve_adjustment=_proposal(),
            directives=(),
        )


def test_post_demand_reschedule_rejects_replacement_before_demand_end() -> None:
    with pytest.raises(ValueError, match="at or after demand end"):
        propose_post_demand_reschedule(
            reserve_adjustment=_proposal(),
            directives=(
                PostDemandActionDirective(
                    original_time_seconds=5.0,
                    original_sequence=0,
                    disposition=PostDemandDisposition.RESCHEDULE,
                    new_time_seconds=16.5,
                    new_sequence=0,
                ),
            ),
        )


def test_post_demand_reschedule_rejects_collision_with_existing_action() -> None:
    with pytest.raises(ValueError, match="collides with another rotation action"):
        propose_post_demand_reschedule(
            reserve_adjustment=_proposal(),
            directives=(
                PostDemandActionDirective(
                    original_time_seconds=5.0,
                    original_sequence=0,
                    disposition=PostDemandDisposition.RESCHEDULE,
                    new_time_seconds=17.0,
                    new_sequence=0,
                ),
            ),
        )


def test_post_demand_reschedule_rejects_replacement_after_plan_duration() -> None:
    with pytest.raises(ValueError, match="after plan duration"):
        propose_post_demand_reschedule(
            reserve_adjustment=_proposal(),
            directives=(
                PostDemandActionDirective(
                    original_time_seconds=5.0,
                    original_sequence=0,
                    disposition=PostDemandDisposition.RESCHEDULE,
                    new_time_seconds=31.0,
                    new_sequence=0,
                ),
            ),
        )
