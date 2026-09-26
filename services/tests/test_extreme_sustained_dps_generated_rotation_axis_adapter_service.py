from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierWiringService,
)
from services.extreme_sustained_dps_generated_rotation_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedRotationAxisAdapterService,
)


class _PlanFrontier:
    def __init__(self, *, proven=True, unresolved=()):
        self.proven = proven
        self.unresolved = tuple(unresolved)
        self.calls = []

    def frontier(self, assembled):
        self.calls.append(("frontier", assembled))
        return SimpleNamespace(
            candidate_count=2,
            denominator_proven=self.proven,
            unresolved=self.unresolved,
        )

    def candidate_at(
        self,
        assembled,
        *,
        duration_seconds,
        index,
        priorities=None,
        encounter_demands=(),
    ):
        self.calls.append(
            (
                "candidate_at",
                assembled,
                duration_seconds,
                index,
                priorities,
                tuple(encounter_demands),
            )
        )
        return SimpleNamespace(
            structural_index=index,
            plan=f"plan:{index}",
            unresolved=(),
        )


class _PolicyFrontier:
    def __init__(self, *, proven=True, unresolved=()):
        self.proven = proven
        self.unresolved = tuple(unresolved)
        self.calls = []

    def frontier(
        self,
        *,
        build,
        seed,
        potion_cooldown_seconds,
        starting_ultimate=0.0,
        ultimate_generation_events=(),
        heroism_windows=(),
        use_scheduled_combat_attacks_for_ultimate=False,
    ):
        self.calls.append(
            (
                "frontier",
                build,
                seed,
                potion_cooldown_seconds,
                starting_ultimate,
                tuple(ultimate_generation_events),
                tuple(heroism_windows),
                use_scheduled_combat_attacks_for_ultimate,
            )
        )
        return SimpleNamespace(
            candidate_count=6,
            ultimate_timing_policies=("ult-0", "ult-1"),
            potion_policies=("potion:none", "potion:a", "potion:b"),
            anchored_policy_denominator_proven=self.proven,
            continuous_potion_timing_closed=False,
            delayed_ultimate_timing_closed=True,
            unresolved=self.unresolved,
        )

    def candidate_at(
        self,
        *,
        build,
        seed,
        potion_cooldown_seconds,
        starting_ultimate,
        index,
        ultimate_generation_events=(),
        heroism_windows=(),
        use_scheduled_combat_attacks_for_ultimate=False,
    ):
        self.calls.append(
            (
                "candidate_at",
                build,
                seed,
                potion_cooldown_seconds,
                starting_ultimate,
                index,
                ultimate_generation_events,
                heroism_windows,
                use_scheduled_combat_attacks_for_ultimate,
            )
        )
        return SimpleNamespace(
            structural_index=index,
            plan=f"{seed.plan}|policy:{index}",
            mechanic_complete=True,
            unresolved=(),
        )


def _assembled():
    return SimpleNamespace(build=SimpleNamespace(Name="generated"))


def _adapter(*, plans=None, policies=None):
    return ExtremeSustainedDPSGeneratedRotationAxisAdapterService(
        rotation_plans=plans or _PlanFrontier(),
        rotation_policies=policies or _PolicyFrontier(),
    )


def _root(adapter):
    return adapter.root(
        _assembled(),
        duration_seconds=10.0,
        potion_cooldown_seconds=45.0,
        starting_ultimate=70.0,
        ultimate_generation_events=("generation",),
        heroism_windows=("heroism",),
        use_scheduled_combat_attacks_for_ultimate=True,
    )


def test_rotation_axes_preserve_plan_dependency_and_policy_inputs() -> None:
    plans = _PlanFrontier()
    policies = _PolicyFrontier()
    adapter = _adapter(plans=plans, policies=policies)
    axes = adapter.axes()

    assert tuple(axis.name for axis in axes) == (
        "Rotation Plan Family",
        "Delayed Ultimate Policy",
    )

    state = _root(adapter)
    assert axes[0].candidate_count(state) == 2
    state = axes[0].candidate_at(state, 1)
    assert axes[1].candidate_count(state) == 2
    state = axes[1].candidate_at(state, 1)

    assert state.complete is True
    assert state.rotation_policy.plan == "plan:1|policy:3"
    policy_call = policies.calls[-1]
    assert policy_call[3:6] == (45.0, 70.0, 3)
    assert policy_call[6:] == (("generation",), ("heroism",), True)


def test_runs_plan_and_anchored_policy_product_through_lazy_search() -> None:
    adapter = _adapter()

    def evaluate(node):
        state = node.state
        assert state.complete
        score = (
            state.rotation_plan.structural_index * 10
            + state.rotation_policy.structural_index
        )
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=node.candidate_key,
            modeled_dps=float(score),
            duration_seconds=10.0,
            mechanic_complete=True,
        )

    result = ExtremeSustainedDPSGeneratedFrontierWiringService.search(
        _root(adapter),
        axes=adapter.axes(),
        evaluate_leaf=evaluate,
        required_duration_seconds=10.0,
    )

    assert result.evaluated_leaf_count == 4
    assert result.best_modeled_dps == 13.0
    assert result.global_maximum_proven is True


def test_unproven_rotation_plan_denominator_fails_closed() -> None:
    adapter = _adapter(
        plans=_PlanFrontier(
            proven=False,
            unresolved=("rotation family denominator missing",),
        )
    )

    with pytest.raises(ValueError, match="rotation family denominator missing"):
        adapter.axes()[0].candidate_count(_root(adapter))


def test_unproven_anchored_policy_denominator_fails_closed() -> None:
    adapter = _adapter(
        policies=_PolicyFrontier(
            proven=False,
            unresolved=("anchored policy input missing",),
        )
    )
    state = adapter.axes()[0].candidate_at(_root(adapter), 0)

    with pytest.raises(ValueError, match="anchored policy input missing"):
        adapter.axes()[1].candidate_count(state)


def test_policy_axis_cannot_run_before_plan_selection() -> None:
    adapter = _adapter()

    with pytest.raises(ValueError, match="selected rotation-plan family"):
        adapter.axes()[1].candidate_count(_root(adapter))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"duration_seconds": 0.0}, "duration"),
        ({"potion_cooldown_seconds": float("inf")}, "potion cooldown"),
        ({"starting_ultimate": -1.0}, "starting Ultimate"),
    ),
)
def test_root_rejects_invalid_runtime_policy_inputs(kwargs, message) -> None:
    adapter = _adapter()
    values = {
        "duration_seconds": 10.0,
        "potion_cooldown_seconds": 45.0,
        "starting_ultimate": 70.0,
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=message):
        adapter.root(_assembled(), **values)



def test_rotation_plan_axis_forwards_priorities_and_encounter_demands() -> None:
    plans = _PlanFrontier()
    adapter = _adapter(plans=plans)
    priorities = object()
    demands = ("demand-a", "demand-b")
    state = adapter.root(
        _assembled(),
        duration_seconds=10.0,
        potion_cooldown_seconds=45.0,
        starting_ultimate=70.0,
        priorities=priorities,
        encounter_demands=demands,
    )

    state = adapter.axes()[0].candidate_at(state, 1)

    call = plans.calls[-1]
    assert call[0] == "candidate_at"
    assert call[4] is priorities
    assert call[5] == demands
    assert state.rotation_plan.plan == "plan:1"



def test_rotation_policy_axis_owns_only_delayed_ultimate_timing() -> None:
    adapter = _adapter()
    policy_axis = adapter.axes()[1]

    assert policy_axis.canonical_axes == ("ultimate_policy",)
    assert policy_axis.omitted_scope == ()



def test_policy_frontier_count_receives_ultimate_runtime_inputs() -> None:
    policies = _PolicyFrontier()
    adapter = _adapter(policies=policies)
    state = _root(adapter)
    state = adapter.axes()[0].candidate_at(state, 0)

    assert adapter.axes()[1].candidate_count(state) == 2
    call = policies.calls[-1]
    assert call[0] == "frontier"
    assert call[3:] == (
        45.0,
        70.0,
        ("generation",),
        ("heroism",),
        True,
    )



def test_generated_policy_axis_always_selects_explicit_no_potion_slice() -> None:
    policies = _PolicyFrontier()
    adapter = _adapter(policies=policies)
    state = adapter.axes()[0].candidate_at(_root(adapter), 0)

    state = adapter.axes()[1].candidate_at(state, 1)

    candidate_call = next(
        row for row in reversed(policies.calls)
        if row[0] == "candidate_at"
    )
    assert candidate_call[5] == 3
    assert state.rotation_policy.structural_index == 3


def test_truthy_non_boolean_rotation_denominator_proof_fails_closed() -> None:
    plans = _PlanFrontier()
    plans.proven = "false"
    adapter = _adapter(plans=plans)

    with pytest.raises(TypeError, match="proof flag must be boolean"):
        adapter.axes()[0].candidate_count(_root(adapter))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("duration_seconds", True, "duration must be numeric"),
        ("potion_cooldown_seconds", True, "cooldown must be numeric"),
        ("starting_ultimate", True, "Ultimate must be numeric"),
        ("use_scheduled_combat_attacks_for_ultimate", "false", "flag must be boolean"),
    ),
)
def test_root_rejects_boolean_laundering_at_rotation_proof_boundary(
    field,
    value,
    message,
) -> None:
    adapter = _adapter()
    values = {
        "duration_seconds": 10.0,
        "potion_cooldown_seconds": 45.0,
        "starting_ultimate": 70.0,
        "use_scheduled_combat_attacks_for_ultimate": False,
    }
    values[field] = value

    with pytest.raises(TypeError, match=message):
        adapter.root(_assembled(), **values)



@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("ultimate_generation_events", ["generation"], "ultimate_generation_events must be a tuple"),
        ("heroism_windows", ["heroism"], "heroism_windows must be a tuple"),
        ("encounter_demands", ["demand"], "encounter_demands must be a tuple"),
    ),
)
def test_rotation_root_rejects_mutable_frontier_inputs(field, value, message) -> None:
    adapter = _adapter()
    values = {
        "duration_seconds": 10.0,
        "potion_cooldown_seconds": 45.0,
        "starting_ultimate": 70.0,
        "ultimate_generation_events": (),
        "heroism_windows": (),
        "encounter_demands": (),
    }
    values[field] = value

    with pytest.raises(TypeError, match=message):
        adapter.root(_assembled(), **values)


def test_delayed_ultimate_policy_index_rejects_boolean() -> None:
    adapter = _adapter()
    state = adapter.axes()[0].candidate_at(_root(adapter), 0)

    with pytest.raises(TypeError, match="policy index must be an integer"):
        adapter.axes()[1].candidate_at(state, True)
