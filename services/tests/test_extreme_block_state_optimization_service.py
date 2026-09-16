from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.block_stats import BlockStatCalculator
from minmax.derived_stats import DerivedStatTrace
from minmax.stat_ids import StatId
from services.extreme_block_state_optimization_service import (
    BLOCK_COST_REDUCTION_OBJECTIVE,
    BLOCK_MITIGATION_OBJECTIVE,
    ExtremeBlockStateOptimizationService,
)


def _context(*, block_cost: float = 1750.0, block_mitigation: float = 0.50):
    cost = DerivedStatTrace(stat=StatId.BLOCK_COST)
    cost.final_value = float(block_cost)
    mitigation = DerivedStatTrace(stat=StatId.BLOCK_MITIGATION)
    mitigation.final_value = float(block_mitigation)
    return SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.BLOCK_COST: cost,
                StatId.BLOCK_MITIGATION: mitigation,
            }
        )
    )


def test_block_state_objectives_are_owned_by_one_shared_service() -> None:
    assert ExtremeBlockStateOptimizationService.objective("block_mitigation") is BLOCK_MITIGATION_OBJECTIVE
    assert ExtremeBlockStateOptimizationService.objective("block_cost_reduction") is BLOCK_COST_REDUCTION_OBJECTIVE


def test_block_mitigation_scores_canonical_ratio_directly() -> None:
    value = ExtremeBlockStateOptimizationService._objective_value(
        _context(block_mitigation=0.73),
        BLOCK_MITIGATION_OBJECTIVE,
    )
    assert value == pytest.approx(0.73)


def test_block_cost_reduction_scores_fraction_removed_from_canonical_base() -> None:
    value = ExtremeBlockStateOptimizationService._objective_value(
        _context(block_cost=875.0),
        BLOCK_COST_REDUCTION_OBJECTIVE,
    )
    assert value == pytest.approx(0.50)
    assert BlockStatCalculator.BASE_BLOCK_COST == pytest.approx(1750.0)


def test_block_cost_reduction_never_rewards_cost_above_base() -> None:
    value = ExtremeBlockStateOptimizationService._objective_value(
        _context(block_cost=1900.0),
        BLOCK_COST_REDUCTION_OBJECTIVE,
    )
    assert value == 0.0
