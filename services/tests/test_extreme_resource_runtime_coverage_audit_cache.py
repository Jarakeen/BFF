from types import SimpleNamespace

import services.extreme_resource_runtime_coverage_audit_service as module
from services.extreme_resource_contextual_passive_review_service import (
    ExtremeResourceContextualPassiveStatus,
)
from services.extreme_resource_runtime_coverage_audit_service import (
    ExtremeResourceRuntimeCoverageAuditService,
)


class _CanonicalRepository:
    def __init__(self, database_path):
        self.database_path = str(database_path)


class _BreakpointService:
    calls = 0

    def __init__(self, repository):
        assert isinstance(repository, _CanonicalRepository)

    def build(self):
        type(self).calls += 1
        return object()


class _RelevanceService:
    calls = 0

    def __init__(self, repository):
        assert isinstance(repository, _CanonicalRepository)

    def build(self, key, breakpoints):
        type(self).calls += 1
        return SimpleNamespace(
            evidence=(),
            unresolved=(),
            denominator_proven=True,
        )


class _PassiveReviewService:
    @classmethod
    def build(cls, key):
        return (
            SimpleNamespace(
                skill_line="Reviewed Line",
                passive_name="Reviewed Passive",
                status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            ),
        )


def test_canonical_database_runtime_audit_is_shared_across_service_instances(monkeypatch, tmp_path):
    ExtremeResourceRuntimeCoverageAuditService._DATABASE_CACHE.clear()
    _BreakpointService.calls = 0
    _RelevanceService.calls = 0

    monkeypatch.setattr(module, "GearSetRepository", _CanonicalRepository)
    monkeypatch.setattr(module, "ExtremeGearSetBonusBreakpointService", _BreakpointService)
    monkeypatch.setattr(module, "ExtremeGearSetObjectiveRelevanceService", _RelevanceService)
    monkeypatch.setattr(module, "ExtremeResourceContextualPassiveReviewService", _PassiveReviewService)

    database = tmp_path / "eso.db"
    first = ExtremeResourceRuntimeCoverageAuditService(database).build("max_magicka")
    second = ExtremeResourceRuntimeCoverageAuditService(database).build("max_magicka")

    assert first is second
    assert first.denominator_proven is True
    assert _BreakpointService.calls == 1
    assert _RelevanceService.calls == 1


def test_injected_repository_does_not_enter_shared_database_cache(monkeypatch):
    class _InjectedRepository:
        pass

    class _InjectedBreakpointService:
        calls = 0

        def __init__(self, repository):
            assert isinstance(repository, _InjectedRepository)

        def build(self):
            type(self).calls += 1
            return object()

    class _InjectedRelevanceService:
        def __init__(self, repository):
            assert isinstance(repository, _InjectedRepository)

        def build(self, key, breakpoints):
            return SimpleNamespace(evidence=(), unresolved=(), denominator_proven=True)

    ExtremeResourceRuntimeCoverageAuditService._DATABASE_CACHE.clear()
    monkeypatch.setattr(module, "ExtremeGearSetBonusBreakpointService", _InjectedBreakpointService)
    monkeypatch.setattr(module, "ExtremeGearSetObjectiveRelevanceService", _InjectedRelevanceService)
    monkeypatch.setattr(module, "ExtremeResourceContextualPassiveReviewService", _PassiveReviewService)

    ExtremeResourceRuntimeCoverageAuditService(repository=_InjectedRepository()).build("max_magicka")
    ExtremeResourceRuntimeCoverageAuditService(repository=_InjectedRepository()).build("max_magicka")

    assert _InjectedBreakpointService.calls == 2
    assert ExtremeResourceRuntimeCoverageAuditService._DATABASE_CACHE == {}
