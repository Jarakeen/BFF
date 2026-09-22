from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from services.extreme_sustained_dps_runtime_effect_universe_service import (
    ExtremeSustainedDPSRuntimeEffectUniverseService,
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
    def __init__(self, audit):
        self.audit = audit
        self.calls = []

    def audit_build(self, build):
        self.calls.append(build)
        return self.audit


def test_collects_only_explicit_runtime_triggered_effects() -> None:
    audit = SimpleNamespace(
        resolved_effects=(
            _effect("damage-proc", trigger="damage_dealt"),
            _effect("conditional-static", condition="target_off_balance"),
            _effect("plain-static"),
        ),
        capability_unresolved=(),
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
        resolved_effects=(
            _effect("potion-buff", trigger="potion_use"),
            _effect("ultimate-proc", trigger="ultimate_activation_in_combat"),
        ),
        capability_unresolved=(),
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
        resolved_effects=(_effect("damage-proc", trigger="damage_dealt"),),
        capability_unresolved=("front skill not found in canonical ability data: Mystery",),
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
        resolved_effects=(effect, effect),
        capability_unresolved=(),
        boundaries=(),
    )
    result = ExtremeSustainedDPSRuntimeEffectUniverseService(
        capability_service=_Capabilities(audit)
    ).resolve(object())

    assert result.effects == (effect,)



def test_deferred_runtime_effect_boundary_fails_universe_closed() -> None:
    audit = SimpleNamespace(
        resolved_effects=(),
        capability_unresolved=(),
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
