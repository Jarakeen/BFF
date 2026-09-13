from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
)


class _Generation:
    def generate_with_evidence(self, **_kwargs):
        return RotationGenerationResult(
            plan=RotationPlan(
                character_name="Rylonia",
                build_name="Corpsebuster DD",
                duration_seconds=60.0,
                actions=(),
            ),
            duration_evidence=SimpleNamespace(summary="seed"),
        )


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(validation="ok")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_dashboard_forwards_explicit_output_condition_context_factory() -> None:
    canonical = _CanonicalCandidates()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=_Generation(),
        canonical_candidates=canonical,
    )
    build = PlayerBuild(Name="Rylonia", BuildName="Corpsebuster DD", Role="DD")
    request = RotationGenerationRequest(
        duration_seconds=60.0,
        ability_priorities=(
            AbilityPriorityEntry(
                bar="front",
                slot=1,
                skill_name="Detonating Siphon",
                priority=10,
            ),
        ),
    )

    def resolver_factory(_plan):
        return lambda _event: frozenset()

    result = support.run_effects(
        player_build=build,
        generation_request=request,
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        runtime_output_condition_context_resolver_factory=resolver_factory,
    )

    assert result.candidate_result is canonical.result
    assert len(canonical.calls) == 1
    assert (
        canonical.calls[0]["runtime_output_condition_context_resolver_factory"]
        is resolver_factory
    )
