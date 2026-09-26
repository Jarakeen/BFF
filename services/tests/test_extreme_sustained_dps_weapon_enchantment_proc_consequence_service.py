import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution,
    ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService,
    ExtremeSustainedDPSWeaponEnchantmentProcOccurrence,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)


def _source():
    return ExtremeSustainedDPSWeaponEnchantmentRuntimeSource(
        item_id=43573,
        identity="absorb_health",
        identity_label="Absorb Health",
        source_label="Glyph of Absorb Health",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        effects=(
            CombatEffect(
                effect_type="damage",
                value=1900.0,
                source="Glyph of Absorb Health",
                unit=EffectUnit.FLAT,
                damage_type="magic",
            ),
            CombatEffect(
                effect_type="health_restore",
                value=861.0,
                source="Glyph of Absorb Health",
                unit=EffectUnit.FLAT,
            ),
        ),
    )


def _selector():
    return EffectVariant(
        name="absorb_health",
        layer=EffectLayer.PROC,
        source="Glyph of Absorb Health",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        trigger="weapon_enchantment_activation",
    )


def _attempt(*, bound=True):
    event = RuntimeEvent(
        time_seconds=1.0,
        sequence=3,
        trigger="weapon_enchantment_activation",
        source="Light Attack",
        target="Boss",
        source_bar="front",
    )
    if not bound:
        return RuntimeEffectEventAttempt(event=event)
    return RuntimeEffectEventAttempt.for_bound_effect(
        event=event,
        effect=_selector(),
    )


def test_selected_enchant_proc_recovers_all_canonical_consequences():
    result = ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService.resolve(
        attempts=(_attempt(),),
        sources=(_source(),),
    )

    assert result.resolved is True
    assert len(result.occurrences) == 1
    occurrence = result.occurrences[0]
    assert occurrence.time_seconds == 1.0
    assert occurrence.sequence == 3
    assert occurrence.source.identity == "absorb_health"
    assert tuple(effect.effect_type for effect in occurrence.consequences) == (
        "damage",
        "health_restore",
    )
    assert any("consequence rows attached to selected procs: 2" in row for row in result.evidence)


def test_unbound_enchant_attempt_fails_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService.resolve(
        attempts=(_attempt(bound=False),),
        sources=(_source(),),
    )

    assert result.occurrences == ()
    assert any("not bound to an exact source" in row for row in result.unresolved)


def test_foreign_bound_source_fails_closed():
    other = EffectVariant(
        name="flame",
        layer=EffectLayer.PROC,
        source="Glyph of Flame",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        trigger="weapon_enchantment_activation",
    )
    event = RuntimeEvent(
        time_seconds=1.0,
        sequence=0,
        trigger="weapon_enchantment_activation",
        source="Light Attack",
        source_bar="front",
    )
    attempt = RuntimeEffectEventAttempt.for_bound_effect(
        event=event,
        effect=other,
    )

    result = ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService.resolve(
        attempts=(attempt,),
        sources=(_source(),),
    )

    assert result.occurrences == ()
    assert any("no canonical equipped source" in row for row in result.unresolved)


def test_non_enchant_runtime_attempts_are_ignored():
    ordinary = RuntimeEffectEventAttempt(
        event=RuntimeEvent(
            time_seconds=1.0,
            sequence=0,
            trigger="damage_dealt",
            source="Skill",
        )
    )

    result = ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService.resolve(
        attempts=(ordinary,),
        sources=(_source(),),
    )

    assert result.resolved is True
    assert result.occurrences == ()


def test_proc_consequence_resolver_requires_tuple_inputs():
    with pytest.raises(TypeError, match="attempts must be a tuple"):
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService.resolve(
            attempts=[_attempt()],  # type: ignore[arg-type]
            sources=(_source(),),
        )

    with pytest.raises(TypeError, match="sources must be a tuple"):
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService.resolve(
            attempts=(_attempt(),),
            sources=[_source()],  # type: ignore[arg-type]
        )


def test_proc_consequence_resolver_requires_typed_nested_records():
    with pytest.raises(TypeError, match="RuntimeEffectEventAttempt records"):
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService.resolve(
            attempts=(object(),),  # type: ignore[arg-type]
            sources=(_source(),),
        )

    with pytest.raises(TypeError, match="runtime source records"):
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService.resolve(
            attempts=(),
            sources=(object(),),  # type: ignore[arg-type]
        )


def test_proc_occurrence_requires_strict_sequence_and_consequence_types():
    with pytest.raises(TypeError, match="sequence must be an integer"):
        ExtremeSustainedDPSWeaponEnchantmentProcOccurrence(
            time_seconds=1.0,
            sequence=True,  # type: ignore[arg-type]
            source=_source(),
            consequences=_source().effects,
        )

    with pytest.raises(TypeError, match="consequences must be a tuple"):
        ExtremeSustainedDPSWeaponEnchantmentProcOccurrence(
            time_seconds=1.0,
            sequence=0,
            source=_source(),
            consequences=list(_source().effects),  # type: ignore[arg-type]
        )


def test_proc_resolution_requires_tuple_occurrences():
    with pytest.raises(TypeError, match="occurrences must be a tuple"):
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
            occurrences=[],  # type: ignore[arg-type]
        )
