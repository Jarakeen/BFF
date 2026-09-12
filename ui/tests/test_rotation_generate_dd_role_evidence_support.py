from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
import ui.rotation_generate_dd_role_evidence_support as dd_support


class _StaticContextService:
    def __init__(self, *, resolved=True, unresolved=()) -> None:
        self.result = SimpleNamespace(resolved=resolved, unresolved=tuple(unresolved))
        self.calls = []

    def resolve(self, build):
        self.calls.append(build)
        return self.result


class _FakeSkillProvider:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def evaluate_action(self, *, candidate, action):
        damage = 200.0 if action.name == "meteor" else 100.0
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=damage,
        )


class _FixedDamageProvider:
    def __init__(self, value: float) -> None:
        self.value = float(value)
        self.calls = []

    def evaluate_action(self, *, candidate, action):
        self.calls.append((candidate, action))
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=self.value,
        )


class _WeaponAttackProviderFactory:
    def __init__(self) -> None:
        self.light = _FixedDamageProvider(40.0)
        self.heavy = _FixedDamageProvider(300.0)
        self.calls = []

    def providers_for(self, **kwargs):
        self.calls.append(kwargs)
        return self.light, self.heavy


def _bundle(*, target_resistance=18200.0):
    return RotationCanonicalEvidenceBundle(
        encounter_id="test_encounter",
        encounter_name="Test Encounter",
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
        target_resistance=target_resistance,
    )


def _dd_build(role="DD"):
    return PlayerBuild(Name="Parse Cat", BuildName="DD", Role=role)


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="dd-candidate",
        plan=RotationPlan(
            character_name="Parse Cat",
            build_name="DD",
            duration_seconds=10.0,
            actions=(
                RotationAction(
                    1.0,
                    1,
                    RotationActionKind.SKILL,
                    name="spammable",
                    bar="front",
                ),
                RotationAction(
                    5.0,
                    2,
                    RotationActionKind.ULTIMATE,
                    name="meteor",
                    bar="front",
                ),
            ),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _woven_candidate():
    return GeneratedRotationCandidate(
        candidate_id="woven-dd",
        plan=RotationPlan(
            character_name="Parse Cat",
            build_name="DD",
            duration_seconds=10.0,
            actions=(
                RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
                RotationAction(
                    0.0,
                    1,
                    RotationActionKind.SKILL,
                    name="spammable",
                    bar="front",
                ),
                RotationAction(4.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front"),
                RotationAction(
                    8.0,
                    0,
                    RotationActionKind.ULTIMATE,
                    name="meteor",
                    bar="front",
                ),
            ),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def test_compose_routes_skill_and_ultimate_into_dd_role_output(monkeypatch) -> None:
    monkeypatch.setattr(
        dd_support,
        "_RotationGenerateBarAwareSkillDamageProvider",
        _FakeSkillProvider,
    )
    static = _StaticContextService()
    support = dd_support.RotationGenerateDDRoleEvidenceSupport(
        database_path="unused-test.db",
        static_context_service=static,  # type: ignore[arg-type]
    )
    build = _dd_build()

    evidence = support.compose(player_build=build, evidence_bundle=_bundle())

    assert static.calls == [build]
    assert evidence.role_key == "dd"
    assert evidence.role_output_label == "projected DPS"
    assert evidence.content_type == "trial"
    output = evidence.plan_evidence_provider.role_output_evidence_provider.evaluate_plan(
        _candidate()
    )
    assert output.unresolved == ()
    assert output.value == pytest.approx(30.0)


def test_compose_routes_verified_light_and_heavy_attack_providers(monkeypatch) -> None:
    monkeypatch.setattr(
        dd_support,
        "_RotationGenerateBarAwareSkillDamageProvider",
        _FakeSkillProvider,
    )
    static = _StaticContextService()
    factory = _WeaponAttackProviderFactory()
    support = dd_support.RotationGenerateDDRoleEvidenceSupport(
        database_path="unused-test.db",
        static_context_service=static,  # type: ignore[arg-type]
        weapon_attack_provider_factory=factory,
    )
    build = _dd_build()

    evidence = support.compose(player_build=build, evidence_bundle=_bundle())
    output = evidence.plan_evidence_provider.role_output_evidence_provider.evaluate_plan(
        _woven_candidate()
    )

    assert len(factory.calls) == 1
    assert factory.calls[0]["player_build"] is build
    assert factory.calls[0]["static_context"] is static.result
    assert factory.calls[0]["target_resistance"] == 18200.0
    assert factory.calls[0]["runtime_build_context_resolver"] is None
    assert output.unresolved == ()
    assert output.value == pytest.approx((40.0 + 100.0 + 300.0 + 200.0) / 10.0)
    assert len(factory.light.calls) == 1
    assert len(factory.heavy.calls) == 1


def test_stabilized_dd_provider_rebinds_weapon_attacks_to_runtime_context(monkeypatch) -> None:
    monkeypatch.setattr(
        dd_support,
        "_RotationGenerateBarAwareSkillDamageProvider",
        _FakeSkillProvider,
    )
    static = _StaticContextService()
    factory = _WeaponAttackProviderFactory()
    support = dd_support.RotationGenerateDDRoleEvidenceSupport(
        database_path="unused-test.db",
        static_context_service=static,  # type: ignore[arg-type]
        weapon_attack_provider_factory=factory,
    )

    evidence = support.compose(player_build=_dd_build(), evidence_bundle=_bundle())
    snapshot = SimpleNamespace(
        plan=_woven_candidate().plan,
        runtime_combat_state_resolver=lambda *_args, **_kwargs: None,
        runtime_activation_anchor_resolver=None,
    )

    runtime_provider = evidence.plan_evidence_provider.for_stabilized_snapshot(snapshot)

    assert runtime_provider is not evidence.plan_evidence_provider.static_provider
    assert len(factory.calls) == 2
    assert callable(factory.calls[1]["runtime_build_context_resolver"])


def test_without_weapon_attack_factory_woven_damage_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        dd_support,
        "_RotationGenerateBarAwareSkillDamageProvider",
        _FakeSkillProvider,
    )
    support = dd_support.RotationGenerateDDRoleEvidenceSupport(
        database_path="unused-test.db",
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
    )

    evidence = support.compose(player_build=_dd_build(), evidence_bundle=_bundle())
    output = evidence.plan_evidence_provider.role_output_evidence_provider.evaluate_plan(
        _woven_candidate()
    )

    assert output.value is None
    assert output.unresolved == (
        "0s #0 light_attack: light_attack damage consequence has no canonical evaluator configured",
        "4s #0 heavy_attack: heavy_attack damage consequence has no canonical evaluator configured",
    )


def test_compose_requires_explicit_target_resistance() -> None:
    support = dd_support.RotationGenerateDDRoleEvidenceSupport(
        database_path="unused-test.db",
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="explicit target resistance"):
        support.compose(player_build=_dd_build(), evidence_bundle=_bundle(target_resistance=None))


def test_compose_rejects_non_dd_role() -> None:
    support = dd_support.RotationGenerateDDRoleEvidenceSupport(
        database_path="unused-test.db",
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="damage-dealer saved-build role"):
        support.compose(player_build=_dd_build("Healer"), evidence_bundle=_bundle())


def test_unresolved_static_context_fails_closed() -> None:
    support = dd_support.RotationGenerateDDRoleEvidenceSupport(
        database_path="unused-test.db",
        static_context_service=_StaticContextService(
            resolved=False,
            unresolved=("back bar static context unresolved",),
        ),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="back bar static context unresolved"):
        support.compose(player_build=_dd_build(), evidence_bundle=_bundle())
