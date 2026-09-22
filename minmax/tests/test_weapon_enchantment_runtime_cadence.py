from __future__ import annotations

import pytest

from minmax.weapon_enchantment_runtime_cadence import (
    WeaponEnchantmentCadenceAuthority,
    WeaponEnchantmentEffectFamily,
    provisional_weapon_enchantment_cadence,
)


def test_damage_cadence_is_research_evidence_not_runtime_authority() -> None:
    evidence = provisional_weapon_enchantment_cadence(
        WeaponEnchantmentEffectFamily.DIRECT_DAMAGE
    )

    assert evidence.base_cooldown_seconds == 4.0
    assert evidence.authority is WeaponEnchantmentCadenceAuthority.PROVISIONAL
    assert evidence.activation_causes == (
        "light_attack",
        "heavy_attack",
        "weapon_ability",
    )
    assert evidence.off_bar_source_persists is True
    assert evidence.cooldown_scope == "per_effect_identity"\n    assert evidence.poison_replaces_enchantment is True\n    assert evidence.same_effect_identity_shares_cooldown is True
    assert evidence.runtime_ready is False

    with pytest.raises(ValueError, match="not authoritative"):
        evidence.require_runtime_ready()


def test_buff_debuff_cooldown_observation_remains_provisional() -> None:
    evidence = provisional_weapon_enchantment_cadence(
        WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF
    )

    assert evidence.base_cooldown_seconds == 10.0
    assert evidence.runtime_ready is False
