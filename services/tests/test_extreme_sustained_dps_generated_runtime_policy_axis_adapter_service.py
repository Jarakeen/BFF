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
        materializer = kwargs.get("candidate_materializer")
        if materializer is None:
            candidates = tuple(
                SimpleNamespace(
                    policy_id=f"heavy:{index}",
                    candidate=SimpleNamespace(
                        candidate_id=f"{seed.candidate_id}|heavy:{index}",
                        plan=f"{seed.plan}|heavy:{index}",
                    ),
                )
                for index in range(2)
            )
        else:
            windows = tuple(kwargs["windows"])
            candidates = (
                SimpleNamespace(
                    policy_id="heavy:none",
                    candidate=seed,
                ),
                SimpleNamespace(
                    policy_id="heavy:discovered",
                    candidate=materializer(windows[:1]),
                ),
            )
        return SimpleNamespace(
            candidates=candidates,
            denominator_proven=self.proven,
            unresolved=self.unresolved,
        )


class _HeavyDiscovery:
    def __init__(self, *, proven=True, unresolved=()):
        self.proven = proven
        self.unresolved = tuple(unresolved)
        self.discover_calls = []
        self.materialize_calls = []

    def discover(self, **kwargs):
        self.discover_calls.append(kwargs)
        return SimpleNamespace(
            windows=("discovered-window-a", "discovered-window-b"),
            denominator_proven=self.proven,
            unresolved=self.unresolved,
        )

    def materialize(self, **kwargs):
        self.materialize_calls.append(kwargs)
        seed = kwargs["seed"]
        selected = tuple(kwargs["windows"])
        return SimpleNamespace(
            candidate_id=f"{seed.candidate_id}|scheduler-heavy",
            plan=f"{seed.plan}|scheduler:{','.join(selected)}",
        )


def _adapter(*, execute=None, heavy=None, discovery=None, complete=False):
    return ExtremeSustainedDPSGeneratedRuntimePolicyAxisAdapterService(
        execute_policies=execute or _ExecuteFrontier(),
        heavy_attack_policies=heavy or _HeavyFrontier(),
        heavy_attack_window_discovery=discovery,
        require_complete_heavy_attack_discovery=complete,
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
        heavy_attack_channel_blocks=("channel-block",),
        heavy_attack_channel_block_denominator_proven=True,
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



def test_complete_heavy_attack_discovery_uses_discovered_windows_and_materializer() -> None:
    discovery = _HeavyDiscovery()
    heavy = _HeavyFrontier()
    adapter = _adapter(
        heavy=heavy,
        discovery=discovery,
        complete=True,
    )
    state = adapter.axes()[0].candidate_at(_root(adapter), 0)

    assert adapter.axes()[1].candidate_count(state) == 2
    state = adapter.axes()[1].candidate_at(state, 1)

    assert discovery.discover_calls
    discover_call = discovery.discover_calls[-1]
    assert discover_call["duration_rules"] == ("rule",)
    assert discover_call["priorities"] == "priorities"
    assert discover_call["channel_blocks"] == ("channel-block",)
    assert discover_call["channel_block_denominator_proven"] is True

    assert heavy.calls[-1]["windows"] == (
        "discovered-window-a",
        "discovered-window-b",
    )
    assert callable(heavy.calls[-1]["candidate_materializer"])
    assert discovery.materialize_calls
    assert state.current_candidate.plan.endswith(
        "|scheduler:discovered-window-a"
    )


def test_complete_heavy_attack_discovery_requires_channel_block_denominator_proof() -> None:
    adapter = _adapter(
        discovery=_HeavyDiscovery(),
        complete=True,
    )
    root = adapter.root(
        SimpleNamespace(plan="anchored-plan"),
        candidate_id="candidate",
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="boss",
        duration_rules=("rule",),
    )
    state = adapter.axes()[0].candidate_at(root, 0)

    with pytest.raises(
        ValueError,
        match="proven encounter channel-block denominator",
    ):
        adapter.axes()[1].candidate_count(state)


def test_unproven_discovered_heavy_attack_denominator_fails_closed() -> None:
    adapter = _adapter(
        discovery=_HeavyDiscovery(
            proven=False,
            unresolved=("encounter channel policy unresolved",),
        ),
        complete=True,
    )
    state = adapter.axes()[0].candidate_at(_root(adapter), 0)

    with pytest.raises(ValueError, match="encounter channel policy unresolved"):
        adapter.axes()[1].candidate_count(state)


def test_complete_heavy_attack_axis_has_no_reviewed_window_omission() -> None:
    adapter = _adapter(
        discovery=_HeavyDiscovery(),
        complete=True,
    )

    assert adapter.axes()[1].canonical_axes == ("heavy_attack_policy",)
    assert adapter.axes()[1].omitted_scope == ()


def test_truthy_non_boolean_runtime_policy_denominator_proof_fails_closed() -> None:
    execute = _ExecuteFrontier()
    execute.expand = lambda **kwargs: SimpleNamespace(
        candidates=(object(),),
        denominator_proven="false",
        unresolved=(),
    )
    adapter = _adapter(execute=execute)

    with pytest.raises(TypeError, match="proof flag must be boolean"):
        adapter.axes()[0].candidate_count(_root(adapter))


def test_runtime_policy_complete_discovery_flag_requires_boolean() -> None:
    with pytest.raises(TypeError, match="discovery flag must be boolean"):
        ExtremeSustainedDPSGeneratedRuntimePolicyAxisAdapterService(
            execute_policies=_ExecuteFrontier(),
            heavy_attack_policies=_HeavyFrontier(),
            require_complete_heavy_attack_discovery="false",
        )



@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("duration_rules", ["rule"], "duration_rules must be a tuple"),
        ("heavy_attack_windows", ["window"], "heavy_attack_windows must be a tuple"),
        ("heavy_attack_channel_blocks", ["block"], "heavy_attack_channel_blocks must be a tuple"),
        (
            "heavy_attack_channel_block_denominator_proven",
            "false",
            "denominator proof must be boolean",
        ),
    ),
)
def test_runtime_policy_root_rejects_mutable_or_truthy_proof_inputs(
    field,
    value,
    message,
) -> None:
    adapter = _adapter()
    values = {
        "candidate_id": "candidate",
        "priorities": object(),
        "snapshot_resolver": object(),
        "target_identity": "boss",
        "duration_rules": (),
        "heavy_attack_windows": (),
        "heavy_attack_channel_blocks": (),
        "heavy_attack_channel_block_denominator_proven": False,
    }
    values[field] = value

    with pytest.raises(TypeError, match=message):
        adapter.root(SimpleNamespace(plan="plan"), **values)



def test_complete_heavy_attack_discovery_rejects_truthy_non_boolean_denominator() -> None:
    discovery = _HeavyDiscovery()
    discovery.proven = "false"
    adapter = _adapter(discovery=discovery, complete=True)
    state = adapter.axes()[0].candidate_at(_root(adapter), 0)

    with pytest.raises(TypeError, match="discovery denominator proof flag must be boolean"):
        adapter.axes()[1].candidate_count(state)
