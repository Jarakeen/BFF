from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_cross_bar_route_proposal_service import RotationCrossBarRouteProposal
from services.rotation_cross_bar_route_slot_feasibility_service import (
    RotationCrossBarRouteSlotFeasibilityService,
)


def _wait(time_seconds: float, bar: str = "back") -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.WAIT,
        bar=bar,
    )


def _skill(time_seconds: float, name: str, bar: str) -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=1,
        kind=RotationActionKind.SKILL,
        name=name,
        bar=bar,
    )


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=60.0,
        actions=actions,
    )


def test_stay_on_target_route_requires_two_consecutive_wait_slots() -> None:
    plan = _plan(_wait(33), _wait(34), _skill(36, "Venom Skull", "front"))
    proposal = RotationCrossBarRouteProposal(
        wait_time_seconds=33.0,
        source_bar="back",
        target_bar="front",
        filler_skill_name="Venom Skull",
        filler_priority=1,
        next_required_bar="front",
        next_required_time_seconds=36.0,
        return_swap_required=False,
    )

    result = RotationCrossBarRouteSlotFeasibilityService().assess(plan, (proposal,))[0]

    assert result.feasible is True
    assert result.required_wait_slots == 2
    assert result.available_wait_times == (33.0, 34.0)


def test_return_route_fails_when_next_required_action_leaves_no_return_slot() -> None:
    plan = _plan(_wait(19), _wait(20), _skill(21, "Stampede", "back"))
    proposal = RotationCrossBarRouteProposal(
        wait_time_seconds=19.0,
        source_bar="back",
        target_bar="front",
        filler_skill_name="Venom Skull",
        filler_priority=1,
        next_required_bar="back",
        next_required_time_seconds=21.0,
        return_swap_required=True,
    )

    result = RotationCrossBarRouteSlotFeasibilityService().assess(plan, (proposal,))[0]

    assert result.feasible is False
    assert result.required_wait_slots == 3
    assert result.available_wait_times == (19.0, 20.0)
    assert "only 2 are available" in result.reason


def test_single_wait_cannot_fabricate_same_second_swap_and_filler() -> None:
    plan = _plan(_wait(10), _skill(12, "Blighted Blastbones", "front"))
    proposal = RotationCrossBarRouteProposal(
        wait_time_seconds=10.0,
        source_bar="back",
        target_bar="front",
        filler_skill_name="Venom Skull",
        filler_priority=1,
        next_required_bar="front",
        next_required_time_seconds=12.0,
        return_swap_required=False,
    )

    result = RotationCrossBarRouteSlotFeasibilityService().assess(plan, (proposal,))[0]

    assert result.feasible is False
    assert result.available_wait_times == (10.0,)
