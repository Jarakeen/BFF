from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from ui.rotation_automatic_potion_cadence_candidate_support import (
    RotationAutomaticPotionCadenceCandidateSupport,
    RotationPotionCooldownScenarioEvidence,
)
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationResult


class _Generation:
    def __init__(self) -> None:
        self.plan = RotationPlan(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=60.0,
            actions=(),
        )

    def generate_with_evidence(self, **kwargs):
        return RotationGenerationResult(
            plan=self.plan,
            duration_evidence=SimpleNamespace(summary="seed"),
        )


class _Candidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(validation="ok")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    build.FrontBarSkills = ["Combat Prayer", "", "", "", "", ""]
    return build


def _request() -> RotationGenerationRequest:
    return RotationGenerationRequest(
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


def _run(support: RotationDashboardCanonicalCandidateSupport, **extra):
    return support.run_effects(
        player_build=_build(),
        generation_request=_request(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
        **extra,
    )


def test_dashboard_default_uses_automatic_potion_cadence_adapter() -> None:
    support = RotationDashboardCanonicalCandidateSupport(generation=_Generation())

    assert isinstance(
        support.canonical_candidates,
        RotationAutomaticPotionCadenceCandidateSupport,
    )


def test_dashboard_forwards_scenario_evidence_only_when_supplied() -> None:
    candidates = _Candidates()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=_Generation(),
        canonical_candidates=candidates,
    )
    scenario = RotationPotionCooldownScenarioEvidence(effects=(), complete=True)

    _run(support, potion_cooldown_scenario_evidence=scenario)
    assert candidates.calls[0]["potion_cooldown_scenario_evidence"] is scenario

    _run(support)
    assert "potion_cooldown_scenario_evidence" not in candidates.calls[1]
