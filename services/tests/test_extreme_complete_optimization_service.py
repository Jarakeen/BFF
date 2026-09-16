from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.block_stats import BlockStatCalculator
from minmax.stat_ids import StatId
from services.extreme_complete_optimization_service import (
    BLOCK_COST_REDUCTION_OBJECTIVE,
    BLOCK_MITIGATION_OBJECTIVE,
    COMPLETE_EXTREME_OBJECTIVES,
    CRITICAL_HEALING_OBJECTIVE,
    ExtremeCompleteOptimizationService,
)


def test_complete_catalog_adds_critical_healing_and_block_objectives() -> None:
    critical = ExtremeCompleteOptimizationService.objective("critical_healing")
    mitigation = ExtremeCompleteOptimizationService.objective("block_mitigation")
    block_cost = ExtremeCompleteOptimizationService.objective("block_cost_reduction")

    assert critical is CRITICAL_HEALING_OBJECTIVE
    assert critical.label == "Critical Healing"
    assert critical.ratio is True
    assert mitigation is BLOCK_MITIGATION_OBJECTIVE
    assert mitigation.ratio is True
    assert block_cost is BLOCK_COST_REDUCTION_OBJECTIVE
    assert block_cost.ratio is True
    assert COMPLETE_EXTREME_OBJECTIVES[-3:] == (
        critical,
        mitigation,
        block_cost,
    )


def test_critical_healing_reads_shared_canonical_core_stat() -> None:
    context = SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.CRITICAL_HEALING: SimpleNamespace(final_value=0.37),
            }
        )
    )

    value = ExtremeCompleteOptimizationService._objective_value(
        context,
        CRITICAL_HEALING_OBJECTIVE,
    )

    assert value == pytest.approx(0.37)


def test_block_mitigation_reads_shared_canonical_block_trace() -> None:
    context = SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.BLOCK_MITIGATION: SimpleNamespace(final_value=0.73),
            }
        )
    )

    value = ExtremeCompleteOptimizationService._objective_value(
        context,
        BLOCK_MITIGATION_OBJECTIVE,
    )

    assert value == pytest.approx(0.73)


def test_block_cost_reduction_scores_fraction_removed_from_canonical_base() -> None:
    context = SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.BLOCK_COST: SimpleNamespace(final_value=875.0),
            }
        )
    )

    value = ExtremeCompleteOptimizationService._objective_value(
        context,
        BLOCK_COST_REDUCTION_OBJECTIVE,
    )

    assert BlockStatCalculator.BASE_BLOCK_COST == pytest.approx(1750.0)
    assert value == pytest.approx(0.50)


def test_block_cost_reduction_never_rewards_cost_above_base() -> None:
    context = SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.BLOCK_COST: SimpleNamespace(final_value=1900.0),
            }
        )
    )

    value = ExtremeCompleteOptimizationService._objective_value(
        context,
        BLOCK_COST_REDUCTION_OBJECTIVE,
    )

    assert value == 0.0


def test_complete_service_delegates_existing_objectives_to_legacy_canonical_path() -> None:
    context = SimpleNamespace(
        character_state=SimpleNamespace(
            max_health=54321.0,
            max_magicka=0.0,
            max_stamina=0.0,
            health_recovery=0.0,
            magicka_recovery=0.0,
            stamina_recovery=0.0,
        ),
        core_state=SimpleNamespace(derived={}),
    )

    value = ExtremeCompleteOptimizationService._objective_value(
        context,
        ExtremeCompleteOptimizationService.objective("max_health"),
    )

    assert value == pytest.approx(54321.0)
