from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_cross_bar_route_mutation_service import (
    RotationCrossBarRouteMutationService,
)
from services.rotation_cross_bar_route_proposal_service import RotationCrossBarRouteProposal
from services.rotation_cross_bar_route_selection_service import (
    RotationCrossBarRouteSelection,
    RotationCrossBarRouteSelectionResult,
)


def _plan(*actions, unresolved=()) -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=60.0,
        actions=tuple(actions),
        unresolved=tuple(unresolved),
    )


def _wait(time_seconds: float, bar: str = "back") -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.WAIT,
        bar=bar,
    )


def _swap(time_seconds: float, bar: str) -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.BAR_SWAP,
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


def _selection(
    *,
    start: float,
    source: str = "back",
    target: str = "front",
    filler: str = "Venom Skull",
    return_swap_required: bool = False,
) -> RotationCrossBarRouteSelection:
    proposal = RotationCrossBarRouteProposal(
        wait_time_seconds=start,
        source_bar=source,
        target_bar=target,
        filler_skill_name=filler,
        filler_priority=1,
        next_required_bar=source if return_swap_required else target,
        next_required_time_seconds=start + 1.0,
        return_swap_required=return_swap_required,
    )
    return RotationCrossBarRouteSelection(
        proposal=proposal,
        reserved_wait_times=(start,),
    )


def test_applies_selected_stay_on_target_route_in_one_skill_gcd_slot() -> None:
    plan = _plan(
        _swap(30.0, "back"),
        _wait(33.0),
        _skill(36.0, "Blighted Blastbones", "front"),
        unresolved=(
            "premature recast of 'Stampede' at 33s had no verified same-bar no-duration filler or caller-proven replacement; scheduled wait instead",
            "execute-phase behavior is not yet scheduled",
        ),
    )
    selected = _selection(start=33.0)

    result = RotationCrossBarRouteMutationService().apply(
        plan,
        RotationCrossBarRouteSelectionResult(selected=(selected,), rejected=()),
    )

    at_33 = [action for action in result.plan.actions if action.time_seconds == 33.0]
    assert [(action.kind, action.name, action.bar, action.sequence) for action in at_33] == [
        (RotationActionKind.BAR_SWAP, None, "front", 0),
        (RotationActionKind.LIGHT_ATTACK, None, "front", 1),
        (RotationActionKind.SKILL, "Venom Skull", "front", 2),
    ]
    assert result.consumed_wait_times == (33.0,)
    assert result.plan.unresolved == ("execute-phase behavior is not yet scheduled",)


def test_applies_return_route_with_same_timestamp_return_swap() -> None:
    plan = _plan(
        _swap(18.0, "back"),
        _wait(19.0),
        _skill(20.0, "Stampede", "back"),
    )
    selected = _selection(start=19.0, return_swap_required=True)

    result = RotationCrossBarRouteMutationService().apply(
        plan,
        RotationCrossBarRouteSelectionResult(selected=(selected,), rejected=()),
    )

    at_19 = [action for action in result.plan.actions if action.time_seconds == 19.0]
    assert [(action.kind, action.name, action.bar, action.sequence) for action in at_19] == [
        (RotationActionKind.BAR_SWAP, None, "front", 0),
        (RotationActionKind.LIGHT_ATTACK, None, "front", 1),
        (RotationActionKind.SKILL, "Venom Skull", "front", 2),
        (RotationActionKind.BAR_SWAP, None, "back", 3),
    ]
    assert result.consumed_wait_times == (19.0,)
    assert any(
        action.time_seconds == 20.0
        and action.kind is RotationActionKind.SKILL
        and action.name == "Stampede"
        and action.bar == "back"
        for action in result.plan.actions
    )


def test_rejects_selected_route_when_reserved_slot_is_no_longer_wait() -> None:
    plan = _plan(
        _swap(30.0, "back"),
        _skill(33.0, "Scalding Rune", "back"),
    )
    selected = _selection(start=33.0)

    try:
        RotationCrossBarRouteMutationService().apply(
            plan,
            RotationCrossBarRouteSelectionResult(selected=(selected,), rejected=()),
        )
    except ValueError as exc:
        assert "no longer maps to WAIT slot" in str(exc)
    else:
        raise AssertionError("expected selected route with stale WAIT evidence to fail closed")


def test_rejects_legacy_multi_slot_selection() -> None:
    plan = _plan(_wait(33.0), _wait(34.0))
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
    selected = RotationCrossBarRouteSelection(
        proposal=proposal,
        reserved_wait_times=(33.0, 34.0),
    )

    try:
        RotationCrossBarRouteMutationService().apply(
            plan,
            RotationCrossBarRouteSelectionResult(selected=(selected,), rejected=()),
        )
    except ValueError as exc:
        assert "exactly one WAIT skill slot" in str(exc)
    else:
        raise AssertionError("expected legacy multi-slot route evidence to fail closed")


def test_no_selection_preserves_plan_identity() -> None:
    plan = _plan(_wait(10.0))
    result = RotationCrossBarRouteMutationService().apply(
        plan,
        RotationCrossBarRouteSelectionResult(selected=(), rejected=()),
    )
    assert result.plan is plan
    assert result.applied == ()
    assert result.consumed_wait_times == ()
