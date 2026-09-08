from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.resource_costs import ResourceType
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_potion_cadence import RotationPotionCadenceRequirement
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from ui.rotation_automatic_potion_cadence_candidate_support import (
    RotationAutomaticPotionCadenceCandidateSupport,
    RotationPotionCooldownScenarioEvidence,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport


class _Adapter:
    def __init__(self, build: CharacterBuild) -> None:
        self.build = build

    def adapt(self, saved, *, character_id=None):
        return SavedBuildAdaptation(build=self.build, unresolved=())


class _ItemService:
    def resolve(self, saved):
        return SimpleNamespace(unresolved=(), total_reduction_seconds=0.0)


class _BuildCooldownService:
    def __init__(self, *, effective: float | None, complete: bool) -> None:
        self.effective = effective
        self.complete = complete
        self.calls = 0

    def resolve(self, **kwargs):
        self.calls += 1
        effective = SimpleNamespace(
            complete=self.complete,
            effective_cooldown_seconds=self.effective,
            unresolved=() if self.complete else ("scenario inventory incomplete",),
        )
        return SimpleNamespace(effective=effective)


class _Pipeline:
    def __init__(self, final_plan: RotationPlan) -> None:
        self.final_plan = final_plan
        self.scorecard = None

    def run_effects(self, **kwargs):
        snapshot = SimpleNamespace(candidate_id="potion-candidate", plan=self.final_plan)
        self.scorecard = kwargs["scorecard_resolver"](snapshot)
        selected = (
            SimpleNamespace(candidate_id="potion-candidate", reasons=("ok",))
            if self.scorecard.supplied_obligations_satisfied
            else None
        )
        return SimpleNamespace(
            selected_candidate=selected,
            ranked_candidates=(SimpleNamespace(candidate_id="potion-candidate", reasons=("x",)),),
        )


def _consequence() -> RotationPlanConsequence:
    return RotationPlanConsequence(
        resource_kind=RotationResourceConsequenceKind.NEUTRAL,
        cast_deltas=(),
        cost_deltas=(),
        total_cost_delta=0,
        minimum_resource_delta=0,
        ending_resource_delta=0,
        shortfall_delta=0,
        wait_delta=0,
    )


def _scorecard(_snapshot) -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.POTION, "Potion A"),
            RotationAction(30.0, 0, RotationActionKind.POTION, "Potion B"),
        ),
    )


def _kwargs(plan: RotationPlan) -> dict:
    return dict(
        player_build=SimpleNamespace(),
        seed_plan=plan,
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=_scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )


def _support(build_service: _BuildCooldownService, plan: RotationPlan):
    character_build = CharacterBuild(
        name="Potion Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        potion_id="essence_of_spell_power",
    )
    adapter = _Adapter(character_build)
    pipeline = _Pipeline(plan)
    canonical = RotationCanonicalCandidateSupport(
        build_adapter=adapter,
        pipeline=pipeline,
    )
    return (
        RotationAutomaticPotionCadenceCandidateSupport(
            canonical_candidates=canonical,
            build_adapter=adapter,
            item_service=_ItemService(),
            build_potion_cooldown_service=build_service,
        ),
        pipeline,
    )


def test_complete_build_context_evidence_automatically_enforces_shared_cadence() -> None:
    plan = _plan()
    build_service = _BuildCooldownService(effective=45.0, complete=True)
    support, pipeline = _support(build_service, plan)

    support.run_effects(
        **_kwargs(plan),
        potion_cooldown_scenario_evidence=RotationPotionCooldownScenarioEvidence(
            effects=(),
            complete=True,
        ),
    )

    assert build_service.calls == 1
    assert support.last_potion_cooldown_resolution is not None
    assert len(pipeline.scorecard.cooldown_violations) == 1
    assert pipeline.scorecard.cooldown_violations[0].required_interval_seconds == 45.0


def test_partial_build_context_evidence_preserves_do_not_guess_behavior() -> None:
    plan = _plan()
    build_service = _BuildCooldownService(effective=None, complete=False)
    support, pipeline = _support(build_service, plan)

    support.run_effects(
        **_kwargs(plan),
        potion_cooldown_scenario_evidence=RotationPotionCooldownScenarioEvidence(
            effects=(),
            complete=False,
        ),
    )

    assert build_service.calls == 1
    assert pipeline.scorecard.cooldown_violations == ()


def test_explicit_cadence_remains_authoritative_over_automatic_derivation() -> None:
    plan = _plan()
    build_service = _BuildCooldownService(effective=45.0, complete=True)
    support, pipeline = _support(build_service, plan)

    support.run_effects(
        **_kwargs(plan),
        potion_cooldown_scenario_evidence=RotationPotionCooldownScenarioEvidence(
            effects=(),
            complete=True,
        ),
        potion_cadence_requirement=RotationPotionCadenceRequirement(25.0),
    )

    assert build_service.calls == 0
    assert pipeline.scorecard.cooldown_violations == ()
