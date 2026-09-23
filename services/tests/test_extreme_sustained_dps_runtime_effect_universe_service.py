from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from services.extreme_sustained_dps_runtime_effect_universe_service import (
    ExtremeSustainedDPSRuntimeEffectUniverseService,
)
from services.extreme_sustained_dps_weapon_enchantment_activation_event_service import (
    WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
)


def _effect(name, *, trigger=None, condition=None):
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source=name,
        trigger=trigger,
        condition=condition,
        duration=5.0,
    )


class _Capabilities:
    def __init__(self, resolution):
        self.resolution = resolution
        self.calls = []

    def resolve_effect_variants(self, build):
        self.calls.append(build)
        return self.resolution


def test_collects_only_explicit_runtime_triggered_effects() -> None:
    audit = SimpleNamespace(
        effects=(
            _effect("damage-proc", trigger="damage_dealt"),
            _effect("conditional-static", condition="target_off_balance"),
            _effect("plain-static"),
        ),
        unresolved=(),
        boundaries=("static condition remains separate",),
    )
    service = ExtremeSustainedDPSRuntimeEffectUniverseService(
        capability_service=_Capabilities(audit)
    )

    result = service.resolve(object())

    assert tuple(effect.name for effect in result.effects) == ("damage-proc",)
    assert result.excluded_plan_owned == ()
    assert result.boundaries == ("static condition remains separate",)
    assert result.resolved is True


def test_potion_use_effects_are_excluded_as_plan_owned_runtime_state() -> None:
    audit = SimpleNamespace(
        effects=(
            _effect("potion-buff", trigger="potion_use"),
            _effect("ultimate-proc", trigger="ultimate_activation_in_combat"),
        ),
        unresolved=(),
        boundaries=(),
    )
    result = ExtremeSustainedDPSRuntimeEffectUniverseService(
        capability_service=_Capabilities(audit)
    ).resolve(object())

    assert tuple(effect.name for effect in result.effects) == ("ultimate-proc",)
    assert tuple(effect.name for effect in result.excluded_plan_owned) == (
        "potion-buff",
    )


def test_capability_gaps_fail_runtime_effect_universe_closed() -> None:
    audit = SimpleNamespace(
        effects=(_effect("damage-proc", trigger="damage_dealt"),),
        unresolved=("front skill not found in canonical ability data: Mystery",),
        boundaries=(),
    )
    result = ExtremeSustainedDPSRuntimeEffectUniverseService(
        capability_service=_Capabilities(audit)
    ).resolve(object())

    assert result.resolved is False
    assert result.unresolved == (
        "front skill not found in canonical ability data: Mystery",
    )


def test_duplicate_runtime_effects_across_bars_are_deduplicated() -> None:
    effect = _effect("damage-proc", trigger="damage_dealt")
    audit = SimpleNamespace(
        effects=(effect, effect),
        unresolved=(),
        boundaries=(),
    )
    result = ExtremeSustainedDPSRuntimeEffectUniverseService(
        capability_service=_Capabilities(audit)
    ).resolve(object())

    assert result.effects == (effect,)



def test_deferred_runtime_effect_boundary_fails_universe_closed() -> None:
    audit = SimpleNamespace(
        effects=(),
        unresolved=(),
        boundaries=(
            "front configured scribed skill recipe resolved; detailed scripted effect conversion deferred: Mystery Skill",
        ),
    )
    result = ExtremeSustainedDPSRuntimeEffectUniverseService(
        capability_service=_Capabilities(audit)
    ).resolve(object())

    assert result.resolved is False
    assert any(
        "detailed scripted effect conversion deferred" in row
        for row in result.unresolved
    )


def test_triggerless_crusher_capability_remains_runtime_timing_blocker() -> None:
    crusher = EffectVariant(
        name="physical_spell_resistance_reduction",
        layer=EffectLayer.PROC,
        source="Crusher Enchantment",
        magnitude=1622.0,
        duration=5.0,
        resistance_reduction=1622.0,
    )
    audit = SimpleNamespace(
        effects=(crusher,),
        unresolved=(),
        boundaries=(
            "front main hand weapon enchantment runtime effect timing deferred: "
            "Crusher Enchantment",
        ),
    )

    result = ExtremeSustainedDPSRuntimeEffectUniverseService(
        capability_service=_Capabilities(audit)
    ).resolve(object())

    assert result.effects == ()
    assert result.resolved is False
    assert result.unresolved == (
        "front main hand weapon enchantment runtime effect timing deferred: "
        "Crusher Enchantment",
    )


def test_single_weapon_enchantment_runtime_variant_can_enter_universe() -> None:
    enchantment = _effect(
        "crusher",
        trigger=WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
    )
    audit = SimpleNamespace(
        effects=(enchantment,),
        unresolved=(),
        boundaries=(),
    )

    result = ExtremeSustainedDPSRuntimeEffectUniverseService(
        capability_service=_Capabilities(audit)
    ).resolve(object())

    assert result.effects == (enchantment,)
    assert result.unresolved == ()
    assert result.resolved is True


def test_multiple_weapon_enchantment_variants_require_source_selection_frontier() -> None:
    crusher = _effect(
        "crusher",
        trigger=WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
    )
    flame = _effect(
        "flame_damage",
        trigger=WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
    )
    audit = SimpleNamespace(
        effects=(crusher, flame),
        unresolved=(),
        boundaries=(),
    )

    result = ExtremeSustainedDPSRuntimeEffectUniverseService(
        capability_service=_Capabilities(audit)
    ).resolve(object())

    assert result.effects == (crusher, flame)
    assert result.resolved is False
    assert result.unresolved == (
        "Multiple weapon-enchantment runtime variants require an explicit "
        "per-opportunity source-selection frontier; one isolated damage "
        "instance may proc only one weapon enchantment",
    )
