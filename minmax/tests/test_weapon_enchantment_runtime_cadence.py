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
    assert evidence.cooldown_authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
    assert "ZOS Update 21 patch notes" in evidence.cooldown_evidence_note
    assert evidence.activation_causes == (
        "light_attack_damage",
        "heavy_attack_damage",
        "weapon_ability_damage",
    )
    assert evidence.activation_authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
    assert "ZOS Update 20 patch notes" in evidence.activation_evidence_note
    assert evidence.off_bar_source_persists is True
    assert evidence.cooldown_scope == "per_effect_identity"
    assert evidence.poison_replaces_enchantment is True
    assert evidence.poison_replacement_authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
    assert "temporarily suppresses weapon enchantments" in evidence.poison_replacement_evidence_note
    assert evidence.same_effect_identity_shares_cooldown is True
    assert evidence.distinct_effect_identities_have_independent_cooldowns is True
    assert evidence.runtime_ready is False

    with pytest.raises(ValueError, match="not authoritative"):
        evidence.require_runtime_ready()


def test_buff_debuff_cooldown_observation_remains_provisional() -> None:
    evidence = provisional_weapon_enchantment_cadence(
        WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF
    )

    assert evidence.base_cooldown_seconds == 10.0
    assert evidence.cooldown_authority is WeaponEnchantmentCadenceAuthority.PROVISIONAL
    assert evidence.poison_replacement_authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
    assert evidence.runtime_ready is False


def test_authoritative_activation_topology_does_not_promote_open_cooldown_math() -> None:
    evidence = provisional_weapon_enchantment_cadence(
        WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF
    )

    assert evidence.activation_authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
    assert evidence.authority is WeaponEnchantmentCadenceAuthority.PROVISIONAL
    assert evidence.runtime_ready is False


def test_field_level_authority_preserves_remaining_runtime_blockers() -> None:
    evidence = provisional_weapon_enchantment_cadence(
        WeaponEnchantmentEffectFamily.DIRECT_DAMAGE
    )

    assert evidence.activation_authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
    assert evidence.cooldown_authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
    assert evidence.poison_replacement_authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
    assert evidence.off_bar_authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
    assert evidence.cooldown_scope_authority is WeaponEnchantmentCadenceAuthority.PROVISIONAL
    assert evidence.same_identity_cooldown_authority is WeaponEnchantmentCadenceAuthority.PROVISIONAL
    assert evidence.distinct_identity_cooldown_authority is WeaponEnchantmentCadenceAuthority.PROVISIONAL
    assert evidence.runtime_ready is False


def test_direct_damage_cadence_names_only_remaining_proof_holes() -> None:
    evidence = provisional_weapon_enchantment_cadence(
        WeaponEnchantmentEffectFamily.DIRECT_DAMAGE
    )

    assert evidence.runtime_blockers == (
        "cooldown scope is not authoritative",
        "same-identity cooldown sharing is not authoritative",
        "distinct-identity cooldown independence is not authoritative",
        "effect-family cadence has not been promoted to authoritative",
    )


def test_buff_debuff_cadence_also_names_open_base_cooldown() -> None:
    evidence = provisional_weapon_enchantment_cadence(
        WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF
    )

    assert evidence.runtime_blockers == (
        "base cooldown is not authoritative",
        "cooldown scope is not authoritative",
        "same-identity cooldown sharing is not authoritative",
        "distinct-identity cooldown independence is not authoritative",
        "effect-family cadence has not been promoted to authoritative",
    )


def test_runtime_ready_error_lists_exact_cadence_blockers() -> None:
    import pytest

    evidence = provisional_weapon_enchantment_cadence(
        WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF
    )

    with pytest.raises(ValueError) as exc_info:
        evidence.require_runtime_ready()

    message = str(exc_info.value)
    assert "base cooldown is not authoritative" in message
    assert "same-identity cooldown sharing is not authoritative" in message
    assert "distinct-identity cooldown independence is not authoritative" in message
