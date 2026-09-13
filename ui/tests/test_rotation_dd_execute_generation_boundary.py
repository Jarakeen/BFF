from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteFillerOpportunity,
    RotationExecuteFillerOpportunityResult,
)
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_dd_execute_generation_context import RotationDDExecuteGenerationContext
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationResult


class _EvidenceBuilder:
    def __init__(self) -> None:
        self.calls = []

    def build(self, plan):
        self.calls.append(plan)
        return SimpleNamespace(rows=(), summary="rebuilt", detail="", unresolved=())


class _UltimateService:
    def __init__(self) -> None:
        self.calls = []

    def apply_generation(
        self,
        *,
        build,
        plan,
        ultimate_bar,
        starting_ultimate,
        use_scheduled_combat_attacks,
    ):
        self.calls.append(plan)
        return SimpleNamespace(plan=replace(plan, assumptions=plan.assumptions + ("ultimate",)))


class _Base:
    def __init__(self, plan: RotationPlan) -> None:
        self.duration_evidence = _EvidenceBuilder()
        self.ultimate_service = _UltimateService()
        self.requests = []
        self.result = RotationGenerationResult(
            plan=plan,
            duration_evidence=SimpleNamespace(rows=(), summary="old", detail="", unresolved=()),
        )

    def generate_with_evidence(self, *, build, request):
        self.requests.append(request)
        return self.result


class _CrossBarOpportunity:
    def find(self, plan, *, priorities):
        return ("route",)


class _Proposal:
    def propose(self, plan, opportunities):
        return ("proposal",)


class _Feasibility:
    def assess(self, plan, proposals):
        return ("feasible",)


class _Selection:
    def select(self, plan, proposals, feasibility):
        return SimpleNamespace(selected=("selected",), rejected=())


class _RouteMutation:
    def __init__(self, routed_plan: RotationPlan) -> None:
        self.routed_plan = routed_plan

    def apply(self, plan, selection, *, weave_light_attacks, initial_bar):
        return SimpleNamespace(plan=self.routed_plan, applied=("selected",))


class _ExecuteOpportunity:
    def find(
        self,
        plan,
        *,
        priorities,
        duration_rules,
        snapshot_resolver,
        target_identity,
    ):
        assert plan.actions[0].name == "Filler"
        assert target_identity == "boss"
        return RotationExecuteFillerOpportunityResult(
            opportunities=(
                RotationExecuteFillerOpportunity(
                    time_seconds=0.0,
                    bar="front",
                    current_skill_name="Filler",
                    execute_skill_name="Execute",
                    current_priority=2,
                    execute_priority=1,
                    target_identity="boss",
                    active_thresholds=(0.25,),
                ),
            ),
        )


class _DamageProvider:
    def evaluate_action(self, *, candidate, action):
        values = {"Filler": 100.0, "Execute": 200.0}
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=values[action.name],
        )


def _plan(name: str) -> RotationPlan:
    return RotationPlan(
        character_name="Tester",
        build_name="DD",
        duration_seconds=3.0,
        actions=(
            RotationAction(
                time_seconds=0.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name=name,
                bar="front",
            ),
        ),
    )


def _build():
    return SimpleNamespace(
        Name="Tester",
        BuildName="DD",
        Role="DD",
        FrontBarSkills=["Filler", "Execute", "", "", ""],
        BackBarSkills=["Back Skill", "", "", "", ""],
    )


def _request(*, ultimate_bar: str = "front") -> RotationGenerationRequest:
    return RotationGenerationRequest(
        duration_seconds=3.0,
        ability_priorities=(
            AbilityPriorityEntry(bar="front", slot=1, skill_name="Filler", priority=2),
            AbilityPriorityEntry(bar="front", slot=2, skill_name="Execute", priority=1),
            AbilityPriorityEntry(bar="back", slot=1, skill_name="Back Skill", priority=1),
        ),
        ultimate_bar=ultimate_bar,
    )


def test_execute_mutation_runs_after_cross_bar_routing_and_before_ultimate() -> None:
    original = _plan("Original")
    routed = _plan("Filler")
    base = _Base(original)
    damage_provider = _DamageProvider()

    def execute_context_resolver(*, build, request, generated, routed_plan):
        assert routed_plan is routed
        return RotationDDExecuteGenerationContext(
            snapshot_resolver=lambda _time: None,
            target_identity="boss",
            action_damage_provider=damage_provider,
        )

    support = RotationDDCrossBarGenerationSupport(
        base=base,
        opportunity_service=_CrossBarOpportunity(),
        proposal_service=_Proposal(),
        feasibility_service=_Feasibility(),
        selection_service=_Selection(),
        mutation_service=_RouteMutation(routed),
        execute_context_resolver=execute_context_resolver,
        execute_opportunity_service=_ExecuteOpportunity(),
    )

    result = support.generate_with_evidence(build=_build(), request=_request())

    assert base.requests[0].ultimate_bar == ""
    assert len(base.ultimate_service.calls) == 1
    assert base.ultimate_service.calls[0].actions[0].name == "Execute"
    assert result.plan.actions[0].name == "Execute"
    assert any("execute phase replaced 'Filler' with 'Execute'" in item for item in result.plan.assumptions)


def test_missing_execute_context_preserves_routed_plan_without_execute_mutation() -> None:
    original = _plan("Original")
    routed = _plan("Filler")
    base = _Base(original)
    support = RotationDDCrossBarGenerationSupport(
        base=base,
        opportunity_service=_CrossBarOpportunity(),
        proposal_service=_Proposal(),
        feasibility_service=_Feasibility(),
        selection_service=_Selection(),
        mutation_service=_RouteMutation(routed),
    )

    result = support.generate_with_evidence(build=_build(), request=_request(ultimate_bar=""))

    assert result.plan.actions[0].name == "Filler"
    assert base.ultimate_service.calls == []
