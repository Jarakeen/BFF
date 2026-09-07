from __future__ import annotations

from minmax.rotation_bar_availability import RotationBarAvailabilityWindow
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_demand_bar_access_service import (
    RotationDemandBarAccessClaim,
    RotationDemandBarAccessService,
)


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Phase 2 healing prep",
        start_seconds=29.13,
        end_seconds=34.13,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            RotationAction(28.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(29.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(30.0, 0, RotationActionKind.SKILL, "Expansive Frost Cloak", "back"),
            RotationAction(31.0, 0, RotationActionKind.WAIT, bar="back"),
            RotationAction(32.0, 0, RotationActionKind.SKILL, "Winter's Revenge", "back"),
            RotationAction(33.0, 0, RotationActionKind.WAIT, bar="back"),
            RotationAction(34.0, 0, RotationActionKind.WAIT, bar="back"),
            RotationAction(35.0, 0, RotationActionKind.BAR_SWAP, bar="front"),
            RotationAction(36.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
        ),
    )


def _claim() -> RotationDemandBarAccessClaim:
    return RotationDemandBarAccessClaim(
        demand_name="Phase 2 healing prep",
        bar="front",
        skill_name="Budding Seeds",
    )


def test_bar_access_claim_routes_to_required_bar_and_restores_displaced_skills() -> None:
    result = RotationDemandBarAccessService().refine(
        plan=_plan(),
        demands=(_demand(),),
        claim=_claim(),
    )

    assert result.applied is True
    rows = [
        (action.time_seconds, action.kind, action.name, action.bar)
        for action in result.plan.actions
        if 30.0 <= action.time_seconds <= 34.0
    ]
    assert rows == [
        (30.0, RotationActionKind.BAR_SWAP, None, "front"),
        (31.0, RotationActionKind.SKILL, "Budding Seeds", "front"),
        (32.0, RotationActionKind.BAR_SWAP, None, "back"),
        (33.0, RotationActionKind.SKILL, "Expansive Frost Cloak", "back"),
        (34.0, RotationActionKind.SKILL, "Winter's Revenge", "back"),
    ]
    assert tuple(action.name for action in result.displaced_actions) == (
        "Expansive Frost Cloak",
        "Winter's Revenge",
    )


def test_bar_access_claim_does_nothing_when_required_skill_already_covers_demand() -> None:
    plan = _plan()
    actions = list(plan.actions)
    actions[3] = RotationAction(31.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front")
    covered = RotationPlan(
        character_name=plan.character_name,
        build_name=plan.build_name,
        duration_seconds=plan.duration_seconds,
        actions=tuple(actions),
    )

    result = RotationDemandBarAccessService().refine(
        plan=covered,
        demands=(_demand(),),
        claim=_claim(),
    )

    assert result.applied is False
    assert result.plan is covered
    assert "already scheduled" in result.reason


def test_bar_access_claim_refuses_to_drop_displaced_work() -> None:
    plan = _plan()
    actions = tuple(
        action
        for action in plan.actions
        if action.time_seconds not in {33.0, 34.0}
    )
    no_restore_room = RotationPlan(
        character_name=plan.character_name,
        build_name=plan.build_name,
        duration_seconds=plan.duration_seconds,
        actions=actions,
    )

    result = RotationDemandBarAccessService().refine(
        plan=no_restore_room,
        demands=(_demand(),),
        claim=_claim(),
    )

    assert result.applied is False
    assert result.plan is no_restore_room
    assert "preserve displaced" in result.reason


def test_bar_access_claim_refuses_route_when_encounter_locks_current_bar() -> None:
    result = RotationDemandBarAccessService().refine(
        plan=_plan(),
        demands=(_demand(),),
        claim=_claim(),
        bar_availability_windows=(
            RotationBarAvailabilityWindow(
                name="single-bar encounter state",
                start_seconds=29.13,
                end_seconds=34.13,
                allowed_bars=frozenset({"back"}),
                bar_swaps_allowed=False,
            ),
        ),
    )

    assert result.applied is False
    assert result.plan == _plan()
    assert "bar availability" in result.reason


def test_bar_access_claim_requires_exact_named_demand() -> None:
    try:
        RotationDemandBarAccessService().refine(
            plan=_plan(),
            demands=(),
            claim=_claim(),
        )
    except ValueError as exc:
        assert "exactly one demand" in str(exc)
    else:
        raise AssertionError("missing demand should fail explicitly")
