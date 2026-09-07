from __future__ import annotations

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
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from services.rotation_temporal_effect_uptime_service import (
    RotationTemporalEffectApplication,
    RotationTemporalEffectRequirement,
    RotationTemporalEffectUptimeService,
)


def _proc_effect() -> EffectVariant:
    return EffectVariant(
        name="chilled",
        layer=EffectLayer.PROC,
        source="Frost Proc Set",
        duration=4.0,
        category=SupportEffectCategory.STATUS,
        target_type=SupportTargetType.ENEMY,
    )


def _duration_modifier() -> EffectVariant:
    return EffectVariant(
        name="status_effect_duration_increase",
        layer=EffectLayer.PASSIVE,
        source="Serpent's Disdain (5)",
        magnitude=16.0,
        category=SupportEffectCategory.OTHER,
        target_type=SupportTargetType.SELF,
    )


def _ultimate_effect() -> EffectVariant:
    return EffectVariant(
        name="major_force",
        layer=EffectLayer.ULTIMATE,
        source="Aggressive Horn",
        duration=10.0,
        trigger="horn_cast",
        category=SupportEffectCategory.BUFF,
        target_type=SupportTargetType.GROUP,
    )


def _build() -> CharacterBuild:
    filler = tuple(
        SlottedSkill(
            skill_id=f"filler_{index}",
            skill_line_id="winters_embrace",
        )
        for index in range(5)
    )
    ultimate = SlottedSkill(
        skill_id="aggressive_horn",
        skill_line_id="assault",
        is_cast=True,
        is_ultimate=True,
        effects=(_ultimate_effect(),),
    )
    front_bar = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(WeaponType.FROST_STAFF),
        off_hand=None,
        slots=filler + (ultimate,),
    )
    armor = (
        ArmorPiece(
            slot=GearSlot.CHEST,
            effects=(_proc_effect(), _duration_modifier()),
        ),
    )
    return CharacterBuild(
        name="Temporal Effect Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=front_bar,
        armor=armor,
    )


def test_explicit_proc_applications_use_build_effective_duration() -> None:
    requirement = RotationTemporalEffectRequirement(
        effect_name="chilled",
        layer=EffectLayer.PROC,
        minimum_uptime=0.90,
        source="Frost Proc Set",
    )
    applications = (
        RotationTemporalEffectApplication(
            time_seconds=0.0,
            effect_name="chilled",
            layer=EffectLayer.PROC,
            source="Frost Proc Set",
            bar="front",
        ),
        RotationTemporalEffectApplication(
            time_seconds=20.0,
            effect_name="chilled",
            layer=EffectLayer.PROC,
            source="Frost Proc Set",
            bar="front",
        ),
    )

    assessment = RotationTemporalEffectUptimeService().assess(
        duration_seconds=40.0,
        build=_build(),
        requirements=(requirement,),
        applications=applications,
    )[0]

    assert assessment.unresolved == ()
    assert assessment.summary is not None
    assert assessment.summary.application_count == 2
    assert assessment.summary.effective_durations == pytest.approx((20.0, 20.0))
    assert assessment.summary.active_seconds == pytest.approx(40.0)
    assert assessment.summary.uptime_fraction == pytest.approx(1.0)
    assert assessment.summary.applied_modifier_sources == ("Serpent's Disdain (5)",)
    assert assessment.satisfied is True


def test_no_proc_application_is_known_zero_not_assumed_from_cooldown_or_availability() -> None:
    requirement = RotationTemporalEffectRequirement(
        effect_name="chilled",
        layer=EffectLayer.PROC,
        minimum_uptime=0.50,
        source="Frost Proc Set",
    )

    assessment = RotationTemporalEffectUptimeService().assess(
        duration_seconds=40.0,
        build=_build(),
        requirements=(requirement,),
        applications=(),
    )[0]

    assert assessment.summary is not None
    assert assessment.summary.application_count == 0
    assert assessment.observed_uptime == pytest.approx(0.0)
    assert assessment.shortfall == pytest.approx(0.50)
    assert assessment.satisfied is False


def test_ultimate_application_requires_matching_trigger_and_bar_evidence() -> None:
    requirement = RotationTemporalEffectRequirement(
        effect_name="major_force",
        layer=EffectLayer.ULTIMATE,
        minimum_uptime=0.25,
        source="Aggressive Horn",
    )
    application = RotationTemporalEffectApplication(
        time_seconds=5.0,
        effect_name="major_force",
        layer=EffectLayer.ULTIMATE,
        source="Aggressive Horn",
        bar="front",
        trigger="horn_cast",
    )

    assessment = RotationTemporalEffectUptimeService().assess(
        duration_seconds=40.0,
        build=_build(),
        requirements=(requirement,),
        applications=(application,),
    )[0]

    assert assessment.summary is not None
    assert assessment.summary.application_count == 1
    assert assessment.summary.active_seconds == pytest.approx(10.0)
    assert assessment.summary.uptime_fraction == pytest.approx(0.25)
    assert assessment.satisfied is True


def test_wrong_ultimate_trigger_stays_unresolved_instead_of_zero() -> None:
    requirement = RotationTemporalEffectRequirement(
        effect_name="major_force",
        layer=EffectLayer.ULTIMATE,
        minimum_uptime=0.25,
        source="Aggressive Horn",
    )
    application = RotationTemporalEffectApplication(
        time_seconds=5.0,
        effect_name="major_force",
        layer=EffectLayer.ULTIMATE,
        source="Aggressive Horn",
        bar="front",
        trigger="wrong_trigger",
    )

    assessment = RotationTemporalEffectUptimeService().assess(
        duration_seconds=40.0,
        build=_build(),
        requirements=(requirement,),
        applications=(application,),
    )[0]

    assert assessment.summary is None
    assert assessment.observed_uptime is None
    assert assessment.satisfied is False
    assert "no exact ultimate effect" in assessment.unresolved[0]


def test_duplicate_temporal_requirement_fails_closed() -> None:
    requirement = RotationTemporalEffectRequirement(
        effect_name="chilled",
        layer=EffectLayer.PROC,
        minimum_uptime=0.50,
        source="Frost Proc Set",
    )

    with pytest.raises(ValueError, match="duplicate rotation temporal effect requirement"):
        RotationTemporalEffectUptimeService().assess(
            duration_seconds=40.0,
            build=_build(),
            requirements=(requirement, requirement),
        )


def test_cast_layer_is_rejected_from_temporal_activation_service() -> None:
    with pytest.raises(ValueError, match="only supports proc, ultimate, or consumable"):
        RotationTemporalEffectRequirement(
            effect_name="chilled",
            layer=EffectLayer.CAST,
            minimum_uptime=0.50,
            source="Winter's Revenge",
        )
