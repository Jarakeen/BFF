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
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_conditional_actual_heal_optimization_service import (
    ExtremeRuntimeSnapshotConditionalActualHealOptimizationService,
)


class ExtremeConditionalActualHealClassRouteCatalogService:
    """Rank whole-character heal routes under explicit emergency conditions.

    The ordinary class-route catalog remains the standing-heal path. This wrapper
    constructs the same route/heal/base-class search around the conditional actual-
    heal optimizer so target-health mechanics are evaluated consistently on every
    route and every whole-build candidate rebuild.

    Runtime-condition windows may now come from the shared ``ExtremeRuntimeSnapshot``.
    Legacy Restoration-heavy and Sacred Ground booleans remain compatibility inputs,
    but production route search no longer needs parallel healer-only runtime truth
    when the unified snapshot already proves those windows at the evaluation instant.

    Cross-class search defaults on here because the Extreme conditional objective
    asks for the strongest legal hypothetical healer, not merely the strongest
    emergency heal available to the saved build's current base class.
    """

    def __init__(
        self,
        *,
        target_health_fraction: float,
        fully_charged_restoration_heavy_attack_completed: bool = False,
        sacred_ground_window_active: bool = False,
        runtime_snapshot: ExtremeRuntimeSnapshot | None = None,
        database_path: str | Path | None = None,
        catalog: ExtremeActualHealClassRouteCatalogService | None = None,
        conditional_optimizer: ExtremeConditionalActualHealOptimizationService | None = None,
    ) -> None:
        value = float(target_health_fraction)
        if not 0.0 <= value <= 1.0:
            raise ValueError("target_health_fraction must be between 0 and 1")
        self.target_health_fraction = value
        self.runtime_snapshot = runtime_snapshot

        if catalog is not None:
            self.catalog = catalog
            self.optimizer = conditional_optimizer
            self.fully_charged_restoration_heavy_attack_completed = bool(
                fully_charged_restoration_heavy_attack_completed
            )
            self.sacred_ground_window_active = bool(sacred_ground_window_active)
            return

        optimizer = conditional_optimizer or (
            ExtremeRuntimeSnapshotConditionalActualHealOptimizationService(
                target_health_fraction=value,
                runtime_snapshot=runtime_snapshot,
                fully_charged_restoration_heavy_attack_completed=(
                    fully_charged_restoration_heavy_attack_completed
                ),
                sacred_ground_window_active=sacred_ground_window_active,
            )
        )
        self.optimizer = optimizer
        self.fully_charged_restoration_heavy_attack_completed = bool(
            getattr(
                optimizer,
                "fully_charged_restoration_heavy_attack_completed",
                fully_charged_restoration_heavy_attack_completed,
            )
        )
        self.sacred_ground_window_active = bool(
            getattr(
                optimizer,
                "sacred_ground_window_active",
                sacred_ground_window_active,
            )
        )
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
        if self.runtime_snapshot is not None:
            scenarios.append(
                "unified runtime snapshot at "
                f"{self.runtime_snapshot.snapshot_time_seconds:.6f}s"
            )
        if self.sacred_ground_window_active:
            scenarios.append(
                "Sacred Ground active/grace window proven at the runtime snapshot; "
                "Minor Mending still requires canonical build/passive legality"
            )
        if self.fully_charged_restoration_heavy_attack_completed:
            if self.runtime_snapshot is not None:
                scenarios.append(
                    "Restoration Staff heavy post-completion window proven at the runtime snapshot; "
                    "Essence Drain Major Mending still requires canonical weapon/passive legality"
                )
            else:
                scenarios.append(
                    "explicit fully charged Restoration Staff heavy attack completed; "
                    "Essence Drain Major Mending requires canonical weapon/passive legality proof"
                )
        return replace(
            result,
            search_scope=(*scenarios, *result.search_scope),
        )
