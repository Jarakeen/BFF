from types import SimpleNamespace

import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from models.build_model import PlayerBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerCanonicalDemandEvidenceProvider,
    RotationCandidateHealerRoleOutputService,
)
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidateRecommendationEvidenceService,
)
from services.rotation_candidate_recommendation_service import RotationCandidateRecommendationService
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_healer_action_healing_service import RotationHealerActionHealingService
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRuntimeEvidence,
)
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


_DEMAND = RotationDemandWindow(
    name="sustained raid damage",
    start_seconds=10.0,
    end_seconds=16.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
    target_count=12,
)


class _FakeCoefficients:
    def __init__(self):
        self._ranks = {
            "Burst Heal": SimpleNamespace(
                rank=SimpleNamespace(
                    skill_rank_id=10,
                    entity_id="burst_heal",
                ),
                unresolved=(),
            ),
            "Raid HoT": SimpleNamespace(
                rank=SimpleNamespace(
                    skill_rank_id=20,
                    entity_id="raid_hot",
                ),
                unresolved=(),
            ),
        }

    def resolve_name(self, name):
        return self._ranks[name]


class _FakeComponents:
    def __init__(self):
        self._by_rank = {
            10: (
                SkillComponentClassification(
                    skill_rank_id=10,
                    coefficient_number=1,
                    effect_kind=SkillEffectKind.HEAL,
                    is_dot=False,
                    source="canonical integration fixture",
                    confidence=1.0,
                ),
            ),
            20: (
                SkillComponentClassification(
                    skill_rank_id=20,
                    coefficient_number=1,
                    effect_kind=SkillEffectKind.HEAL,
                    is_dot=True,
                    source="canonical integration fixture",
                    confidence=1.0,
                ),
            ),
        }

    def get_for_skill_rank(self, skill_rank_id):
        return self._by_rank.get(skill_rank_id, ())


class _FakeTooltipService:
    def __init__(self):
        self.coefficients = _FakeCoefficients()
        self.components = _FakeComponents()

    def evaluate_entity_id(self, *, build, context, entity_id):
        if entity_id == "burst_heal":
            return SimpleNamespace(
                skill=SimpleNamespace(skill_rank_id=10),
                components=(SimpleNamespace(coefficient_number=1, final_value=1200.0),),
                component_actual_effect_trace=(
                    SimpleNamespace(coefficient_number=1, output_value=1200.0),
                ),
                unresolved=(),
            )
        if entity_id == "raid_hot":
            return SimpleNamespace(
                skill=SimpleNamespace(skill_rank_id=20),
                components=(SimpleNamespace(coefficient_number=1, final_value=300.0),),
                component_actual_effect_trace=(
                    SimpleNamespace(coefficient_number=1, output_value=300.0),
                ),
                unresolved=(),
            )
        raise AssertionError(f"unexpected entity id: {entity_id}")


class _PeriodicTimingService:
    def inspect(self, build):
        return SimpleNamespace(
            entries=(
                SimpleNamespace(
                    skill_name="Raid HoT",
                    coefficient_number=1,
                    timing="raid-hot-canonical-timing",
                ),
            ),
            unresolved=(),
        )


class _PeriodicRuntimeEvidenceService:
    def resolve(self, *, canonical, observation, repeated_applications):
        assert canonical == "raid-hot-canonical-timing"
        assert repeated_applications is False
        return SimpleNamespace(
            runtime_evidence=RotationHealerPeriodicRuntimeEvidence(
                source_name="Raid HoT",
                coefficient_number=1,
                duration_seconds=10.0,
                tick_interval_seconds=2.0,
                first_tick_offset_seconds=2.0,
                tick_on_expiry_boundary=True,
            ),
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


def _action(time_seconds, sequence, name):
    return RotationAction(
        time_seconds=time_seconds,
        sequence=sequence,
        kind=RotationActionKind.SKILL,
        name=name,
        bar="front",
    )


def _candidate(candidate_id, *, include_hot):
    actions = [
        _action(12.0, 2, "Burst Heal"),
    ]
    if include_hot:
        actions.insert(0, _action(8.0, 1, "Raid HoT"))
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Healer Tester",
            build_name="Canonical Recommendation Healer",
            duration_seconds=20.0,
            actions=tuple(actions),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def test_canonical_healing_projection_runtime_and_demand_output_reach_healer_recommendation() -> None:
    build = PlayerBuild()
    action_healing = RotationHealerActionHealingService(
        ".",
        tooltip_service=_FakeTooltipService(),
    )
    canonical_healing = RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path="unused.sqlite",
        build=build,
        context=object(),
        action_healing_service=action_healing,
        periodic_timing_service=_PeriodicTimingService(),
        periodic_runtime_evidence_service=_PeriodicRuntimeEvidenceService(),
    )
    role_output = RotationCandidateHealerRoleOutputService(
        demand=_DEMAND,
        demand_evidence_provider=canonical_healing,
    )
    plan_evidence = RotationCandidateCanonicalPlanEvidenceService(
        build=build,
        sustain_service=_SustainService(),
        duration_service=_DurationService(),
        role_output_evidence_provider=role_output,
        provider_workload_evidence_provider=_WorkloadProvider(),
    )
    evidence_provider = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_evidence,
        scorecard_service=_ScorecardService(),
    )

    burst_only = _candidate("burst-only", include_hot=False)
    maintained_hot = _candidate("maintained-hot", include_hot=True)
    result = RotationCandidateRecommendationService().recommend(
        candidates=(burst_only, maintained_hot),
        evidence_provider=evidence_provider,
        role_key="healer",
        role_output_label="modeled healing per demand-second",
        assigned_support_label="assigned support uptime",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "maintained-hot"

    entries = {entry.candidate.candidate_id: entry for entry in result.entries}
    # Burst Heal lands once in the 6s demand window: 1200 / 6 = 200.
    assert entries["burst-only"].evidence.role_output_value == pytest.approx(200.0)
    # Raid HoT cast at 8s ticks at 10/12/14/16 inside the exact demand window.
    # 1200 direct + (4 * 300) periodic = 2400 / 6 = 400.
    assert entries["maintained-hot"].evidence.role_output_value == pytest.approx(400.0)
    assert entries["burst-only"].evidence.assigned_support_value == pytest.approx(0.90)
    assert entries["maintained-hot"].evidence.assigned_support_value == pytest.approx(0.90)
    assert entries["burst-only"].evidence.sustain_margin == pytest.approx(5000.0)
    assert entries["maintained-hot"].evidence.sustain_margin == pytest.approx(5000.0)
    assert entries["burst-only"].evidence.primary_role_displacement_seconds == pytest.approx(2.0)
    assert entries["maintained-hot"].evidence.primary_role_displacement_seconds == pytest.approx(2.0)
