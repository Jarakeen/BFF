import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from services.extreme_sustained_dps_weapon_enchantment_cooldown_readiness_service import (
    ExtremeSustainedDPSWeaponEnchantmentCooldownReadiness,
    ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService,
    ExtremeSustainedDPSWeaponEnchantmentCooldownState,
)


def _effect(source, slot):
    return EffectVariant(
        name=source.casefold().replace(" ", "_"),
        layer=EffectLayer.PROC,
        source=source,
        active_bar=BarId.FRONT,
        source_slot=slot,
    )


def _state(effect, cooldown, last=None):
    return ExtremeSustainedDPSWeaponEnchantmentCooldownState(
        effect=effect,
        cooldown_seconds=cooldown,
        last_activation_time_seconds=last,
    )


def test_never_activated_source_is_ready():
    main = _effect("Main Enchant", "main_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService.resolve(
        activation_time_seconds=2.0,
        candidates=(main,),
        states=(_state(main, 4.0),),
    )

    assert result.resolved is True
    assert result.ready == (main,)
    assert result.blocked == ()
    assert result.ready_at == ((main, 0.0),)


def test_exact_cooldown_boundary_is_ready():
    main = _effect("Main Enchant", "main_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService.resolve(
        activation_time_seconds=5.0,
        candidates=(main,),
        states=(_state(main, 4.0, 1.0),),
    )

    assert result.ready == (main,)
    assert result.blocked == ()
    assert result.ready_at == ((main, 5.0),)


def test_dual_wield_sources_can_have_distinct_explicit_readiness():
    main = _effect("Main Enchant", "main_hand")
    off = _effect("Off Enchant", "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService.resolve(
        activation_time_seconds=3.0,
        candidates=(main, off),
        states=(
            _state(main, 4.0, 1.0),
            _state(off, 4.0, None),
        ),
    )

    assert result.ready == (off,)
    assert result.blocked == (main,)
    assert result.ready_at == ((main, 5.0), (off, 0.0))


def test_missing_candidate_state_fails_closed():
    main = _effect("Main Enchant", "main_hand")
    off = _effect("Off Enchant", "off_hand")

    result = ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService.resolve(
        activation_time_seconds=3.0,
        candidates=(main, off),
        states=(_state(main, 4.0, 1.0),),
    )

    assert result.resolved is False
    assert result.ready == ()
    assert result.blocked == ()
    assert any("missing" in row for row in result.unresolved)


def test_foreign_state_fails_closed():
    main = _effect("Main Enchant", "main_hand")
    foreign = EffectVariant(
        name="foreign",
        layer=EffectLayer.PROC,
        source="Foreign",
        active_bar=BarId.BACK,
        source_slot="main_hand",
    )

    result = ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService.resolve(
        activation_time_seconds=3.0,
        candidates=(main,),
        states=(
            _state(main, 4.0),
            _state(foreign, 4.0),
        ),
    )

    assert result.resolved is False
    assert any("outside the source-owned candidate set" in row for row in result.unresolved)


@pytest.mark.parametrize(
    "field,value,match",
    (
        ("cooldown_seconds", "4", "cooldown_seconds must be numeric"),
        ("last_activation_time_seconds", "1", "last_activation_time_seconds must be numeric"),
    ),
)
def test_cooldown_state_rejects_coerced_numeric_fields(field, value, match):
    kwargs = {
        "effect": _effect("Main Enchant", "main_hand"),
        "cooldown_seconds": 4.0,
        "last_activation_time_seconds": 1.0,
    }
    kwargs[field] = value

    with pytest.raises(TypeError, match=match):
        ExtremeSustainedDPSWeaponEnchantmentCooldownState(**kwargs)


def test_cooldown_resolver_requires_tuple_typed_inputs():
    main = _effect("Main Enchant", "main_hand")

    with pytest.raises(TypeError, match="candidates must be a tuple"):
        ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService.resolve(
            activation_time_seconds=1.0,
            candidates=[main],  # type: ignore[arg-type]
            states=(_state(main, 4.0),),
        )

    with pytest.raises(TypeError, match="states must be a tuple"):
        ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService.resolve(
            activation_time_seconds=1.0,
            candidates=(main,),
            states=[_state(main, 4.0)],  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="activation_time_seconds must be numeric"):
        ExtremeSustainedDPSWeaponEnchantmentCooldownReadinessService.resolve(
            activation_time_seconds="1.0",  # type: ignore[arg-type]
            candidates=(main,),
            states=(_state(main, 4.0),),
        )


def test_cooldown_readiness_requires_tuple_ready_at_rows():
    main = _effect("Main Enchant", "main_hand")

    with pytest.raises(TypeError, match="ready_at rows must be"):
        ExtremeSustainedDPSWeaponEnchantmentCooldownReadiness(
            ready=(main,),
            blocked=(),
            ready_at=([main, 0.0],),  # type: ignore[list-item]
        )
