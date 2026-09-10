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
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_healer_demand_criteria_service import (
    RotationCandidateHealerCriteriaHardObligationService,
    RotationHealerDemandCriterion,
    RotationHealerDemandCriterionSourceKind,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
)
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


_DEMAND = RotationDemandWindow(
    name="execute burn",
    start_seconds=20.0,
    end_seconds=25.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
)


def _candidate(candidate_id: str) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Healer Tester",
            build_name="Encounter Healer",
            duration_seconds=40.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _DemandEvidenceProvider:
    def __init__(self, totals_by_candidate, unresolved_by_candidate=None):
        self.totals_by_candidate = dict(totals_by_candidate)
        self.unresolved_by_candidate = dict(unresolved_by_candidate or {})

    def evaluate_demand(self, *, candidate, demand):
        return RotationHealerDemandHealingEvidence(
            demand=demand,
            direct_events=(),
            periodic_events=(),
            delayed_events=(),
            modeled_direct_healing=float(self.totals_by_candidate[candidate.candidate_id]),
            modeled_periodic_healing=0.0,
            modeled_delayed_healing=0.0,
            unresolved=tuple(self.unresolved_by_candidate.get(candidate.candidate_id, ())),
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
    def __init__(self, support_by_candidate):
        self.support_by_candidate = dict(support_by_candidate)

    def evaluate_plan(self, candidate):
        return SimpleNamespace(
            alternative_id=candidate.candidate_id,
            viable=True,
            primary_role_displacement_seconds=2.0,
            recipient_coverage_result=SimpleNamespace(fully_covered=True),
            temporal_coverage_result=SimpleNamespace(
                full_requirement_met=True,
                coverage_ratio=float(self.support_by_candidate[candidate.candidate_id]),
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


def _criterion(source_kind, minimum=800.0):
    return RotationHealerDemandCriterion(
        demand_name=_DEMAND.name,
        minimum_modeled_healing_per_demand_second=minimum,
        source_kind=source_kind,
        provenance=("encounter evidence fixture",),
    )


def test_verified_healer_criterion_gates_before_better_support_uptime() -> None:
    candidates = (
        _candidate("passes-criterion"),
        _candidate("fails-criterion-better-support"),
    )
    demand_provider = _DemandEvidenceProvider(
        {
            "passes-criterion": 4500.0,                 # 900/s, passes 800/s
            "fails-criterion-better-support": 3500.0,  # 700/s, fails 800/s
        }
    )
    role_output = RotationCandidateHealerMultiDemandRoleOutputService(
        demands=(_DEMAND,),
        demand_evidence_provider=demand_provider,
    )
    hard_gate = RotationCandidateHealerCriteriaHardObligationService(
        multi_demand_output_service=role_output,
        criteria=(
            _criterion(
                RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE
            ),
        ),
    )
    plan_evidence = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(),
        duration_service=_DurationService(),
        role_output_evidence_provider=role_output,
        role_hard_obligation_evidence_provider=hard_gate,
        provider_workload_evidence_provider=_WorkloadProvider(
            {
                "passes-criterion": 0.80,
                "fails-criterion-better-support": 0.99,
            }
        ),
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
    assert result.recommended.candidate.candidate_id == "passes-criterion"

    entries = {entry.candidate.candidate_id: entry for entry in result.entries}
    failed = entries["fails-criterion-better-support"]
    assert failed.evidence.assigned_support_value == pytest.approx(0.99)
    assert failed.evidence.role_hard_obligation_satisfied is False
    assert failed.ranking.tier is RotationCandidateTier.INELIGIBLE
    assert any(
        "verified healer criterion failed" in reason
        for reason in failed.reasons
    )


def test_caller_assumption_does_not_become_a_hard_gate() -> None:
    candidate = _candidate("below-assumed-threshold")
    role_output = RotationCandidateHealerMultiDemandRoleOutputService(
        demands=(_DEMAND,),
        demand_evidence_provider=_DemandEvidenceProvider(
            {"below-assumed-threshold": 500.0}
        ),
    )
    hard_gate = RotationCandidateHealerCriteriaHardObligationService(
        multi_demand_output_service=role_output,
        criteria=(
            _criterion(
                RotationHealerDemandCriterionSourceKind.CALLER_ASSUMPTION,
                minimum=5000.0,
            ),
        ),
    )

    evidence = hard_gate.evaluate_plan(candidate)

    assert evidence.satisfied is True
    assert evidence.reasons == ()


def test_unresolved_verified_healer_criterion_fails_closed() -> None:
    candidate = _candidate("unknown-healing")
    role_output = RotationCandidateHealerMultiDemandRoleOutputService(
        demands=(_DEMAND,),
        demand_evidence_provider=_DemandEvidenceProvider(
            {"unknown-healing": 5000.0},
            unresolved_by_candidate={
                "unknown-healing": ("periodic refresh behavior unresolved",),
            },
        ),
    )
    hard_gate = RotationCandidateHealerCriteriaHardObligationService(
        multi_demand_output_service=role_output,
        criteria=(
            _criterion(
                RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE
            ),
        ),
    )

    evidence = hard_gate.evaluate_plan(candidate)

    assert evidence.satisfied is None
    assert any("verified healer criterion unresolved" in reason for reason in evidence.reasons)
