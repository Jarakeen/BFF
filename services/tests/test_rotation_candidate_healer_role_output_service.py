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
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerRoleOutputService,
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


_DEMAND = RotationDemandWindow(
    name="dangerous healing window",
    start_seconds=10.0,
    end_seconds=15.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
)


def _candidate(candidate_id: str) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Healer Tester",
            build_name="Demand Healer",
            duration_seconds=30.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _DemandEvidenceProvider:
    def __init__(self, totals, unresolved=()):
        self.totals = dict(totals)
        self.unresolved = tuple(unresolved)

    def evaluate_demand(self, *, candidate, demand):
        total = float(self.totals[candidate.candidate_id])
        return RotationHealerDemandHealingEvidence(
            demand=demand,
            direct_events=(),
            periodic_events=(),
            delayed_events=(),
            modeled_direct_healing=total,
            modeled_periodic_healing=0.0,
            modeled_delayed_healing=0.0,
            unresolved=self.unresolved,
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
    def __init__(self, support_values):
        self.support_values = dict(support_values)

    def evaluate_plan(self, candidate):
        ratio = float(self.support_values[candidate.candidate_id])
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


def _recommend(*, totals, support_values):
    candidates = tuple(_candidate(candidate_id) for candidate_id in totals)
    role_output = RotationCandidateHealerRoleOutputService(
        demand=_DEMAND,
        demand_evidence_provider=_DemandEvidenceProvider(totals),
    )
    plan_evidence = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(),
        duration_service=_DurationService(),
        role_output_evidence_provider=role_output,
        provider_workload_evidence_provider=_WorkloadProvider(support_values),
    )
    evidence_provider = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_evidence,
        scorecard_service=_ScorecardService(),
    )
    return RotationCandidateRecommendationService().recommend(
        candidates=candidates,
        evidence_provider=evidence_provider,
        role_key="healer",
        role_output_label="modeled healing per demand-second",
        assigned_support_label="assigned support uptime",
    )


def test_healer_role_output_is_modeled_healing_per_demand_second() -> None:
    candidate = _candidate("healer-a")
    service = RotationCandidateHealerRoleOutputService(
        demand=_DEMAND,
        demand_evidence_provider=_DemandEvidenceProvider({"healer-a": 7500.0}),
    )

    result = service.evaluate_plan(candidate)

    assert result.resolved_value == pytest.approx(1500.0)
    assert result.unresolved == ()


def test_unresolved_healing_evidence_keeps_role_output_unknown() -> None:
    candidate = _candidate("healer-a")
    service = RotationCandidateHealerRoleOutputService(
        demand=_DEMAND,
        demand_evidence_provider=_DemandEvidenceProvider(
            {"healer-a": 7500.0},
            unresolved=("periodic runtime unresolved",),
        ),
    )

    result = service.evaluate_plan(candidate)

    assert result.value is None
    assert result.resolved_value is None
    assert result.unresolved == ("periodic runtime unresolved",)


def test_equal_support_candidates_use_healing_output_as_late_tiebreak() -> None:
    result = _recommend(
        totals={"lower-healing": 5000.0, "higher-healing": 7500.0},
        support_values={"lower-healing": 0.90, "higher-healing": 0.90},
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "higher-healing"
    entries = {entry.candidate.candidate_id: entry for entry in result.entries}
    assert entries["lower-healing"].evidence.role_output_value == pytest.approx(1000.0)
    assert entries["higher-healing"].evidence.role_output_value == pytest.approx(1500.0)


def test_higher_healing_cannot_outweigh_better_assigned_support() -> None:
    result = _recommend(
        totals={"better-support": 5000.0, "more-healing": 50000.0},
        support_values={"better-support": 0.90, "more-healing": 0.80},
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "better-support"
