import pytest

from minmax.character_build.effect_duration_resolver import EffectDurationResolver
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.gear_set_known_effects import known_effects_for_bonus_row
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType


def _effect(name: str, *, duration: float, category: SupportEffectCategory) -> EffectVariant:
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source="test source",
        duration=duration,
        category=category,
        target_type=SupportTargetType.GROUP,
    )


def _jorvuld() -> EffectVariant:
    known = known_effects_for_bonus_row(
        bonus_id=-1,
        set_id=-1,
        set_name="Jorvuld's Guidance",
        piece_count=5,
    )
    assert len(known) == 1
    row = known[0]
    return EffectVariant(
        name=row.name,
        layer=row.layer,
        source="Jorvuld's Guidance (5)",
        magnitude=row.magnitude,
        scaling=row.scaling,
        condition=row.condition,
        target_type=row.target_type,
        category=row.category,
        stacking=row.stacking,
        exclusivity_group=row.exclusivity_group,
    )


def test_jorvulds_known_effect_preserves_u50_five_piece_semantics() -> None:
    modifier = _jorvuld()

    assert modifier.name == "major_minor_buff_duration_increase"
    assert modifier.layer is EffectLayer.PASSIVE
    assert modifier.magnitude == pytest.approx(0.40)
    assert modifier.target_type is SupportTargetType.SELF_OR_ALLY
    assert modifier.category is SupportEffectCategory.OTHER
    assert "40%" in (modifier.scaling or "")
    assert modifier.condition == "in_combat"


def test_jorvulds_extends_roaring_major_slayer_from_12_to_16_point_8_seconds() -> None:
    major_slayer = _effect(
        "major_slayer",
        duration=12.0,
        category=SupportEffectCategory.BUFF,
    )

    resolved = EffectDurationResolver().resolve(
        major_slayer,
        available_effects=(_jorvuld(),),
    )

    assert resolved.base_duration_seconds == pytest.approx(12.0)
    assert resolved.effective_duration_seconds == pytest.approx(16.8)
    assert resolved.unresolved == ()
    assert len(resolved.applied_modifiers) == 1
    assert resolved.applied_modifiers[0].seconds == pytest.approx(4.8)
    assert resolved.applied_modifiers[0].source == "Jorvuld's Guidance (5)"


def test_jorvulds_extends_minor_buff_by_same_percentage() -> None:
    minor_courage = _effect(
        "minor_courage",
        duration=10.0,
        category=SupportEffectCategory.BUFF,
    )

    resolved = EffectDurationResolver().resolve(
        minor_courage,
        available_effects=(_jorvuld(),),
    )

    assert resolved.effective_duration_seconds == pytest.approx(14.0)


def test_jorvulds_does_not_extend_major_enemy_debuff() -> None:
    major_breach = _effect(
        "major_breach",
        duration=20.0,
        category=SupportEffectCategory.DEBUFF,
    )

    resolved = EffectDurationResolver().resolve(
        major_breach,
        available_effects=(_jorvuld(),),
    )

    assert resolved.effective_duration_seconds == pytest.approx(20.0)
    assert resolved.applied_modifiers == ()


def test_jorvulds_does_not_extend_non_major_minor_buff() -> None:
    generic_buff = _effect(
        "weapon_spell_damage",
        duration=10.0,
        category=SupportEffectCategory.BUFF,
    )

    resolved = EffectDurationResolver().resolve(
        generic_buff,
        available_effects=(_jorvuld(),),
    )

    assert resolved.effective_duration_seconds == pytest.approx(10.0)
    assert resolved.applied_modifiers == ()
