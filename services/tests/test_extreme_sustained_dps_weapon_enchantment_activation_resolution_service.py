from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_weapon_enchantment_activation_resolution_service import (
    ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService,
)
from services.extreme_sustained_dps_weapon_enchantment_cooldown_readiness_service import (
    ExtremeSustainedDPSWeaponEnchantmentCooldownState,
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
    assert result.cooldown_state_proven is False
    assert result.proc_occurs is None


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
    assert result.cooldown_state_proven is True
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


def test_composite_resolver_can_derive_ready_subset_from_explicit_cooldown_states():
    main = _effect("Main Enchant", BarId.FRONT, "main_hand")
    off = _effect("Off Enchant", BarId.FRONT, "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService().resolve(
        activation_event=_event(),
        enchantment_effects=(main, off),
        cooldown_states=(
            ExtremeSustainedDPSWeaponEnchantmentCooldownState(
                effect=main,
                cooldown_seconds=4.0,
                last_activation_time_seconds=0.0,
            ),
            ExtremeSustainedDPSWeaponEnchantmentCooldownState(
                effect=off,
                cooldown_seconds=4.0,
                last_activation_time_seconds=None,
            ),
        ),
    )

    assert result.resolved is True
    assert result.exact is off
    assert result.alternatives == (off,)
    assert result.proc_occurs is True
    assert any("Cooldown-ready candidates" in row for row in result.evidence)


def test_composite_resolver_rejects_two_cooldown_truth_sources():
    import pytest

    main = _effect("Main Enchant", BarId.FRONT, "main_hand")

    with pytest.raises(ValueError, match="not both"):
        ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService().resolve(
            activation_event=_event(),
            enchantment_effects=(main,),
            cooldown_ready=(main,),
            cooldown_states=(
                ExtremeSustainedDPSWeaponEnchantmentCooldownState(
                    effect=main,
                    cooldown_seconds=4.0,
                ),
            ),
        )


def test_single_owned_source_with_explicit_ready_state_proves_proc():
    main = _effect("Main Enchant", BarId.FRONT, "main_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService().resolve(
        activation_event=_event(),
        enchantment_effects=(main,),
        cooldown_ready=(main,),
    )

    assert result.exact is main
    assert result.cooldown_state_proven is True
    assert result.proc_occurs is True


def test_activation_resolution_requires_tuple_effect_collections():
    service = ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService()
    main = _effect("Main Enchant", BarId.FRONT, "main_hand")

    with pytest.raises(TypeError, match="enchantment_effects must be a tuple"):
        service.resolve(
            activation_event=_event(),
            enchantment_effects=[main],  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="cooldown_ready must be a tuple"):
        service.resolve(
            activation_event=_event(),
            enchantment_effects=(main,),
            cooldown_ready=[main],  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="cooldown_states must be a tuple"):
        service.resolve(
            activation_event=_event(),
            enchantment_effects=(main,),
            cooldown_states=[],  # type: ignore[arg-type]
        )


def test_activation_resolution_requires_typed_effect_records():
    service = ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService()

    with pytest.raises(TypeError, match="must contain EffectVariant records"):
        service.resolve(
            activation_event=_event(),
            enchantment_effects=(object(),),  # type: ignore[arg-type]
        )


def test_activation_resolution_requires_string_trigger():
    event = _event()
    object.__setattr__(event, "trigger", 7)

    with pytest.raises(TypeError, match="event trigger must be a string"):
        ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService().resolve(
            activation_event=event,
            enchantment_effects=(),
        )


def test_activation_resolution_requires_numeric_event_time_for_cooldown_states():
    main = _effect("Main Enchant", BarId.FRONT, "main_hand")
    event = _event()
    object.__setattr__(event, "time_seconds", "2.0")

    with pytest.raises(TypeError, match="time_seconds must be numeric"):
        ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService().resolve(
            activation_event=event,
            enchantment_effects=(main,),
            cooldown_states=(
                ExtremeSustainedDPSWeaponEnchantmentCooldownState(
                    effect=main,
                    cooldown_seconds=4.0,
                ),
            ),
        )
