from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearSlot
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_candidate_temporal_effect_service import (
    RotationCandidateTemporalEffectResult,
)
from services.rotation_candidate_temporal_legality_service import (
    RotationCandidateTemporalLegalityInput,
    RotationCandidateTemporalLegalityService,
)
from services.rotation_temporal_effect_uptime_service import (
    RotationTemporalEffectApplication,
)


@dataclass(frozen=True)
class _Generated:
    plan: RotationPlan


@dataclass(frozen=True)
class _EffectResult:
    candidate_id: str
    generated_candidate: _Generated


def _build() -> CharacterBuild:
    proc = EffectVariant(
        name="major_courage",
        layer=EffectLayer.PROC,
        source="Support Proc Set",
        duration=10.0,
        cooldown=20.0,
        category=SupportEffectCategory.BUFF,
        target_type=SupportTargetType.GROUP,
    )
    return CharacterBuild(
        name="Temporal Legality Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(WeaponType.FROST_STAFF),
            off_hand=None,
            slots=(),
        ),
        back_bar=Bar(
            bar_id=BarId.BACK,
            main_hand=Weapon(WeaponType.FROST_STAFF),
            off_hand=None,
            slots=(),
        ),
        armor=(ArmorPiece(slot=GearSlot.CHEST, effects=(proc,)),),
    )


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Temporal Legality Build",
        duration_seconds=40.0,
        actions=tuple(actions),
    )


def _upstream(candidate_id: str, plan: RotationPlan, *, eligible: bool = True, rank: int = 1):
    return RotationCandidateTemporalEffectResult(
        effect_result=_EffectResult(candidate_id, _Generated(plan)),
        temporal_assessments=(),
        tier=(RotationCandidateTier.ELIGIBLE if eligible else RotationCandidateTier.INELIGIBLE),
        rank=rank,
        reasons=(f"upstream {candidate_id}",),
    )


def _app(time: float, *, bar: str = "front") -> RotationTemporalEffectApplication:
    return RotationTemporalEffectApplication(
        time_seconds=time,
        effect_name="major_courage",
        layer=EffectLayer.PROC,
        source="Support Proc Set",
        bar=bar,
    )


def test_illegal_cooldown_makes_otherwise_eligible_candidate_ineligible() -> None:
    service = RotationCandidateTemporalLegalityService()
    plan = _plan()

    ranked = service.evaluate_and_rank(
        build=_build(),
        candidates=(
            RotationCandidateTemporalLegalityInput(
                temporal_result=_upstream("illegal", plan, rank=1),
                applications=(_app(0.0), _app(10.0)),
                initial_bar="front",
            ),
            RotationCandidateTemporalLegalityInput(
                temporal_result=_upstream("legal", plan, rank=2),
                applications=(_app(0.0), _app(20.0)),
                initial_bar="front",
            ),
        ),
    )

    assert [item.candidate_id for item in ranked] == ["legal", "illegal"]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("inside the canonical 20.000s cooldown" in reason for reason in ranked[1].reasons)


def test_wrong_plan_bar_is_hard_legality_failure() -> None:
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
    )
    ranked = RotationCandidateTemporalLegalityService().evaluate_and_rank(
        build=_build(),
        candidates=(
            RotationCandidateTemporalLegalityInput(
                temporal_result=_upstream("candidate", plan),
                applications=(_app(10.0, bar="front"),),
                initial_bar="front",
            ),
        ),
    )

    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert ranked[0].effect_legality.is_legal is True
    assert ranked[0].plan_legality.is_legal is False
    assert any("plan has back bar active" in reason for reason in ranked[0].reasons)


def test_upstream_failure_remains_ineligible_when_temporal_legality_passes() -> None:
    ranked = RotationCandidateTemporalLegalityService().evaluate_and_rank(
        build=_build(),
        candidates=(
            RotationCandidateTemporalLegalityInput(
                temporal_result=_upstream("candidate", _plan(), eligible=False),
                applications=(_app(0.0), _app(20.0)),
                initial_bar="front",
            ),
        ),
    )

    assert ranked[0].effect_legality.is_legal is True
    assert ranked[0].plan_legality.is_legal is True
    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE


def test_same_timestamp_swap_unresolved_fails_closed() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
    )
    ranked = RotationCandidateTemporalLegalityService().evaluate_and_rank(
        build=_build(),
        candidates=(
            RotationCandidateTemporalLegalityInput(
                temporal_result=_upstream("candidate", plan),
                applications=(_app(10.0, bar="back"),),
                initial_bar="front",
            ),
        ),
    )

    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert ranked[0].plan_legality.violations == ()
    assert ranked[0].plan_legality.unresolved


def test_duplicate_candidate_ids_fail_closed() -> None:
    service = RotationCandidateTemporalLegalityService()
    plan = _plan()
    candidate = RotationCandidateTemporalLegalityInput(
        temporal_result=_upstream("same", plan),
        applications=(),
        initial_bar="front",
    )

    try:
        service.evaluate_and_rank(
            build=_build(),
            candidates=(candidate, candidate),
        )
    except ValueError as exc:
        assert "duplicate rotation temporal-legality candidate_id" in str(exc)
    else:
        raise AssertionError("duplicate candidate IDs must fail closed")
