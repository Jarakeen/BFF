from __future__ import annotations

from dataclasses import dataclass

from models.build_model import PlayerBuild
from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogResult,
    ExtremeActualHealClassRouteCatalogService,
    ExtremeActualHealClassRouteEntry,
)
from services.extreme_sorcerer_blood_magic_class_route_catalog_service import (
    ExtremeSorcererBloodMagicClassRouteCatalogResult,
    ExtremeSorcererBloodMagicClassRouteCatalogService,
    ExtremeSorcererBloodMagicClassRouteEntry,
)


@dataclass(frozen=True)
class ExtremeMaximumHealingEventRouteEntry:
    """One comparable maximum single-heal event from any modeled route source."""

    source_kind: str
    source_name: str
    event_value: float | None
    event_kind: str
    mechanic_complete: bool
    unresolved: tuple[str, ...]
    route_entry: ExtremeActualHealClassRouteEntry | ExtremeSorcererBloodMagicClassRouteEntry

    @property
    def route(self):
        return self.route_entry.route

    @property
    def slotted_index(self) -> int:
        return int(self.route_entry.slotted_index)


@dataclass(frozen=True)
class ExtremeMaximumHealingEventClassRouteCatalogResult:
    entries: tuple[ExtremeMaximumHealingEventRouteEntry, ...]
    best_scored: ExtremeMaximumHealingEventRouteEntry | None
    best_complete: ExtremeMaximumHealingEventRouteEntry | None
    ordinary: ExtremeActualHealClassRouteCatalogResult
    blood_magic: ExtremeSorcererBloodMagicClassRouteCatalogResult
    search_scope: tuple[str, ...]
    omitted_scope: tuple[str, ...]

    @property
    def global_maximum_proven(self) -> bool:
        return bool(
            self.entries
            and not self.omitted_scope
            and self.best_scored is not None
            and self.best_scored.mechanic_complete
            and all(entry.mechanic_complete for entry in self.entries)
        )


class ExtremeMaximumHealingEventClassRouteCatalogService:
    """Compare modeled route candidates by their largest legal single heal event.

    Ordinary coefficient-backed heals contribute the canonical ``critical_heal``
    maximum. That field already preserves explicitly non-crittable components at
    normal value, while unresolved critical eligibility leaves the maximum
    unresolved. This aggregator therefore must not fall back to ``normal_heal``
    for an ordinary entry whose critical maximum is unknown.

    Blood Magic contributes its normal event because the reviewed Max-Health proc
    policy proves it cannot critically heal. The comparison therefore uses one
    objective for both families: largest healing event delivered to one canonical
    recipient/event identity, not a mixture of critical-only and normal-only
    leaderboards.

    This service is an aggregation boundary only. Each source catalog remains
    authoritative for route legality, build materialization, progression, and
    mechanic completeness.
    """

    SEARCH_SCOPE = (
        "ordinary coefficient-backed maximum healing events across legal class routes",
        "Blood Magic non-critical maximum healing events across legal Dark Magic routes",
        "single event magnitude comparison across critical and explicitly non-critical heal families",
    )

    def __init__(
        self,
        *,
        ordinary: ExtremeActualHealClassRouteCatalogService | None = None,
        blood_magic: ExtremeSorcererBloodMagicClassRouteCatalogService | None = None,
    ) -> None:
        self.ordinary = ordinary if ordinary is not None else ExtremeActualHealClassRouteCatalogService()
        self.blood_magic = (
            blood_magic
            if blood_magic is not None
            else ExtremeSorcererBloodMagicClassRouteCatalogService()
        )

    def rank(
        self,
        baseline_build: PlayerBuild,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
        include_base_class_changes: bool = False,
    ) -> ExtremeMaximumHealingEventClassRouteCatalogResult:
        kwargs = {
            "active_bar": active_bar,
            "max_passes": max_passes,
            "include_base_class_changes": include_base_class_changes,
        }
        ordinary_result = self.ordinary.rank(baseline_build, **kwargs)
        blood_magic_result = self.blood_magic.rank(baseline_build, **kwargs)

        entries = [
            *(self._ordinary_entry(entry) for entry in ordinary_result.entries),
            *(self._blood_magic_entry(entry) for entry in blood_magic_result.entries),
        ]
        ranked = tuple(sorted(entries, key=self._rank_key))
        scored = tuple(entry for entry in ranked if entry.event_value is not None)
        complete = tuple(entry for entry in scored if entry.mechanic_complete)

        search_scope = self._unique(
            (*self.SEARCH_SCOPE, *ordinary_result.search_scope, *blood_magic_result.search_scope)
        )
        omitted_scope = self._unique(
            (
                *ordinary_result.omitted_scope,
                *(
                    item
                    for item in blood_magic_result.omitted_scope
                    if item != "global maximum-event comparison against ordinary-heal candidates"
                ),
            )
        )

        return ExtremeMaximumHealingEventClassRouteCatalogResult(
            entries=ranked,
            best_scored=scored[0] if scored else None,
            best_complete=complete[0] if complete else None,
            ordinary=ordinary_result,
            blood_magic=blood_magic_result,
            search_scope=search_scope,
            omitted_scope=omitted_scope,
        )

    @staticmethod
    def _ordinary_entry(
        entry: ExtremeActualHealClassRouteEntry,
    ) -> ExtremeMaximumHealingEventRouteEntry:
        event_value: float | None = None
        event_kind = "unresolved"
        if entry.optimization is not None:
            value = entry.optimization.optimized_event.critical_heal
            if value is not None:
                event_value = float(value)
                event_kind = "canonical_maximum"
        return ExtremeMaximumHealingEventRouteEntry(
            source_kind="ordinary_skill",
            source_name=entry.candidate.name,
            event_value=event_value,
            event_kind=event_kind,
            mechanic_complete=entry.mechanic_complete,
            unresolved=entry.unresolved,
            route_entry=entry,
        )

    @staticmethod
    def _blood_magic_entry(
        entry: ExtremeSorcererBloodMagicClassRouteEntry,
    ) -> ExtremeMaximumHealingEventRouteEntry:
        value = entry.normal_heal
        return ExtremeMaximumHealingEventRouteEntry(
            source_kind="blood_magic",
            source_name=f"Blood Magic via {entry.trigger.name}",
            event_value=None if value is None else float(value),
            event_kind="normal_noncritical",
            mechanic_complete=entry.mechanic_complete,
            unresolved=entry.unresolved,
            route_entry=entry,
        )

    @staticmethod
    def _rank_key(entry: ExtremeMaximumHealingEventRouteEntry) -> tuple[float, str, str, tuple[str, ...], int]:
        value = entry.event_value
        return (
            -(float(value) if value is not None else float("-inf")),
            entry.source_kind,
            entry.source_name.casefold(),
            entry.route.equipped_skill_lines,
            entry.slotted_index,
        )

    @staticmethod
    def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value for value in values if value))
