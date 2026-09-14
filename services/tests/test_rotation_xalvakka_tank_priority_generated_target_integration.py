from types import SimpleNamespace

from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
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
from services.rotation_tank_encounter_priority_context_service import (
    RotationTankEncounterPriorityCue,
)
from services.rotation_tank_taunt_candidate_service import (
    RotationTankTauntActionClaim,
    RotationTankTauntCandidateService,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
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


def _candidate(candidate_id: str, actions=()) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Tank",
            build_name=candidate_id,
            duration_seconds=20.0,
            actions=tuple(actions),
        ),
        refresh_leads=(),
    )


class _FakeTauntObligationService:
    def assess(self, *, plan, requirement):
        applications = tuple(
            action
            for action in plan.actions
            if action.kind is RotationActionKind.SKILL
            and str(action.name or "").casefold() == requirement.source_skill_name.casefold()
            and requirement.window_start_seconds <= action.time_seconds <= requirement.window_end_seconds
            and (requirement.bar is None or action.bar == requirement.bar)
            and (
                requirement.target_key is None
                or action.target_key == requirement.target_key
            )
        )
        return SimpleNamespace(
            resolved=True,
            satisfied=len(applications) >= requirement.minimum_applications,
            applications=applications,
            unresolved=(),
        )


class _EvidenceProvider:
    def __init__(self, rows, priority_context):
        self.rows = rows
        self.plan_evidence_provider = SimpleNamespace(
            tank_priority_context=tuple(priority_context)
        )

    def evaluate(self, *, baseline, candidate):
        return self.rows[candidate.candidate_id]


def _evidence(candidate_id: str, support: float) -> RotationCandidateRecommendationEvidence:
    return RotationCandidateRecommendationEvidence(
        candidate_id=candidate_id,
        scorecard=_scorecard(),
        role_output_value=0.0,
        assigned_support_value=support,
        sustain_margin=1000.0,
        primary_role_displacement_seconds=0.0,
    )


def _iron_priority() -> RotationTankEncounterPriorityCue:
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
        interpretation="reviewed Xalvakka Iron Atronach priority",
    )


def test_generated_target_specific_taunt_reaches_automatic_tank_priority_ranking() -> None:
    requirement = RotationTankTauntApplicationRequirement(
        requirement_id="iron_pickup",
        source_skill_name="Pierce Armor",
        window_start_seconds=5.0,
        window_end_seconds=5.0,
        minimum_applications=1,
        bar="front",
        target_key="iron_atronach",
    )
    claim = RotationTankTauntActionClaim(
        requirement_id="iron_pickup",
        action_time_seconds=5.0,
        action_sequence=0,
        bar="front",
    )
    slot = RotationActionSlotRequirement(
        action_name="Pierce Armor",
        allowed_bars=("front",),
        action_kind=RotationActionKind.SKILL,
    )
    taunt_service = RotationTankTauntCandidateService(
        "unused.db",
        obligation_service=_FakeTauntObligationService(),
    )
    projected = taunt_service.project(
        candidate=_candidate("iron-ready"),
        requirements=(requirement,),
        claims=(claim,),
        slot_requirements=(slot,),
    )

    assert projected.resolved is True
    assert projected.candidate is not None
    assert projected.candidate.plan.actions[0].target_key == "iron_atronach"

    generic = _candidate(
        "higher-support",
        actions=(
            RotationAction(
                time_seconds=5.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Pierce Armor",
                bar="front",
                target_key="daedroth",
            ),
        ),
    )
    provider = _EvidenceProvider(
        {
            "higher-support": _evidence("higher-support", 0.99),
            "iron-ready": _evidence("iron-ready", 0.90),
        },
        (_iron_priority(),),
    )

    result = RotationCandidateRecommendationService().recommend(
        candidates=(generic, projected.candidate),
        evidence_provider=provider,
        role_key="tank",
        role_output_label="optional output",
        assigned_support_label="assigned support coverage",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "iron-ready"
    assert result.recommended.tank_priority_assessment is not None
    cue = result.recommended.tank_priority_assessment.cues[0]
    assert cue.status.value == "satisfied"
    assert cue.matching_action_count == 1
    assert cue.first_matching_action_seconds == 5.0
