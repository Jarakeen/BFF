from __future__ import annotations

from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_execute_filler_mutation_service import (
    RotationExecuteFillerMutation,
    RotationExecuteFillerMutationResult,
)
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteFillerOpportunity,
    RotationExecuteFillerOpportunityResult,
)
from services.rotation_execute_filler_policy_service import RotationExecuteFillerPolicyService


class _OpportunityService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def find(self, plan, **kwargs):
        self.calls.append((plan, kwargs))
        return self.result


class _MutationService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def apply(self, *, candidate, opportunities):
        self.calls.append((candidate, opportunities))
        return self.result


def _candidate(candidate_id="candidate"):
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Tester",
            build_name="DD Build",
            duration_seconds=10.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _opportunity():
    return RotationExecuteFillerOpportunity(
        time_seconds=8.0,
        bar="front",
        current_skill_name="Filler",
        execute_skill_name="Execute",
        current_priority=1,
        execute_priority=5,
        target_identity="boss",
        active_thresholds=(0.25,),
    )


def test_no_execute_opportunities_preserve_original_candidate_and_fail_closed_evidence() -> None:
    candidate = _candidate()
    opportunity = _OpportunityService(
        RotationExecuteFillerOpportunityResult(
            opportunities=(),
            unresolved=("canonical execute identity unresolved",),
        )
    )
    mutation = _MutationService(None)
    service = RotationExecuteFillerPolicyService(
        opportunity_service=opportunity,  # type: ignore[arg-type]
        mutation_service=mutation,  # type: ignore[arg-type]
    )

    result = service.apply(
        candidate=candidate,
        priorities=object(),  # type: ignore[arg-type]
        duration_rules=(),
        snapshot_resolver=lambda _: None,
        target_identity="boss",
    )

    assert result.candidate is candidate
    assert result.opportunities == ()
    assert result.mutations == ()
    assert result.unresolved == ("canonical execute identity unresolved",)
    assert mutation.calls == []


def test_policy_composes_opportunity_and_mutation_results() -> None:
    candidate = _candidate()
    mutated = _candidate("mutated")
    execute_opportunity = _opportunity()
    applied = RotationExecuteFillerMutation(
        time_seconds=8.0,
        sequence=1,
        bar="front",
        replaced_skill_name="Filler",
        execute_skill_name="Execute",
        current_damage=100.0,
        execute_damage=150.0,
    )
    opportunity = _OpportunityService(
        RotationExecuteFillerOpportunityResult(
            opportunities=(execute_opportunity,),
            unresolved=("shared warning",),
        )
    )
    mutation = _MutationService(
        RotationExecuteFillerMutationResult(
            candidate=mutated,
            comparisons=(),
            mutations=(applied,),
            unresolved=("shared warning", "comparison warning"),
        )
    )
    service = RotationExecuteFillerPolicyService(
        opportunity_service=opportunity,  # type: ignore[arg-type]
        mutation_service=mutation,  # type: ignore[arg-type]
    )

    result = service.apply(
        candidate=candidate,
        priorities=object(),  # type: ignore[arg-type]
        duration_rules=(),
        snapshot_resolver=lambda _: None,
        target_identity="boss",
    )

    assert result.candidate is mutated
    assert result.opportunities == (execute_opportunity,)
    assert result.mutations == (applied,)
    assert result.unresolved == ("shared warning", "comparison warning")
    assert mutation.calls == [(candidate, (execute_opportunity,))]
