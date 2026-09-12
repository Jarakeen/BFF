from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
import ui.rotation_generate_dd_role_evidence_support as dd_support


class _StaticContextService:
    def __init__(self) -> None:
        self.result = SimpleNamespace(resolved=True, unresolved=())

    def resolve(self, build):
        return self.result


class _Registry:
    def load(self):
        return ()


class _SkillProvider:
    calls = []

    def __init__(self, **kwargs) -> None:
        type(self).calls.append(kwargs)

    def evaluate_action(self, *, candidate, action):
        raise AssertionError("provider execution is not needed for binding test")


class _WeaponFactory:
    def __init__(self) -> None:
        self.calls = []

    def providers_for(self, **kwargs):
        self.calls.append(kwargs)
        return None, None


def _bundle() -> RotationCanonicalEvidenceBundle:
    return RotationCanonicalEvidenceBundle(
        encounter_id="target-resistance-test",
        encounter_name="Target Resistance Test",
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


def test_stabilized_generate_dd_providers_receive_runtime_target_resistance(monkeypatch) -> None:
    _SkillProvider.calls = []
    monkeypatch.setattr(
        dd_support,
        "_RotationGenerateBarAwareSkillDamageProvider",
        _SkillProvider,
    )
    factory = _WeaponFactory()
    support = dd_support.RotationGenerateDDRoleEvidenceSupport(
        database_path="unused.db",
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
        weapon_attack_provider_factory=factory,
        periodic_runtime_semantics_registry=_Registry(),  # type: ignore[arg-type]
    )
    evidence = support.compose(
        player_build=PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD"),
        evidence_bundle=_bundle(),
    )

    resolver_calls = []

    def target_resistance_resolver(time_seconds, sequence=None):
        resolver_calls.append((float(time_seconds), sequence))
        return 12345.0

    snapshot = SimpleNamespace(
        plan=SimpleNamespace(duration_seconds=10.0),
        runtime_combat_state_resolver=None,
        runtime_target_combat_state_resolver=None,
        runtime_target_resistance_resolver=target_resistance_resolver,
        runtime_activation_anchor_resolver=None,
    )
    rebound = evidence.plan_evidence_provider.for_stabilized_snapshot(snapshot)

    assert rebound is not evidence.plan_evidence_provider.static_provider
    assert len(_SkillProvider.calls) == 2
    assert _SkillProvider.calls[0]["runtime_target_resistance_resolver"] is None
    assert _SkillProvider.calls[1]["runtime_target_resistance_resolver"] is target_resistance_resolver
    assert len(factory.calls) == 2
    assert factory.calls[0]["runtime_target_resistance_resolver"] is None
    assert factory.calls[1]["runtime_target_resistance_resolver"] is target_resistance_resolver
    assert target_resistance_resolver(4.0, 2) == 12345.0
    assert resolver_calls == [(4.0, 2)]
