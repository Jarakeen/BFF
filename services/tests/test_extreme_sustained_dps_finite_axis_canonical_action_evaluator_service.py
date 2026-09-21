from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.extreme_sustained_dps_finite_axis_canonical_action_evaluator_service import (
    ExtremeSustainedDPSExactActionScenario,
)


def _plan():
    return RotationPlan(
        character_name="Test",
        build_name="Build",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Skill A",
                bar="front",
            ),
        ),
        assumptions=(),
        unresolved=(),
    )


def test_exact_action_scenario_normalizes_initial_bar() -> None:
    scenario = ExtremeSustainedDPSExactActionScenario(
        plan=_plan(),
        action_time_seconds=1.0,
        action_sequence=0,
        target_resistance=18200.0,
        initial_bar=" FRONT ",
    )

    assert scenario.initial_bar == "front"


def test_exact_action_scenario_rejects_invalid_bar() -> None:
    try:
        ExtremeSustainedDPSExactActionScenario(
            plan=_plan(),
            action_time_seconds=1.0,
            action_sequence=0,
            target_resistance=18200.0,
            initial_bar="middle",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected invalid initial bar to fail")


def test_exact_action_scenario_rejects_negative_target_resistance() -> None:
    try:
        ExtremeSustainedDPSExactActionScenario(
            plan=_plan(),
            action_time_seconds=1.0,
            action_sequence=0,
            target_resistance=-1.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected negative target resistance to fail")
