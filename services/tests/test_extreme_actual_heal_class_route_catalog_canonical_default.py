from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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


def test_route_catalog_preserves_explicitly_injected_optimizer():
    optimizer = _InjectedOptimizer()
    service = ExtremeActualHealClassRouteCatalogService(
        optimizer=optimizer,
        candidates=object(),
        routes=object(),
        progression_normalizer=object(),
    )

    assert service.optimizer is optimizer
