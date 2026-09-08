from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.stat_ids import StatId
from services.extreme_complete_optimization_service import (
    COMPLETE_EXTREME_OBJECTIVES,
    CRITICAL_HEALING_OBJECTIVE,
    ExtremeCompleteOptimizationService,
)


def test_complete_catalog_adds_critical_healing_as_ratio_objective() -> None:
    objective = ExtremeCompleteOptimizationService.objective("critical_healing")

    assert objective is CRITICAL_HEALING_OBJECTIVE
    assert objective.label == "Critical Healing"
    assert objective.ratio is True
    assert COMPLETE_EXTREME_OBJECTIVES[-1] is objective


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
