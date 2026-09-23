from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.support_effect_category import SupportEffectCategory
from minmax.weapon_enchantment_runtime_cadence import (
    WeaponEnchantmentCadenceAuthority,
    WeaponEnchantmentCadenceEvidence,
    WeaponEnchantmentEffectFamily,
)
from services.extreme_sustained_dps_weapon_enchantment_cooldown_policy_resolver import (
    ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver,
)


def _effect(
    *,
    name="crusher",
    source="Glyph of Crushing",
    category=SupportEffectCategory.DEBUFF,
):
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source=source,
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        trigger="weapon_enchantment_activation",
        category=category,
    )


def _authoritative_cadence(
    family=WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF,
    cooldown=10.0,
):
    authority = WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
    return WeaponEnchantmentCadenceEvidence(
        family=family,
        base_cooldown_seconds=cooldown,
        authority=authority,
        cooldown_authority=authority,
        cooldown_evidence_note="reviewed cooldown evidence",
        activation_causes=(
            "light_attack_damage",
            "heavy_attack_damage",
            "weapon_ability_damage",
        ),
        activation_authority=authority,
        activation_evidence_note="reviewed activation evidence",
        off_bar_source_persists=True,
        off_bar_authority=authority,
        off_bar_evidence_note="reviewed source-persistence evidence",
        cooldown_scope="per_effect_identity",
        cooldown_scope_authority=authority,
        poison_replaces_enchantment=True,
        poison_replacement_authority=authority,
        poison_replacement_evidence_note="reviewed poison evidence",
        same_effect_identity_shares_cooldown=True,
        same_identity_cooldown_authority=authority,
        evidence_note="reviewed complete cadence fixture",
    )


def test_current_crusher_cadence_fails_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver().resolve(
        enchantment_effects=(_effect(),),
    )

    assert result.policies == ()
    assert result.resolved is False
    assert any("base cooldown is not authoritative" in row for row in result.unresolved)
    assert any("cooldown scope is not authoritative" in row for row in result.unresolved)
    assert any("same-identity cooldown sharing is not authoritative" in row for row in result.unresolved)


def test_unclassified_direct_damage_variant_is_not_guessed_from_source_or_name():
    effect = _effect(
        name="flame_damage",
        source="Glyph of Flame",
        category=SupportEffectCategory.OTHER,
    )

    result = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver().resolve(
        enchantment_effects=(effect,),
    )

    assert result.policies == ()
    assert result.unresolved == (
        "weapon-enchantment effect family is not canonically classified: "
        "Glyph of Flame [front/main_hand]",
    )


def test_authoritative_four_second_value_alone_does_not_bypass_topology_gate():
    effect = _effect(
        name="flame_damage",
        source="Glyph of Flame",
        category=SupportEffectCategory.OTHER,
    )
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        effect_family_resolver=lambda _effect: WeaponEnchantmentEffectFamily.DIRECT_DAMAGE,
    )

    result = resolver.resolve(enchantment_effects=(effect,))

    assert result.policies == ()
    assert any("cooldown scope is not authoritative" in row for row in result.unresolved)
    assert any("same-identity cooldown sharing is not authoritative" in row for row in result.unresolved)
    assert not any("base cooldown is not authoritative" in row for row in result.unresolved)


def test_fully_authoritative_cadence_projects_effect_name_as_cooldown_identity():
    effect = _effect()
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        cadence_provider=lambda family: _authoritative_cadence(family, 9.0),
    )

    result = resolver.resolve(enchantment_effects=(effect,))

    assert result.resolved is True
    assert result.unresolved == ()
    assert len(result.policies) == 1
    policy = result.policies[0]
    assert policy.effect is effect
    assert policy.cooldown_identity == "crusher"
    assert policy.cooldown_seconds == 9.0
    assert policy.authoritative is True
    assert any("authoritative cooldown policy crusher @ 9s" in row for row in result.evidence)


def test_duplicate_same_identity_sources_receive_same_authoritative_cooldown_key():
    main = _effect()
    off = EffectVariant(
        name="crusher",
        layer=EffectLayer.PROC,
        source="Glyph of Crushing",
        active_bar=BarId.FRONT,
        source_slot="off_hand",
        trigger="weapon_enchantment_activation",
        category=SupportEffectCategory.DEBUFF,
    )
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        cadence_provider=lambda family: _authoritative_cadence(family, 10.0),
    )

    result = resolver.resolve(enchantment_effects=(main, off))

    assert result.resolved is True
    assert [policy.cooldown_identity for policy in result.policies] == [
        "crusher",
        "crusher",
    ]
