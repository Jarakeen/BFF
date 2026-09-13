from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace

import pytest

from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationResult


@dataclass
class _EvidenceBuilder:
    calls: int = 0

    def build(self, plan):
        self.calls += 1
        return ("rebuilt", len(plan.actions))


class _UltimateService:
    def __init__(self):
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
        self.calls.append(
            SimpleNamespace(
                build=build,
                plan=plan,
                ultimate_bar=ultimate_bar,
                starting_ultimate=starting_ultimate,
                use_scheduled_combat_attacks=use_scheduled_combat_attacks,
            )
        )
        final_plan = replace(
            plan,
            assumptions=tuple(plan.assumptions) + ("canonical ultimate projection applied",),
        )
        return SimpleNamespace(plan=final_plan)


class _Base:
    def __init__(self, result):
        self.result = result
        self.duration_evidence = _EvidenceBuilder()
        self.ultimate_service = _UltimateService()
        self.calls = 0
        self.requests = []

    def generate_with_evidence(self, *, build, request):
        self.calls += 1
        self.requests.append(request)
        return self.result


class _Opportunity:
    def find(self, plan, *, priorities):
        return ("opportunity",)


class _Proposal:
    def propose(self, plan, opportunities):
        return ("proposal",)


class _Feasibility:
    def assess(self, plan, proposals):
        return ("feasible",)


class _Selection:
    def select(self, plan, proposals, feasibility):
        return SimpleNamespace(selected=("selected",), rejected=())


class _Mutation:
    def __init__(self, mutated_plan):
        self.mutated_plan = mutated_plan
        self.calls = 0

    def apply(self, plan, selection, *, weave_light_attacks, initial_bar):
        self.calls += 1
        return SimpleNamespace(
            plan=self.mutated_plan,
            applied=("selected",),
            consumed_wait_times=(1.0, 2.0),
        )


def _plan(
    name: str,
    *,
    assumptions: tuple[str, ...] = (),
    unresolved: tuple[str, ...] = (),
) -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
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
        assumptions=assumptions,
        unresolved=unresolved,
    )


def _build(role="DD"):
    return SimpleNamespace(
        Name="Rylonia",
        BuildName="Corpsebuster DD",
        Role=role,
        FrontBarSkills=["Venom Skull", "", "", "", ""],
        BackBarSkills=["Stampede", "", "", "", ""],
    )


def _request(
    *,
    ultimate_bar="",
    starting_ultimate=0.0,
    use_scheduled_combat_attacks_for_ultimate=False,
):
    return RotationGenerationRequest(
        duration_seconds=3.0,
        ability_priorities=(
            AbilityPriorityEntry(
                bar="front",
                slot=1,
                skill_name="Venom Skull",
                priority=1,
            ),
            AbilityPriorityEntry(
                bar="back",
                slot=1,
                skill_name="Stampede",
                priority=1,
            ),
        ),
        ultimate_bar=ultimate_bar,
        starting_ultimate=starting_ultimate,
        use_scheduled_combat_attacks_for_ultimate=use_scheduled_combat_attacks_for_ultimate,
    )


def test_dd_explicit_priority_generation_applies_selected_cross_bar_mutation() -> None:
    original = _plan("Original")
    mutated = _plan("Venom Skull")
    result = RotationGenerationResult(plan=original, duration_evidence=("old",))
    base = _Base(result)
    mutation = _Mutation(mutated)
    support = RotationDDCrossBarGenerationSupport(
        base=base,
        opportunity_service=_Opportunity(),
        proposal_service=_Proposal(),
        feasibility_service=_Feasibility(),
        selection_service=_Selection(),
        mutation_service=mutation,
    )

    generated = support.generate_with_evidence(build=_build(), request=_request())

    assert generated.plan is mutated
    assert generated.duration_evidence == ("rebuilt", 1)
    assert mutation.calls == 1
    assert base.duration_evidence.calls == 1
    assert base.ultimate_service.calls == []


def test_non_dd_generation_is_delegated_unchanged() -> None:
    original = _plan("Original")
    result = RotationGenerationResult(plan=original, duration_evidence=("old",))
    base = _Base(result)
    mutation = _Mutation(_plan("Mutated"))
    support = RotationDDCrossBarGenerationSupport(base=base, mutation_service=mutation)

    request = _request(ultimate_bar="front")
    generated = support.generate_with_evidence(build=_build("Healer"), request=request)

    assert generated is result
    assert base.requests == [request]
    assert mutation.calls == 0
    assert base.duration_evidence.calls == 0
    assert base.ultimate_service.calls == []


def test_explicit_ultimate_is_projected_after_selected_cross_bar_mutation() -> None:
    original = _plan(
        "Original",
        unresolved=(
            "ultimate timing is not scheduled because no ultimate bar is selected",
            "execute-phase behavior is not yet scheduled",
        ),
    )
    mutated = _plan(
        "Venom Skull",
        unresolved=original.unresolved,
    )
    result = RotationGenerationResult(plan=original, duration_evidence=("old",))
    base = _Base(result)
    mutation = _Mutation(mutated)
    support = RotationDDCrossBarGenerationSupport(
        base=base,
        opportunity_service=_Opportunity(),
        proposal_service=_Proposal(),
        feasibility_service=_Feasibility(),
        selection_service=_Selection(),
        mutation_service=mutation,
    )
    request = _request(
        ultimate_bar="front",
        starting_ultimate=42.0,
        use_scheduled_combat_attacks_for_ultimate=True,
    )

    generated = support.generate_with_evidence(build=_build(), request=request)

    assert len(base.requests) == 1
    assert base.requests[0].ultimate_bar == ""
    assert base.requests[0].starting_ultimate == 42.0
    assert base.requests[0].use_scheduled_combat_attacks_for_ultimate is True
    assert mutation.calls == 1

    assert len(base.ultimate_service.calls) == 1
    ultimate_call = base.ultimate_service.calls[0]
    assert ultimate_call.plan.actions[0].name == "Venom Skull"
    assert ultimate_call.ultimate_bar == "front"
    assert ultimate_call.starting_ultimate == 42.0
    assert ultimate_call.use_scheduled_combat_attacks is True
    assert (
        "ultimate timing is not scheduled because no ultimate bar is selected"
        not in ultimate_call.plan.unresolved
    )
    assert "execute-phase behavior is not yet scheduled" in ultimate_call.plan.unresolved
    assert (
        "dashboard Ultimate projection explicitly selects the front slot-6 ultimate"
        in ultimate_call.plan.assumptions
    )
    assert (
        "scheduled light/heavy attacks are treated as successful damaging attacks for base Ultimate generation"
        in ultimate_call.plan.assumptions
    )

    assert generated.ultimate_projection is not None
    assert generated.plan.actions[0].name == "Venom Skull"
    assert "canonical ultimate projection applied" in generated.plan.assumptions
    assert generated.duration_evidence == ("rebuilt", 1)
    assert base.duration_evidence.calls == 1


def test_invalid_explicit_ultimate_bar_still_fails_before_deferred_generation() -> None:
    original = _plan("Original")
    result = RotationGenerationResult(plan=original, duration_evidence=("old",))
    base = _Base(result)
    support = RotationDDCrossBarGenerationSupport(base=base)

    with pytest.raises(ValueError, match="ultimate bar must be"):
        support.generate_with_evidence(
            build=_build(),
            request=_request(ultimate_bar="middle"),
        )

    assert base.calls == 0
