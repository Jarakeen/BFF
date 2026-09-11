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
    def __init__(self) -> None:
        self.plan = RotationPlan(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=60.0,
            actions=(),
        )

    def generate_with_evidence(self, **_kwargs):
        return RotationGenerationResult(
            plan=self.plan,
            duration_evidence=SimpleNamespace(summary="seed"),
        )


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(validation="ok")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_dashboard_defaults_heavy_restore_to_canonical_generated_plan_evidence() -> None:
    generation = _Generation()
    canonical = _CanonicalCandidates()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=generation,
        canonical_candidates=canonical,
    )
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    request = RotationGenerationRequest(
        duration_seconds=60.0,
        ability_priorities=(
            AbilityPriorityEntry(
                bar="front",
                slot=1,
                skill_name="Combat Prayer",
                priority=10,
            ),
        ),
    )

    result = support.run_effects(
        player_build=build,
        generation_request=request,
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
    )

    assert result.candidate_result is canonical.result
    assert len(canonical.calls) == 1
    assert canonical.calls[0]["restoration_resolver"] is None
