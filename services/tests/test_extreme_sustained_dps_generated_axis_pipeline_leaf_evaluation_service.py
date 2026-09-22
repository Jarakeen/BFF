from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_generated_axis_pipeline_leaf_evaluation_service import (
    ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierNode,
)
from services.extreme_sustained_dps_generated_runtime_state_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedRuntimeStateLeaf,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
)


class _RuntimeEvaluation:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def evaluate(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return self.result


def _node(*, complete=True, omit=None):
    values = {
        "build": "final-build",
        "progression": "progression",
        "gear_state": "gear-state",
        "plan": "final-plan",
    }
    if omit:
        values[omit] = None

    state = SimpleNamespace(
        complete=complete,
        gear=SimpleNamespace(
            progression="pre-late-progression",
            gear_state=values["gear_state"],
        ),
        late=SimpleNamespace(
            assembled=SimpleNamespace(
                build=values["build"],
                progression=values["progression"],
            ),
        ),
        runtime=SimpleNamespace(
            current_candidate=SimpleNamespace(plan=values["plan"]),
        ),
    )
    return ExtremeSustainedDPSGeneratedFrontierNode(
        candidate_key="candidate:1",
        state=state,
        coordinates=(("Runtime", 0),),
        evidence=("pipeline coordinate evidence",),
    )


def _runtime_result():
    return SimpleNamespace(
        record=SimpleNamespace(
            modeled_dps=123.5,
            duration_seconds=10.0,
        ),
        mechanic_complete=True,
        evidence=("canonical runtime evidence",),
        unresolved=(),
    )


def test_extracts_complete_pipeline_witness_for_canonical_runtime_evaluation() -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )

    exact = service.evaluate(
        _node(),
        runtime_snapshot="snapshot",
        target_health=1_000_000,
        target_resistance=18_200.0,
        target_name="Boss",
        initial_bar="back",
    )

    assert exact.modeled_dps == 123.5
    assert exact.duration_seconds == 10.0
    assert exact.mechanic_complete is True
    assert exact.evidence == (
        "pipeline coordinate evidence",
        "canonical runtime evidence",
    )

    build, kwargs = runtime.calls[0]
    assert build == "final-build"
    assert kwargs == {
        "progression": "progression",
        "gear_state": "gear-state",
        "plan": "final-plan",
        "runtime_snapshot": "snapshot",
        "target_health": 1_000_000,
        "target_resistance": 18_200.0,
        "target_name": "Boss",
        "initial_bar": "back",
    }


def test_factory_returns_wiring_compatible_one_argument_evaluator() -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )

    evaluate = service.evaluator(
        runtime_snapshot="snapshot",
        target_health=100,
        target_resistance=0.0,
    )
    exact = evaluate(_node())

    assert exact.candidate_key == "candidate:1"
    assert exact.modeled_dps == 123.5


def test_incomplete_pipeline_leaf_fails_closed_without_running_simulation() -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )

    exact = service.evaluate(
        _node(complete=False),
        runtime_snapshot="snapshot",
        target_health=100,
        target_resistance=0.0,
    )

    assert exact.modeled_dps is None
    assert exact.mechanic_complete is False
    assert exact.unresolved == ("Generated axis pipeline leaf is incomplete",)
    assert runtime.calls == []


def test_missing_pipeline_witness_fails_closed_with_exact_field_name() -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )

    exact = service.evaluate(
        _node(omit="gear_state"),
        runtime_snapshot="snapshot",
        target_health=100,
        target_resistance=0.0,
    )

    assert exact.modeled_dps is None
    assert exact.mechanic_complete is False
    assert "dual-bar gear state" in exact.unresolved[0]
    assert runtime.calls == []



def test_selected_generated_runtime_state_overrides_fixed_search_snapshot() -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )
    base = _node()
    choice = ExtremeSustainedDPSRuntimeStateChoice(
        "runtime:selected",
        "selected-snapshot",
        evidence=("selected runtime evidence",),
    )
    node = ExtremeSustainedDPSGeneratedFrontierNode(
        candidate_key="candidate:runtime",
        state=ExtremeSustainedDPSGeneratedRuntimeStateLeaf(
            pipeline_state=base.state,
            runtime_state_choice=choice,
            omitted_scope=(),
        ),
        coordinates=(*base.coordinates, ("Runtime State", 0)),
        evidence=base.evidence,
    )

    exact = service.evaluate(
        node,
        runtime_snapshot="fixed-search-snapshot",
        target_health=100,
        target_resistance=0.0,
    )

    assert exact.mechanic_complete is True
    assert runtime.calls[0][1]["runtime_snapshot"] == "selected-snapshot"
    assert "selected runtime evidence" in exact.evidence



def test_finalized_potion_plan_supersedes_runtime_policy_plan() -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )
    base = _node()
    base.state.finalized_potion = SimpleNamespace(
        candidate=SimpleNamespace(plan="finalized-potion-plan"),
    )

    exact = service.evaluate(
        base,
        runtime_snapshot="snapshot",
        target_health=100,
        target_resistance=0.0,
    )

    assert exact.mechanic_complete is True
    assert runtime.calls[0][1]["plan"] == "finalized-potion-plan"


def test_exact_leaf_uses_final_assembled_progression_not_gear_stage_progression() -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )

    service.evaluate(
        _node(),
        runtime_snapshot="snapshot",
        target_health=100,
        target_resistance=0.0,
    )

    assert runtime.calls[0][1]["progression"] == "progression"
    assert runtime.calls[0][1]["progression"] != "pre-late-progression"
