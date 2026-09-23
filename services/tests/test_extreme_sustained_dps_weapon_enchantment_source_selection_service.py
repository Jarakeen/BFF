from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_weapon_enchantment_source_ownership_service import (
    ExtremeSustainedDPSWeaponEnchantmentSourceOwnership,
)
from services.extreme_sustained_dps_weapon_enchantment_source_selection_service import (
    ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService,
)


def _effect(source, slot):
    return EffectVariant(
        name=source.casefold().replace(" ", "_"),
        layer=EffectLayer.PROC,
        source=source,
        active_bar=BarId.FRONT,
        source_slot=slot,
    )


def _ownership(*effects):
    return ExtremeSustainedDPSWeaponEnchantmentSourceOwnership(
        activation_event=RuntimeEvent(
            time_seconds=1.0,
            trigger="weapon_enchantment_activation",
            source="Dual Wield Skill",
            source_bar="front",
        ),
        candidates=tuple(effects),
    )


def test_single_source_owned_enchantment_is_exact_without_cooldown_selection():
    main = _effect("Main Enchant", "main_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService().resolve(
        ownership=_ownership(main),
    )

    assert result.unresolved == ()
    assert result.exact is main
    assert result.alternatives == (main,)


def test_multi_source_selection_requires_cooldown_ready_evidence():
    main = _effect("Main Enchant", "main_hand")
    off = _effect("Off Enchant", "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService().resolve(
        ownership=_ownership(main, off),
    )

    assert result.exact is None
    assert result.alternatives == (main, off)
    assert any("cooldown-ready state" in row for row in result.unresolved)


def test_one_ready_dual_wield_enchantment_resolves_update20_preference():
    main = _effect("Main Enchant", "main_hand")
    off = _effect("Off Enchant", "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService().resolve(
        ownership=_ownership(main, off),
        cooldown_ready=(off,),
    )

    assert result.unresolved == ()
    assert result.exact is off
    assert result.alternatives == (off,)


def test_two_ready_dual_wield_enchantments_remain_finite_alternatives():
    main = _effect("Main Enchant", "main_hand")
    off = _effect("Off Enchant", "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService().resolve(
        ownership=_ownership(main, off),
        cooldown_ready=(main, off),
    )

    assert result.exact is None
    assert result.alternatives == (main, off)
    assert any("source-selection alternatives" in row for row in result.unresolved)


def test_no_ready_enchantments_resolve_to_no_proc_source():
    main = _effect("Main Enchant", "main_hand")
    off = _effect("Off Enchant", "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService().resolve(
        ownership=_ownership(main, off),
        cooldown_ready=(),
    )

    assert result.unresolved == ()
    assert result.exact is None
    assert result.alternatives == ()


def test_foreign_cooldown_ready_evidence_fails_closed():
    main = _effect("Main Enchant", "main_hand")
    other = EffectVariant(
        name="foreign",
        layer=EffectLayer.PROC,
        source="Foreign",
        active_bar=BarId.BACK,
        source_slot="main_hand",
    )

    result = ExtremeSustainedDPSWeaponEnchantmentSourceSelectionService().resolve(
        ownership=_ownership(main, _effect("Off Enchant", "off_hand")),
        cooldown_ready=(other,),
    )

    assert result.exact is None
    assert result.alternatives == ()
    assert any("outside the source-owned candidate set" in row for row in result.unresolved)
