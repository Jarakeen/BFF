from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_recommendation_service import (
    RotationCandidateRecommendationEvidence,
    RotationCandidateRecommendationService,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_tank_encounter_priority_context_service import RotationTankEncounterPriorityCue


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


def _candidate(candidate_id: str, target_key: str) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Tank",
            build_name=candidate_id,
            duration_seconds=10.0,
            actions=(
                RotationAction(
                    time_seconds=1.0,
                    sequence=0,
                    kind=RotationActionKind.SKILL,
                    name="taunt",
                    bar="front",
                    target_key=target_key,
                ),
            ),
        ),
        refresh_leads=(),
    )


def _priority() -> RotationTankEncounterPriorityCue:
    return RotationTankEncounterPriorityCue(
        encounter_id="xalvakka",
        lane_id="add_handler",
        member_id="tank-b",
        priority=20,
        responsibility_id="pack_encounter_adds",
        target_key="encounter_adds",
        actor_name="Iron Atronach",
        directive="acquire_and_maintain_owned_add_when_active",
        trigger="reviewed_add_activity",
        hard_policy=False,
        interpretation="fixture",
    )


def _evidence(candidate_id: str, support: float) -> RotationCandidateRecommendationEvidence:
    return RotationCandidateRecommendationEvidence(
        candidate_id=candidate_id,
        scorecard=_scorecard(),
        role_output_value=0.0,
        assigned_support_value=support,
        sustain_margin=1000.0,
        primary_role_displacement_seconds=0.0,
    )


class _Provider:
    def __init__(self):
        self.plan_evidence_provider = SimpleNamespace(tank_priority_context=(_priority(),))
        self.rows = {
            "higher-support": _evidence("higher-support", 0.99),
            "iron-ready": _evidence("iron-ready", 0.90),
        }

    def evaluate(self, *, baseline, candidate):
        return self.rows[candidate.candidate_id]


def test_recommendation_reuses_canonical_tank_priority_context_automatically() -> None:
    result = RotationCandidateRecommendationService().recommend(
        candidates=(
            _candidate("higher-support", "daedroth"),
            _candidate("iron-ready", "iron_atronach"),
        ),
        evidence_provider=_Provider(),
        role_key="tank",
        role_output_label="optional output",
        assigned_support_label="assigned support coverage",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "iron-ready"
    assert result.recommended.tank_priority_assessment is not None


def test_explicit_empty_tank_priority_context_disables_auto_threading() -> None:
    result = RotationCandidateRecommendationService().recommend(
        candidates=(
            _candidate("higher-support", "daedroth"),
            _candidate("iron-ready", "iron_atronach"),
        ),
        evidence_provider=_Provider(),
        role_key="tank",
        role_output_label="optional output",
        assigned_support_label="assigned support coverage",
        tank_priority_context=(),
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "higher-support"
    assert result.recommended.tank_priority_assessment is None
