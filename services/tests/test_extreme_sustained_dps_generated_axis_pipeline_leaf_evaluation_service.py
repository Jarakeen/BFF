from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer

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
        effects=(
            EffectVariant(
                name="runtime_effect_metadata",
                layer=EffectLayer.CAST,
                source="runtime-state test",
            ),
        ),
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
    assert runtime.calls[0][1]["runtime_effects"][0].name == "runtime_effect_metadata"
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


def test_leaf_evaluation_rejects_truthy_non_boolean_complete_flag() -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )
    node = _node()
    node.state.complete = "false"

    with pytest.raises(TypeError, match="complete flag must be boolean"):
        service.evaluate(
            node,
            runtime_snapshot="snapshot",
            target_health=100,
            target_resistance=0.0,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("target_health", True, "target health must be an integer"),
        ("target_resistance", True, "target resistance must be numeric"),
    ),
)
def test_leaf_evaluation_rejects_boolean_numeric_inputs(field, value, message) -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )
    values = {
        "runtime_snapshot": "snapshot",
        "target_health": 100,
        "target_resistance": 0.0,
    }
    values[field] = value

    with pytest.raises(TypeError, match=message):
        service.evaluate(_node(), **values)


@pytest.mark.parametrize(
    "field,value,message",
    (
        ("target_health", "100", "target health must be an integer"),
        ("target_resistance", "0", "target resistance must be numeric"),
        ("target_name", 7, "target_name must be a string"),
        ("initial_bar", 1, "initial_bar must be a string"),
    ),
)
def test_leaf_evaluation_rejects_coerced_scalar_inputs(field, value, message) -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )
    values = {
        "runtime_snapshot": "snapshot",
        "target_health": 100,
        "target_resistance": 0.0,
        "target_name": "Boss",
        "initial_bar": "front",
    }
    values[field] = value

    with pytest.raises(TypeError, match=message):
        service.evaluate(_node(), **values)


def test_leaf_evaluation_rejects_invalid_scalar_ranges() -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )

    with pytest.raises(ValueError, match="target health must be positive"):
        service.evaluate(
            _node(),
            runtime_snapshot="snapshot",
            target_health=0,
            target_resistance=0.0,
        )

    with pytest.raises(ValueError, match="target resistance must be finite and non-negative"):
        service.evaluate(
            _node(),
            runtime_snapshot="snapshot",
            target_health=100,
            target_resistance=float("inf"),
        )

    with pytest.raises(ValueError, match="initial_bar must be front or back"):
        service.evaluate(
            _node(),
            runtime_snapshot="snapshot",
            target_health=100,
            target_resistance=0.0,
            initial_bar="middle",
        )


def test_runtime_state_choice_requires_tuple_unresolved_and_effects() -> None:
    runtime = _RuntimeEvaluation(_runtime_result())
    service = ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
        runtime_evaluation=runtime,
    )
    base = _node()

    malformed_unresolved = SimpleNamespace(
        unresolved=["gap"],
        snapshot="snapshot",
        evidence=(),
        effects=(),
    )
    node = ExtremeSustainedDPSGeneratedFrontierNode(
        candidate_key="candidate:bad-unresolved",
        state=SimpleNamespace(
            **base.state.__dict__,
            runtime_state_choice=malformed_unresolved,
        ),
        coordinates=base.coordinates,
        evidence=base.evidence,
    )
    with pytest.raises(TypeError, match="unresolved evidence must be a tuple"):
        service.evaluate(
            node,
            runtime_snapshot="snapshot",
            target_health=100,
            target_resistance=0.0,
        )

    malformed_effects = SimpleNamespace(
        unresolved=(),
        snapshot="snapshot",
        evidence=(),
        effects=[],
    )
    node = ExtremeSustainedDPSGeneratedFrontierNode(
        candidate_key="candidate:bad-effects",
        state=SimpleNamespace(
            **base.state.__dict__,
            runtime_state_choice=malformed_effects,
        ),
        coordinates=base.coordinates,
        evidence=base.evidence,
    )
    with pytest.raises(TypeError, match="effects must be a tuple"):
        service.evaluate(
            node,
            runtime_snapshot="snapshot",
            target_health=100,
            target_resistance=0.0,
        )
