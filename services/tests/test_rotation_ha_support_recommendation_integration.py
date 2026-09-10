from types import SimpleNamespace

import pytest

from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.support_effect_category import SupportEffectCategory
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidateRecommendationEvidenceService,
)
from services.rotation_candidate_recommendation_service import RotationCandidateRecommendationService
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_heavy_attack_effect_duration_service import (
    RotationHeavyAttackEffectDurationService,
)
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.team_provider_coverage_service import (
    TeamProviderCoverageProfile,
    TeamProviderCoverageService,
)
from services.team_provider_rotation_workload_service import (
    TeamProviderRotationContribution,
    TeamProviderRotationWorkloadService,
    TeamProviderScheduledActionCost,
)
from services.team_provider_temporal_coverage_service import (
    TeamProviderTemporalCoverageService,
    TeamProviderTemporalRequirement,
    TeamProviderTimedApplication,
)


_DURATION_SECONDS = 60.0
_RO_BASE_DURATION_SECONDS = 12.0
_RO_EFFECTIVE_DURATION_SECONDS = 16.8
_RO_REELIGIBILITY_SECONDS = 22.0


def _candidate(candidate_id: str, heavy_times: tuple[float, ...]) -> GeneratedRotationCandidate:
    actions = tuple(
        RotationAction(
            time_seconds=time_seconds,
            sequence=index,
            kind=RotationActionKind.HEAVY_ATTACK,
            name="Restoration Staff Heavy Attack",
            bar="back",
        )
        for index, time_seconds in enumerate(heavy_times)
    )
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Support Tester",
            build_name="RoJo Healer",
            duration_seconds=_DURATION_SECONDS,
            actions=actions,
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


class _DurationAnalysisService:
    def analyze(self, plan, **kwargs):
        return object()


class _BuildDurationResolver:
    def resolve(self, **kwargs):
        effect = kwargs["effect"]
        assert effect.duration == pytest.approx(_RO_BASE_DURATION_SECONDS)
        return SimpleNamespace(
            effective_duration_seconds=_RO_EFFECTIVE_DURATION_SECONDS,
            unresolved=(),
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


class _RoaringHeavyWorkloadProvider:
    def __init__(self, *, effect_duration_seconds: float) -> None:
        self.effect_duration_seconds = float(effect_duration_seconds)
        self.workload_service = TeamProviderRotationWorkloadService()

    def evaluate_plan(self, candidate):
        heavy_actions = tuple(
            action
            for action in candidate.plan.actions
            if action.kind is RotationActionKind.HEAVY_ATTACK
        )
        recipient = TeamProviderCoverageService.evaluate(
            TeamProviderCoverageProfile(
                provider_key="roaring_opportunist",
                targets_per_application=5,
                max_applications_per_cycle=max(1, len(heavy_actions)),
                application_label="fully charged heavy attack",
            ),
            required_recipients=5,
        )
        temporal = TeamProviderTemporalCoverageService.evaluate(
            TeamProviderTemporalRequirement(
                effect_key="major_slayer",
                start_seconds=0.0,
                end_seconds=_DURATION_SECONDS,
                label="assigned Major Slayer window",
                minimum_distinct_sources=1,
                target_coverage_ratio=0.50,
            ),
            applications=tuple(
                TeamProviderTimedApplication(
                    effect_key="major_slayer",
                    source="Roaring Opportunist",
                    start_seconds=action.time_seconds,
                    duration_seconds=self.effect_duration_seconds,
                )
                for action in heavy_actions
            ),
        )
        contribution = TeamProviderRotationContribution(
            plan=candidate.plan,
            provider_actions=tuple(
                TeamProviderScheduledActionCost(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    gcd_seconds=0.0,
                    cast_channel_seconds=1.8,
                    resource_costs=(),
                    primary_role_displacement_seconds=1.8,
                    heavy_attack_completed=True,
                )
                for action in heavy_actions
            ),
        )
        return self.workload_service.assess_from_coverage(
            alternative_id=candidate.candidate_id,
            effect_key="major_slayer",
            duration_seconds=_DURATION_SECONDS,
            recipient_coverage_result=recipient,
            temporal_coverage_result=temporal,
            contributions=(contribution,),
        )


def test_rojo_heavy_timing_flows_through_real_coverage_workload_and_healer_ranking() -> None:
    incentive = HealerHeavyAttackBuildIncentive(
        bar="back",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Roaring Opportunist",
        source="canonical test fixture",
        recurrence_seconds=_RO_REELIGIBILITY_SECONDS,
        maximum_effect_duration_seconds=_RO_BASE_DURATION_SECONDS,
        required_effect_name="major_slayer",
        required_effect_category=SupportEffectCategory.BUFF,
    )
    duration_evidence = RotationHeavyAttackEffectDurationService(
        duration_service=_BuildDurationResolver(),
    ).enrich(
        build=object(),
        incentives=(incentive,),
    )
    enriched = duration_evidence.incentives[0]

    assert enriched.maximum_effect_duration_seconds == pytest.approx(12.0)
    assert enriched.effective_effect_duration_seconds == pytest.approx(16.8)
    assert enriched.recurrence_seconds == pytest.approx(22.0)

    correct_timing = _candidate("correct-rojo-timing", (0.0, 22.0, 44.0))
    delayed_timing = _candidate("delayed-rojo-timing", (0.0, 30.0))
    plan_evidence = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(),
        duration_service=_DurationAnalysisService(),
        provider_workload_evidence_provider=_RoaringHeavyWorkloadProvider(
            effect_duration_seconds=enriched.effective_effect_duration_seconds,
        ),
    )
    evidence_provider = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_evidence,
        scorecard_service=_ScorecardService(),
    )

    result = RotationCandidateRecommendationService().recommend(
        candidates=(delayed_timing, correct_timing),
        evidence_provider=evidence_provider,
        role_key="healer",
        role_output_label="useful healing output",
        assigned_support_label="assigned Major Slayer uptime",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "correct-rojo-timing"

    entries = {entry.candidate.candidate_id: entry for entry in result.entries}
    assert entries["correct-rojo-timing"].evidence.assigned_support_value == pytest.approx(0.84)
    assert entries["delayed-rojo-timing"].evidence.assigned_support_value == pytest.approx(0.56)
    assert entries["correct-rojo-timing"].evidence.primary_role_displacement_seconds == pytest.approx(5.4)
    assert entries["delayed-rojo-timing"].evidence.primary_role_displacement_seconds == pytest.approx(3.6)
