from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_cross_bar_route_proposal_service import RotationCrossBarRouteProposal
from services.rotation_cross_bar_route_selection_service import RotationCrossBarRouteSelectionService
from services.rotation_cross_bar_route_slot_feasibility_service import (
    RotationCrossBarRouteSlotFeasibility,
)


def _wait(time_seconds: float, bar: str = "back") -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.WAIT,
        bar=bar,
    )


def _proposal(time_seconds: float, *, return_swap: bool = False) -> RotationCrossBarRouteProposal:
    return RotationCrossBarRouteProposal(
        wait_time_seconds=time_seconds,
        source_bar="back",
        target_bar="front",
        filler_skill_name="Venom Skull",
        filler_priority=1,
        next_required_bar="back" if return_swap else "front",
        next_required_time_seconds=time_seconds + 1.0,
        return_swap_required=return_swap,
    )


def _feasible(time_seconds: float, *, required: int = 1) -> RotationCrossBarRouteSlotFeasibility:
    return RotationCrossBarRouteSlotFeasibility(
        wait_time_seconds=time_seconds,
        source_bar="back",
        target_bar="front",
        filler_skill_name="Venom Skull",
        required_wait_slots=required,
        available_wait_times=tuple(time_seconds + offset for offset in range(required)),
        feasible=True,
        reason="route fits",
    )


def test_selector_rejects_duplicate_route_competing_for_same_wait_slot() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=50.0,
        actions=(
            RotationAction(40.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _wait(44.0),
        ),
    )
    first = _proposal(44.0, return_swap=True)
    second = _proposal(44.0, return_swap=True)

    result = RotationCrossBarRouteSelectionService().select(
        plan,
        (first, second),
        (_feasible(44.0),),
    )

    assert [row.proposal.wait_time_seconds for row in result.selected] == [44.0]
    assert [row.proposal.wait_time_seconds for row in result.rejected] == [44.0]
    assert "overlaps WAIT slot" in result.rejected[0].reason


def test_selector_tracks_active_bar_after_stay_on_target_route() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=40.0,
        actions=(
            RotationAction(30.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _wait(33.0),
            _wait(36.0),
        ),
    )
    first = _proposal(33.0)
    stale = _proposal(36.0)

    result = RotationCrossBarRouteSelectionService().select(
        plan,
        (first, stale),
        (_feasible(33.0), _feasible(36.0)),
    )

    assert [row.proposal.wait_time_seconds for row in result.selected] == [33.0]
    assert [row.proposal.wait_time_seconds for row in result.rejected] == [36.0]
    assert "source bar is stale" in result.rejected[0].reason


def test_selector_return_route_restores_source_bar_for_next_wait_route() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=50.0,
        actions=(
            RotationAction(30.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _wait(33.0),
            _wait(34.0),
        ),
    )

    result = RotationCrossBarRouteSelectionService().select(
        plan,
        (_proposal(33.0, return_swap=True), _proposal(34.0, return_swap=True)),
        (_feasible(33.0), _feasible(34.0)),
    )

    assert [row.proposal.wait_time_seconds for row in result.selected] == [33.0, 34.0]
    assert result.rejected == ()


def test_selector_honors_original_bar_swap_before_later_route() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=50.0,
        actions=(
            RotationAction(30.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _wait(33.0),
            RotationAction(40.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _wait(44.0),
        ),
    )

    result = RotationCrossBarRouteSelectionService().select(
        plan,
        (_proposal(33.0), _proposal(44.0)),
        (_feasible(33.0), _feasible(44.0)),
    )

    assert [row.proposal.wait_time_seconds for row in result.selected] == [33.0, 44.0]
    assert result.rejected == ()
