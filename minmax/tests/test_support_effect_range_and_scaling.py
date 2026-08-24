"""
Focused tests proving EffectVariant.range and EffectVariant.scaling
survive effect_variant_to_support_effect() into SupportEffect, without
evaluating the scaling formula and without changing the meaning of
duration (which remains the base duration).

This targets one specific information-loss bug: range and scaling were
already present on EffectVariant and already present on SupportEffect's
sibling fields conceptually, but effect_variant_to_support_effect() did
not thread them through, so a resolved SupportEffect silently lost both
values. No new model was introduced to fix this - both fields were added
directly to the existing SupportEffect dataclass.
"""

from __future__ import annotations

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.support_effect_resolver import (
    effect_variant_to_support_effect,
)
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType


def test_range_and_scaling_survive_conversion() -> None:
    variant = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Master Architect (5)",
        magnitude=10.0,
        duration=1.0,
        target_count=5,
        range=28.0,
        scaling="1 second per 10 Ultimate spent",
        trigger="ultimate_activation_in_combat",
        target_type=SupportTargetType.GROUP,
    )

    support_effect = effect_variant_to_support_effect(variant)

    assert support_effect.range == 28.0
    assert support_effect.scaling == "1 second per 10 Ultimate spent"


def test_scaling_string_is_preserved_exactly_not_evaluated() -> None:
    """
    The scaling string must survive character-for-character. Nothing in
    the conversion path is allowed to interpret, truncate, or compute a
    result from it.
    """
    variant = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Master Architect (5)",
        scaling="1 second per 10 Ultimate spent",
    )

    support_effect = effect_variant_to_support_effect(variant)

    assert support_effect.scaling == "1 second per 10 Ultimate spent"
    assert isinstance(support_effect.scaling, str)


def test_duration_still_means_base_duration_not_a_scaled_value() -> None:
    """
    duration=1.0 must remain the BASE duration after conversion - adding
    `scaling` must not change what `duration` means or its value.
    """
    variant = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Master Architect (5)",
        duration=1.0,
        scaling="1 second per 10 Ultimate spent",
    )

    support_effect = effect_variant_to_support_effect(variant)

    assert support_effect.duration == 1.0


def test_range_defaults_to_none_when_not_set_on_variant() -> None:
    variant = EffectVariant(
        name="major_courage",
        layer=EffectLayer.PROC,
        source="Some Skill",
    )

    support_effect = effect_variant_to_support_effect(variant)

    assert support_effect.range is None


def test_scaling_defaults_to_none_when_not_set_on_variant() -> None:
    variant = EffectVariant(
        name="major_courage",
        layer=EffectLayer.PROC,
        source="Some Skill",
    )

    support_effect = effect_variant_to_support_effect(variant)

    assert support_effect.scaling is None


def test_support_effect_accepts_range_and_scaling_directly() -> None:
    """
    SupportEffect itself (independent of the conversion function) must
    accept both fields - this is the smallest compatible change: two new
    optional fields on the existing dataclass, not a new model.
    """
    support_effect = SupportEffect(
        source="Master Architect (5)",
        name="major_slayer",
        category=SupportEffectCategory.BUFF,
        effect_type="major_slayer",
        target_type=SupportTargetType.GROUP,
        magnitude=10.0,
        target_count=5,
        range=28.0,
        duration=1.0,
        scaling="1 second per 10 Ultimate spent",
    )

    assert support_effect.range == 28.0
    assert support_effect.scaling == "1 second per 10 Ultimate spent"
    assert support_effect.duration == 1.0


def test_master_architect_bridge_output_preserves_range_and_scaling() -> None:
    """
    End-to-end with the actual Master Architect EffectVariant shape
    established by the gear-set bridge: range=28.0 and
    scaling="1 second per 10 Ultimate spent" must both come through
    unchanged, alongside the other already-preserved fields.
    """
    master_architect_variant = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Master Architect (5)",
        magnitude=10.0,
        duration=1.0,
        target_count=5,
        range=28.0,
        scaling="1 second per 10 Ultimate spent",
        trigger="ultimate_activation_in_combat",
        target_type=SupportTargetType.GROUP,
    )

    support_effect = effect_variant_to_support_effect(master_architect_variant)

    assert support_effect.name == "major_slayer"
    assert support_effect.magnitude == 10.0
    assert support_effect.target_type == SupportTargetType.GROUP
    assert support_effect.target_count == 5
    assert support_effect.range == 28.0
    assert support_effect.duration == 1.0
    assert support_effect.scaling == "1 second per 10 Ultimate spent"
    assert support_effect.trigger is not None
    assert support_effect.trigger.trigger == "ultimate_activation_in_combat"
