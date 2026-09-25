from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from minmax.support_effect_category import SupportEffectCategory
from minmax.weapon_enchantment_runtime_cadence import (
    WeaponEnchantmentCadenceAuthority,
    WeaponEnchantmentCadenceEvidence,
    WeaponEnchantmentEffectFamily,
)
from services.extreme_sustained_dps_weapon_enchantment_cadence_family_service import (
    ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
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
        distinct_effect_identities_have_independent_cooldowns=True,
        distinct_identity_cooldown_authority=authority,
        distinct_identity_cooldown_evidence_note="reviewed distinct-identity independence evidence",
        evidence_note="reviewed complete cadence fixture",
    )


def test_current_crusher_cadence_fails_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver().resolve(
        enchantment_effects=(_effect(),),
    )

    assert result.policies == ()
    assert result.resolved is False
    assert any("base cooldown is not authoritative" in row for row in result.unresolved)
    assert not any("cooldown scope is not authoritative" in row for row in result.unresolved)
    assert not any("same-identity cooldown sharing is not authoritative" in row for row in result.unresolved)
    assert not any("distinct-identity cooldown independence is not authoritative" in row for row in result.unresolved)


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


def test_single_direct_damage_identity_does_not_require_unrelated_multi_identity_topology():
    effect = _effect(
        name="flame_damage",
        source="Glyph of Flame",
        category=SupportEffectCategory.OTHER,
    )
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        effect_family_resolver=lambda _effect: WeaponEnchantmentEffectFamily.DIRECT_DAMAGE,
    )

    result = resolver.resolve(enchantment_effects=(effect,))

    assert result.resolved is True
    assert result.unresolved == ()
    assert len(result.policies) == 1
    assert result.policies[0].cooldown_identity == "flame_damage"
    assert result.policies[0].cooldown_seconds == 4.0



def test_two_distinct_direct_damage_identities_still_require_independence_topology():
    front = _effect(
        name="flame_damage",
        source="Glyph of Flame",
        category=SupportEffectCategory.OTHER,
    )
    back = EffectVariant(
        name="shock_damage",
        layer=EffectLayer.PROC,
        source="Glyph of Shock",
        active_bar=BarId.BACK,
        source_slot="main_hand",
        trigger="weapon_enchantment_activation",
        category=SupportEffectCategory.OTHER,
    )
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        effect_family_resolver=lambda _effect: WeaponEnchantmentEffectFamily.DIRECT_DAMAGE,
    )

    result = resolver.resolve(enchantment_effects=(front, back))

    assert result.policies == ()
    assert any("cooldown scope is not authoritative" in row for row in result.unresolved)
    assert any(
        "distinct-identity cooldown independence is not authoritative" in row
        for row in result.unresolved
    )
    assert not any(
        "same-identity cooldown sharing is not authoritative" in row
        for row in result.unresolved
    )


def test_duplicate_direct_damage_identity_uses_authoritative_shared_timer_without_distinct_scope():
    main = _effect(
        name="flame_damage",
        source="Glyph of Flame",
        category=SupportEffectCategory.OTHER,
    )
    off = EffectVariant(
        name="flame_damage",
        layer=EffectLayer.PROC,
        source="Glyph of Flame",
        active_bar=BarId.FRONT,
        source_slot="off_hand",
        trigger="weapon_enchantment_activation",
        category=SupportEffectCategory.OTHER,
    )
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        effect_family_resolver=lambda _effect: WeaponEnchantmentEffectFamily.DIRECT_DAMAGE,
    )

    result = resolver.resolve(enchantment_effects=(main, off))

    assert result.resolved is True
    assert result.unresolved == ()
    assert [policy.cooldown_identity for policy in result.policies] == [
        "flame_damage",
        "flame_damage",
    ]
    assert all(policy.cooldown_seconds == 4.0 for policy in result.policies)


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

class _RuntimeSources:
    def __init__(self, sources):
        self.sources = tuple(sources)

    def resolve(self, _build):
        class _Resolution:
            sources = self.sources
            evidence = ("canonical equipped enchant sources resolved",)
            unresolved = ()
        return _Resolution()


def _runtime_source(*, identity, label, effect_type, damage_type=None, weapon_trait=None, weapon_quality=None):
    return ExtremeSustainedDPSWeaponEnchantmentRuntimeSource(
        item_id=1,
        identity=identity,
        identity_label=identity.replace("_", " ").title(),
        source_label=label,
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        effects=(
            CombatEffect(
                effect_type=effect_type,
                value=100.0,
                source=label,
                unit=EffectUnit.FLAT,
                damage_type=damage_type,
            ),
        ),
        weapon_trait=weapon_trait,
        weapon_quality=weapon_quality,
    )


def test_canonical_single_direct_damage_source_reaches_exact_four_second_policy():
    source = _runtime_source(
        identity="flame",
        label="Glyph of Flame",
        effect_type="damage",
        damage_type="flame",
    )
    effect = _effect(
        name="flame",
        source="Glyph of Flame",
        category=SupportEffectCategory.OTHER,
    )
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        runtime_source_service=_RuntimeSources((source,)),
        cadence_family_service=ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService(),
    )

    result = resolver.resolve(
        player_build=object(),
        enchantment_effects=(effect,),
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert any("cadence family=direct_damage" in row for row in result.evidence)
    assert len(result.policies) == 1
    assert result.policies[0].cooldown_identity == "flame"
    assert result.policies[0].cooldown_seconds == 4.0


def test_canonical_crusher_source_reaches_buff_debuff_family_and_keeps_base_cooldown_open():
    source = _runtime_source(
        identity="crushing",
        label="Glyph of Crushing",
        effect_type="physical_spell_resistance_reduction",
    )
    effect = _effect(
        name="crushing",
        source="Glyph of Crushing",
        category=SupportEffectCategory.OTHER,
    )
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        runtime_source_service=_RuntimeSources((source,)),
        cadence_family_service=ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService(),
    )

    result = resolver.resolve(
        player_build=object(),
        enchantment_effects=(effect,),
    )

    assert result.policies == ()
    assert any("cadence family=buff_or_debuff" in row for row in result.evidence)
    assert any("base cooldown is not authoritative" in row for row in result.unresolved)
    assert not any("cooldown scope is not authoritative" in row for row in result.unresolved)
    assert not any("same-identity cooldown sharing is not authoritative" in row for row in result.unresolved)
    assert not any("distinct-identity cooldown independence is not authoritative" in row for row in result.unresolved)


def test_canonical_policy_resolution_requires_build_context():
    source = _runtime_source(
        identity="flame",
        label="Glyph of Flame",
        effect_type="damage",
        damage_type="flame",
    )
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        runtime_source_service=_RuntimeSources((source,)),
        cadence_family_service=ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService(),
    )

    result = resolver.resolve(
        enchantment_effects=(
            _effect(
                name="flame",
                source="Glyph of Flame",
                category=SupportEffectCategory.OTHER,
            ),
        ),
    )

    assert result.policies == ()
    assert any("requires player_build" in row for row in result.unresolved)




class _MalformedCooldownRules:
    def __init__(self, result):
        self.result = result

    def resolve_cooldown(self, **_kwargs):
        return self.result


class _CooldownResultWithoutFinal:
    reduction = 50.0


class _CooldownResultWithBadReduction:
    final_cooldown = 2.0
    reduction = "not-a-number"


def test_malformed_cooldown_rule_result_fails_closed_instead_of_crashing():
    source = _runtime_source(
        identity="flame",
        label="Glyph of Flame",
        effect_type="damage",
        damage_type="flame",
        weapon_trait="Infused",
        weapon_quality="Gold",
    )
    effect = _effect(
        name="flame",
        source="Glyph of Flame",
        category=SupportEffectCategory.OTHER,
    )
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        cadence_provider=lambda family: _authoritative_cadence(family, 4.0),
        runtime_source_service=_RuntimeSources((source,)),
        cadence_family_service=ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService(),
        cooldown_rule_resolver=_MalformedCooldownRules(_CooldownResultWithoutFinal()),
    )

    result = resolver.resolve(
        player_build=object(),
        enchantment_effects=(effect,),
    )

    assert result.policies == ()
    assert any(
        "returned no numeric final cooldown" in row
        for row in result.unresolved
    )


def test_malformed_cooldown_reduction_evidence_fails_closed_instead_of_crashing():
    source = _runtime_source(
        identity="flame",
        label="Glyph of Flame",
        effect_type="damage",
        damage_type="flame",
        weapon_trait="Infused",
        weapon_quality="Gold",
    )
    effect = _effect(
        name="flame",
        source="Glyph of Flame",
        category=SupportEffectCategory.OTHER,
    )
    resolver = ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
        cadence_provider=lambda family: _authoritative_cadence(family, 4.0),
        runtime_source_service=_RuntimeSources((source,)),
        cadence_family_service=ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService(),
        cooldown_rule_resolver=_MalformedCooldownRules(_CooldownResultWithBadReduction()),
    )

    result = resolver.resolve(
        player_build=object(),
        enchantment_effects=(effect,),
    )

    assert result.policies == ()
    assert any(
        "returned non-numeric reduction evidence" in row
        for row in result.unresolved
    )
