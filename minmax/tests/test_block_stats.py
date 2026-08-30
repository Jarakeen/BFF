from __future__ import annotations

import pytest

from minmax.block_stats import (
    BlockCostInputs,
    BlockCostModifier,
    BlockMitigationInputs,
    BlockStatCalculator,
)


def test_block_cost_applies_flat_reductions_before_sequential_percent_sources():
    inputs = BlockCostInputs(
        flat_reductions=(("Tireless Guardian", 40.0), ("Bracing glyphs", 324.0)),
        sequential_modifiers=(
            BlockCostModifier("Fortress", -0.36),
            BlockCostModifier("Sturdy", -0.24),
            BlockCostModifier("Medium Armor", -0.03),
            BlockCostModifier("Light Armor", 0.03),
        ),
    )

    trace = BlockStatCalculator().block_cost(inputs)

    assert trace.raw_value == pytest.approx(673.54366464)
    assert trace.final_value == 674


def test_block_mitigation_amount_blocked_bucket_uses_base_unblocked_half():
    inputs = BlockMitigationInputs(
        amount_blocked_modifiers=(
            ("Sword and Board", 0.20),
            ("Iron Skin", 0.10),
            ("Fortification", 0.04),
        ),
    )

    trace = BlockStatCalculator().block_mitigation(inputs)

    assert trace.final_value == pytest.approx(0.67)


def test_heavy_armor_block_mitigation_is_direct_percentage_points():
    inputs = BlockMitigationInputs(
        direct_points=(("Heavy Armor", 0.05),),
        amount_blocked_modifiers=(("Sword and Board", 0.20),),
    )

    trace = BlockStatCalculator().block_mitigation(inputs)

    assert trace.final_value == pytest.approx(0.65)
