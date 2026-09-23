from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_weapon_enchantment_source_ownership_service import (
    ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService,
)


def _effect(source, bar):
    return EffectVariant(
        name="crusher",
        layer=EffectLayer.PROC,
        source=source,
        active_bar=bar,
    )


def test_source_ownership_keeps_only_effects_from_activation_source_bar():
    front = _effect("Front Crusher", BarId.FRONT)
    back = _effect("Back Crusher", BarId.BACK)
    event = RuntimeEvent(
        time_seconds=4.0,
        trigger="weapon_enchantment_activation",
        source="Wall of Elements",
        source_bar="back",
    )

    result = ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService().resolve(
        activation_event=event,
        enchantment_effects=(front, back),
    )

    assert result.unresolved == ()
    assert result.candidates == (back,)


def test_source_ownership_preserves_multiple_same_bar_candidates_for_later_selection():
    main = _effect("Main Hand", BarId.FRONT)
    off = _effect("Off Hand", BarId.FRONT)
    event = RuntimeEvent(
        time_seconds=1.0,
        trigger="weapon_enchantment_activation",
        source="Dual Wield Skill",
        source_bar="front",
    )

    result = ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService().resolve(
        activation_event=event,
        enchantment_effects=(main, off),
    )

    assert result.unresolved == ()
    assert result.candidates == (main, off)
    assert any("does not choose a Dual Wield hand" in row for row in result.evidence)


def test_source_ownership_fails_closed_without_activation_source_bar():
    event = RuntimeEvent(
        time_seconds=1.0,
        trigger="weapon_enchantment_activation",
        source="Weapon Skill",
    )

    result = ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService().resolve(
        activation_event=event,
        enchantment_effects=(_effect("Front", BarId.FRONT),),
    )

    assert result.candidates == ()
    assert any("source-bar provenance" in row for row in result.unresolved)


def test_source_ownership_fails_closed_when_enchantment_has_no_bar_identity():
    event = RuntimeEvent(
        time_seconds=1.0,
        trigger="weapon_enchantment_activation",
        source="Weapon Skill",
        source_bar="front",
    )

    result = ExtremeSustainedDPSWeaponEnchantmentSourceOwnershipService().resolve(
        activation_event=event,
        enchantment_effects=(
            _effect("Unknown", None),
        ),
    )

    assert result.candidates == ()
    assert any("lacks source-bar ownership" in row for row in result.unresolved)
