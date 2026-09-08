from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from models.build_model import PlayerBuild
from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogResult,
    ExtremeActualHealClassRouteCatalogService,
)
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)


class ExtremeConditionalActualHealClassRouteCatalogService:
    """Rank whole-character heal routes under explicit emergency conditions.

    The ordinary class-route catalog remains the standing-heal path. This wrapper
    constructs the same route/heal/base-class search around the conditional actual-
    heal optimizer so target-health mechanics are evaluated consistently on every
    route and every whole-build candidate rebuild.

    Callers may also request the reviewed post-Restoration-heavy scenario. That
    trigger remains explicit and is delegated to the conditional optimizer, where
    Essence Drain must prove the active Restoration Staff and passive rank before
    Major Mending enters canonical CombatState.

    Cross-class search defaults on here because the Extreme conditional objective
    asks for the strongest legal hypothetical healer, not merely the strongest
    emergency heal available to the saved build's current base class.
    """

    def __init__(
        self,
        *,
        target_health_fraction: float,
        fully_charged_restoration_heavy_attack_completed: bool = False,
        database_path: str | Path | None = None,
        catalog: ExtremeActualHealClassRouteCatalogService | None = None,
        conditional_optimizer: ExtremeConditionalActualHealOptimizationService | None = None,
    ) -> None:
        value = float(target_health_fraction)
        if not 0.0 <= value <= 1.0:
            raise ValueError("target_health_fraction must be between 0 and 1")
        self.target_health_fraction = value
        self.fully_charged_restoration_heavy_attack_completed = bool(
            fully_charged_restoration_heavy_attack_completed
        )

        if catalog is not None:
            self.catalog = catalog
            self.optimizer = conditional_optimizer
            return

        optimizer = conditional_optimizer or ExtremeConditionalActualHealOptimizationService(
            target_health_fraction=value,
            fully_charged_restoration_heavy_attack_completed=(
                self.fully_charged_restoration_heavy_attack_completed
            ),
        )
        self.optimizer = optimizer
        self.catalog = ExtremeActualHealClassRouteCatalogService(
            database_path=database_path,
            optimizer=optimizer,
        )

    def rank(
        self,
        baseline_build: PlayerBuild,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
        include_base_class_changes: bool = True,
    ) -> ExtremeActualHealClassRouteCatalogResult:
        result = self.catalog.rank(
            baseline_build,
            active_bar=active_bar,
            max_passes=max_passes,
            include_base_class_changes=include_base_class_changes,
        )
        scenarios = [
            "explicit conditional target health fraction "
            f"{self.target_health_fraction:.6f}"
        ]
        if self.fully_charged_restoration_heavy_attack_completed:
            scenarios.append(
                "explicit fully charged Restoration Staff heavy attack completed; "
                "Essence Drain Major Mending requires canonical legality proof"
            )
        return replace(
            result,
            search_scope=(*scenarios, *result.search_scope),
        )
