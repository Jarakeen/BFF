from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from services.extreme_actual_heal_armor_progression_service import (
    ExtremeActualHealArmorProgressionService,
)
from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogService,
)
from services.extreme_canonical_actual_heal_optimization_service import (
    ExtremeCanonicalActualHealOptimizationService,
)


class _InjectedOptimizer:
    def __init__(self) -> None:
        self.optimizer = SimpleNamespace(database_path=Path("fake.db"))


def test_route_catalog_defaults_to_canonical_actual_heal_optimizer():
    service = ExtremeActualHealClassRouteCatalogService()

    assert isinstance(service.optimizer, ExtremeCanonicalActualHealOptimizationService)
    assert isinstance(
        service.progression_normalizer,
        ExtremeActualHealArmorProgressionService,
    )


def test_route_catalog_preserves_explicitly_injected_optimizer():
    optimizer = _InjectedOptimizer()
    progression = object()
    service = ExtremeActualHealClassRouteCatalogService(
        optimizer=optimizer,
        candidates=object(),
        routes=object(),
        progression_normalizer=progression,
    )

    assert service.optimizer is optimizer
    assert service.progression_normalizer is progression
