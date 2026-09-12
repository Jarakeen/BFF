from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
    PeriodicDamageMagnitudePolicy,
)
from services.rotation_dd_periodic_runtime_semantics_registry_service import (
    RotationDDPeriodicRuntimeSemanticsRegistryService,
)
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
import ui.rotation_generate_dd_role_evidence_support as dd_support


class _StaticContextService:
    def resolve(self, build):
        del build
        return SimpleNamespace(resolved=True, unresolved=())


class _Registry:
    def load(self):
        return ()


class _RecordingSupport(dd_support.RotationGenerateDDRoleEvidenceSupport):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.calls = []

    def _build_plan_evidence_provider(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(role_output_evidence_provider=object())


def _bundle() -> RotationCanonicalEvidenceBundle:
    return RotationCanonicalEvidenceBundle(
        encounter_id="test",
        encounter_name="Test",
        content_type="trial",
        demands=(),
        options=(),
        requirements=(),
        passives=(),
        evaluator_resolver=None,
        scorecard_resolver=None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.35,
        target_resistance=18200.0,
    )


def _support() -> _RecordingSupport:
    return _RecordingSupport(
        database_path="unused.db",
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
        periodic_runtime_semantics_registry=_Registry(),  # type: ignore[arg-type]
    )


def test_generate_binds_snapshot_activation_anchor_resolver() -> None:
    support = _support()
    role_evidence = support.compose(
        player_build=PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD"),
        evidence_bundle=_bundle(),
    )

    assert len(support.calls) == 1
    assert support.calls[0]["activation_anchor_resolver"] is None

    runtime_combat_state_resolver = object()

    def anchor_resolver(action, anchor):
        del action, anchor
        return 2.25

    snapshot = SimpleNamespace(
        plan=SimpleNamespace(duration_seconds=37.0),
        runtime_combat_state_resolver=runtime_combat_state_resolver,
        runtime_activation_anchor_resolver=anchor_resolver,
    )
    role_evidence.plan_evidence_provider.for_stabilized_snapshot(snapshot)

    assert len(support.calls) == 2
    runtime_call = support.calls[1]
    assert runtime_call["runtime_build_context_resolver"] is not None
    assert runtime_call["activation_anchor_resolver"] is anchor_resolver


def test_anchor_only_snapshot_still_builds_runtime_provider() -> None:
    support = _support()
    role_evidence = support.compose(
        player_build=PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD"),
        evidence_bundle=_bundle(),
    )

    def anchor_resolver(action, anchor):
        del action, anchor
        return 1.5

    snapshot = SimpleNamespace(
        plan=SimpleNamespace(duration_seconds=20.0),
        runtime_combat_state_resolver=None,
        runtime_activation_anchor_resolver=anchor_resolver,
    )
    role_evidence.plan_evidence_provider.for_stabilized_snapshot(snapshot)

    assert len(support.calls) == 2
    runtime_call = support.calls[1]
    assert runtime_call["runtime_build_context_resolver"] is None
    assert runtime_call["activation_anchor_resolver"] is anchor_resolver


def test_generate_stabilized_stampede_provider_composes_reviewed_runtime_authorities() -> None:
    support = _RecordingSupport(
        database_path="unused.db",
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
        periodic_runtime_semantics_registry=(
            RotationDDPeriodicRuntimeSemanticsRegistryService()
        ),
    )
    role_evidence = support.compose(
        player_build=PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD"),
        evidence_bundle=_bundle(),
    )

    runtime_combat_state_resolver = object()

    def anchor_resolver(action, anchor):
        del action, anchor
        return 1.3

    snapshot = SimpleNamespace(
        plan=SimpleNamespace(duration_seconds=37.0),
        runtime_combat_state_resolver=runtime_combat_state_resolver,
        runtime_activation_anchor_resolver=anchor_resolver,
    )
    role_evidence.plan_evidence_provider.for_stabilized_snapshot(snapshot)

    assert len(support.calls) == 2
    runtime_call = support.calls[1]
    stampede = next(
        row
        for row in runtime_call["periodic_runtime_semantics"]
        if row.skill_entity_id == "stampede" and row.coefficient_number == 2
    )

    assert stampede.activation_anchor is PeriodicDamageActivationAnchor.IMPACT
    assert stampede.magnitude_policy is PeriodicDamageMagnitudePolicy.DYNAMIC_AT_TICK
    assert stampede.first_tick_offset_seconds == 1.0
    assert stampede.verified_interval_seconds == 1.0
    assert runtime_call["runtime_build_context_resolver"] is not None
    assert runtime_call["activation_anchor_resolver"] is anchor_resolver
