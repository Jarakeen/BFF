from __future__ import annotations

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.support_target_type import SupportTargetType
from services.extreme_sustained_dps_runtime_effect_relevance_service import (
    ExtremeSustainedDPSRuntimeEffectRelevanceService,
)


def _effect(name: str, *, source: str = "Test", target_type=SupportTargetType.SELF):
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source=source,
        trigger="damage_dealt",
        duration=5.0,
        target_type=target_type,
    )


def test_weapon_spell_damage_is_dps_relevant() -> None:
    effect = _effect("weapon_spell_damage")
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == (effect,)
    assert result.irrelevant == ()
    assert result.unresolved == ()


def test_damage_shield_is_proven_irrelevant_to_sustained_dps() -> None:
    effect = _effect("damage_shield", source="Champion Point: From the Brink")
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == ()
    assert result.irrelevant == (effect,)
    assert result.unresolved == ()


def test_named_offensive_buff_is_relevant() -> None:
    effect = _effect("major_courage")
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == (effect,)
    assert result.unresolved == ()


def test_named_defensive_buff_is_irrelevant() -> None:
    effect = _effect("major_resolve")
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.irrelevant == (effect,)
    assert result.unresolved == ()


def test_unknown_runtime_identity_fails_closed() -> None:
    effect = _effect("mystery_runtime_power")
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == ()
    assert result.irrelevant == ()
    assert any("no reviewed sustained-DPS relevance disposition" in row for row in result.unresolved)


def test_enemy_target_vulnerability_is_dps_relevant() -> None:
    effect = _effect(
        "major_vulnerability",
        target_type=SupportTargetType.ENEMY,
    )
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == (effect,)
    assert result.irrelevant == ()
    assert result.unresolved == ()


def test_vulnerability_without_enemy_target_classification_fails_closed() -> None:
    effect = _effect(
        "major_vulnerability",
        target_type=SupportTargetType.SELF,
    )
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == ()
    assert result.irrelevant == ()
    assert any("requires canonical ENEMY target classification" in row for row in result.unresolved)


def test_enemy_target_breach_is_dps_relevant() -> None:
    effect = _effect(
        "major_breach",
        target_type=SupportTargetType.ENEMY,
    )
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == (effect,)
    assert result.irrelevant == ()
    assert result.unresolved == ()


def test_enemy_target_brittle_is_dps_relevant() -> None:
    effect = _effect(
        "minor_brittle",
        target_type=SupportTargetType.ENEMY,
    )
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == (effect,)
    assert result.irrelevant == ()
    assert result.unresolved == ()


def test_explicit_fixed_target_resistance_reduction_is_relevant() -> None:
    effect = EffectVariant(
        name="synthetic_resistance_debuff",
        layer=EffectLayer.PROC,
        source="Synthetic Debuff",
        trigger="damage_dealt",
        duration=5.0,
        target_type=SupportTargetType.ENEMY,
        resistance_reduction=1234.0,
    )
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == (effect,)
    assert result.unresolved == ()


def test_scaled_target_resistance_reduction_fails_closed() -> None:
    effect = EffectVariant(
        name="roar_of_alkosh",
        layer=EffectLayer.PROC,
        source="Roar of Alkosh (5)",
        trigger="synergy_activation",
        duration=10.0,
        target_type=SupportTargetType.ENEMY,
        resistance_reduction=6000.0,
        scaling="Weapon Damage, up to 6000 resistance reduction",
    )
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == ()
    assert any("unresolved scaling" in row for row in result.unresolved)


def test_explicit_fixed_target_damage_amplification_is_relevant() -> None:
    effect = EffectVariant(
        name="synthetic_damage_amplification",
        layer=EffectLayer.PROC,
        source="Synthetic Amplifier",
        trigger="damage_dealt",
        duration=5.0,
        target_type=SupportTargetType.ENEMY,
        damage_amplification=0.07,
    )
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == (effect,)
    assert result.unresolved == ()


def test_scaled_target_damage_amplification_fails_closed() -> None:
    effect = EffectVariant(
        name="synthetic_scaled_amplification",
        layer=EffectLayer.PROC,
        source="Synthetic Scaled Amplifier",
        trigger="damage_dealt",
        duration=5.0,
        target_type=SupportTargetType.ENEMY,
        damage_amplification=0.10,
        scaling="up to 10% based on unresolved runtime state",
    )
    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))
    assert result.relevant == ()
    assert any("unresolved scaling" in row for row in result.unresolved)


def test_unresolved_scaling_is_classified_as_source_data_gap() -> None:
    effect = EffectVariant(
        name="scaled_resistance_debuff",
        layer=EffectLayer.PROC,
        source="Scaled Debuff",
        trigger="damage_dealt",
        duration=5.0,
        target_type=SupportTargetType.ENEMY,
        resistance_reduction=6000.0,
        scaling="up to 6000 from unresolved source state",
    )

    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))

    assert result.source_data_unresolved == result.unresolved
    assert result.math_unresolved == ()
    assert any("source-data blockers: 1" in row for row in result.evidence)


def test_unknown_runtime_identity_is_classified_as_math_review_gap() -> None:
    effect = _effect("mystery_runtime_power", source="Mystery Proc")

    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))

    assert result.math_unresolved == result.unresolved
    assert result.source_data_unresolved == ()
    assert any("math/review blockers: 1" in row for row in result.evidence)


def test_missing_enemy_target_classification_is_source_data_gap() -> None:
    effect = _effect(
        "major_vulnerability",
        source="Targeting Mystery",
        target_type=SupportTargetType.SELF,
    )

    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))

    assert result.source_data_unresolved == result.unresolved
    assert result.math_unresolved == ()


def test_unresolved_master_architect_duration_scaling_is_source_gap() -> None:
    effect = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Master Architect (5)",
        magnitude=10.0,
        duration=1.0,
        scaling="1 second per 10 Ultimate spent",
        trigger="ultimate_activation_in_combat",
        target_type=SupportTargetType.GROUP,
    )

    result = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify((effect,))

    assert result.relevant == ()
    assert result.math_unresolved == ()
    assert result.source_data_unresolved == result.unresolved
    assert any(
        "requires canonical Ultimate spend resolution" in row
        for row in result.unresolved
    )
