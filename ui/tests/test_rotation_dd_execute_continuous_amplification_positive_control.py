from __future__ import annotations

from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import SkillComponentClassification, SkillEffectKind
from minmax.skill_component_condition import SkillComponentCondition, SkillComponentConditionType
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequence,
    SkillComponentConditionalConsequenceType,
)
from minmax.stat_ids import StatId
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)
from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidence,
    RotationExecuteComponentEvidence,
)
from services.rotation_execute_filler_opportunity_service import RotationExecuteFillerOpportunityService
from services.rotation_target_health_timeline_service import (
    RotationTargetHealthObservation,
    RotationTargetHealthTimeline,
    RotationTargetHealthTimelineService,
)
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_dd_execute_health_timeline_context_support import (
    RotationDDExecuteHealthTimelineContextSupport,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationResult


def _trace(value: float):
    return SimpleNamespace(final_value=value)


def _context():
    return SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.WEAPON_DAMAGE: _trace(3000.0),
                StatId.SPELL_DAMAGE: _trace(3000.0),
                StatId.PHYSICAL_PENETRATION: _trace(0.0),
                StatId.SPELL_PENETRATION: _trace(0.0),
                StatId.CRITICAL_CHANCE: _trace(0.0),
                StatId.CRITICAL_DAMAGE: _trace(0.0),
            }
        ),
        fight_duration=10.0,
        target_resistance=None,
        combat_state=CombatState(),
        dd_exploiter_bonus=0.0,
    )


class _Calculator:
    def evaluate_entity_id(self, entity_id, context):
        if entity_id == "Filler":
            return SimpleNamespace(
                skill=SimpleNamespace(skill_rank_id=301),
                components=(SimpleNamespace(coefficient_number=1, final_value=2000.0),),
                unresolved=(),
            )
        if entity_id == "Killer's Blade":
            return SimpleNamespace(
                skill=SimpleNamespace(skill_rank_id=302),
                components=(
                    SimpleNamespace(coefficient_number=1, final_value=1000.0),
                    SimpleNamespace(coefficient_number=2, final_value=500.0),
                ),
                unresolved=(),
            )
        return SimpleNamespace(skill=None, components=(), unresolved=(f"unknown skill {entity_id}",))


class _Components:
    def get_for_skill_rank(self, skill_rank_id):
        numbers = (1,) if skill_rank_id == 301 else (1, 2)
        return tuple(
            SkillComponentClassification(
                skill_rank_id=skill_rank_id,
                coefficient_number=number,
                effect_kind=SkillEffectKind.DAMAGE,
                damage_type="magical",
                is_dot=False,
                is_aoe=False,
                can_crit=False,
                source="synthetic positive control",
            )
            for number in numbers
        )


class _Consequences:
    def __init__(self):
        condition = SkillComponentCondition(
            skill_rank_id=302,
            coefficient_number=1,
            condition_type=SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT,
            threshold=0.50,
            evidence="reviewed target below 50% Health",
        )
        self.amplification = SkillComponentConditionalConsequence(
            skill_rank_id=302,
            coefficient_number=1,
            consequence_type=SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
            condition=condition,
            maximum_bonus_fraction=4.0,
            evidence="reviewed Killer's Blade up to 400% more damage",
        )

    def resolve(self, skill_rank_id, coefficient_number):
        if skill_rank_id == 302 and coefficient_number == 1:
            return (self.amplification,)
        return ()


class _OpportunityEvidence:
    def resolve(self, skill_name: str) -> RotationExecuteCandidateEvidence:
        if skill_name != "Killer's Blade":
            return RotationExecuteCandidateEvidence(
                requested_skill_name=skill_name,
                resolved_skill_name=skill_name,
                entity_id=f"synthetic:{skill_name}",
            )
        return RotationExecuteCandidateEvidence(
            requested_skill_name="Killer's Blade",
            resolved_skill_name="Killer's Blade",
            entity_id="synthetic:killers_blade",
            components=(
                RotationExecuteComponentEvidence(
                    skill_name="Killer's Blade",
                    entity_id="synthetic:killers_blade",
                    skill_rank_id=302,
                    coefficient_number=1,
                    threshold=0.50,
                    consequence_type=SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
                    maximum_bonus_fraction=4.0,
                    condition_evidence="reviewed target below 50% Health",
                    consequence_evidence="reviewed linear missing-Health amplification",
                ),
            ),
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
        build_name="Continuous Execute Positive Control",
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
        BuildName="Continuous Execute Positive Control",
        Role="DD",
        FrontBarSkills=["Filler", "Killer's Blade", "", "", ""],
        BackBarSkills=[],
    )


def _request() -> RotationGenerationRequest:
    return RotationGenerationRequest(
        duration_seconds=3.0,
        ability_priorities=(
            AbilityPriorityEntry(bar="front", slot=1, skill_name="Filler", priority=2),
            AbilityPriorityEntry(bar="front", slot=2, skill_name="Killer's Blade", priority=1),
        ),
    )


def test_generate_uses_reviewed_continuous_execute_damage_only_when_health_proves_it() -> None:
    timeline = RotationTargetHealthTimeline(
        target_identity="boss",
        observations=(
            RotationTargetHealthObservation(
                time_seconds=0.0,
                target_identity="boss",
                current_health=75.0,
                maximum_health=100.0,
                evidence="above Killer's Blade execute threshold",
            ),
            RotationTargetHealthObservation(
                time_seconds=1.0,
                target_identity="boss",
                current_health=25.0,
                maximum_health=100.0,
                evidence="reviewed low-Health execute point",
            ),
        ),
    )
    timeline_service = RotationTargetHealthTimelineService()
    snapshot_resolver = timeline_service.snapshot_resolver(timeline)
    damage_provider = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(),
        component_repository=_Components(),
        conditional_consequence_repository=_Consequences(),
        runtime_target_snapshot_resolver=lambda time_seconds, sequence: snapshot_resolver(time_seconds),
        execute_target_identity="boss",
    )
    execute_context = RotationDDExecuteHealthTimelineContextSupport(
        timeline=timeline,
        action_damage_provider=damage_provider,
        timeline_service=timeline_service,
    )
    execute_opportunity = RotationExecuteFillerOpportunityService(
        evidence_service=_OpportunityEvidence(),
    )
    support = RotationDDCrossBarGenerationSupport(
        base=_Base(_plan()),
        opportunity_service=_NoCrossBarOpportunity(),
        proposal_service=_NoCrossBarProposal(),
        feasibility_service=_NoCrossBarFeasibility(),
        selection_service=_NoCrossBarSelection(),
        mutation_service=_NoCrossBarMutation(),
        execute_context_resolver=execute_context,
        execute_opportunity_service=execute_opportunity,
    )

    result = support.generate_with_evidence(build=_build(), request=_request())

    assert [action.name for action in result.plan.actions] == [
        "Filler",
        "Killer's Blade",
        "Filler",
    ]
    assert any(
        "execute phase replaced 'Filler' with 'Killer's Blade' at 1s" in assumption
        for assumption in result.plan.assumptions
    )
    assert not any("at 0s" in assumption and "Killer's Blade" in assumption for assumption in result.plan.assumptions)
    assert not any("at 2s" in assumption and "Killer's Blade" in assumption for assumption in result.plan.assumptions)
