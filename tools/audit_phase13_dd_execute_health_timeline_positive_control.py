from __future__ import annotations

"""Synthetic production-boundary proof for target-Health execute Generate behavior."""

from types import SimpleNamespace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_conditional_consequence import SkillComponentConditionalConsequenceType
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidence,
    RotationExecuteComponentEvidence,
)
from services.rotation_execute_filler_opportunity_service import RotationExecuteFillerOpportunityService
from services.rotation_target_health_timeline_service import (
    RotationTargetHealthObservation,
    RotationTargetHealthTimeline,
)
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_dd_execute_health_timeline_context_support import RotationDDExecuteHealthTimelineContextSupport
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationResult


class _Evidence:
    def resolve(self, skill_name: str) -> RotationExecuteCandidateEvidence:
        if skill_name != "Execute":
            return RotationExecuteCandidateEvidence(skill_name, skill_name, f"synthetic:{skill_name}")
        return RotationExecuteCandidateEvidence(
            "Execute", "Execute", "synthetic:execute",
            components=(RotationExecuteComponentEvidence(
                skill_name="Execute", entity_id="synthetic:execute", skill_rank_id=1,
                coefficient_number=1, threshold=0.25,
                consequence_type=SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT,
                maximum_bonus_fraction=None,
                condition_evidence="synthetic reviewed target below 25% Health",
                consequence_evidence="synthetic reviewed execute component activates",
            ),),
        )


class _Damage:
    def evaluate_action(self, *, candidate, action):
        del candidate
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value={"Filler": 100.0, "Execute": 200.0}[action.name],
        )


class _Duration:
    def build(self, plan):
        del plan
        return SimpleNamespace(rows=(), summary="", detail="", unresolved=())


class _Base:
    def __init__(self, plan):
        self.duration_evidence = _Duration()
        self.ultimate_service = SimpleNamespace()
        self.result = RotationGenerationResult(
            plan=plan,
            duration_evidence=SimpleNamespace(rows=(), summary="", detail="", unresolved=()),
        )
    def generate_with_evidence(self, *, build, request):
        del build, request
        return self.result


class _EmptyOpportunity:
    def find(self, plan, *, priorities): del plan, priorities; return ()
class _EmptyProposal:
    def propose(self, plan, opportunities): del plan, opportunities; return ()
class _EmptyFeasibility:
    def assess(self, plan, proposals): del plan, proposals; return ()
class _EmptySelection:
    def select(self, plan, proposals, feasibility):
        del plan, proposals, feasibility
        return SimpleNamespace(selected=(), rejected=())
class _EmptyMutation:
    def apply(self, plan, selection, *, weave_light_attacks, initial_bar):
        del selection, weave_light_attacks, initial_bar
        return SimpleNamespace(plan=plan, applied=())


def main() -> int:
    plan = RotationPlan(
        character_name="Synthetic",
        build_name="Execute Positive Control",
        duration_seconds=3.0,
        actions=tuple(
            RotationAction(float(t), 0, RotationActionKind.SKILL, name="Filler", bar="front")
            for t in (0, 1, 2)
        ),
    )
    build = SimpleNamespace(
        Name="Synthetic", BuildName="Execute Positive Control", Role="DD",
        FrontBarSkills=["Filler", "Execute", "", "", ""], BackBarSkills=[],
    )
    request = RotationGenerationRequest(
        duration_seconds=3.0,
        ability_priorities=(
            AbilityPriorityEntry(bar="front", slot=1, skill_name="Filler", priority=2),
            AbilityPriorityEntry(bar="front", slot=2, skill_name="Execute", priority=1),
        ),
    )
    timeline = RotationTargetHealthTimeline(
        target_identity="boss",
        observations=(
            RotationTargetHealthObservation(0.0, "boss", 50.0, 100.0, evidence="above threshold"),
            RotationTargetHealthObservation(1.0, "boss", 20.0, 100.0, evidence="below threshold"),
        ),
    )
    support = RotationDDCrossBarGenerationSupport(
        base=_Base(plan),
        opportunity_service=_EmptyOpportunity(), proposal_service=_EmptyProposal(),
        feasibility_service=_EmptyFeasibility(), selection_service=_EmptySelection(),
        mutation_service=_EmptyMutation(),
        execute_context_resolver=RotationDDExecuteHealthTimelineContextSupport(
            timeline=timeline, action_damage_provider=_Damage(),
        ),
        execute_opportunity_service=RotationExecuteFillerOpportunityService(evidence_service=_Evidence()),
    )
    result = support.generate_with_evidence(build=build, request=request)
    names = tuple(action.name for action in result.plan.actions)

    print("=" * 72)
    print(" PHASE 13 DD EXECUTE HEALTH-TIMELINE POSITIVE CONTROL")
    print("=" * 72)
    print("0s target Health=50% -> expected Filler")
    print("1s target Health=20% -> expected Execute")
    print("2s target Health=unknown -> expected Filler (fail closed)")
    print(f"scheduled_actions={names}")
    passed = names == ("Filler", "Execute", "Filler")
    print(f"RESULT={'PASS' if passed else 'FAIL'}")
    print(
        "Interpretation: execute mutation occurs only when explicit runtime Health proves the reviewed threshold active and canonical exact-slot damage is greater."
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
