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
from services.rotation_effect_uptime_service import (
    RotationEffectUptimeRequirement,
    RotationEffectUptimeService,
)


def _status_effect(*, layer: EffectLayer = EffectLayer.CAST) -> EffectVariant:
    return EffectVariant(
        name="chilled",
        layer=layer,
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


def _build(*, with_modifier: bool = True, effect: EffectVariant | None = None) -> CharacterBuild:
    winter = SlottedSkill(
        skill_id="winters_revenge",
        skill_line_id="winters_embrace",
        is_cast=True,
        effects=((effect or _status_effect()),),
    )
    front_bar = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(WeaponType.FROST_STAFF),
        off_hand=None,
        slots=(winter,),
    )
    armor = (
        ArmorPiece(
            slot=GearSlot.CHEST,
            effects=(_modifier(),),
        ),
    ) if with_modifier else ()
    return CharacterBuild(
        name="Effect Uptime Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=front_bar,
        armor=armor,
    )


def _plan(*, casts=(0.0, 20.0), explicit_bar: bool = True) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Effect Uptime Build",
        duration_seconds=40.0,
        actions=tuple(
            RotationAction(
                time_seconds=time,
                sequence=index,
                kind=RotationActionKind.SKILL,
                name="Winter's Revenge",
                bar="front" if explicit_bar else None,
            )
            for index, time in enumerate(casts)
        ),
    )


def _requirement(minimum: float = 0.9) -> RotationEffectUptimeRequirement:
    return RotationEffectUptimeRequirement(
        effect_name="chilled",
        source_skill_name="Winter's Revenge",
        bar="front",
        minimum_uptime=minimum,
    )


def test_serpents_disdain_changes_effect_uptime_not_cast_count() -> None:
    assessment = RotationEffectUptimeService().assess(
        plan=_plan(),
        build=_build(with_modifier=True),
        requirements=(_requirement(),),
    )[0]

    assert assessment.unresolved == ()
    assert assessment.summary is not None
    assert assessment.summary.base_duration_seconds == pytest.approx(4.0)
    assert assessment.summary.effective_duration_seconds == pytest.approx(20.0)
    assert assessment.summary.cast_count == 2
    assert assessment.summary.active_seconds == pytest.approx(40.0)
    assert assessment.summary.uptime_fraction == pytest.approx(1.0)
    assert assessment.summary.applied_modifier_sources == ("Serpent's Disdain (5)",)
    assert assessment.satisfied is True


def test_same_cast_schedule_has_lower_effect_uptime_without_modifier() -> None:
    assessment = RotationEffectUptimeService().assess(
        plan=_plan(),
        build=_build(with_modifier=False),
        requirements=(_requirement(),),
    )[0]

    assert assessment.summary is not None
    assert assessment.summary.cast_count == 2
    assert assessment.summary.effective_duration_seconds == pytest.approx(4.0)
    assert assessment.summary.active_seconds == pytest.approx(8.0)
    assert assessment.summary.uptime_fraction == pytest.approx(0.2)
    assert assessment.shortfall == pytest.approx(0.7)
    assert assessment.satisfied is False


def test_no_casts_is_known_zero_coverage_not_missing_evidence() -> None:
    assessment = RotationEffectUptimeService().assess(
        plan=_plan(casts=()),
        build=_build(),
        requirements=(_requirement(),),
    )[0]

    assert assessment.unresolved == ()
    assert assessment.summary is not None
    assert assessment.summary.cast_count == 0
    assert assessment.observed_uptime == pytest.approx(0.0)
    assert assessment.satisfied is False


def test_missing_source_skill_stays_unresolved() -> None:
    requirement = RotationEffectUptimeRequirement(
        effect_name="chilled",
        source_skill_name="Deep Fissure",
        bar="front",
        minimum_uptime=0.5,
    )
    assessment = RotationEffectUptimeService().assess(
        plan=_plan(),
        build=_build(),
        requirements=(requirement,),
    )[0]

    assert assessment.summary is None
    assert assessment.observed_uptime is None
    assert assessment.satisfied is False
    assert "not slotted" in assessment.unresolved[0]


def test_proc_effect_is_not_inferred_from_skill_casts() -> None:
    assessment = RotationEffectUptimeService().assess(
        plan=_plan(),
        build=_build(effect=_status_effect(layer=EffectLayer.PROC)),
        requirements=(_requirement(),),
    )[0]

    assert assessment.summary is None
    assert assessment.observed_uptime is None
    assert "not a verified cast-produced effect" in assessment.unresolved[0]


def test_scheduled_casts_need_explicit_bar_evidence() -> None:
    assessment = RotationEffectUptimeService().assess(
        plan=_plan(explicit_bar=False),
        build=_build(),
        requirements=(_requirement(),),
    )[0]

    assert assessment.summary is None
    assert assessment.observed_uptime is None
    assert assessment.unresolved == (
        "scheduled casts of \"Winter's Revenge\" need explicit bar evidence",
    )


def test_duplicate_effect_uptime_requirement_fails_closed() -> None:
    requirement = _requirement()
    with pytest.raises(ValueError, match="duplicate rotation effect uptime requirement"):
        RotationEffectUptimeService().assess(
            plan=_plan(),
            build=_build(),
            requirements=(requirement, requirement),
        )
