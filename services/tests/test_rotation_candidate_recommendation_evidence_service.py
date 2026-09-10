import pytest

from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidatePlanEvidence,
    RotationCandidateRecommendationEvidenceService,
    RotationCandidateSharedEvaluationContext,
)
from services.rotation_candidate_recommendation_service import (
    RotationCandidateRecommendationService,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


def _plan(name: str) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name=name,
        duration_seconds=20.0,
        actions=(),
    )


def _candidate(candidate_id: str) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=_plan(candidate_id),
        refresh_leads=(),
        action_claims=(),
    )


def _scorecard(*, missing_effects: tuple[str, ...] = ()) -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=RotationPlanConsequence(
            resource_kind=RotationResourceConsequenceKind.NEUTRAL,
            cast_deltas=(),
            cost_deltas=(),
            total_cost_delta=0,
            minimum_resource_delta=0,
            ending_resource_delta=0,
            shortfall_delta=0,
            wait_delta=0,
        ),
        demand_coverage=(),
        missing_required_effects=missing_effects,
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


class _PlanEvidenceProvider:
    def __init__(self, by_id):
        self.by_id = by_id
        self.calls = []

    def evaluate_plan(self, candidate):
        self.calls.append(candidate.candidate_id)
        return self.by_id[candidate.candidate_id]


class _ScorecardService:
    def __init__(self, by_candidate_id):
        self.by_candidate_id = by_candidate_id
        self.calls = []

    def compare(self, **kwargs):
        self.calls.append(kwargs)
        return self.by_candidate_id[kwargs["candidate_plan"].build_name]


def _plan_evidence(
    *,
    output: float | None,
    support: float | None = None,
    sustain: float | None = 1000.0,
    displacement: float | None = 0.0,
):
    return RotationCandidatePlanEvidence(
        sustain=object(),
        duration=None,
        role_output_value=output,
        assigned_support_value=support,
        sustain_margin=sustain,
        primary_role_displacement_seconds=displacement,
    )


def test_evidence_bridge_feeds_real_recommendation_composer_without_recomputing_policy() -> None:
    candidates = (
        _candidate("baseline"),
        _candidate("huge-output-misses-job"),
        _candidate("valid-output"),
    )
    plan_provider = _PlanEvidenceProvider(
        {
            "baseline": _plan_evidence(output=100_000),
            "huge-output-misses-job": _plan_evidence(output=250_000),
            "valid-output": _plan_evidence(output=125_000),
        }
    )
    scorecards = _ScorecardService(
        {
            "baseline": _scorecard(),
            "huge-output-misses-job": _scorecard(
                missing_effects=("major_brittle",)
            ),
            "valid-output": _scorecard(),
        }
    )
    evidence_service = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_provider,
        scorecard_service=scorecards,
    )

    result = RotationCandidateRecommendationService().recommend(
        candidates=candidates,
        evidence_provider=evidence_service,
        role_key="dd",
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "valid-output"
    assert [entry.candidate.candidate_id for entry in result.entries] == [
        "valid-output",
        "baseline",
        "huge-output-misses-job",
    ]
    assert plan_provider.calls == [
        "baseline",
        "huge-output-misses-job",
        "valid-output",
    ]
    assert len(scorecards.calls) == 3
    assert all(
        call["baseline_plan"].build_name == "baseline"
        for call in scorecards.calls
    )


def test_baseline_plan_evidence_is_evaluated_once_and_reused_for_every_scorecard() -> None:
    baseline = _candidate("baseline")
    sibling = _candidate("sibling")
    baseline_evidence = _plan_evidence(output=100_000)
    sibling_evidence = _plan_evidence(output=110_000)
    plan_provider = _PlanEvidenceProvider(
        {"baseline": baseline_evidence, "sibling": sibling_evidence}
    )
    scorecards = _ScorecardService(
        {"baseline": _scorecard(), "sibling": _scorecard()}
    )
    service = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_provider,
        scorecard_service=scorecards,
    )

    service.evaluate(baseline=baseline, candidate=baseline)
    service.evaluate(baseline=baseline, candidate=sibling)

    assert plan_provider.calls == ["baseline", "sibling"]
    assert scorecards.calls[0]["baseline_sustain"] is baseline_evidence.sustain
    assert scorecards.calls[1]["baseline_sustain"] is baseline_evidence.sustain
    assert scorecards.calls[1]["candidate_sustain"] is sibling_evidence.sustain


def test_shared_hard_obligation_context_is_forwarded_unchanged_to_scorecard_service() -> None:
    baseline = _candidate("baseline")
    marker_demand = object()
    marker_requirement = object()
    marker_uptime = object()
    context = RotationCandidateSharedEvaluationContext(
        demands=(marker_demand,),
        demand_requirements=(marker_requirement,),
        runtime_uptime_requirements=(marker_uptime,),
    )
    plan_provider = _PlanEvidenceProvider(
        {"baseline": _plan_evidence(output=100_000)}
    )
    scorecards = _ScorecardService({"baseline": _scorecard()})
    service = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_provider,
        context=context,
        scorecard_service=scorecards,
    )

    service.evaluate(baseline=baseline, candidate=baseline)

    call = scorecards.calls[0]
    assert call["demands"] == (marker_demand,)
    assert call["demand_requirements"] == (marker_requirement,)
    assert call["runtime_uptime_requirements"] == (marker_uptime,)


def test_evidence_bridge_fails_closed_when_role_critical_measurement_is_unknown() -> None:
    candidate = _candidate("unknown-output")
    plan_provider = _PlanEvidenceProvider(
        {"unknown-output": _plan_evidence(output=None)}
    )
    scorecards = _ScorecardService({"unknown-output": _scorecard()})
    evidence_service = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_provider,
        scorecard_service=scorecards,
    )

    result = RotationCandidateRecommendationService().recommend(
        candidates=(candidate,),
        evidence_provider=evidence_service,
        role_key="dd",
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
    )

    assert result.recommended is None
    assert result.best_available is not None
    assert result.best_available.ranking.tier.value == "ineligible"
    assert "role ranking evidence missing: role output" in (
        result.best_available.ranking.role_reasons
    )


def test_evidence_bridge_rejects_cross_family_baseline_reuse() -> None:
    first = _candidate("first-baseline")
    second = _candidate("second-baseline")
    plan_provider = _PlanEvidenceProvider(
        {
            "first-baseline": _plan_evidence(output=100_000),
            "second-baseline": _plan_evidence(output=100_000),
        }
    )
    scorecards = _ScorecardService(
        {"first-baseline": _scorecard(), "second-baseline": _scorecard()}
    )
    service = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_provider,
        scorecard_service=scorecards,
    )

    service.evaluate(baseline=first, candidate=first)

    with pytest.raises(ValueError, match="cannot mix candidate families"):
        service.evaluate(baseline=second, candidate=second)
