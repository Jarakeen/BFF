from __future__ import annotations

from dataclasses import dataclass

from models.build_model import PlayerBuild
from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogResult,
    ExtremeActualHealClassRouteCatalogService,
)


_HEAL_EVENT_RECORD_KEYS = ("actual_heal", "critical_heal")


@dataclass(frozen=True)
class ExtremeHealingEventRecordResult:
    objective_key: str
    catalog: ExtremeActualHealClassRouteCatalogResult

    @property
    def best_scored_value(self) -> float | None:
        entry = self.catalog.best_scored
        if entry is None:
            return None
        return entry.critical_heal

    @property
    def best_complete_value(self) -> float | None:
        entry = self.catalog.best_complete
        if entry is None:
            return None
        return entry.critical_heal

    @property
    def mechanic_complete(self) -> bool:
        entry = self.catalog.best_scored
        return bool(entry is not None and entry.mechanic_complete)

    @property
    def global_maximum_proven(self) -> bool:
        return bool(self.catalog.global_maximum_proven)


class ExtremeHealingEventRecordService:
    """Project one canonical H1 search into both heal-event record identities.

    ESO's largest realizable single healing event may be a critical event. The
    canonical healing-event service therefore already exposes ``critical_heal``
    as the event ceiling while retaining ``normal_heal`` separately for evidence.
    ``MOST Actual Heal`` and ``MOST Critical Heal`` consequently share the same
    legal-character search and winner today; this service makes that reuse
    explicit instead of running the expensive class-route/gear/skill search twice.

    This projection does not broaden H1 proof scope. Any omitted class-passive,
    multi-skill, group, or runtime surface reported by the underlying catalog
    remains attached to both record identities.
    """

    def __init__(
        self,
        catalog: ExtremeActualHealClassRouteCatalogService | None = None,
    ) -> None:
        self.catalog = catalog or ExtremeActualHealClassRouteCatalogService()

    def evaluate_pair(
        self,
        baseline_build: PlayerBuild,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
    ) -> tuple[ExtremeHealingEventRecordResult, ExtremeHealingEventRecordResult]:
        ranked = self.catalog.rank(
            baseline_build,
            active_bar=active_bar,
            max_passes=max_passes,
            include_base_class_changes=True,
        )
        return tuple(
            ExtremeHealingEventRecordResult(objective_key=key, catalog=ranked)
            for key in _HEAL_EVENT_RECORD_KEYS
        )  # type: ignore[return-value]

    def evaluate(
        self,
        baseline_build: PlayerBuild,
        objective_key: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
    ) -> ExtremeHealingEventRecordResult:
        normalized = str(objective_key or "").strip().casefold()
        if normalized not in _HEAL_EVENT_RECORD_KEYS:
            raise ValueError(f"Unsupported healing-event Extreme record: {objective_key!r}")
        actual, critical = self.evaluate_pair(
            baseline_build,
            active_bar=active_bar,
            max_passes=max_passes,
        )
        return actual if normalized == "actual_heal" else critical


__all__ = [
    "ExtremeHealingEventRecordResult",
    "ExtremeHealingEventRecordService",
]
