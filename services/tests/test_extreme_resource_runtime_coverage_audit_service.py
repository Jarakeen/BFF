from types import SimpleNamespace

import services.extreme_resource_runtime_coverage_audit_service as module
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
)
from services.extreme_resource_contextual_passive_review_service import (
    ExtremeResourceContextualPassiveStatus,
)
from services.extreme_resource_runtime_coverage_audit_service import (
    ExtremeResourceRuntimeCoverageAuditService,
)


class _Repository:
    pass


class _BreakpointService:
    def __init__(self, repository):
        assert isinstance(repository, _Repository)

    def build(self):
        return object()


class _RelevanceService:
    def __init__(self, repository):
        assert isinstance(repository, _Repository)

    def build(self, key, breakpoints):
        assert key == "max_health"
        return SimpleNamespace(
            evidence=(
                SimpleNamespace(
                    status=ExtremeGearSetObjectiveRelevance.RELEVANT,
                    set_id=10,
                    set_name="Conditional Health Set",
                    piece_count=5,
                    candidate=SimpleNamespace(
                        source_effects=(
                            Effect(
                                operation=EffectOperation.ADD,
                                value=2500.0,
                                source="Conditional Health Set (5)",
                                stat=StatId.MAX_HEALTH,
                                unit=EffectUnit.FLAT,
                                condition="food_buff_active",
                            ),
                        ),
                    ),
                ),
                SimpleNamespace(
                    status=ExtremeGearSetObjectiveRelevance.RELEVANT,
                    set_id=20,
                    set_name="Static Health Set",
                    piece_count=5,
                    candidate=SimpleNamespace(
                        source_effects=(
                            Effect(
                                operation=EffectOperation.ADD,
                                value=1200.0,
                                source="Static Health Set (5)",
                                stat=StatId.MAX_HEALTH,
                                unit=EffectUnit.FLAT,
                            ),
                        ),
                    ),
                ),
            ),
            unresolved=(),
            denominator_proven=True,
        )


class _PassiveReviewService:
    @classmethod
    def build(cls, key):
        assert key == "max_health"
        return (
            SimpleNamespace(
                skill_line="Green Balance",
                passive_name="Maturation",
                status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            ),
        )


def test_conditional_gear_effect_remains_explicit_runtime_blocker(monkeypatch):
    monkeypatch.setattr(module, "ExtremeGearSetBonusBreakpointService", _BreakpointService)
    monkeypatch.setattr(module, "ExtremeGearSetObjectiveRelevanceService", _RelevanceService)
    monkeypatch.setattr(module, "ExtremeResourceContextualPassiveReviewService", _PassiveReviewService)

    audit = ExtremeResourceRuntimeCoverageAuditService(repository=_Repository()).build("max_health")

    assert audit.denominator_proven is True
    assert audit.projection_complete is False
    assert audit.condition_markers == ("food_buff_active",)
    assert len(audit.conditional_gear_effects) == 1
    assert audit.conditional_gear_effects[0].set_name == "Conditional Health Set"
    assert audit.contextual_passives_reviewed == ("Green Balance: Maturation",)
    assert audit.unresolved == ()


def test_runtime_projection_closes_when_relevant_gear_has_no_conditions(monkeypatch):
    class _StaticRelevanceService(_RelevanceService):
        def build(self, key, breakpoints):
            result = super().build(key, breakpoints)
            return SimpleNamespace(
                evidence=(result.evidence[1],),
                unresolved=(),
                denominator_proven=True,
            )

    monkeypatch.setattr(module, "ExtremeGearSetBonusBreakpointService", _BreakpointService)
    monkeypatch.setattr(module, "ExtremeGearSetObjectiveRelevanceService", _StaticRelevanceService)
    monkeypatch.setattr(module, "ExtremeResourceContextualPassiveReviewService", _PassiveReviewService)

    audit = ExtremeResourceRuntimeCoverageAuditService(repository=_Repository()).build("max_health")

    assert audit.denominator_proven is True
    assert audit.projection_complete is True
    assert audit.conditional_gear_effects == ()
    assert audit.condition_markers == ()


def test_contextual_passive_boundary_fails_closed(monkeypatch):
    class _OpenPassiveReviewService:
        @classmethod
        def build(cls, key):
            return (
                SimpleNamespace(
                    skill_line="Some Line",
                    passive_name="Some Passive",
                    status=ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED,
                ),
            )

    monkeypatch.setattr(module, "ExtremeGearSetBonusBreakpointService", _BreakpointService)
    monkeypatch.setattr(module, "ExtremeGearSetObjectiveRelevanceService", _RelevanceService)
    monkeypatch.setattr(module, "ExtremeResourceContextualPassiveReviewService", _OpenPassiveReviewService)

    audit = ExtremeResourceRuntimeCoverageAuditService(repository=_Repository()).build("max_health")

    assert audit.denominator_proven is False
    assert audit.projection_complete is False
    assert any("Some Passive" in item for item in audit.unresolved)


def test_unreviewed_runtime_objective_fails_closed():
    service = ExtremeResourceRuntimeCoverageAuditService(repository=_Repository())
    try:
        service.build("spell_damage")
    except KeyError as exc:
        assert "unreviewed Extreme resource runtime objective" in str(exc)
    else:
        raise AssertionError("expected unsupported runtime objective to fail closed")
