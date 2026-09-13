from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationActionKind
from models.build_model import PlayerBuild
from ui.rotation_generate_dd_target_health_role_evidence_support import (
    RotationGenerateDDTargetHealthRoleEvidenceSupport,
    _RotationGenerateTargetHealthBarAwareSkillDamageProvider,
)


class _EmptyTargetHealthRegistry:
    def load(self):
        return ()


def test_live_support_installs_target_health_aware_skill_provider_without_enabling_unreviewed_health() -> None:
    support = RotationGenerateDDTargetHealthRoleEvidenceSupport(
        database_path="unused-test.db",
        periodic_target_health_semantics_registry=_EmptyTargetHealthRegistry(),  # type: ignore[arg-type]
    )

    plan_evidence = support._build_plan_evidence_provider(
        player_build=PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD"),
        evidence_bundle=SimpleNamespace(resource=ResourceType.MAGICKA),
        static_context=SimpleNamespace(),
        target_resistance=18200.0,
        periodic_runtime_semantics=(),
        runtime_build_context_resolver=None,
        runtime_target_combat_state_resolver=None,
        runtime_target_resistance_resolver=None,
        activation_anchor_resolver=None,
    )

    role_output = plan_evidence.role_output_evidence_provider
    router = role_output.action_damage_evidence_provider
    skill_provider = router._providers[RotationActionKind.SKILL]

    assert isinstance(skill_provider, _RotationGenerateTargetHealthBarAwareSkillDamageProvider)
    assert skill_provider.periodic_target_health_semantics == ()
    assert skill_provider.runtime_target_snapshot_resolver is None
    assert skill_provider.target_identity == ""


def test_live_support_preserves_explicit_target_snapshot_inputs() -> None:
    resolver = lambda time_seconds, sequence=None: None
    support = RotationGenerateDDTargetHealthRoleEvidenceSupport(
        database_path="unused-test.db",
        periodic_target_health_semantics_registry=_EmptyTargetHealthRegistry(),  # type: ignore[arg-type]
        runtime_target_snapshot_resolver=resolver,
        target_identity="boss",
    )

    plan_evidence = support._build_plan_evidence_provider(
        player_build=PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD"),
        evidence_bundle=SimpleNamespace(resource=ResourceType.MAGICKA),
        static_context=SimpleNamespace(),
        target_resistance=18200.0,
        periodic_runtime_semantics=(),
        runtime_build_context_resolver=None,
        runtime_target_combat_state_resolver=None,
        runtime_target_resistance_resolver=None,
        activation_anchor_resolver=None,
    )

    router = plan_evidence.role_output_evidence_provider.action_damage_evidence_provider
    skill_provider = router._providers[RotationActionKind.SKILL]

    assert skill_provider.runtime_target_snapshot_resolver is resolver
    assert skill_provider.target_identity == "boss"
