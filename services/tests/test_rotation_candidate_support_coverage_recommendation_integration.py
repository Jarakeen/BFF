from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidateRecommendationEvidenceService,
)
from services.rotation_candidate_recommendation_service import RotationCandidateRecommendationService
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


def _candidate(candidate_id: str) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Support Tester",
            build_name="Assigned Support",
            duration_seconds=30.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _SustainService:
    def evaluate(self, **kwargs):
        return SimpleNamespace(
            run=SimpleNamespace(
                sustain=SimpleNamespace(
                    minimum_amount=5000.0,
                    ending_margin=5000.0,
                    sustains=True,
                )
            ),
            unresolved=(),
        )


class _DurationService:
    def analyze(self, plan, **kwargs):
        return object()


class _WorkloadProvider:
    def __init__(self, ratios):
        self.ratios = dict(ratios)

    def evaluate_plan(self, candidate):
        ratio = float(self.ratios[candidate.candidate_id])
        return SimpleNamespace(
            alternative_id=candidate.candidate_id,
            viable=True,
            primary_role_displacement_seconds=2.0,
            recipient_coverage_result=SimpleNamespace(fully_covered=True),
            temporal_coverage_result=SimpleNamespace(
                full_requirement_met=True,
                coverage_ratio=ratio,
            ),
        )


class _ScorecardService:
    def compare(self, **kwargs):
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


def test_support_recommendation_prefers_higher_canonical_assignment_coverage() -> None:
    baseline = _candidate("baseline")
    better = _candidate("better-coverage")
    plan_evidence = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(),
        duration_service=_DurationService(),
        provider_workload_evidence_provider=_WorkloadProvider(
            {
                "baseline": 0.80,
                "better-coverage": 0.90,
            }
        ),
    )
    evidence_provider = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_evidence,
        scorecard_service=_ScorecardService(),
    )

    result = RotationCandidateRecommendationService().recommend(
        candidates=(baseline, better),
        evidence_provider=evidence_provider,
        role_key="healer",
        role_output_label="useful healing output",
        assigned_support_label="assigned support uptime",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "better-coverage"

    entries = {entry.candidate.candidate_id: entry for entry in result.entries}
    assert entries["baseline"].evidence.assigned_support_value == pytest.approx(0.80)
    assert entries["better-coverage"].evidence.assigned_support_value == pytest.approx(0.90)
    assert entries["baseline"].evidence.sustain_margin == pytest.approx(5000.0)
    assert entries["better-coverage"].evidence.sustain_margin == pytest.approx(5000.0)
    assert entries["baseline"].evidence.primary_role_displacement_seconds == pytest.approx(2.0)
    assert entries["better-coverage"].evidence.primary_role_displacement_seconds == pytest.approx(2.0)
