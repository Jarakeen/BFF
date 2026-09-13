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


def test_stay_on_target_route_uses_one_wait_skill_slot() -> None:
    plan = _plan(_wait(33), _skill(36, "Venom Skull", "front"))
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
    assert result.required_wait_slots == 1
    assert result.available_wait_times == (33.0,)
    assert "non-GCD bar swap" in result.reason


def test_return_route_uses_one_wait_slot_before_next_source_bar_skill() -> None:
    plan = _plan(_wait(19), _skill(20, "Stampede", "back"))
    proposal = RotationCrossBarRouteProposal(
        wait_time_seconds=19.0,
        source_bar="back",
        target_bar="front",
        filler_skill_name="Venom Skull",
        filler_priority=1,
        next_required_bar="back",
        next_required_time_seconds=20.0,
        return_swap_required=True,
    )

    result = RotationCrossBarRouteSlotFeasibilityService().assess(plan, (proposal,))[0]

    assert result.feasible is True
    assert result.required_wait_slots == 1
    assert result.available_wait_times == (19.0,)
    assert "same-GCD return swap" in result.reason


def test_route_fails_closed_without_wait_skill_slot() -> None:
    plan = _plan(_skill(10, "Scalding Rune", "back"), _skill(12, "Blighted Blastbones", "front"))
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
    assert result.required_wait_slots == 1
    assert result.available_wait_times == ()
    assert "none is available" in result.reason


def test_route_rejects_same_timestamp_next_skill_obligation() -> None:
    plan = _plan(_wait(10), _skill(10, "Blighted Blastbones", "front"))
    proposal = RotationCrossBarRouteProposal(
        wait_time_seconds=10.0,
        source_bar="back",
        target_bar="front",
        filler_skill_name="Venom Skull",
        filler_priority=1,
        next_required_bar="front",
        next_required_time_seconds=10.0,
        return_swap_required=False,
    )

    result = RotationCrossBarRouteSlotFeasibilityService().assess(plan, (proposal,))[0]

    assert result.feasible is False
    assert "collide" in result.reason
