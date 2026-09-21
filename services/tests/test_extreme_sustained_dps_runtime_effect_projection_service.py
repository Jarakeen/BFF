from __future__ import annotations

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.stat_ids import StatId
from minmax.support_target_type import SupportTargetType
from services.extreme_sustained_dps_runtime_effect_projection_service import (
    ExtremeSustainedDPSRuntimeEffectProjectionService,
)


def _variant(name, magnitude=460.0):
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source="Armor of Truth (5)",
        magnitude=magnitude,
        duration=10.0,
        trigger="damage_off_balance_target",
        target_type=SupportTargetType.SELF,
    )


def test_weapon_spell_damage_projects_to_both_canonical_power_stats() -> None:
    result = ExtremeSustainedDPSRuntimeEffectProjectionService.project(
        (_variant("weapon_spell_damage"),)
    )

    assert result.resolved is True
    assert result.projected_variant_count == 1
    assert tuple(effect.stat for effect in result.effects) == (
        StatId.WEAPON_DAMAGE,
        StatId.SPELL_DAMAGE,
    )
    assert tuple(effect.value for effect in result.effects) == (460.0, 460.0)


def test_unknown_runtime_effect_fails_closed() -> None:
    result = ExtremeSustainedDPSRuntimeEffectProjectionService.project(
        (_variant("mysterious_runtime_effect"),)
    )

    assert result.effects == ()
    assert result.resolved is False
    assert any("no reviewed stat projection" in row for row in result.unresolved)


def test_missing_runtime_magnitude_fails_closed() -> None:
    result = ExtremeSustainedDPSRuntimeEffectProjectionService.project(
        (_variant("weapon_spell_damage", magnitude=None),)
    )

    assert result.effects == ()
    assert result.resolved is False
    assert any("no canonical magnitude" in row for row in result.unresolved)
