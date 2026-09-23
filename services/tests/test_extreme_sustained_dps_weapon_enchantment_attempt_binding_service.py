from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_weapon_enchantment_activation_resolution_service import (
    ExtremeSustainedDPSWeaponEnchantmentActivationResolution,
)
from services.extreme_sustained_dps_weapon_enchantment_attempt_binding_service import (
    ExtremeSustainedDPSWeaponEnchantmentAttemptBindingService,
)


def _effect():
    return EffectVariant(
        name="crusher",
        layer=EffectLayer.PROC,
        source="Crusher Enchantment",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        trigger="weapon_enchantment_activation",
    )


def _event():
    return RuntimeEvent(
        time_seconds=1.0,
        trigger="weapon_enchantment_activation",
        source="Light Attack",
        source_bar="front",
    )


def test_exact_ready_source_becomes_effect_bound_attempt():
    effect = _effect()
    result = ExtremeSustainedDPSWeaponEnchantmentAttemptBindingService.bind(
        ExtremeSustainedDPSWeaponEnchantmentActivationResolution(
            activation_event=_event(),
            exact=effect,
            alternatives=(effect,),
            cooldown_state_proven=True,
        )
    )

    assert result.resolved is True
    assert result.attempt is not None
    assert result.attempt.applies_to(effect) is True


def test_proven_no_proc_creates_no_runtime_attempt():
    result = ExtremeSustainedDPSWeaponEnchantmentAttemptBindingService.bind(
        ExtremeSustainedDPSWeaponEnchantmentActivationResolution(
            activation_event=_event(),
            exact=None,
            alternatives=(),
            cooldown_state_proven=True,
        )
    )

    assert result.resolved is True
    assert result.attempt is None
    assert any("produced no proc" in row for row in result.evidence)


def test_source_without_cooldown_truth_fails_closed_before_binding():
    effect = _effect()
    result = ExtremeSustainedDPSWeaponEnchantmentAttemptBindingService.bind(
        ExtremeSustainedDPSWeaponEnchantmentActivationResolution(
            activation_event=_event(),
            exact=effect,
            alternatives=(effect,),
            cooldown_state_proven=False,
        )
    )

    assert result.resolved is False
    assert result.attempt is None
    assert any("cooldown readiness" in row for row in result.unresolved)


def test_unresolved_source_selection_is_preserved():
    result = ExtremeSustainedDPSWeaponEnchantmentAttemptBindingService.bind(
        ExtremeSustainedDPSWeaponEnchantmentActivationResolution(
            activation_event=_event(),
            exact=None,
            alternatives=(_effect(),),
            unresolved=("source selection unresolved",),
        )
    )

    assert result.resolved is False
    assert result.unresolved == ("source selection unresolved",)
