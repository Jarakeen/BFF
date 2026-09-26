from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace

import pytest

from models.build_model import PlayerBuild

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
    choice: object | None = None
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
                    assembled=SimpleNamespace(
                        build="assembled-build",
                        progression="assembled-progression",
                    ),
                    result=state.result + "|late",
                ),
                self.calls,
            ),
        )


class _EncounterAdapter:
    def __init__(self, calls):
        self.calls = calls

    def root(self, assembled):
        self.calls.append(("encounter", "root", assembled))
        return _Stage("encounter", assembled=assembled)

    def axes(self):
        return (
            _one_axis(
                "Encounter",
                lambda state: replace(
                    state,
                    complete=True,
                    choice=SimpleNamespace(demands=("demand-a", "demand-b")),
                    result=state.result + "|encounter",
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


class _FinalizedPotionAdapter:
    def __init__(self, calls):
        self.calls = calls

    def root(
        self,
        upstream_state,
        *,
        build,
        progression,
        potion_cooldown_seconds,
        evidence_resolver,
    ):
        self.calls.append(
            (
                "finalized-potion",
                "root",
                build,
                progression,
                potion_cooldown_seconds,
                evidence_resolver,
                upstream_state.runtime,
            )
        )
        return _Stage("finalized-potion")

    def axis(self):
        return _one_axis(
            "FinalizedPotion",
            lambda state: replace(
                state,
                complete=True,
                result=state.result + "|finalized-potion",
            ),
            self.calls,
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
        heavy_attack_channel_blocks=("channel-block",),
        heavy_attack_channel_block_denominator_proven=True,
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
    assert runtime_root[3]["heavy_attack_channel_blocks"] == ("channel-block",)
    assert (
        runtime_root[3]["heavy_attack_channel_block_denominator_proven"]
        is True
    )

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



def test_optional_encounter_policy_stage_forwards_demands_into_rotation_root() -> None:
    calls = []
    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_LateAdapter(calls),
        encounter_policy_adapter=_EncounterAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
    )
    state = _root(pipeline)

    axes = pipeline.axes()
    assert tuple(axis.name for axis in axes) == (
        "Gear",
        "Late",
        "Encounter",
        "Rotation",
        "Runtime",
    )

    for axis in axes:
        assert axis.candidate_count(state) == 1
        state = axis.candidate_at(state, 0)

    assert state.complete is True
    rotation_root = next(row for row in calls if row[:2] == ("rotation", "root"))
    assert rotation_root[3]["priorities"] == "priorities"
    assert rotation_root[3]["encounter_demands"] == ("demand-a", "demand-b")



def test_optional_finalized_potion_stage_runs_after_runtime_and_owns_completion() -> None:
    calls = []
    evidence_resolver = object()
    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_LateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
        finalized_potion_adapter=_FinalizedPotionAdapter(calls),
        finalized_potion_evidence_resolver=evidence_resolver,
    )
    state = _root(pipeline)
    axes = pipeline.axes()

    assert tuple(axis.name for axis in axes) == (
        "Gear",
        "Late",
        "Rotation",
        "Runtime",
        "FinalizedPotion",
    )

    for axis in axes[:-1]:
        assert axis.candidate_count(state) == 1
        state = axis.candidate_at(state, 0)

    assert state.runtime.complete is True
    assert state.finalized_potion is None
    assert state.complete is False

    assert axes[-1].candidate_count(state) == 1
    state = axes[-1].candidate_at(state, 0)

    assert state.complete is True
    finalized_root = next(
        row for row in calls
        if row[:2] == ("finalized-potion", "root")
    )
    assert finalized_root[2] == "assembled-build"
    assert finalized_root[3] == "assembled-progression"
    assert finalized_root[4] == 45.0
    assert finalized_root[5] is evidence_resolver
    assert finalized_root[6].complete is True


def test_finalized_potion_stage_requires_explicit_evidence_resolver() -> None:
    calls = []
    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_LateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
        finalized_potion_adapter=_FinalizedPotionAdapter(calls),
    )
    state = _root(pipeline)

    for axis in pipeline.axes()[:-1]:
        state = axis.candidate_at(state, 0)

    with pytest.raises(ValueError, match="timing-evidence resolver"):
        pipeline.axes()[-1].candidate_count(state)



def test_candidate_runtime_state_stage_runs_after_finalized_potion() -> None:
    from services.extreme_sustained_dps_runtime_state_frontier_service import (
        ExtremeSustainedDPSRuntimeStateChoice,
        ExtremeSustainedDPSRuntimeStateFrontierService,
    )

    calls = []

    class _RuntimeStateResolver:
        def resolve(self, state):
            calls.append(("candidate-runtime-state", state.finalized_potion.complete))
            return ExtremeSustainedDPSRuntimeStateFrontierService.build(
                (
                    ExtremeSustainedDPSRuntimeStateChoice(
                        "runtime:final",
                        "snapshot:final",
                    ),
                ),
                denominator_proven=True,
                source="candidate final runtime family",
            )

    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_LateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
        finalized_potion_adapter=_FinalizedPotionAdapter(calls),
        finalized_potion_evidence_resolver=object(),
        runtime_state_frontier_resolver=_RuntimeStateResolver(),
    )
    state = _root(pipeline)
    axes = pipeline.axes()

    assert tuple(axis.name for axis in axes) == (
        "Gear",
        "Late",
        "Rotation",
        "Runtime",
        "FinalizedPotion",
        "Runtime State",
    )

    for axis in axes[:-1]:
        state = axis.candidate_at(state, 0)

    assert state.finalized_potion.complete is True
    assert state.complete is True

    assert axes[-1].candidate_count(state) == 1
    leaf = axes[-1].candidate_at(state, 0)

    assert leaf.complete is True
    assert leaf.runtime_state_choice.runtime_state_id == "runtime:final"
    assert leaf.runtime_state_choice.snapshot == "snapshot:final"
    assert ("candidate-runtime-state", True) in calls



class _PotionCooldownResolver:
    def __init__(self, *, cooldown=37.0, unresolved=()):
        self.cooldown = cooldown
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            complete=self.cooldown is not None and not self.unresolved,
            cooldown_seconds=self.cooldown,
            unresolved=self.unresolved,
        )


def test_pipeline_resolves_effective_potion_cooldown_from_finalized_build() -> None:
    calls = []
    resolver = _PotionCooldownResolver(cooldown=37.0)
    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_LateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
    )
    state = pipeline.root(
        "build",
        "progression",
        dual_bar_frontier="dual-frontier",
        candidate_id_prefix="structural:9",
        duration_seconds=10.0,
        potion_cooldown_seconds=None,
        potion_cooldown_resolver=resolver,
        potion_cooldown_scenario="scenario-proof",
        starting_ultimate=70.0,
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="boss",
    )

    for axis in pipeline.axes()[:2]:
        state = axis.candidate_at(state, 0)

    assert pipeline.axes()[2].candidate_count(state) == 1
    rotation_root = next(row for row in calls if row[:2] == ("rotation", "root"))
    assert rotation_root[3]["potion_cooldown_seconds"] == 37.0
    assert resolver.calls == [
        {
            "player_build": "assembled-build",
            "progression": "assembled-progression",
            "scenario": "scenario-proof",
        }
    ]


def test_pipeline_refuses_unresolved_effective_potion_cooldown() -> None:
    calls = []
    resolver = _PotionCooldownResolver(
        cooldown=None,
        unresolved=("scenario potion cooldown inventory incomplete",),
    )
    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_LateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
    )
    state = pipeline.root(
        "build",
        "progression",
        dual_bar_frontier="dual-frontier",
        candidate_id_prefix="structural:9",
        duration_seconds=10.0,
        potion_cooldown_seconds=None,
        potion_cooldown_resolver=resolver,
        starting_ultimate=70.0,
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="boss",
    )

    for axis in pipeline.axes()[:2]:
        state = axis.candidate_at(state, 0)

    with pytest.raises(ValueError, match="potion cooldown is unresolved"):
        pipeline.axes()[2].candidate_count(state)



class _PotionlessLateAdapter(_LateAdapter):
    def axes(self):
        return (
            _one_axis(
                "Late",
                lambda state: replace(
                    state,
                    complete=True,
                    assembled=SimpleNamespace(
                        build=PlayerBuild(Potion=""),
                        progression="assembled-progression",
                    ),
                    result=state.result + "|late",
                ),
                self.calls,
            ),
        )


def test_potionless_candidate_does_not_require_irrelevant_cooldown_proof() -> None:
    calls = []
    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_PotionlessLateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
    )
    state = pipeline.root(
        "build",
        "progression",
        dual_bar_frontier="dual-frontier",
        candidate_id_prefix="structural:9",
        duration_seconds=10.0,
        potion_cooldown_seconds=None,
        starting_ultimate=0.0,
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="boss",
    )

    for axis in pipeline.axes()[:2]:
        state = axis.candidate_at(state, 0)

    assert pipeline.axes()[2].candidate_count(state) == 1
    rotation_root = next(row for row in calls if row[:2] == ("rotation", "root"))
    assert rotation_root[3]["potion_cooldown_seconds"] == 45.0



@pytest.mark.parametrize("cooldown", [0.0, -1.0])
def test_raw_potion_cooldown_must_be_positive(cooldown: float) -> None:
    calls = []
    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_LateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
    )
    state = pipeline.root(
        "build",
        "progression",
        dual_bar_frontier="dual-frontier",
        candidate_id_prefix="structural:10",
        duration_seconds=10.0,
        potion_cooldown_seconds=cooldown,
        starting_ultimate=0.0,
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="boss",
    )
    for axis in pipeline.axes()[:2]:
        state = axis.candidate_at(state, 0)

    with pytest.raises(ValueError, match="potion cooldown must be positive"):
        pipeline.axes()[2].candidate_count(state)


def test_pipeline_rejects_truthy_non_boolean_stage_complete_flag() -> None:
    calls = []
    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_LateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
    )
    state = _root(pipeline)
    state = replace(state, gear=SimpleNamespace(complete="false", context="context"))

    with pytest.raises(TypeError, match="complete flag must be boolean"):
        pipeline.axes()[1].candidate_count(state)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("duration_seconds", True, "duration must be numeric"),
        ("potion_cooldown_seconds", True, "cooldown must be numeric"),
        ("starting_ultimate", True, "Ultimate must be numeric"),
        ("use_scheduled_combat_attacks_for_ultimate", "false", "flag must be boolean"),
        ("heavy_attack_channel_block_denominator_proven", "false", "proof flag must be boolean"),
    ),
)
def test_pipeline_root_rejects_boolean_laundering(field, value, message) -> None:
    calls = []
    pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
        gear_adapter=_GearAdapter(calls),
        late_adapter=_LateAdapter(calls),
        rotation_adapter=_RotationAdapter(calls),
        runtime_policy_adapter=_RuntimeAdapter(calls),
    )
    values = {
        "duration_seconds": 10.0,
        "potion_cooldown_seconds": 45.0,
        "starting_ultimate": 0.0,
        "use_scheduled_combat_attacks_for_ultimate": False,
        "heavy_attack_channel_block_denominator_proven": False,
    }
    values[field] = value

    with pytest.raises(TypeError, match=message):
        pipeline.root(
            "build",
            "progression",
            dual_bar_frontier="dual-frontier",
            candidate_id_prefix="structural:strict",
            priorities="priorities",
            snapshot_resolver="resolver",
            target_identity="boss",
            **values,
        )
