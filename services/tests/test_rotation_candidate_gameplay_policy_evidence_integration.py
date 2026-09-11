from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidatePlanEvidence,
    RotationCandidateRecommendationEvidenceService,
)
from services.rotation_candidate_recommendation_service import (
    RotationCandidateRecommendationService,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyContext,
    RotationGameplayPolicyStatus,
)
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


def _candidate(candidate_id: str) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="DD",
            build_name=candidate_id,
            duration_seconds=20.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _scorecard() -> RotationCandidateScorecard:
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
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


class _PlanEvidenceProvider:
    def __init__(self, outputs):
        self.outputs = outputs

    def evaluate_plan(self, candidate):
        return RotationCandidatePlanEvidence(
            sustain=object(),
            role_output_value=self.outputs[candidate.candidate_id],
            assigned_support_value=None,
            sustain_margin=1000.0,
            primary_role_displacement_seconds=0.0,
        )


class _ScorecardService:
    def compare(self, **kwargs):
        return _scorecard()


class _PolicyContextProvider:
    def __init__(self, contexts):
        self.contexts = contexts
        self.calls = []

    def context_for(self, candidate):
        self.calls.append(candidate.candidate_id)
        return self.contexts.get(candidate.candidate_id)


def _context(
    candidate_id: str,
    *,
    personal_heals=(),
    reliable_group_healing=True,
    exceptions=(),
):
    return RotationGameplayPolicyContext(
        candidate_id=candidate_id,
        role="dd",
        content_type="trial",
        personal_heal_skill_slots=tuple(personal_heals),
        reliable_group_healing=reliable_group_healing,
        exception_contexts=tuple(exceptions),
    )


def test_recommendation_evidence_derives_policy_and_prefers_clean_dd_candidate() -> None:
    clean = _candidate("clean")
    redundant_heal = _candidate("redundant-heal")
    context_provider = _PolicyContextProvider(
        {
            "clean": _context("clean"),
            "redundant-heal": _context(
                "redundant-heal",
                personal_heals=("resolving_vigor",),
            ),
        }
    )
    evidence_service = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=_PlanEvidenceProvider(
            {"clean": 100_000.0, "redundant-heal": 200_000.0}
        ),
        scorecard_service=_ScorecardService(),
        gameplay_policy_context_provider=context_provider,
    )

    result = RotationCandidateRecommendationService().recommend(
        candidates=(clean, redundant_heal),
        evidence_provider=evidence_service,
        role_key="dd",
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "clean"
    assert [entry.candidate.candidate_id for entry in result.entries] == [
        "clean",
        "redundant-heal",
    ]
    assert result.entries[0].evidence.gameplay_policy_assessment.status is RotationGameplayPolicyStatus.SATISFIED
    assert result.entries[1].evidence.gameplay_policy_assessment.status is RotationGameplayPolicyStatus.DISFAVORED
    assert context_provider.calls == ["clean", "redundant-heal"]


def test_explicit_encounter_exception_is_carried_as_policy_override() -> None:
    candidate = _candidate("portal-dd")
    evidence_service = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=_PlanEvidenceProvider({"portal-dd": 100_000.0}),
        scorecard_service=_ScorecardService(),
        gameplay_policy_context_provider=_PolicyContextProvider(
            {
                "portal-dd": _context(
                    "portal-dd",
                    personal_heals=("resolving_vigor",),
                    exceptions=("portal_or_split_group_assignment",),
                )
            }
        ),
    )

    evidence = evidence_service.evaluate(baseline=candidate, candidate=candidate)

    assert evidence.gameplay_policy_assessment is not None
    assert evidence.gameplay_policy_assessment.status is RotationGameplayPolicyStatus.OVERRIDDEN
    assert evidence.gameplay_policy_assessment.matched_exceptions == (
        "portal_or_split_group_assignment",
    )


def test_missing_policy_context_provider_preserves_legacy_none_assessment() -> None:
    candidate = _candidate("legacy")
    evidence_service = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=_PlanEvidenceProvider({"legacy": 100_000.0}),
        scorecard_service=_ScorecardService(),
    )

    evidence = evidence_service.evaluate(baseline=candidate, candidate=candidate)

    assert evidence.gameplay_policy_assessment is None


def test_policy_context_candidate_mismatch_fails_closed() -> None:
    candidate = _candidate("candidate")
    evidence_service = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=_PlanEvidenceProvider({"candidate": 100_000.0}),
        scorecard_service=_ScorecardService(),
        gameplay_policy_context_provider=_PolicyContextProvider(
            {"candidate": _context("different-candidate")}
        ),
    )

    try:
        evidence_service.evaluate(baseline=candidate, candidate=candidate)
    except ValueError as exc:
        assert "gameplay-policy context candidate mismatch" in str(exc)
    else:
        raise AssertionError("candidate-mismatched gameplay policy context must fail closed")
