from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
)
from services.extreme_sustained_dps_generated_axis_pipeline_service import (
    ExtremeSustainedDPSGeneratedAxisPipelineService,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierWiringService,
    ExtremeSustainedDPSIndexedFrontierAxis,
)


@dataclass(frozen=True)
class _Stage:
    name: str
    complete: bool = False
    context: object | None = None
    assembled: object | None = None
    rotation_plan: object | None = None
    rotation_policy: object | None = None
    result: str = ""


def _one_axis(name, finish, calls, *, with_bound=False):
    def count(state):
        calls.append((name, "count", state.name))
        return 1

    def candidate_at(state, index):
        calls.append((name, "at", state.name, index))
        return finish(state)

    bound_inputs = None
    if with_bound:
        def bound_inputs(state):
            calls.append((name, "bound", state.name))
            return ()

    return ExtremeSustainedDPSIndexedFrontierAxis(
        name,
        candidate_count=count,
        candidate_at=candidate_at,
        bound_inputs=bound_inputs,
    )


class _GearAdapter:
    def __init__(self, calls):
        self.calls = calls

    def root(self, build, progression, *, dual_bar_frontier):
        self.calls.append(("gear", "root", build, progression, dual_bar_frontier))
        return _Stage("gear")

    def axes(self):
        return (
            _one_axis(
                "Gear",
                lambda state: replace(
                    state,
                    complete=True,
                    context="cross-axis-context",
                    result="gear",
                ),
                self.calls,
                with_bound=True,
            ),
        )


class _MundusFoodAdapter:
    def __init__(self, calls):
        self.calls = calls

    def root(self, context):
        self.calls.append(("mundus-food", "root", context))
        return _Stage("mundus-food", context=context)

    def axes(self):
        return (
            _one_axis(
                "MundusFood",
                lambda state: replace(
                    state,
                    complete=True,
                    context="mundus-food-context",
                    result=state.result + "|mundus-food",
                ),
                self.calls,
            ),
        )


class _LateAdapter:
    def __init__(self, calls):
        self.calls = calls

    def root(self, context):
        self.calls.append(("late", "root", context))
        return _Stage("late")

    def axes(self):
        return (
            _one_axis(
                "Late",
                lambda state: replace(
                    state,
                    complete=True,
                    assembled="assembled-candidate",
                    result=state.result + "|late",
                ),
                self.calls,
            ),
        )


class _RotationAdapter:
    def __init__(self, calls):
        self.calls = calls

    def root(self, assembled, **kwargs):
        self.calls.append(("rotation", "root", assembled, kwargs))
        return _Stage("rotation")

    def axes(self):
        return (
            _one_axis(
                "Rotation",
                lambda state: replace(
                    state,
                    complete=True,
                    rotation_plan=SimpleNamespace(structural_index=3),
                    rotation_policy=SimpleNamespace(
                        structural_index=5,
                        plan="anchored-plan",
                    ),
                    result=state.result + "|rotation",
                ),
                self.calls,
            ),
        )


class _RuntimeAdapter:
    def __init__(self, calls):
        self.calls = calls

    def root(self, policy, **kwargs):
        self.calls.append(("runtime", "root", policy, kwargs))
        return _Stage("runtime")

    def axes(self):
        return (
            _one_axis(
                "Runtime",
                lambda state: replace(
                    state,
                    complete=True,
                    result=state.result + "|runtime",
                ),
                self.calls,
            ),
        )


def _pipeline(calls):
    return ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_LateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
    )


def _root(pipeline):
    return pipeline.root(
        "build",
        "progression",
        dual_bar_frontier="dual-frontier",
        candidate_id_prefix="structural:9",
        duration_seconds=10.0,
        potion_cooldown_seconds=45.0,
        starting_ultimate=70.0,
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="boss",
        ultimate_generation_events=("generation",),
        heroism_windows=("heroism",),
        use_scheduled_combat_attacks_for_ultimate=True,
        duration_rules=("rule",),
        heavy_attack_windows=("window",),
    )


def test_composes_adapter_states_and_runtime_identity_in_order() -> None:
    calls = []
    pipeline = _pipeline(calls)
    state = _root(pipeline)

    axes = pipeline.axes()
    assert tuple(axis.name for axis in axes) == (
        "Gear",
        "Late",
        "Rotation",
        "Runtime",
    )

    for axis in axes:
        assert axis.candidate_count(state) == 1
        state = axis.candidate_at(state, 0)

    assert state.complete is True
    runtime_root = next(row for row in calls if row[:2] == ("runtime", "root"))
    assert runtime_root[3]["candidate_id"] == (
        "structural:9|rotation-plan:3|anchored-policy:5"
    )
    assert runtime_root[3]["heavy_attack_windows"] == ("window",)

    rotation_root = next(row for row in calls if row[:2] == ("rotation", "root"))
    assert rotation_root[3]["ultimate_generation_events"] == ("generation",)
    assert rotation_root[3]["heroism_windows"] == ("heroism",)
    assert (
        rotation_root[3]["use_scheduled_combat_attacks_for_ultimate"]
        is True
    )


def test_runs_all_adapter_stages_through_one_lazy_search_tree() -> None:
    calls = []
    pipeline = _pipeline(calls)

    def evaluate(node):
        assert node.state.complete
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=node.candidate_key,
            modeled_dps=123.0,
            duration_seconds=10.0,
            mechanic_complete=True,
        )

    result = ExtremeSustainedDPSGeneratedFrontierWiringService.search(
        _root(pipeline),
        axes=pipeline.axes(),
        evaluate_leaf=evaluate,
        required_duration_seconds=10.0,
    )

    assert result.evaluated_leaf_count == 1
    assert result.best_modeled_dps == 123.0
    assert result.global_maximum_proven is True
    assert any(row[:2] == ("Gear", "bound") for row in calls)


def test_later_stage_rejects_incomplete_upstream_state() -> None:
    calls = []
    pipeline = _pipeline(calls)
    state = _root(pipeline)

    with pytest.raises(ValueError, match="complete gear-axis"):
        pipeline.axes()[1].candidate_count(state)


def test_pipeline_requires_stable_candidate_identity_prefix() -> None:
    pipeline = _pipeline([])

    with pytest.raises(ValueError, match="candidate_id_prefix"):
        pipeline.root(
            "build",
            "progression",
            dual_bar_frontier="dual",
            candidate_id_prefix=" ",
            duration_seconds=10.0,
            potion_cooldown_seconds=45.0,
            starting_ultimate=0.0,
            priorities=object(),
            snapshot_resolver=object(),
            target_identity="boss",
        )



def test_optional_mundus_food_stage_sits_between_gear_and_late() -> None:
    calls = []
    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        mundus_food_adapter=_MundusFoodAdapter(calls),
        late_adapter=_LateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
    )
    state = _root(pipeline)

    axes = pipeline.axes()
    assert tuple(axis.name for axis in axes) == (
        "Gear",
        "MundusFood",
        "Late",
        "Rotation",
        "Runtime",
    )

    for axis in axes:
        assert axis.candidate_count(state) == 1
        state = axis.candidate_at(state, 0)

    assert state.complete is True
    late_root = next(row for row in calls if row[:2] == ("late", "root"))
    assert late_root[2] == "mundus-food-context"
