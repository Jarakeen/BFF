from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequenceType,
)
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidence,
    RotationExecuteComponentEvidence,
)
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteFillerOpportunityService,
)
from services.rotation_target_health_timeline_service import (
    RotationTargetHealthObservation,
    RotationTargetHealthTimeline,
)
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_dd_execute_health_timeline_context_support import (
    RotationDDExecuteHealthTimelineContextSupport,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationResult


class _EvidenceService:
    def resolve(self, skill_name: str) -> RotationExecuteCandidateEvidence:
        if skill_name != "Execute":
            return RotationExecuteCandidateEvidence(
                requested_skill_name=skill_name,
                resolved_skill_name=skill_name,
                entity_id=f"synthetic:{skill_name}",
            )
        return RotationExecuteCandidateEvidence(
            requested_skill_name="Execute",
            resolved_skill_name="Execute",
            entity_id="synthetic:execute",
            components=(
                RotationExecuteComponentEvidence(
                    skill_name="Execute",
                    entity_id="synthetic:execute",
                    skill_rank_id=1,
                    coefficient_number=1,
                    threshold=0.25,
                    consequence_type=SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT,
                    maximum_bonus_fraction=None,
                    condition_evidence="synthetic reviewed target below 25% Health",
                    consequence_evidence="synthetic reviewed execute component activates",
                ),
            ),
        )


class _DamageProvider:
    def evaluate_action(self, *, candidate, action):
        del candidate
        values = {"Filler": 100.0, "Execute": 200.0}
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=values[action.name],
        )


class _DurationEvidence:
    def build(self, plan):
        del plan
        return SimpleNamespace(rows=(), summary="", detail="", unresolved=())


class _Base:
    def __init__(self, plan: RotationPlan) -> None:
        self.duration_evidence = _DurationEvidence()
        self.ultimate_service = SimpleNamespace()
        self.result = RotationGenerationResult(
            plan=plan,
            duration_evidence=SimpleNamespace(rows=(), summary="", detail="", unresolved=()),
        )

    def generate_with_evidence(self, *, build, request):
        del build, request
        return self.result


class _NoCrossBarOpportunity:
    def find(self, plan, *, priorities):
        del plan, priorities
        return ()


class _NoCrossBarProposal:
    def propose(self, plan, opportunities):
        del plan, opportunities
        return ()


class _NoCrossBarFeasibility:
    def assess(self, plan, proposals):
        del plan, proposals
        return ()


class _NoCrossBarSelection:
    def select(self, plan, proposals, feasibility):
        del plan, proposals, feasibility
        return SimpleNamespace(selected=(), rejected=())


class _NoCrossBarMutation:
    def apply(self, plan, selection, *, weave_light_attacks, initial_bar):
        del selection, weave_light_attacks, initial_bar
        return SimpleNamespace(plan=plan, applied=())


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Synthetic",
        build_name="Execute Positive Control",
        duration_seconds=3.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, name="Filler", bar="front"),
            RotationAction(1.0, 0, RotationActionKind.SKILL, name="Filler", bar="front"),
            RotationAction(2.0, 0, RotationActionKind.SKILL, name="Filler", bar="front"),
        ),
    )


def _build():
    return SimpleNamespace(
        Name="Synthetic",
        BuildName="Execute Positive Control",
        Role="DD",
        FrontBarSkills=["Filler", "Execute", "", "", ""],
        BackBarSkills=[],
    )


def _request() -> RotationGenerationRequest:
    return RotationGenerationRequest(
        duration_seconds=3.0,
        ability_priorities=(
            AbilityPriorityEntry(bar="front", slot=1, skill_name="Filler", priority=2),
            AbilityPriorityEntry(bar="front", slot=2, skill_name="Execute", priority=1),
        ),
    )


def test_generate_swaps_only_inside_explicit_low_health_evidence_window() -> None:
    timeline = RotationTargetHealthTimeline(
        target_identity="boss",
        observations=(
            RotationTargetHealthObservation(
                time_seconds=0.0,
                target_identity="boss",
                current_health=50.0,
                maximum_health=100.0,
                evidence="above execute threshold",
            ),
            RotationTargetHealthObservation(
                time_seconds=1.0,
                target_identity="boss",
                current_health=20.0,
                maximum_health=100.0,
                evidence="below execute threshold",
            ),
        ),
    )
    context = RotationDDExecuteHealthTimelineContextSupport(
        timeline=timeline,
        action_damage_provider=_DamageProvider(),
    )
    execute_opportunity = RotationExecuteFillerOpportunityService(
        evidence_service=_EvidenceService(),
    )
    support = RotationDDCrossBarGenerationSupport(
        base=_Base(_plan()),
        opportunity_service=_NoCrossBarOpportunity(),
        proposal_service=_NoCrossBarProposal(),
        feasibility_service=_NoCrossBarFeasibility(),
        selection_service=_NoCrossBarSelection(),
        mutation_service=_NoCrossBarMutation(),
        execute_context_resolver=context,
        execute_opportunity_service=execute_opportunity,
    )

    result = support.generate_with_evidence(build=_build(), request=_request())

    assert [action.name for action in result.plan.actions] == ["Filler", "Execute", "Filler"]
    assert any(
        "execute phase replaced 'Filler' with 'Execute' at 1s" in assumption
        for assumption in result.plan.assumptions
    )
    assert not any("at 0s" in assumption and "Execute" in assumption for assumption in result.plan.assumptions)
    assert not any("at 2s" in assumption and "Execute" in assumption for assumption in result.plan.assumptions)
