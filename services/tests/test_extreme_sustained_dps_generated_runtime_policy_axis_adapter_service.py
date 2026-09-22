from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierWiringService,
)
from services.extreme_sustained_dps_generated_runtime_policy_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedRuntimePolicyAxisAdapterService,
)


class _ExecuteFrontier:
    def __init__(self, *, proven=True, unresolved=()):
        self.proven = proven
        self.unresolved = tuple(unresolved)
        self.calls = []

    def expand(self, **kwargs):
        self.calls.append(kwargs)
        seed = kwargs["seed"]
        return SimpleNamespace(
            candidates=tuple(
                SimpleNamespace(
                    policy_id=f"execute:{index}",
                    candidate=SimpleNamespace(
                        candidate_id=f"{seed.candidate_id}|execute:{index}",
                        plan=f"{seed.plan}|execute:{index}",
                    ),
                )
                for index in range(2)
            ),
            denominator_proven=self.proven,
            unresolved=self.unresolved,
        )


class _HeavyFrontier:
    def __init__(self, *, proven=True, unresolved=()):
        self.proven = proven
        self.unresolved = tuple(unresolved)
        self.calls = []

    def expand(self, **kwargs):
        self.calls.append(kwargs)
        seed = kwargs["seed"]
        return SimpleNamespace(
            candidates=tuple(
                SimpleNamespace(
                    policy_id=f"heavy:{index}",
                    candidate=SimpleNamespace(
                        candidate_id=f"{seed.candidate_id}|heavy:{index}",
                        plan=f"{seed.plan}|heavy:{index}",
                    ),
                )
                for index in range(2)
            ),
            denominator_proven=self.proven,
            unresolved=self.unresolved,
        )


def _adapter(*, execute=None, heavy=None):
    return ExtremeSustainedDPSGeneratedRuntimePolicyAxisAdapterService(
        execute_policies=execute or _ExecuteFrontier(),
        heavy_attack_policies=heavy or _HeavyFrontier(),
    )


def _root(adapter):
    return adapter.root(
        SimpleNamespace(plan="anchored-plan"),
        candidate_id="assembled:7|rotation:3",
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="boss",
        duration_rules=("rule",),
        heavy_attack_windows=("reviewed-window",),
    )


def test_runtime_policy_axes_preserve_evidence_and_dependency_order() -> None:
    execute = _ExecuteFrontier()
    heavy = _HeavyFrontier()
    adapter = _adapter(execute=execute, heavy=heavy)
    axes = adapter.axes()

    assert tuple(axis.name for axis in axes) == (
        "Execute Policy",
        "Reviewed Heavy Attack Policy",
    )

    state = _root(adapter)
    assert state.seed.plan == "anchored-plan"
    assert state.seed.refresh_leads == ()
    assert state.seed.action_claims == ()

    assert axes[0].candidate_count(state) == 2
    state = axes[0].candidate_at(state, 1)
    assert axes[1].candidate_count(state) == 2
    state = axes[1].candidate_at(state, 1)

    assert state.complete is True
    assert state.current_candidate.plan == (
        "anchored-plan|execute:1|heavy:1"
    )
    assert execute.calls[-1]["target_identity"] == "boss"
    assert execute.calls[-1]["snapshot_resolver"] == "resolver"
    assert execute.calls[-1]["duration_rules"] == ("rule",)
    assert heavy.calls[-1]["windows"] == ("reviewed-window",)


def test_runs_explicit_runtime_policy_product_through_lazy_search() -> None:
    adapter = _adapter()

    def evaluate(node):
        assert node.state.complete
        execute_index = int(node.state.execute_policy.policy_id.rsplit(":", 1)[1])
        heavy_index = int(node.state.heavy_attack_policy.policy_id.rsplit(":", 1)[1])
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=node.candidate_key,
            modeled_dps=float(execute_index * 10 + heavy_index),
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
    assert result.best_modeled_dps == 11.0
    assert result.global_maximum_proven is True


def test_unproven_execute_denominator_fails_closed() -> None:
    adapter = _adapter(
        execute=_ExecuteFrontier(
            proven=False,
            unresolved=("target Health snapshot missing",),
        )
    )

    with pytest.raises(ValueError, match="target Health snapshot missing"):
        adapter.axes()[0].candidate_count(_root(adapter))


def test_unproven_heavy_attack_denominator_fails_closed() -> None:
    adapter = _adapter(
        heavy=_HeavyFrontier(
            proven=False,
            unresolved=("reviewed channel collision",),
        )
    )
    state = adapter.axes()[0].candidate_at(_root(adapter), 0)

    with pytest.raises(ValueError, match="reviewed channel collision"):
        adapter.axes()[1].candidate_count(state)


def test_heavy_attack_axis_cannot_run_before_execute_selection() -> None:
    adapter = _adapter()

    with pytest.raises(ValueError, match="selected execute policy"):
        adapter.axes()[1].candidate_count(_root(adapter))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"candidate_id": " "}, "candidate_id"),
        ({"target_identity": ""}, "target identity"),
        ({"snapshot_resolver": None}, "snapshot resolver"),
    ),
)
def test_root_requires_explicit_runtime_policy_identity_and_evidence(
    kwargs,
    message,
) -> None:
    adapter = _adapter()
    values = {
        "candidate_id": "candidate",
        "priorities": object(),
        "snapshot_resolver": object(),
        "target_identity": "boss",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=message):
        adapter.root(SimpleNamespace(plan="plan"), **values)



def test_heavy_attack_axis_carries_reviewed_window_omission() -> None:
    adapter = _adapter()
    heavy_axis = adapter.axes()[1]

    assert heavy_axis.canonical_axes == ("heavy_attack_policy",)
    assert heavy_axis.omitted_scope == (
        "Heavy Attack windows outside the caller-supplied reviewed safe set are not claimed closed",
    )
