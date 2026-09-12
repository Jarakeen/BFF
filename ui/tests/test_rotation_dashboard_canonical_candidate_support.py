from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.combat_state import CombatState
from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
)


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    build.FrontBarSkills = ["Combat Prayer", "", "", "", "", ""]
    return build


def _request(**changes) -> RotationGenerationRequest:
    values = dict(
        duration_seconds=60.0,
        ability_priorities=(
            AbilityPriorityEntry(
                bar="front",
                slot=1,
                skill_name="Combat Prayer",
                priority=10,
            ),
        ),
        stabilize_recovery_heavies=True,
        recovery_pressure_resolver=lambda context: None,
    )
    values.update(changes)
    return RotationGenerationRequest(**values)


class _Generation:
    def __init__(self) -> None:
        self.calls = []
        self.plan = RotationPlan(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=60.0,
            actions=(),
        )
        self.result = RotationGenerationResult(
            plan=self.plan,
            duration_evidence=SimpleNamespace(summary="seed evidence"),
        )

    def generate_with_evidence(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(validation="canonical-validation")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _CandidateResolverService:
    def __init__(self) -> None:
        self.calls = []
        self.evaluator = object()
        self.scorecard = object()

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            evaluator_resolver=self.evaluator,
            scorecard_resolver=self.scorecard,
        )


def test_dashboard_default_candidate_bridge_enables_static_build_context() -> None:
    support = RotationDashboardCanonicalCandidateSupport(generation=_Generation())

    assert isinstance(
        support.canonical_candidates.static_context_service,
        RotationStaticBuildContextService,
    )


def test_dashboard_path_generates_unstabilized_seed_then_runs_canonical_candidates() -> None:
    generation = _Generation()
    canonical = _CanonicalCandidates()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=generation,
        canonical_candidates=canonical,
    )
    player_build = _build()
    evaluator_resolver = object()
    scorecard_resolver = object()
    restoration_resolver = object()
    wait_factory = object()
    reserve_resolver = object()
    combat_state = CombatState(
        in_combat=True,
        active_buffs=("Major Sorcery",),
    )

    result = support.run_effects(
        player_build=player_build,
        generation_request=_request(),
        evaluator_resolver=evaluator_resolver,
        scorecard_resolver=scorecard_resolver,
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=restoration_resolver,
        combat_state=combat_state,
        demands=(item for item in ("demand-a", "demand-b")),
        options=(item for item in ("option-a",)),
        wait_decision_factory=wait_factory,
        requirements=(item for item in ("major-brittle",)),
        passives=(item for item in ("class-passive", "armor-passive")),
        reserve_assessment_resolver=reserve_resolver,
        max_iterations=8,
        baseline_id="dashboard-baseline",
        character_id="magrat-id",
    )

    assert result.seed_generation is generation.result
    assert result.candidate_result is canonical.result
    assert len(generation.calls) == 1
    seed_request = generation.calls[0]["request"]
    assert seed_request.stabilize_recovery_heavies is False
    assert seed_request.recovery_pressure_resolver is None
    assert seed_request.ability_priorities == _request().ability_priorities

    assert len(canonical.calls) == 1
    call = canonical.calls[0]
    assert call["player_build"] is player_build
    assert call["seed_plan"] is generation.plan
    assert call["priorities"].character_name == "Magrat"
    assert call["priorities"].build_name == "DF Healer"
    assert call["priorities"].role == "Healer"
    assert call["priorities"].entries == _request().ability_priorities
    assert call["evaluator_resolver"] is evaluator_resolver
    assert call["scorecard_resolver"] is scorecard_resolver
    assert call["resource"] is ResourceType.MAGICKA
    assert call["maximum_amount"] == 32000
    assert call["trigger_fraction"] == 0.35
    assert call["restoration_resolver"] is restoration_resolver
    assert call["combat_state"] is combat_state
    assert call["demands"] == ("demand-a", "demand-b")
    assert call["options"] == ("option-a",)
    assert call["requirements"] == ("major-brittle",)
    assert call["passives"] == ("class-passive", "armor-passive")
    assert call["wait_decision_factory"] is wait_factory
    assert call["reserve_assessment_resolver"] is reserve_resolver
    assert call["max_iterations"] == 8
    assert call["baseline_id"] == "dashboard-baseline"
    assert call["character_id"] == "magrat-id"


def test_dashboard_composes_omitted_resolver_pair_from_exact_generated_seed() -> None:
    generation = _Generation()
    canonical = _CanonicalCandidates()
    resolver_service = _CandidateResolverService()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=generation,
        canonical_candidates=canonical,
        candidate_resolver_service=resolver_service,  # type: ignore[arg-type]
    )
    player_build = _build()

    support.run_effects(
        player_build=player_build,
        generation_request=_request(),
        evaluator_resolver=None,
        scorecard_resolver=None,
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        demands=("healing-demand",),  # type: ignore[arg-type]
    )

    assert len(resolver_service.calls) == 1
    resolver_call = resolver_service.calls[0]
    assert resolver_call["player_build"] is player_build
    assert resolver_call["baseline_plan"] is generation.plan
    assert resolver_call["resource"] is ResourceType.MAGICKA
    assert resolver_call["context"].demands == ("healing-demand",)
    canonical_call = canonical.calls[0]
    assert canonical_call["evaluator_resolver"] is resolver_service.evaluator
    assert canonical_call["scorecard_resolver"] is resolver_service.scorecard


def test_dashboard_rejects_partial_generate_resolver_pair() -> None:
    generation = _Generation()
    canonical = _CanonicalCandidates()
    resolver_service = _CandidateResolverService()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=generation,
        canonical_candidates=canonical,
        candidate_resolver_service=resolver_service,  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="both candidate resolvers or neither"):
        support.run_effects(
            player_build=_build(),
            generation_request=_request(),
            evaluator_resolver=object(),
            scorecard_resolver=None,
            resource=ResourceType.MAGICKA,
            maximum_amount=32000,
            trigger_fraction=0.35,
        )

    assert len(generation.calls) == 1
    assert resolver_service.calls == []
    assert canonical.calls == []


def test_dashboard_path_requires_explicit_priorities_before_candidate_evaluation() -> None:
    generation = _Generation()
    canonical = _CanonicalCandidates()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=generation,
        canonical_candidates=canonical,
    )

    with pytest.raises(ValueError, match="requires explicit ability priorities"):
        support.run_effects(
            player_build=_build(),
            generation_request=_request(ability_priorities=()),
            evaluator_resolver=object(),
            scorecard_resolver=object(),
            resource=ResourceType.MAGICKA,
            maximum_amount=32000,
            trigger_fraction=0.35,
            restoration_resolver=object(),
        )

    assert generation.calls == []
    assert canonical.calls == []


def test_dashboard_path_does_not_mutate_original_generation_request() -> None:
    generation = _Generation()
    canonical = _CanonicalCandidates()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=generation,
        canonical_candidates=canonical,
    )
    request = _request()
    original_pressure = request.recovery_pressure_resolver

    support.run_effects(
        player_build=_build(),
        generation_request=request,
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )

    assert request.stabilize_recovery_heavies is True
    assert request.recovery_pressure_resolver is original_pressure


def test_dashboard_forwards_runtime_activation_anchor_evidence_unchanged() -> None:
    generation = _Generation()
    canonical = _CanonicalCandidates()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=generation,
        canonical_candidates=canonical,
    )
    anchor_evidence = object()

    support.run_effects(
        player_build=_build(),
        generation_request=_request(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        runtime_activation_anchor_evidence=(anchor_evidence,),  # type: ignore[arg-type]
    )

    assert canonical.calls[0]["runtime_activation_anchor_evidence"] == (
        anchor_evidence,
    )
