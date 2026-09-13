from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

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


class _Base:
    def __init__(self, result):
        self.result = result
        self.duration_evidence = _EvidenceBuilder()
        self.calls = 0

    def generate_with_evidence(self, *, build, request):
        self.calls += 1
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


def _plan(name: str) -> RotationPlan:
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
    )


def _build(role="DD"):
    return SimpleNamespace(
        Name="Rylonia",
        BuildName="Corpsebuster DD",
        Role=role,
        FrontBarSkills=["Venom Skull", "", "", "", ""],
        BackBarSkills=["Stampede", "", "", "", ""],
    )


def _request(*, ultimate_bar=""):
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


def test_non_dd_generation_is_delegated_unchanged() -> None:
    original = _plan("Original")
    result = RotationGenerationResult(plan=original, duration_evidence=("old",))
    base = _Base(result)
    mutation = _Mutation(_plan("Mutated"))
    support = RotationDDCrossBarGenerationSupport(base=base, mutation_service=mutation)

    generated = support.generate_with_evidence(build=_build("Healer"), request=_request())

    assert generated is result
    assert mutation.calls == 0
    assert base.duration_evidence.calls == 0


def test_explicit_ultimate_generation_remains_owned_by_base_generator() -> None:
    original = _plan("Original")
    result = RotationGenerationResult(plan=original, duration_evidence=("old",))
    base = _Base(result)
    mutation = _Mutation(_plan("Mutated"))
    support = RotationDDCrossBarGenerationSupport(base=base, mutation_service=mutation)

    generated = support.generate_with_evidence(
        build=_build(),
        request=_request(ultimate_bar="front"),
    )

    assert generated is result
    assert mutation.calls == 0
    assert base.duration_evidence.calls == 0
