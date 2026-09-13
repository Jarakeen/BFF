from types import SimpleNamespace

from minmax.rotation_plan import RotationActionKind
from models.build_model import PlayerBuild
from services.rotation_candidate_periodic_damage_conditional_output_service import (
    RotationCandidatePeriodicDamageConditionalOutputService,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_generate_dd_conditional_output_support import (
    RotationGenerateDDConditionalOutputSupport,
)


class _RawProjection:
    def project(self, *, plan, semantics):
        del plan, semantics
        raise AssertionError("projection execution is not part of this composition test")


class _PlanProvider:
    def __init__(self, projection=None):
        self.skill_provider = SimpleNamespace(
            periodic_runtime_projection_service=projection,
        )
        self.role_output_evidence_provider = SimpleNamespace(
            action_damage_evidence_provider=SimpleNamespace(
                _providers={RotationActionKind.SKILL: self.skill_provider}
            )
        )

    def evaluate_plan(self, candidate):
        return candidate


class _SnapshotProvider:
    def __init__(self, *, static_provider, runtime_provider_factory):
        self.static_provider = static_provider
        self.runtime_provider_factory = runtime_provider_factory


class _BaseSupport:
    def __init__(self, snapshot_provider):
        self.snapshot_provider = snapshot_provider

    def compose(self, *, player_build, evidence_bundle):
        del player_build, evidence_bundle
        return RotationCanonicalRoleEvidence(
            plan_evidence_provider=self.snapshot_provider,
            role_output_label="projected DPS",
            assigned_support_label="assigned support coverage",
            role_key="dd",
        )


def _snapshot(**overrides):
    values = dict(
        runtime_combat_state_resolver=None,
        runtime_target_combat_state_resolver=None,
        runtime_target_resistance_resolver=None,
        runtime_activation_anchor_resolver=None,
        runtime_output_condition_context_resolver=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _compose(*, static_projection=True):
    static = _PlanProvider(_RawProjection() if static_projection else None)
    runtime_calls = []

    def runtime_factory(snapshot):
        runtime_calls.append(snapshot)
        return _PlanProvider(_RawProjection())

    base = _BaseSupport(
        _SnapshotProvider(
            static_provider=static,
            runtime_provider_factory=runtime_factory,
        )
    )
    evidence = RotationGenerateDDConditionalOutputSupport(base).compose(
        player_build=PlayerBuild(Name="DD", BuildName="Conditional"),
        evidence_bundle=SimpleNamespace(),
    )
    return evidence, static, runtime_calls


def test_static_dd_periodic_projection_is_wrapped_fail_closed() -> None:
    evidence, static, runtime_calls = _compose()

    projection = static.skill_provider.periodic_runtime_projection_service
    assert isinstance(
        projection,
        RotationCandidatePeriodicDamageConditionalOutputService,
    )
    assert projection.condition_context_resolver is None
    assert evidence.plan_evidence_provider.evaluate_plan("candidate") == "candidate"
    assert runtime_calls == []


def test_condition_context_alone_triggers_stabilized_runtime_rebind() -> None:
    evidence, _static, runtime_calls = _compose()
    resolver = lambda _event: frozenset({"target_in_some_reviewed_geometry"})
    snapshot = _snapshot(runtime_output_condition_context_resolver=resolver)

    runtime_provider = evidence.plan_evidence_provider.for_stabilized_snapshot(snapshot)

    assert runtime_calls == [snapshot]
    projection = runtime_provider.role_output_evidence_provider.action_damage_evidence_provider._providers[
        RotationActionKind.SKILL
    ].periodic_runtime_projection_service
    assert isinstance(
        projection,
        RotationCandidatePeriodicDamageConditionalOutputService,
    )
    assert projection.condition_context_resolver is resolver


def test_no_runtime_facts_reuses_static_provider() -> None:
    evidence, static, runtime_calls = _compose()

    selected = evidence.plan_evidence_provider.for_stabilized_snapshot(_snapshot())

    assert selected is static
    assert runtime_calls == []


def test_existing_runtime_fact_still_rebinds_without_condition_context() -> None:
    evidence, _static, runtime_calls = _compose()
    snapshot = _snapshot(runtime_combat_state_resolver=object())

    runtime_provider = evidence.plan_evidence_provider.for_stabilized_snapshot(snapshot)

    assert runtime_calls == [snapshot]
    projection = runtime_provider.role_output_evidence_provider.action_damage_evidence_provider._providers[
        RotationActionKind.SKILL
    ].periodic_runtime_projection_service
    assert isinstance(
        projection,
        RotationCandidatePeriodicDamageConditionalOutputService,
    )
    assert projection.condition_context_resolver is None


def test_missing_periodic_projection_remains_valid_for_direct_only_support() -> None:
    evidence, static, runtime_calls = _compose(static_projection=False)

    assert static.skill_provider.periodic_runtime_projection_service is None
    assert evidence.plan_evidence_provider.for_stabilized_snapshot(_snapshot()) is static
    assert runtime_calls == []
