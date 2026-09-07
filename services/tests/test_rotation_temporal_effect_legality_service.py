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
from services.rotation_temporal_effect_legality_service import (
    RotationTemporalEffectLegalityService,
)
from services.rotation_temporal_effect_uptime_service import (
    RotationTemporalEffectApplication,
)


def _proc_effect(*, cooldown: float | None = 20.0) -> EffectVariant:
    return EffectVariant(
        name="proc_buff",
        layer=EffectLayer.PROC,
        source="Cooldown Set",
        duration=10.0,
        cooldown=cooldown,
        category=SupportEffectCategory.BUFF,
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


def _build(*, proc_cooldown: float | None = 20.0) -> CharacterBuild:
    fillers = tuple(
        SlottedSkill(
            skill_id=f"filler_{index}",
            skill_line_id="winters_embrace",
        )
        for index in range(5)
    )
    horn = SlottedSkill(
        skill_id="aggressive_horn",
        skill_line_id="assault",
        is_cast=True,
        is_ultimate=True,
        effects=(_ultimate_effect(),),
    )
    return CharacterBuild(
        name="Temporal Legality Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(WeaponType.FROST_STAFF),
            off_hand=None,
            slots=fillers + (horn,),
        ),
        armor=(
            ArmorPiece(
                slot=GearSlot.CHEST,
                effects=(_proc_effect(cooldown=proc_cooldown),),
            ),
        ),
    )


def _proc_application(time_seconds: float) -> RotationTemporalEffectApplication:
    return RotationTemporalEffectApplication(
        time_seconds=time_seconds,
        effect_name="proc_buff",
        layer=EffectLayer.PROC,
        source="Cooldown Set",
        bar="front",
    )


def test_proc_activations_at_or_after_canonical_cooldown_are_legal() -> None:
    assessment = RotationTemporalEffectLegalityService().assess(
        build=_build(),
        applications=(
            _proc_application(0.0),
            _proc_application(20.0),
            _proc_application(40.0),
        ),
    )

    assert assessment.unresolved == ()
    assert assessment.violations == ()
    assert assessment.is_legal is True


def test_proc_activation_inside_canonical_cooldown_is_illegal() -> None:
    assessment = RotationTemporalEffectLegalityService().assess(
        build=_build(),
        applications=(
            _proc_application(0.0),
            _proc_application(8.0),
        ),
    )

    assert assessment.unresolved == ()
    assert assessment.is_legal is False
    assert len(assessment.violations) == 1
    assert assessment.violations[0].time_seconds == pytest.approx(8.0)
    assert "8.000s after the prior activation" in assessment.violations[0].reason
    assert "20.000s cooldown" in assessment.violations[0].reason


def test_effect_without_canonical_cooldown_has_no_spacing_constraint() -> None:
    assessment = RotationTemporalEffectLegalityService().assess(
        build=_build(proc_cooldown=None),
        applications=(
            _proc_application(0.0),
            _proc_application(1.0),
        ),
    )

    assert assessment.unresolved == ()
    assert assessment.violations == ()
    assert assessment.is_legal is True


def test_wrong_ultimate_trigger_stays_unresolved() -> None:
    application = RotationTemporalEffectApplication(
        time_seconds=5.0,
        effect_name="major_force",
        layer=EffectLayer.ULTIMATE,
        source="Aggressive Horn",
        bar="front",
        trigger="wrong_trigger",
    )

    assessment = RotationTemporalEffectLegalityService().assess(
        build=_build(),
        applications=(application,),
    )

    assert assessment.is_legal is False
    assert assessment.violations == ()
    assert len(assessment.unresolved) == 1
    assert "no exact ultimate effect" in assessment.unresolved[0]


def test_invalid_canonical_cooldown_stays_unresolved() -> None:
    assessment = RotationTemporalEffectLegalityService().assess(
        build=_build(proc_cooldown=float("nan")),
        applications=(_proc_application(0.0),),
    )

    assert assessment.is_legal is False
    assert assessment.violations == ()
    assert any("canonical cooldown is invalid" in item for item in assessment.unresolved)


def test_duplicate_claimed_activation_fails_closed() -> None:
    application = _proc_application(10.0)

    with pytest.raises(ValueError, match="duplicate rotation temporal effect application"):
        RotationTemporalEffectLegalityService().assess(
            build=_build(),
            applications=(application, application),
        )
