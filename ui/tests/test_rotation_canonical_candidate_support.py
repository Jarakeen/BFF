from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.resource_costs import ResourceType
from services.canonical_knowledge_gap import CanonicalKnowledgeDomain, CanonicalKnowledgeGap
from services.rotation_mechanics_dependency_service import RotationMechanicsDependency
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport
from ui.rotation_recovery_validation_support import RotationRecoveryValidationScope


class _Adapter:
    def __init__(self, adaptation: SavedBuildAdaptation) -> None:
        self.adaptation = adaptation
        self.calls = []

    def adapt(self, saved, *, character_id=None):
        self.calls.append((saved, character_id))
        return self.adaptation


class _Pipeline:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _DependencyService:
    def __init__(self, dependencies=("dependency-a",)) -> None:
        self.dependencies = tuple(dependencies)
        self.calls = []

    def discover(self, **kwargs):
        self.calls.append(kwargs)
        return self.dependencies

    @staticmethod
    def keys(dependencies):
        return tuple(str(getattr(item, "key", item)) for item in dependencies)


class _CoverageReport:
    def __init__(self, gaps=()) -> None:
        self.gaps = tuple(gaps)
        self.calls = []

    def dependency_gaps_for(self, consumer, dependency_keys):
        self.calls.append((consumer, tuple(dependency_keys)))
        return self.gaps


class _StaticContextService:
    def __init__(self, resolution) -> None:
        self.resolution = resolution
        self.calls = []

    def resolve(self, build, **kwargs):
        self.calls.append(build)
        return self.resolution


def _static_context(*, resolved: bool, unresolved=(), maximum_by_bar=None):
    maxima = dict(maximum_by_bar or {"front": 30000, "back": 30000})
    contexts = {
        "front": SimpleNamespace(active_bar="front"),
        "back": SimpleNamespace(active_bar="back"),
    }

    def maximum_amounts_for(resource):
        return tuple((bar, amount) for bar, amount in maxima.items())

    def uniform_maximum_amount_for(resource):
        values = tuple(maxima.values())
        return values[0] if values and len(set(values)) == 1 else None

    def maximum_amount_for(bar, resource):
        return maxima[str(bar).casefold()]

    def context_for(bar):
        return contexts.get(str(bar).casefold()) if resolved else None

    def maximum_events_for(plan, resource):
        return ("bar-aware-maximum-events", plan, resource)

    def displayed_recovery_resolver_for(plan, resource):
        return ("bar-aware-displayed-recovery", plan, resource)

    return SimpleNamespace(
        resolved=resolved,
        unresolved=tuple(unresolved),
        contexts=tuple(contexts.values()) if resolved else (),
        maximum_amounts_for=maximum_amounts_for,
        uniform_maximum_amount_for=uniform_maximum_amount_for,
        maximum_amount_for=maximum_amount_for,
        context_for=context_for,
        maximum_events_for=maximum_events_for,
        displayed_recovery_resolver_for=displayed_recovery_resolver_for,
    )


def _gap(*, blocking: bool) -> CanonicalKnowledgeGap:
    return CanonicalKnowledgeGap(
        domain=CanonicalKnowledgeDomain.RESOURCE_RECOVERY,
        key="heavy_attack:restoration",
        summary="Heavy-attack restoration evidence is incomplete.",
        needed_evidence="Provide verified completed-heavy restoration evidence.",
        consumers=("rotation_maker",),
        source_context="candidate dependency test",
        blocking=blocking,
    )


def _selectable_pipeline_result():
    return SimpleNamespace(
        selected_candidate=SimpleNamespace(
            candidate_id="safe-policy",
            reasons=("all tracked hard obligations satisfied",),
        ),
        ranked_candidates=(),
    )


def _run(support: RotationCanonicalCandidateSupport, **overrides):
    values = {
        "player_build": object(),
        "seed_plan": object(),
        "priorities": object(),
        "evaluator_resolver": object(),
        "scorecard_resolver": object(),
        "resource": ResourceType.MAGICKA,
        "maximum_amount": 30000,
        "trigger_fraction": 0.35,
        "restoration_resolver": object(),
    }
    values.update(overrides)
    return support.run_effects(**values), values


def test_unresolved_saved_build_fails_closed_before_candidate_pipeline() -> None:
    canonical_build = object()
    adapter = _Adapter(
        SavedBuildAdaptation(
            build=canonical_build,
            unresolved=("Gear set not found: Example Set",),
        )
    )
    pipeline = _Pipeline(result=object())
    support = RotationCanonicalCandidateSupport(build_adapter=adapter, pipeline=pipeline)

    result, values = _run(support, character_id="character-1")

    assert adapter.calls == [(values["player_build"], "character-1")]
    assert pipeline.calls == []
    assert result.pipeline_result is None
    assert result.build_adaptation.build is canonical_build
    assert result.validation.scope is RotationRecoveryValidationScope.NOT_EVALUATED
    assert result.validation.selectable is None
    assert any("Example Set" in reason for reason in result.validation.reasons)


def test_resolved_saved_build_flows_into_effect_pipeline_with_materialized_evidence() -> None:
    canonical_build = object()
    adapter = _Adapter(SavedBuildAdaptation(build=canonical_build, unresolved=()))
    pipeline_result = _selectable_pipeline_result()
    pipeline = _Pipeline(result=pipeline_result)
    support = RotationCanonicalCandidateSupport(build_adapter=adapter, pipeline=pipeline)

    result, values = _run(
        support,
        demands=(item for item in ("demand-a", "demand-b")),
        options=(item for item in ("option-a", "option-b")),
        requirements=(item for item in ("major-brittle",)),
        passives=(item for item in ("class-passive", "armor-passive")),
        wait_decision_factory="wait-factory",
        reserve_assessment_resolver="reserve-resolver",
        max_iterations=8,
        baseline_id="saved-build-baseline",
    )

    assert len(pipeline.calls) == 1
    call = pipeline.calls[0]
    assert call["player_build"] is values["player_build"]
    assert call["character_build"] is canonical_build
    assert call["seed_plan"] is values["seed_plan"]
    assert call["priorities"] is values["priorities"]
    assert call["demands"] == ("demand-a", "demand-b")
    assert call["options"] == ("option-a", "option-b")
    assert call["requirements"] == ("major-brittle",)
    assert call["passives"] == ("class-passive", "armor-passive")
    assert call["wait_decision_factory"] == "wait-factory"
    assert call["reserve_assessment_resolver"] == "reserve-resolver"
    assert call["max_iterations"] == 8
    assert call["baseline_id"] == "saved-build-baseline"
    assert call["calculation_context"] is None
    assert call["maximum_event_resolver"] is None
    assert call["displayed_recovery_resolver_factory"] is None
    assert result.pipeline_result is pipeline_result
    assert result.validation.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE
    assert result.validation.selectable is True
    assert result.validation.selected_candidate_id == "safe-policy"


def test_unresolved_static_build_context_stops_candidate_pipeline_before_coverage() -> None:
    canonical_build = object()
    static = _static_context(
        resolved=False,
        unresolved=("front static context: Partial passive rank is not yet modeled: Prodigy 1/2",),
    )
    static_service = _StaticContextService(static)
    dependency_service = _DependencyService(("heavy_attack:restoration",))
    report = _CoverageReport((_gap(blocking=False),))
    pipeline = _Pipeline(result=_selectable_pipeline_result())
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(SavedBuildAdaptation(build=canonical_build, unresolved=())),
        pipeline=pipeline,
        dependency_service=dependency_service,
        static_context_service=static_service,
    )

    result, values = _run(support, coverage_report=report)

    assert static_service.calls == [values["player_build"]]
    assert pipeline.calls == []
    assert dependency_service.calls == []
    assert report.calls == []
    assert result.static_context is static
    assert result.validation.scope is RotationRecoveryValidationScope.NOT_EVALUATED
    assert result.validation.selectable is None
    assert any("Prodigy 1/2" in reason for reason in result.validation.reasons)


def test_resolved_static_build_context_is_retained_while_candidate_pipeline_runs() -> None:
    canonical_build = object()
    static = _static_context(resolved=True)
    static_service = _StaticContextService(static)
    pipeline_result = _selectable_pipeline_result()
    pipeline = _Pipeline(result=pipeline_result)
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(SavedBuildAdaptation(build=canonical_build, unresolved=())),
        pipeline=pipeline,
        static_context_service=static_service,
    )

    result, values = _run(support)

    assert static_service.calls == [values["player_build"]]
    assert len(pipeline.calls) == 1
    assert pipeline.calls[0]["calculation_context"] is static.context_for("front")
    assert pipeline.calls[0]["maximum_event_resolver"] is static.maximum_events_for
    assert pipeline.calls[0]["displayed_recovery_resolver_factory"] is static.displayed_recovery_resolver_for
    assert result.pipeline_result is pipeline_result
    assert result.static_context is static
    assert result.canonical_maximum_amount == 30000
    assert result.validation.selectable is True


def test_uniform_static_resource_ceiling_replaces_provisional_caller_maximum() -> None:
    canonical_build = object()
    static = _static_context(resolved=True, maximum_by_bar={"front": 31500, "back": 31500})
    pipeline = _Pipeline(result=_selectable_pipeline_result())
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(SavedBuildAdaptation(build=canonical_build, unresolved=())),
        pipeline=pipeline,
        static_context_service=_StaticContextService(static),
    )

    result, _ = _run(support, maximum_amount=99999)

    assert len(pipeline.calls) == 1
    assert pipeline.calls[0]["maximum_amount"] == 31500
    assert result.canonical_maximum_amount == 31500


def test_bar_sensitive_static_resource_ceiling_runs_with_per_plan_maximum_events() -> None:
    canonical_build = object()
    static = _static_context(
        resolved=True,
        maximum_by_bar={"front": 32000, "back": 31800},
    )
    pipeline = _Pipeline(result=_selectable_pipeline_result())
    dependency_service = _DependencyService(("heavy_attack:restoration",))
    report = _CoverageReport((_gap(blocking=False),))
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(SavedBuildAdaptation(build=canonical_build, unresolved=())),
        pipeline=pipeline,
        dependency_service=dependency_service,
        static_context_service=_StaticContextService(static),
    )

    result, _ = _run(support, coverage_report=report, maximum_amount=99999)

    assert len(pipeline.calls) == 1
    call = pipeline.calls[0]
    assert call["maximum_amount"] == 32000
    assert call["calculation_context"] is static.context_for("front")
    assert call["maximum_event_resolver"] is static.maximum_events_for
    assert call["displayed_recovery_resolver_factory"] is static.displayed_recovery_resolver_for
    assert dependency_service.calls
    assert report.calls
    assert result.pipeline_result is pipeline.result
    assert result.canonical_maximum_amount == 32000
    assert result.validation.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE
    assert result.validation.selectable is True


def test_blocking_discovered_mechanics_gap_stops_candidate_pipeline() -> None:
    canonical_build = object()
    dependency_service = _DependencyService(("heavy_attack:restoration",))
    report = _CoverageReport((_gap(blocking=True),))
    pipeline = _Pipeline(result=_selectable_pipeline_result())
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(SavedBuildAdaptation(build=canonical_build, unresolved=())),
        pipeline=pipeline,
        dependency_service=dependency_service,
    )

    result, _ = _run(
        support,
        coverage_report=report,
        demands=(item for item in ("demand-a",)),
        requirements=(item for item in ("major-brittle",)),
        passives=(item for item in ("class-passive",)),
    )

    assert pipeline.calls == []
    assert report.calls == [("rotation_maker", ("heavy_attack:restoration",))]
    assert dependency_service.calls[0]["character_build"] is canonical_build
    assert dependency_service.calls[0]["demands"] == ("demand-a",)
    assert dependency_service.calls[0]["requirements"] == ("major-brittle",)
    assert dependency_service.calls[0]["passives"] == ("class-passive",)
    assert result.pipeline_result is None
    assert result.mechanics_dependencies == ("heavy_attack:restoration",)
    assert result.knowledge_gaps == report.gaps
    assert result.validation.scope is RotationRecoveryValidationScope.NOT_EVALUATED
    assert result.validation.selectable is None
    assert any("Bring back:" in reason for reason in result.validation.reasons)


def test_blocking_gap_reason_includes_matching_exact_build_dependency_evidence() -> None:
    canonical_build = object()
    dependency = RotationMechanicsDependency(
        key="heavy_attack:restoration",
        reason="Recovery-heavy path is enabled.",
        evidence=("front:weapon=restoration_staff", "recovery_heavy_candidate_path=enabled"),
    )
    report = _CoverageReport((_gap(blocking=True),))
    pipeline = _Pipeline(result=_selectable_pipeline_result())
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(SavedBuildAdaptation(build=canonical_build, unresolved=())),
        pipeline=pipeline,
        dependency_service=_DependencyService((dependency,)),
    )

    result, _ = _run(support, coverage_report=report)

    assert pipeline.calls == []
    detail = " ".join(result.validation.reasons)
    assert "Relevant build evidence:" in detail
    assert "front:weapon=restoration_staff" in detail
    assert "recovery_heavy_candidate_path=enabled" in detail


def test_advisory_discovered_mechanics_gap_is_retained_without_blocking_pipeline() -> None:
    canonical_build = object()
    dependency_service = _DependencyService(("effect_duration:build_modifiers",))
    report = _CoverageReport((_gap(blocking=False),))
    pipeline_result = _selectable_pipeline_result()
    pipeline = _Pipeline(result=pipeline_result)
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(SavedBuildAdaptation(build=canonical_build, unresolved=())),
        pipeline=pipeline,
        dependency_service=dependency_service,
    )

    result, _ = _run(support, coverage_report=report)

    assert len(pipeline.calls) == 1
    assert result.pipeline_result is pipeline_result
    assert result.mechanics_dependencies == ("effect_duration:build_modifiers",)
    assert result.knowledge_gaps == report.gaps
    assert result.validation.selectable is True


def test_resolved_pipeline_with_no_valid_candidate_is_definitively_nonselectable() -> None:
    adapter = _Adapter(SavedBuildAdaptation(build=object(), unresolved=()))
    pipeline_result = SimpleNamespace(
        selected_candidate=None,
        ranked_candidates=(
            SimpleNamespace(
                candidate_id="resource-fix-breaks-support",
                reasons=("required effect uptime failed",),
            ),
        ),
    )
    support = RotationCanonicalCandidateSupport(
        build_adapter=adapter,
        pipeline=_Pipeline(result=pipeline_result),
    )

    result, _ = _run(support)

    assert result.validation.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE
    assert result.validation.selectable is False
    assert result.validation.selected_candidate_id is None
    assert result.validation.reasons == (
        "resource-fix-breaks-support: required effect uptime failed",
    )
