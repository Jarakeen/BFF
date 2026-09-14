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


def _candidate(candidate_id: str, target: str | None) -> GeneratedRotationCandidate:
    actions = () if target is None else (
        RotationAction(
            time_seconds=1.0,
            sequence=0,
            kind=RotationActionKind.SKILL,
            name="taunt",
            bar="front",
            target_key=target,
        ),
    )
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Tank",
            build_name=candidate_id,
            duration_seconds=10.0,
            actions=actions,
        ),
        refresh_leads=(),
    )


class _EvidenceProvider:
    def __init__(self, rows):
        self.rows = rows

    def evaluate(self, *, baseline, candidate):
        return self.rows[candidate.candidate_id]


def _evidence(candidate_id: str, *, support: float, missing_effects=()):
    return RotationCandidateRecommendationEvidence(
        candidate_id=candidate_id,
        scorecard=_scorecard(missing_effects=tuple(missing_effects)),
        role_output_value=0.0,
        assigned_support_value=support,
        sustain_margin=1000.0,
        primary_role_displacement_seconds=0.0,
    )


def _iron_priority():
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


def test_tank_priority_coverage_precedes_generic_support_soft_objective() -> None:
    generic_winner = _candidate("higher-support", "daedroth")
    priority_winner = _candidate("iron-ready", "iron_atronach")
    provider = _EvidenceProvider(
        {
            "higher-support": _evidence("higher-support", support=0.99),
            "iron-ready": _evidence("iron-ready", support=0.90),
        }
    )

    result = RotationCandidateRecommendationService().recommend(
        candidates=(generic_winner, priority_winner),
        evidence_provider=provider,
        role_key="tank",
        role_output_label="optional output",
        assigned_support_label="assigned support coverage",
        tank_priority_context=(_iron_priority(),),
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "iron-ready"
    assert result.recommended.tank_priority_assessment is not None
    assert any("explicit target action present" in reason for reason in result.recommended.reasons)


def test_tank_priority_context_cannot_rescue_ineligible_candidate() -> None:
    invalid_but_priority_ready = _candidate("invalid-iron", "iron_atronach")
    valid_without_priority_target = _candidate("valid-other", "daedroth")
    provider = _EvidenceProvider(
        {
            "invalid-iron": _evidence(
                "invalid-iron",
                support=1.0,
                missing_effects=("required_support_effect",),
            ),
            "valid-other": _evidence("valid-other", support=0.80),
        }
    )

    result = RotationCandidateRecommendationService().recommend(
        candidates=(invalid_but_priority_ready, valid_without_priority_target),
        evidence_provider=provider,
        role_key="tank",
        role_output_label="optional output",
        assigned_support_label="assigned support coverage",
        tank_priority_context=(_iron_priority(),),
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "valid-other"
    invalid = next(entry for entry in result.entries if entry.candidate.candidate_id == "invalid-iron")
    assert invalid.ranking.tier.value == "ineligible"
