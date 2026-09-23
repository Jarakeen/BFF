from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_weapon_enchantment_activation_resolution_service import (
    ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService,
)


def _effect(source, bar, slot):
    return EffectVariant(
        name=source.casefold().replace(" ", "_"),
        layer=EffectLayer.PROC,
        source=source,
        active_bar=bar,
        source_slot=slot,
    )


def _event(bar="front", trigger="weapon_enchantment_activation"):
    return RuntimeEvent(
        time_seconds=2.0,
        sequence=4,
        trigger=trigger,
        source="Weapon Damage",
        source_bar=bar,
    )


def test_composite_resolver_keeps_off_bar_source_ownership():
    front = _effect("Front Enchant", BarId.FRONT, "main_hand")
    back = _effect("Back Enchant", BarId.BACK, "main_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService().resolve(
        activation_event=_event("back"),
        enchantment_effects=(front, back),
    )

    assert result.resolved is True
    assert result.exact is back
    assert result.alternatives == (back,)
    assert result.proc_occurs is True


def test_composite_resolver_keeps_dual_wield_choice_open_without_cooldown_truth():
    main = _effect("Main Enchant", BarId.FRONT, "main_hand")
    off = _effect("Off Enchant", BarId.FRONT, "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService().resolve(
        activation_event=_event(),
        enchantment_effects=(main, off),
    )

    assert result.exact is None
    assert result.alternatives == (main, off)
    assert result.proc_occurs is None
    assert any("cooldown-ready state" in row for row in result.unresolved)


def test_composite_resolver_uses_caller_proven_ready_subset():
    main = _effect("Main Enchant", BarId.FRONT, "main_hand")
    off = _effect("Off Enchant", BarId.FRONT, "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService().resolve(
        activation_event=_event(),
        enchantment_effects=(main, off),
        cooldown_ready=(off,),
    )

    assert result.resolved is True
    assert result.exact is off
    assert result.alternatives == (off,)
    assert result.proc_occurs is True


def test_composite_resolver_can_prove_no_proc_when_all_owned_sources_are_on_cooldown():
    main = _effect("Main Enchant", BarId.FRONT, "main_hand")
    off = _effect("Off Enchant", BarId.FRONT, "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService().resolve(
        activation_event=_event(),
        enchantment_effects=(main, off),
        cooldown_ready=(),
    )

    assert result.resolved is True
    assert result.exact is None
    assert result.alternatives == ()
    assert result.proc_occurs is False


def test_composite_resolver_rejects_non_enchantment_runtime_event():
    result = ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService().resolve(
        activation_event=_event(trigger="damage_dealt"),
        enchantment_effects=(),
    )

    assert result.resolved is False
    assert result.proc_occurs is None
    assert any("canonical weapon_enchantment_activation" in row for row in result.unresolved)
