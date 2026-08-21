from minmax.combat_calculation import CombatEffectResult
from minmax.combat_contribution import (
    calculate_combat_contribution,
)


def test_full_uptime_preserves_value():
    result = CombatEffectResult(
        effect_type="damage",
        value=2534,
        source="Glyph of Frost",
        uptime=1.0,
    )

    contribution = calculate_combat_contribution(result)

    assert contribution.raw_value == 2534
    assert contribution.uptime == 1.0
    assert contribution.effective_value == 2534


def test_partial_uptime_reduces_contribution():
    result = CombatEffectResult(
        effect_type="damage",
        value=1622,
        source="Temporary Effect",
        uptime=0.5,
    )

    contribution = calculate_combat_contribution(result)

    assert contribution.raw_value == 1622
    assert contribution.uptime == 0.5
    assert contribution.effective_value == 811


def test_zero_uptime_has_no_effective_contribution():
    result = CombatEffectResult(
        effect_type="damage",
        value=2534,
        source="Inactive Effect",
        uptime=0.0,
    )

    contribution = calculate_combat_contribution(result)

    assert contribution.effective_value == 0.0