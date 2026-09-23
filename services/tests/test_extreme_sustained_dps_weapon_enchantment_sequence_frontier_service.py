from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_weapon_enchantment_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy,
    ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService,
)


def _effect(source, slot, *, name=None):
    return EffectVariant(
        name=name or source.casefold().replace(" ", "_"),
        layer=EffectLayer.PROC,
        source=source,
        active_bar=BarId.FRONT,
        source_slot=slot,
        trigger="weapon_enchantment_activation",
    )


def _event(time_seconds, sequence=0):
    return RuntimeEvent(
        time_seconds=time_seconds,
        sequence=sequence,
        trigger="weapon_enchantment_activation",
        source="Weapon Damage",
        source_bar="front",
    )


def _policy(effect, identity, cooldown=4.0, authoritative=True):
    return ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy(
        effect=effect,
        cooldown_identity=identity,
        cooldown_seconds=cooldown,
        authoritative=authoritative,
    )


def test_two_ready_dual_wield_sources_create_finite_source_branches():
    main = _effect("Main Enchant", "main_hand")
    off = _effect("Off Enchant", "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService().build(
        events=(_event(1.0),),
        effects=(main, off),
        policies=(
            _policy(main, "main"),
            _policy(off, "off"),
        ),
        event_denominator_proven=True,
        source="reviewed fixture",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 2
    selected = {
        choice.attempts[0].bound_effect_key
        for choice in result.choices
    }
    assert len(selected) == 2


def test_first_source_choice_changes_second_hit_readiness():
    main = _effect("Main Enchant", "main_hand")
    off = _effect("Off Enchant", "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService().build(
        events=(_event(1.0), _event(2.0, 1)),
        effects=(main, off),
        policies=(
            _policy(main, "main"),
            _policy(off, "off"),
        ),
        event_denominator_proven=True,
        source="reviewed fixture",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 2
    assert all(len(choice.attempts) == 2 for choice in result.choices)
    assert all(
        choice.attempts[0].bound_effect_key
        != choice.attempts[1].bound_effect_key
        for choice in result.choices
    )


def test_shared_identity_timer_blocks_duplicate_enchant_after_first_proc():
    main = _effect("Main Flame", "main_hand", name="flame")
    off = _effect("Off Flame", "off_hand", name="flame")

    result = ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService().build(
        events=(_event(1.0), _event(2.0, 1)),
        effects=(main, off),
        policies=(
            _policy(main, "flame-shared"),
            _policy(off, "flame-shared"),
        ),
        event_denominator_proven=True,
        source="reviewed fixture",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 2
    assert all(len(choice.attempts) == 1 for choice in result.choices)
    assert all(len(choice.no_proc_events) == 1 for choice in result.choices)


def test_cooldown_expiry_reopens_previously_used_source():
    main = _effect("Main Enchant", "main_hand")
    off = _effect("Off Enchant", "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService().build(
        events=(_event(1.0), _event(2.0, 1), _event(5.0, 2)),
        effects=(main, off),
        policies=(
            _policy(main, "main"),
            _policy(off, "off"),
        ),
        event_denominator_proven=True,
        source="reviewed fixture",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 4
    assert all(len(choice.attempts) == 3 for choice in result.choices)


def test_provisional_policy_fails_closed():
    main = _effect("Main Enchant", "main_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService().build(
        events=(_event(1.0),),
        effects=(main,),
        policies=(
            _policy(main, "main", authoritative=False),
        ),
        event_denominator_proven=True,
        source="provisional fixture",
    )

    assert result.denominator_proven is False
    assert any("not authoritative" in row for row in result.unresolved)


def test_missing_policy_fails_closed():
    main = _effect("Main Enchant", "main_hand")
    off = _effect("Off Enchant", "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService().build(
        events=(_event(1.0),),
        effects=(main, off),
        policies=(_policy(main, "main"),),
        event_denominator_proven=True,
        source="partial fixture",
    )

    assert result.denominator_proven is False
    assert any("missing" in row for row in result.unresolved)

def test_multi_consequence_variants_share_one_source_branch_and_one_proc_attempt():
    damage = EffectVariant(
        name="glyph_of_absorb_health",
        layer=EffectLayer.PROC,
        source="Glyph of Absorb Health",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        trigger="weapon_enchantment_activation",
        magnitude=1900.0,
    )
    restore = EffectVariant(
        name="glyph_of_absorb_health",
        layer=EffectLayer.PROC,
        source="Glyph of Absorb Health",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        trigger="weapon_enchantment_activation",
        magnitude=861.0,
    )

    result = ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService().build(
        events=(_event(1.0),),
        effects=(damage, restore),
        policies=(
            _policy(damage, "glyph_of_absorb_health"),
            _policy(restore, "glyph_of_absorb_health"),
        ),
        event_denominator_proven=True,
        source="reviewed multi-consequence fixture",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 1
    attempt = result.choices[0].attempts[0]
    assert attempt.applies_to(damage) is True
    assert attempt.applies_to(restore) is True
    assert any("consequence variants supplied: 2" in row for row in result.evidence)
    assert any("Distinct weapon-enchantment sources supplied: 1" in row for row in result.evidence)


def test_conflicting_policies_for_one_binding_source_fail_closed():
    damage = _effect("Main Enchant", "main_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService().build(
        events=(_event(1.0),),
        effects=(damage,),
        policies=(
            _policy(damage, "main", cooldown=4.0),
            _policy(damage, "main", cooldown=5.0),
        ),
        event_denominator_proven=True,
        source="conflicting policy fixture",
    )

    assert result.denominator_proven is False
    assert any("conflicting" in row for row in result.unresolved)

