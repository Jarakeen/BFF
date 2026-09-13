from __future__ import annotations

"""Proof-reduce legal class routes for Extreme Max Health.

The complete legal route universe remains the denominator. Routes may share one
canonical scoring witness only when they own the same reviewed Max Health class-line
semantics and the same pure-Necromancer Class Mastery eligibility.

This is deliberately narrower than general class equivalence. The projection relies
on the complete max-resource passive coverage audit and the reviewed Max Health
contextual-passive ledger. Non-class axes (Heavy Armor Juggernaut, Undaunted Mettle,
Emperor, gear, provisioning, etc.) remain owned by their existing finite-axis services.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.character_class import CharacterClass
from services.extreme_heal_class_route_service import (
    ExtremeHealClassRoute,
    canonical_class_skill_line_id,
)
from services.extreme_resource_contextual_passive_review_service import (
    ExtremeResourceContextualPassiveReviewService,
    ExtremeResourceContextualPassiveStatus,
)
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)


OBJECTIVE = "max_health"
_CLASS_LINE_KEYS = frozenset(
    canonical_class_skill_line_id(value)
    for value in (
        "Bone Tyrant",
        "Shadow",
        "Green Balance",
        "Daedric Summoning",
    )
)
_CLASS_MASTERY_KEY = "class_mastery"


@dataclass(frozen=True)
class ExtremeMaxHealthClassRouteProjection:
    source_route_count: int
    routes: tuple[ExtremeHealClassRoute, ...]
    signatures: tuple[tuple[str, ...], ...]
    reviewed_route_axes: tuple[str, ...]
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


class ExtremeMaxHealthClassRouteProjectionService:
    """Collapse 3-line class routes by exact reviewed Max Health semantics."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        passive_audit_service: ExtremeResourcePassiveCoverageAuditService | None = None,
    ) -> None:
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

    @staticmethod
    def _nothing_wasted_eligible(route: ExtremeHealClassRoute) -> bool:
        return bool(
            route.class_mastery_allowed
            and route.base_class is CharacterClass.NECROMANCER
        )

    @classmethod
    def _signature(cls, route: ExtremeHealClassRoute) -> tuple[str, ...]:
        selected = {
            canonical_class_skill_line_id(value)
            for value in route.equipped_skill_lines
        }
        values = sorted(line for line in _CLASS_LINE_KEYS if line in selected)
        if cls._nothing_wasted_eligible(route):
            values.append(_CLASS_MASTERY_KEY)
        return tuple(values)

    @staticmethod
    def _reviewed_axes() -> tuple[str, ...]:
        rows = ExtremeResourceContextualPassiveReviewService.status_rows(
            OBJECTIVE,
            ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
        )
        axes: set[str] = set()
        for row in rows:
            line = canonical_class_skill_line_id(row.skill_line)
            if line in _CLASS_LINE_KEYS:
                axes.add(line)
            elif str(row.skill_line).strip().casefold() == "class mastery":
                axes.add(_CLASS_MASTERY_KEY)
        return tuple(sorted(axes))

    def build(
        self,
        source_routes: tuple[ExtremeHealClassRoute, ...],
    ) -> ExtremeMaxHealthClassRouteProjection:
        routes = tuple(source_routes or ())
        unresolved: list[str] = []

        audit = self.passive_audit_service.build(OBJECTIVE)
        if not bool(getattr(audit, "projection_complete", False)):
            unresolved.append(
                "Max Health class-route projection requires complete canonical passive coverage"
            )

        reviewed_axes = self._reviewed_axes()
        expected_axes = tuple(sorted((*_CLASS_LINE_KEYS, _CLASS_MASTERY_KEY)))
        if reviewed_axes != expected_axes:
            unresolved.append(
                "Reviewed Max Health class-route axes do not match the projection contract: "
                f"expected={expected_axes!r}, reviewed={reviewed_axes!r}"
            )
        if not routes:
            unresolved.append("Canonical legal class-route universe is empty")

        witnesses: dict[tuple[str, ...], ExtremeHealClassRoute] = {}
        for route in routes:
            signature = self._signature(route)
            current = witnesses.get(signature)
            if current is None or self._route_identity(route) < self._route_identity(current):
                witnesses[signature] = route

        signatures = tuple(sorted(witnesses))
        retained = tuple(witnesses[signature] for signature in signatures)
        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        denominator_proven = bool(
            routes
            and witnesses
            and reviewed_axes == expected_axes
            and bool(getattr(audit, "projection_complete", False))
            and not final_unresolved
        )
        return ExtremeMaxHealthClassRouteProjection(
            source_route_count=len(routes),
            routes=retained,
            signatures=signatures,
            reviewed_route_axes=reviewed_axes,
            denominator_proven=denominator_proven,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeMaxHealthClassRouteProjection",
    "ExtremeMaxHealthClassRouteProjectionService",
]
