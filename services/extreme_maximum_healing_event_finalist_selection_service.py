from __future__ import annotations

from dataclasses import dataclass

from services.extreme_maximum_healing_event_class_route_catalog_service import (
    ExtremeMaximumHealingEventClassRouteCatalogResult,
    ExtremeMaximumHealingEventRouteEntry,
)


@dataclass(frozen=True)
class ExtremeMaximumHealingEventFinalistSelectionResult:
    finalists: tuple[ExtremeMaximumHealingEventRouteEntry, ...]
    screened_scored_entries: int
    exact_duplicates_removed: int
    represented_families: int
    max_families: int
    routes_per_family: int
    omitted_scope: tuple[str, ...]


class ExtremeMaximumHealingEventFinalistSelectionService:
    """Choose a route-diverse Stage-2 shortlist from baseline screen results.

    This is deliberately a performance heuristic, not a proof reducer. Entries
    are first deduplicated only when their source, event identity, route, slot,
    value, and unresolved evidence are identical. The remaining candidates are
    grouped by healing-event family, then several distinct class-line routes are
    retained per family. Equal baseline values across different routes are never
    assumed mechanically interchangeable because later build mutations can make
    route passives relevant.
    """

    OMITTED_SCOPE = (
        "whole-build optimization outside the selected Stage-2 finalist families/routes",
        "proof that a lower baseline family cannot overtake after whole-build mutation",
    )

    def select(
        self,
        result: ExtremeMaximumHealingEventClassRouteCatalogResult,
        *,
        max_families: int = 8,
        routes_per_family: int = 3,
    ) -> ExtremeMaximumHealingEventFinalistSelectionResult:
        family_limit = max(1, int(max_families))
        route_limit = max(1, int(routes_per_family))
        scored = tuple(entry for entry in result.entries if entry.event_value is not None)

        unique: list[ExtremeMaximumHealingEventRouteEntry] = []
        seen_exact: set[tuple] = set()
        for entry in scored:
            key = self._exact_key(entry)
            if key in seen_exact:
                continue
            seen_exact.add(key)
            unique.append(entry)

        family_order: list[tuple] = []
        by_family: dict[tuple, list[ExtremeMaximumHealingEventRouteEntry]] = {}
        for entry in unique:
            family = self._family_key(entry)
            if family not in by_family:
                by_family[family] = []
                family_order.append(family)
            by_family[family].append(entry)

        finalists: list[ExtremeMaximumHealingEventRouteEntry] = []
        for family in family_order[:family_limit]:
            seen_routes: set[tuple[str, ...]] = set()
            for entry in by_family[family]:
                route = tuple(entry.route.equipped_skill_lines)
                if route in seen_routes:
                    continue
                seen_routes.add(route)
                finalists.append(entry)
                if len(seen_routes) >= route_limit:
                    break

        return ExtremeMaximumHealingEventFinalistSelectionResult(
            finalists=tuple(finalists),
            screened_scored_entries=len(scored),
            exact_duplicates_removed=len(scored) - len(unique),
            represented_families=min(len(family_order), family_limit),
            max_families=family_limit,
            routes_per_family=route_limit,
            omitted_scope=self.OMITTED_SCOPE,
        )

    @staticmethod
    def _family_key(entry: ExtremeMaximumHealingEventRouteEntry) -> tuple:
        trace = entry.trace
        return (
            entry.source_kind,
            entry.source_name.casefold(),
            entry.event_kind,
            tuple(trace.coefficient_numbers),
            tuple(trace.recipient_scopes),
            tuple(trace.recipient_keys),
            tuple(trace.event_keys),
            tuple(trace.temporal_scopes),
        )

    @classmethod
    def _exact_key(cls, entry: ExtremeMaximumHealingEventRouteEntry) -> tuple:
        return (
            cls._family_key(entry),
            None if entry.event_value is None else float(entry.event_value),
            entry.route.base_class.value,
            tuple(entry.route.equipped_skill_lines),
            int(entry.slotted_index),
            bool(entry.mechanic_complete),
            tuple(entry.unresolved),
            tuple(entry.trace.unresolved),
        )
