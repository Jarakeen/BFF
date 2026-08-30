from __future__ import annotations

import pytest

from minmax.healing_scaling_diagnostic import (
    HealingScenario,
    combat_prayer_investigation_scenarios,
    evaluate_healing_scenario,
)
from minmax.skill_coefficients import SkillCoefficient


def test_healing_scenario_applies_power_then_tooltip_healing_done():
    coefficient = SkillCoefficient(1, "8", 0.1, 1.0, 0.0)
    scenario = HealingScenario(
        name="test",
        effective_power_flat=200.0,
        power_percent=0.20,
        tooltip_healing_done=0.10,
    )

    result = evaluate_healing_scenario(
        coefficient,
        max_stat=30000.0,
        base_power=1500.0,
        scenario=scenario,
    )

    assert result.effective_power == pytest.approx(2040.0)
    assert result.base_coefficient_value == pytest.approx(5040.0)
    assert result.tooltip_value == pytest.approx(5544.0)


def test_combat_prayer_scenarios_keep_powered_out_of_displayed_tooltip_ladder():
    scenarios = combat_prayer_investigation_scenarios(ritual_bonus=0.13096)

    assert [scenario.name for scenario in scenarios] == [
        "Ritual only",
        "Ritual + Restoration Master",
        "+ Soothing Tide",
        "+ Rejuvenator",
        "+ Major Sorcery",
        "+ Major Mending",
    ]
    assert scenarios[-1].tooltip_healing_done == pytest.approx(0.44096)
    assert all("Powered" not in scenario.name for scenario in scenarios)


def test_combat_prayer_fixture_produces_auditable_scenario_ladder():
    coefficient = SkillCoefficient(
        coefficient_number=1,
        type="8",
        a=0.116163,
        b=1.22023,
        c=-0.138672,
        r=1.0,
    )
    scenarios = combat_prayer_investigation_scenarios(ritual_bonus=0.13096)
    values = [
        evaluate_healing_scenario(
            coefficient,
            max_stat=31022.0,
            base_power=1464.0,
            scenario=scenario,
        ).tooltip_value
        for scenario in scenarios
    ]

    assert values == sorted(values)
    assert values[0] == pytest.approx(6095.74618758864)
    assert values[-1] == pytest.approx(8713.98449621568)
    assert 9436.0 > values[-1]
