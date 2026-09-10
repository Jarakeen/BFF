from types import SimpleNamespace

import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_multi_demand_role_output_service import (
    RotationCandidateHealerMultiDemandRoleOutputService,
)
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidateRecommendationEvidenceService,
)
from services.rotation_candidate_recommendation_service import RotationCandidateRecommendationService
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
)
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


_DEMANDS = (
    RotationDemandWindow(
        name="first burn",
        start_seconds=10.0,
        end_seconds=15.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.SUSTAINED,
    ),
    RotationDemandWindow(
        name="second burn",
        start_seconds=30.0,
        end_seconds=35.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.SUSTAINED,
    ),
)


def _candidate(candidate_id: str) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Healer Tester",
            build_name="Two Window Healer",
            duration_seconds=45.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _DemandEvidenceProvider:
    def __init__(self, totals_by_candidate):
        self.totals_by_candidate = {
            candidate_id: dict(values)
            for candidate_id, values in totals_by_candidate.items()
        }

    def evaluate_demand(self, *, candidate, demand):
        total = float(self.totals_by_candidate[candidate.candidate_id][demand.name])
        return RotationHealerDemandHealingEvidence(
            demand=demand,
            direct_events=(),
            periodic_events=(),
            delayed_events=(),
            modeled_direct_healing=total,
            modeled_periodic_healing=0.0,
            modeled_delayed_healing=0.0,
            unresolved=(),
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
    def evaluate_plan(self, candidate):
        return SimpleNamespace(
            alternative_id=candidate.candidate_id,
            viable=True,
            primary_role_displacement_seconds=2.0,
            recipient_coverage_result=SimpleNamespace(fully_covered=True),
            temporal_coverage_result=SimpleNamespace(
                full_requirement_met=True,
                coverage_ratio=0.90,
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


def test_steady_healer_beats_spiky_healer_on_weakest_required_window() -> None:
    candidates = (
        _candidate("steady-healer"),
        _candidate("spiky-healer"),
    )
    demand_provider = _DemandEvidenceProvider(
        {
            "steady-healer": {
                "first burn": 5000.0,   # 1000/s
                "second burn": 4000.0,  # 800/s floor
            },
            "spiky-healer": {
                "first burn": 50000.0,  # 10000/s
                "second burn": 2500.0,  # 500/s floor
            },
        }
    )
    role_output = RotationCandidateHealerMultiDemandRoleOutputService(
        demands=_DEMANDS,
        demand_evidence_provider=demand_provider,
    )
    plan_evidence = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(),
        duration_service=_DurationService(),
        role_output_evidence_provider=role_output,
        provider_workload_evidence_provider=_WorkloadProvider(),
    )
    evidence_provider = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_evidence,
        scorecard_service=_ScorecardService(),
    )

    result = RotationCandidateRecommendationService().recommend(
        candidates=candidates,
        evidence_provider=evidence_provider,
        role_key="healer",
        role_output_label="weakest healing-window modeled output",
        assigned_support_label="assigned support uptime",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "steady-healer"

    entries = {entry.candidate.candidate_id: entry for entry in result.entries}
    assert entries["steady-healer"].evidence.role_output_value == pytest.approx(800.0)
    assert entries["spiky-healer"].evidence.role_output_value == pytest.approx(500.0)
