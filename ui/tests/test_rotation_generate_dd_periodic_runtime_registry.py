from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageMagnitudePolicy,
    PeriodicDamageRefreshBoundary,
    RotationPeriodicDamageRuntimeSemantics,
)
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
import ui.rotation_generate_dd_role_evidence_support as dd_support


class _StaticContextService:
    def resolve(self, build):
        del build
        return SimpleNamespace(resolved=True, unresolved=())


class _Registry:
    def __init__(self, rows):
        self.rows = tuple(rows)
        self.calls = 0

    def load(self):
        self.calls += 1
        return self.rows


class _SkillProvider:
    calls = []

    def __init__(self, **kwargs):
        self.__class__.calls.append(kwargs)

    def evaluate_action(self, *, candidate, action):
        raise AssertionError("this test verifies Generate composition only")


def _bundle():
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


def test_generate_passes_reviewed_periodic_semantics_to_skill_provider(monkeypatch) -> None:
    semantic = RotationPeriodicDamageRuntimeSemantics(
        skill_entity_id="burning_talons",
        coefficient_number=2,
        first_tick_offset_seconds=2.0,
        refresh_boundary=PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK,
        source="reviewed U50 runtime evidence",
        magnitude_policy=PeriodicDamageMagnitudePolicy.SNAPSHOT_AT_CAST,
    )
    registry = _Registry((semantic,))
    _SkillProvider.calls.clear()
    monkeypatch.setattr(
        dd_support,
        "_RotationGenerateBarAwareSkillDamageProvider",
        _SkillProvider,
    )

    dd_support.RotationGenerateDDRoleEvidenceSupport(
        database_path="unused.db",
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
        periodic_runtime_semantics_registry=registry,  # type: ignore[arg-type]
    ).compose(
        player_build=PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD"),
        evidence_bundle=_bundle(),
    )

    assert registry.calls == 1
    assert len(_SkillProvider.calls) == 1
    assert _SkillProvider.calls[0]["periodic_runtime_semantics"] == (semantic,)
