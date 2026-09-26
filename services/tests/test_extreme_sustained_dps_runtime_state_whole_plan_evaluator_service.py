from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
)
from services.extreme_sustained_dps_runtime_state_whole_plan_evaluator_service import (
    ExtremeSustainedDPSRuntimeStateWholePlanEvaluator,
)


class _Runtime:
    def __init__(self, rows):
        self.rows = rows

    def evaluate(self, build, **kwargs):
        return self.rows[kwargs["runtime_snapshot"]]


def _scenario():
    return SimpleNamespace(
        build=object(),
        progression=object(),
        gear_state=object(),
        plan=SimpleNamespace(duration_seconds=20.0),
        target_health=100000,
        target_resistance=18200.0,
        target_name="Boss",
        initial_bar="front",
    )


def test_runtime_choice_evaluator_varies_only_snapshot_and_returns_modeled_dps() -> None:
    snapshot = object()
    evaluator = ExtremeSustainedDPSRuntimeStateWholePlanEvaluator(
        ".",
        scenario=_scenario(),
        runtime_service=_Runtime(
            {
                snapshot: SimpleNamespace(
                    record=SimpleNamespace(modeled_dps=123.0, duration_seconds=20.0),
                    mechanic_complete=True,
                    unresolved=(),
                )
            }
        ),
    )

    result = evaluator.evaluate(
        ExtremeSustainedDPSRuntimeStateChoice("runtime:1", snapshot)
    )

    assert result.choice_id == "runtime:1"
    assert result.modeled_dps == 123.0
    assert result.duration_seconds == 20.0
    assert result.mechanic_complete is True


def test_runtime_gap_remains_unresolved() -> None:
    snapshot = object()
    evaluator = ExtremeSustainedDPSRuntimeStateWholePlanEvaluator(
        ".",
        scenario=_scenario(),
        runtime_service=_Runtime(
            {
                snapshot: SimpleNamespace(
                    record=None,
                    mechanic_complete=False,
                    unresolved=("cooldown ownership unresolved",),
                )
            }
        ),
    )

    result = evaluator.evaluate(
        ExtremeSustainedDPSRuntimeStateChoice("runtime:gap", snapshot)
    )

    assert result.modeled_dps is None
    assert result.mechanic_complete is False
    assert result.unresolved == ("cooldown ownership unresolved",)


def test_runtime_choice_evaluator_requires_strict_mechanic_complete() -> None:
    snapshot = object()
    evaluator = ExtremeSustainedDPSRuntimeStateWholePlanEvaluator(
        ".",
        scenario=_scenario(),
        runtime_service=_Runtime(
            {
                snapshot: SimpleNamespace(
                    record=None,
                    mechanic_complete=1,
                    unresolved=(),
                )
            }
        ),
    )

    import pytest
    with pytest.raises(TypeError, match="mechanic_complete must be boolean"):
        evaluator.evaluate(
            ExtremeSustainedDPSRuntimeStateChoice("runtime:strict", snapshot)
        )


def test_runtime_choice_evaluator_requires_tuple_runtime_unresolved() -> None:
    snapshot = object()
    evaluator = ExtremeSustainedDPSRuntimeStateWholePlanEvaluator(
        ".",
        scenario=_scenario(),
        runtime_service=_Runtime(
            {
                snapshot: SimpleNamespace(
                    record=None,
                    mechanic_complete=False,
                    unresolved=[],
                )
            }
        ),
    )

    import pytest
    with pytest.raises(TypeError, match="result unresolved must be a tuple"):
        evaluator.evaluate(
            ExtremeSustainedDPSRuntimeStateChoice("runtime:strict", snapshot)
        )
