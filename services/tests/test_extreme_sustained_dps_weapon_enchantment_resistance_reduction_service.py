import pytest

from minmax.character_build.effect_layer import BarId
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution,
    ExtremeSustainedDPSWeaponEnchantmentProcOccurrence,
)
from services.extreme_sustained_dps_weapon_enchantment_resistance_reduction_service import (
    ExtremeSustainedDPSWeaponEnchantmentResistanceReductionService,
    ExtremeSustainedDPSWeaponEnchantmentResistanceResolution,
    ExtremeSustainedDPSWeaponEnchantmentResistanceWindow,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)


def _occurrence(time_seconds, *, duration=5.0, target="target", value=1622.0):
    effect = CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=value,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target=target,
        duration_value=duration,
        duration_unit="seconds",
    )
    source = ExtremeSustainedDPSWeaponEnchantmentRuntimeSource(
        item_id=1,
        identity="crushing",
        identity_label="Crushing",
        source_label="Glyph of Crushing",
        active_bar=BarId.FRONT,
        source_slot="main_hand",
        effects=(effect,),
    )
    return ExtremeSustainedDPSWeaponEnchantmentProcOccurrence(
        time_seconds=time_seconds,
        sequence=0,
        source=source,
        consequences=(effect,),
    )


def test_selected_crusher_projects_exact_resistance_window():
    result = ExtremeSustainedDPSWeaponEnchantmentResistanceReductionService.resolve(
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
            occurrences=(_occurrence(1.0),),
        )
    )

    assert result.resolved is True
    assert result.reduction_at(0.999) == 0.0
    assert result.reduction_at(1.0) == 1622.0
    assert result.reduction_at(5.999) == 1622.0
    assert result.reduction_at(6.0) == 0.0


def test_adjacent_crusher_windows_are_not_treated_as_overlap():
    result = ExtremeSustainedDPSWeaponEnchantmentResistanceReductionService.resolve(
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
            occurrences=(
                _occurrence(1.0),
                _occurrence(6.0),
            ),
        )
    )

    assert result.resolved is True
    assert result.reduction_at(5.999) == 1622.0
    assert result.reduction_at(6.0) == 1622.0


def test_overlapping_crusher_windows_fail_closed():
    result = ExtremeSustainedDPSWeaponEnchantmentResistanceReductionService.resolve(
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
            occurrences=(
                _occurrence(1.0),
                _occurrence(5.0),
            ),
        )
    )

    assert result.resolved is False
    assert any("overlap" in row for row in result.unresolved)


def test_crusher_requires_reviewed_target_and_duration():
    result = ExtremeSustainedDPSWeaponEnchantmentResistanceReductionService.resolve(
        ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
            occurrences=(_occurrence(1.0, duration=None, target=None),),
        )
    )

    assert result.resolved is False
    assert any("duration" in row for row in result.unresolved)


@pytest.mark.parametrize(
    "field,value,match",
    (
        ("start_seconds", "1", "start_seconds must be numeric"),
        ("end_seconds", "6", "end_seconds must be numeric"),
        ("magnitude", "1622", "magnitude must be numeric"),
        ("source_label", 7, "source_label must be a non-empty string"),
    ),
)
def test_resistance_window_rejects_coerced_fields(field, value, match):
    kwargs = {
        "start_seconds": 1.0,
        "end_seconds": 6.0,
        "magnitude": 1622.0,
        "source_label": "Glyph of Crushing",
    }
    kwargs[field] = value

    with pytest.raises(TypeError, match=match):
        ExtremeSustainedDPSWeaponEnchantmentResistanceWindow(**kwargs)


def test_resistance_window_rejects_invalid_ranges():
    with pytest.raises(ValueError, match="end_seconds must be after"):
        ExtremeSustainedDPSWeaponEnchantmentResistanceWindow(
            start_seconds=1.0,
            end_seconds=1.0,
            magnitude=1622.0,
            source_label="Glyph of Crushing",
        )


def test_resistance_window_active_at_requires_numeric_finite_time():
    window = ExtremeSustainedDPSWeaponEnchantmentResistanceWindow(
        start_seconds=1.0,
        end_seconds=6.0,
        magnitude=1622.0,
        source_label="Glyph of Crushing",
    )

    with pytest.raises(TypeError, match="time_seconds must be numeric"):
        window.active_at("1.0")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="time_seconds must be finite"):
        window.active_at(float("nan"))


def test_resistance_resolution_requires_tuple_windows():
    with pytest.raises(TypeError, match="windows must be a tuple"):
        ExtremeSustainedDPSWeaponEnchantmentResistanceResolution(
            windows=[],  # type: ignore[arg-type]
        )
