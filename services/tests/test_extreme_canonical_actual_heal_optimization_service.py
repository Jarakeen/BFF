from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from services.extreme_canonical_actual_heal_optimization_service import (
    ExtremeCanonicalActualHealOptimizationService,
)
from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
)


def _optimizer():
    return SimpleNamespace(database_path=Path("ignored.db"))


def test_standing_optimizer_defaults_to_canonical_healing_event_service():
    service = ExtremeCanonicalActualHealOptimizationService(
        optimizer=_optimizer(),
    )

    assert isinstance(service.healing_events, ExtremeCanonicalHealingEventService)


def test_explicit_healing_event_evaluator_remains_authoritative():
    custom = object()
    service = ExtremeCanonicalActualHealOptimizationService(
        optimizer=_optimizer(),
        healing_events=custom,
    )

    assert service.healing_events is custom
