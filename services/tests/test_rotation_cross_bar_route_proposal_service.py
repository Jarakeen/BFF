from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_cross_bar_filler_opportunity_service import (
    RotationCrossBarFillerOpportunity,
)
from services.rotation_cross_bar_route_proposal_service import (
    RotationCrossBarRouteProposalService,
)


def _action(time_seconds, sequence, kind, name=None, bar=None):
    return RotationAction(
        time_seconds=float(time_seconds),
        sequence=int(sequence),
        kind=kind,
        name=name,
        bar=bar,
    )


def test_route_proposal_marks_return_swap_when_next_skill_is_back_bar() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=20.0,
        actions=(
            _action(10, 0, RotationActionKind.WAIT, bar="back"),
            _action(12, 1, RotationActionKind.SKILL, "Scalding Rune", "back"),
        ),
    )
    opportunity = RotationCrossBarFillerOpportunity(
        wait_time_seconds=10.0,
        wait_bar="back",
        target_bar="front",
        filler_skill_name="Venom Skull",
        filler_priority=1,
    )

    proposals = RotationCrossBarRouteProposalService().propose(plan, (opportunity,))

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.source_bar == "back"
    assert proposal.target_bar == "front"
    assert proposal.filler_skill_name == "Venom Skull"
    assert proposal.next_required_bar == "back"
    assert proposal.next_required_time_seconds == 12.0
    assert proposal.return_swap_required is True


def test_route_proposal_does_not_require_return_when_next_skill_is_target_bar() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=20.0,
        actions=(
            _action(10, 0, RotationActionKind.WAIT, bar="back"),
            _action(11, 1, RotationActionKind.SKILL, "Venom Skull", "front"),
        ),
    )
    opportunity = RotationCrossBarFillerOpportunity(
        wait_time_seconds=10.0,
        wait_bar="back",
        target_bar="front",
        filler_skill_name="Venom Skull",
        filler_priority=1,
    )

    proposal = RotationCrossBarRouteProposalService().propose(plan, (opportunity,))[0]

    assert proposal.next_required_bar == "front"
    assert proposal.next_required_time_seconds == 11.0
    assert proposal.return_swap_required is False


def test_route_proposal_leaves_return_unresolved_at_plan_end() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=10.0,
        actions=(
            _action(10, 0, RotationActionKind.WAIT, bar="back"),
        ),
    )
    opportunity = RotationCrossBarFillerOpportunity(
        wait_time_seconds=10.0,
        wait_bar="back",
        target_bar="front",
        filler_skill_name="Venom Skull",
        filler_priority=1,
    )

    proposal = RotationCrossBarRouteProposalService().propose(plan, (opportunity,))[0]

    assert proposal.next_required_bar is None
    assert proposal.next_required_time_seconds is None
    assert proposal.return_swap_required is False
