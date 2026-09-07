from __future__ import annotations

from dataclasses import dataclass

import pytest

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearSlot
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from services.rotation_candidate_effect_evaluation_service import (
    RotationCandidateEffectEvaluationInput,
    RotationCandidateEffectEvaluationService,
)
from services.rotation_candidate_effect_obligation_service import (
    RotationCandidateEffectObligationService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingResult,
    RotationCandidateTier,
)
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement


@dataclass
class _ScorecardStub:
    name: str


class _FakeBaseRanker:
    def __init__(self, ordering: tuple[tuple[str, RotationCandidateTier], ...]) -> None:
        self.ordering = ordering

    def rank(self, candidates: tuple[RotationCandidateRankingInput, ...]):
        by_id = {candidate.candidate_id: candidate for candidate in candidates}
        return tuple(
            RotationCandidateRankingResult(
                candidate_id=candidate_id,
                scorecard=by_id[candidate_id].scorecard,
                tier=tier,
                rank=index + 1,
                reasons=(f"base {candidate_id}",),
            )
            for index, (candidate_id, tier) in enumerate(self.ordering)
        )


def _status_effect() -> EffectVariant:
    return EffectVariant(
        name="chilled",
        layer=EffectLayer.CAST,
        source="Winter's Revenge",
        duration=4.0,
        category=SupportEffectCategory.STATUS,
        target_type=SupportTargetType.ENEMY,
    )


def _modifier() -> EffectVariant:
    return EffectVariant(
        name="status_effect_duration_increase",
        layer=EffectLayer.PASSIVE,
        source="Serpent's Disdain (5)",
        magnitude=16.0,
        category=SupportEffectCategory.OTHER,
        target_type=SupportTargetType.SELF,
    )


def _build() -> CharacterBuild:
    winter = SlottedSkill(
        skill_id="winters_revenge",
        skill_line_id="winters_embrace",
        is_cast=True,
        effects=(_status_effect(),),
    )
    return CharacterBuild(
        name="Effect Candidate Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(WeaponType.FROST_STAFF),
            off_hand=None,
            slots=(winter,),
        ),
        armor=(
            ArmorPiece(
                slot=GearSlot.CHEST,
                effects=(_modifier(),),
            ),
        ),
    )


def _plan(*casts: float) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Effect Candidate Build",
        duration_seconds=40.0,
        actions=tuple(
            RotationAction(
                time_seconds=time,
                sequence=index,
                kind=RotationActionKind.SKILL,
                name="Winter's Revenge",
                bar="front",
            )
            for index, time in enumerate(casts)
        ),
    )


def _candidate(candidate_id: str, *casts: float) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=_plan(*casts),
        refresh_leads=(),
    )


def _ranking_input(candidate_id: str) -> RotationCandidateRankingInput:
    return RotationCandidateRankingInput(
        candidate_id=candidate_id,
        scorecard=_ScorecardStub(candidate_id),
    )


def _input(candidate_id: str, *casts: float) -> RotationCandidateEffectEvaluationInput:
    return RotationCandidateEffectEvaluationInput(
        generated_candidate=_candidate(candidate_id, *casts),
        ranking_input=_ranking_input(candidate_id),
    )


def _requirement() -> RotationEffectUptimeRequirement:
    return RotationEffectUptimeRequirement(
        effect_name="chilled",
        source_skill_name="Winter's Revenge",
        minimum_uptime=0.90,
        bar="front",
    )


def test_generated_candidates_are_assessed_before_final_ranking() -> None:
    service = RotationCandidateEffectEvaluationService(
        obligation_service=RotationCandidateEffectObligationService(
            _FakeBaseRanker((
                ("better-resource", RotationCandidateTier.ELIGIBLE),
                ("meets-effect", RotationCandidateTier.ELIGIBLE),
            ))
        )
    )

    ranked = service.evaluate_and_rank(
        build=_build(),
        candidates=(
            _input("better-resource", 0.0),
            _input("meets-effect", 0.0, 20.0),
        ),
        requirements=(_requirement(),),
    )

    assert [item.candidate_id for item in ranked] == ["meets-effect", "better-resource"]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE

    passing = ranked[0].ranking_result.effect_uptime_assessments[0]
    failing = ranked[1].ranking_result.effect_uptime_assessments[0]
    assert passing.observed_uptime == pytest.approx(1.0)
    assert passing.summary is not None
    assert passing.summary.applied_modifier_sources == ("Serpent's Disdain (5)",)
    assert failing.observed_uptime == pytest.approx(0.5)


def test_generated_schedule_is_retained_after_effect_ranking() -> None:
    service = RotationCandidateEffectEvaluationService(
        obligation_service=RotationCandidateEffectObligationService(
            _FakeBaseRanker((("candidate", RotationCandidateTier.ELIGIBLE),))
        )
    )

    ranked = service.evaluate_and_rank(
        build=_build(),
        candidates=(_input("candidate", 0.0, 20.0),),
        requirements=(_requirement(),),
    )

    assert ranked[0].generated_candidate.candidate_id == "candidate"
    assert tuple(action.time_seconds for action in ranked[0].generated_candidate.plan.actions) == (
        0.0,
        20.0,
    )


def test_no_effect_requirements_preserves_existing_base_order() -> None:
    service = RotationCandidateEffectEvaluationService(
        obligation_service=RotationCandidateEffectObligationService(
            _FakeBaseRanker((
                ("second", RotationCandidateTier.ELIGIBLE),
                ("first", RotationCandidateTier.ELIGIBLE),
            ))
        )
    )

    ranked = service.evaluate_and_rank(
        build=_build(),
        candidates=(
            _input("first", 0.0),
            _input("second", 0.0),
        ),
    )

    assert [item.candidate_id for item in ranked] == ["second", "first"]
    assert all(item.ranking_result.effect_uptime_assessments == () for item in ranked)


def test_generated_and_ranking_candidate_ids_must_match() -> None:
    with pytest.raises(ValueError, match="same candidate_id"):
        RotationCandidateEffectEvaluationInput(
            generated_candidate=_candidate("generated", 0.0),
            ranking_input=_ranking_input("scorecard"),
        )


def test_duplicate_candidate_ids_fail_closed_before_evaluation() -> None:
    service = RotationCandidateEffectEvaluationService(
        obligation_service=RotationCandidateEffectObligationService(
            _FakeBaseRanker((("same", RotationCandidateTier.ELIGIBLE),))
        )
    )

    with pytest.raises(ValueError, match="duplicate rotation effect-evaluation candidate_id"):
        service.evaluate_and_rank(
            build=_build(),
            candidates=(
                _input("same", 0.0),
                _input("SAME", 0.0, 20.0),
            ),
            requirements=(_requirement(),),
        )
