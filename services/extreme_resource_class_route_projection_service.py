from __future__ import annotations

"""Proof-reduce legal class/subclass routes for Extreme max-resource ceilings.

The complete legal route universe remains the denominator.  For Max Magicka and
Max Stamina, a route may be represented by another legal route only when the
canonical passive coverage audit is complete and both routes own the same set of
class skill lines that contain reviewed resource-relevant contextual passives.

Non-class passive axes (Mages Guild, Undaunted, Emperor, etc.) do not distinguish
class routes and remain owned by their existing finite-axis services.  The reducer
never invents a synthetic subclass configuration: every retained witness is one of
the original legal routes.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.extreme_heal_class_route_service import (
    ExtremeHealClassRoute,
    ExtremeHealClassRouteService,
    canonical_class_skill_line_id,
)
from services.extreme_resource_contextual_passive_review_service import (
    ExtremeResourceContextualPassiveReviewService,
    ExtremeResourceContextualPassiveStatus,
)
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)


_SUPPORTED_OBJECTIVES = frozenset({"max_magicka", "max_stamina"})
_CLASS_LINE_IDS = frozenset(
    canonical_class_skill_line_id(value)
    for value in ExtremeHealClassRouteService.ALL_CLASS_LINES
)


@dataclass(frozen=True)
class ExtremeResourceClassRouteProjection:
    objective_key: str
    source_route_count: int
    routes: tuple[ExtremeHealClassRoute, ...]
    relevant_class_lines: tuple[str, ...]
    signatures: tuple[tuple[str, ...], ...]
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(
            self.denominator_proven
            and self.source_route_count > 0
            and self.routes
            and len(self.routes) == len(self.signatures)
            and not self.unresolved
        )

    @property
    def scope(self) -> tuple[str, ...]:
        if not self.projection_complete:
            return ()
        lines = ", ".join(self.relevant_class_lines) or "none"
        return (
            "legal class/subclass routes proof-reduced by reviewed max-resource "
            f"class-passive ownership signature ({lines}); "
            f"{self.source_route_count} legal routes -> {len(self.routes)} exact witnesses",
        )


class ExtremeResourceClassRouteProjectionService:
    """Collapse legal routes by their target-resource class-passive signature."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        passive_audit_service: Any | None = None,
    ) -> None:
        if passive_audit_service is None and database_path is None:
            raise ValueError(
                "database_path is required when no passive audit service is supplied"
            )
        self.passive_audit_service = passive_audit_service or (
            ExtremeResourcePassiveCoverageAuditService(database_path)
        )

    @staticmethod
    def _route_identity(route: ExtremeHealClassRoute) -> tuple[str, bool, tuple[str, ...]]:
        return (
            str(route.base_class.value),
            bool(route.is_subclassed),
            tuple(route.equipped_skill_lines),
        )

    @classmethod
    def _relevant_class_lines(cls, objective_key: str) -> tuple[str, ...]:
        rows = ExtremeResourceContextualPassiveReviewService.status_rows(
            objective_key,
            ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
        )
        values = {
            canonical_class_skill_line_id(row.skill_line)
            for row in rows
            if canonical_class_skill_line_id(row.skill_line) in _CLASS_LINE_IDS
        }
        return tuple(sorted(values))

    @staticmethod
    def _signature(
        route: ExtremeHealClassRoute,
        relevant_lines: tuple[str, ...],
    ) -> tuple[str, ...]:
        selected = {
            canonical_class_skill_line_id(value)
            for value in route.equipped_skill_lines
        }
        return tuple(line for line in relevant_lines if line in selected)

    def build(
        self,
        objective_key: str,
        source_routes: tuple[ExtremeHealClassRoute, ...],
    ) -> ExtremeResourceClassRouteProjection:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(
                f"unreviewed Extreme class-route projection objective: {objective_key!r}"
            )

        routes = tuple(source_routes or ())
        unresolved: list[str] = []
        audit = self.passive_audit_service.build(key)
        if not bool(getattr(audit, "projection_complete", False)):
            unresolved.append(
                "Class-route projection requires complete canonical max-resource passive coverage"
            )

        relevant_lines = self._relevant_class_lines(key)
        if not relevant_lines:
            unresolved.append(
                f"No reviewed route-sensitive class lines were found for {key}"
            )
        if not routes:
            unresolved.append("Canonical legal class-route universe is empty")

        witnesses: dict[tuple[str, ...], ExtremeHealClassRoute] = {}
        for route in routes:
            signature = self._signature(route, relevant_lines)
            current = witnesses.get(signature)
            if current is None or self._route_identity(route) < self._route_identity(current):
                witnesses[signature] = route

        signatures = tuple(sorted(witnesses))
        retained = tuple(witnesses[signature] for signature in signatures)
        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        denominator_proven = bool(
            routes
            and relevant_lines
            and bool(getattr(audit, "projection_complete", False))
            and witnesses
            and not final_unresolved
        )
        return ExtremeResourceClassRouteProjection(
            objective_key=key,
            source_route_count=len(routes),
            routes=retained,
            relevant_class_lines=relevant_lines,
            signatures=signatures,
            denominator_proven=denominator_proven,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeResourceClassRouteProjection",
    "ExtremeResourceClassRouteProjectionService",
]
