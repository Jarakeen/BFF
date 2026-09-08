from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.resource_costs import ResourceType
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
    support = RotationCanonicalCandidateSupport(
        build_adapter=adapter,
        pipeline=pipeline,
    )

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
    pipeline_result = SimpleNamespace(
        selected_candidate=SimpleNamespace(
            candidate_id="safe-policy",
            reasons=("all tracked hard obligations satisfied",),
        ),
        ranked_candidates=(),
    )
    pipeline = _Pipeline(result=pipeline_result)
    support = RotationCanonicalCandidateSupport(
        build_adapter=adapter,
        pipeline=pipeline,
    )

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
    assert result.pipeline_result is pipeline_result
    assert result.validation.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE
    assert result.validation.selectable is True
    assert result.validation.selected_candidate_id == "safe-policy"


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
