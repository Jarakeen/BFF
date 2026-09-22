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
