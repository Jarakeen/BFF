from __future__ import annotations

"""Proof-reduce projected Extreme class routes by monotonic relevant-line dominance.

The complete legal class-route universe remains the denominator in the upstream
``ExtremeResourceClassRouteProjectionService``.  That service first collapses the
3,220 legal routes to exact witnesses for the reviewed route-sensitive max-resource
class-line signatures.

For Max Magicka and Max Stamina, those reviewed route-sensitive effects are optional,
non-negative max-resource contributions.  Owning an additional relevant line never
forces its trigger onto the active bar; the existing active-bar search remains free to
choose the strongest legal trigger combination.  Therefore, when one retained legal
route owns a relevant-line signature that is a superset of every other retained
signature, that route weakly dominates the other route witnesses for the scalar
maximum objective.

This service owns no passive magnitudes and never invents a route.  It only promotes
an already-retained legal route when the upstream denominator proof is complete.  Any
ambiguity or incomplete projection fails closed to the upstream route frontier.
"""

from dataclasses import dataclass
from pathlib import Path

from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_resource_class_route_projection_service import (
    ExtremeResourceClassRouteProjectionService,
)


_SUPPORTED_OBJECTIVES = frozenset({"max_magicka", "max_stamina"})


@dataclass(frozen=True)
class ExtremeResourceClassRouteDominanceProjection:
    objective_key: str
    source_route_count: int
    projected_route_count: int
    routes: tuple[ExtremeHealClassRoute, ...]
    signature: tuple[str, ...]
    relevant_class_lines: tuple[str, ...]
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(
            self.denominator_proven
            and self.source_route_count > 0
            and self.projected_route_count > 0
            and len(self.routes) == 1
            and self.signature
            and not self.unresolved
        )

    @property
    def scope(self) -> tuple[str, ...]:
        if not self.projection_complete:
            return ()
        route = self.routes[0]
        return (
            "projected legal class-route witnesses proof-reduced by monotonic reviewed "
            "max-resource relevant-line dominance; "
            f"{self.source_route_count} legal routes -> {self.projected_route_count} exact "
            f"signatures -> 1 dominant legal witness ({route.base_class.value}: "
            f"{', '.join(self.signature)})",
        )


class ExtremeResourceClassRouteDominanceProjectionService:
    """Retain one legal route whose reviewed relevant-line signature dominates all."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        route_projection_service: ExtremeResourceClassRouteProjectionService | None = None,
    ) -> None:
        if route_projection_service is None and database_path is None:
            raise ValueError(
                "database_path is required when no class-route projection service is supplied"
            )
        self.route_projection_service = route_projection_service or (
            ExtremeResourceClassRouteProjectionService(database_path)
        )

    @staticmethod
    def _route_identity(route: ExtremeHealClassRoute) -> tuple[str, bool, tuple[str, ...]]:
        return (
            str(route.base_class.value),
            bool(route.is_subclassed),
            tuple(route.equipped_skill_lines),
        )

    def build(
        self,
        objective_key: str,
        source_routes: tuple[ExtremeHealClassRoute, ...],
    ) -> ExtremeResourceClassRouteDominanceProjection:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(
                f"unreviewed Extreme class-route dominance objective: {objective_key!r}"
            )

        source = tuple(source_routes or ())
        upstream = self.route_projection_service.build(key, source)
        routes = tuple(getattr(upstream, "routes", ()) or ())
        signatures = tuple(getattr(upstream, "signatures", ()) or ())
        relevant_class_lines = tuple(
            getattr(upstream, "relevant_class_lines", ()) or ()
        )
        unresolved: list[str] = list(tuple(getattr(upstream, "unresolved", ()) or ()))
        if not bool(getattr(upstream, "projection_complete", False)):
            unresolved.append(
                "Class-route dominance requires complete exact route-signature projection"
            )
            return ExtremeResourceClassRouteDominanceProjection(
                objective_key=key,
                source_route_count=len(source),
                projected_route_count=len(routes),
                routes=(),
                signature=(),
                relevant_class_lines=relevant_class_lines,
                denominator_proven=False,
                unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
            )

        if len(routes) != len(signatures) or not routes:
            unresolved.append(
                "Class-route dominance requires one retained legal witness per exact signature"
            )

        dominant_indexes: list[int] = []
        signature_sets = [set(signature) for signature in signatures]
        for index, candidate in enumerate(signature_sets):
            if all(candidate.issuperset(other) for other in signature_sets):
                dominant_indexes.append(index)

        retained: tuple[ExtremeHealClassRoute, ...] = ()
        dominant_signature: tuple[str, ...] = ()
        if dominant_indexes:
            maximal_signatures = {
                tuple(signatures[index]) for index in dominant_indexes
            }
            if len(maximal_signatures) == 1:
                dominant_signature = next(iter(maximal_signatures))
                candidates = tuple(
                    routes[index]
                    for index in dominant_indexes
                    if tuple(signatures[index]) == dominant_signature
                )
                if candidates:
                    retained = (
                        min(candidates, key=self._route_identity),
                    )
            else:
                unresolved.append(
                    "Class-route dominance found multiple incomparable maximum signatures"
                )
        else:
            unresolved.append(
                "No projected legal class route owns a superset of every reviewed relevant-line signature"
            )

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        denominator_proven = bool(
            source
            and retained
            and dominant_signature
            and not final_unresolved
        )
        return ExtremeResourceClassRouteDominanceProjection(
            objective_key=key,
            source_route_count=len(source),
            projected_route_count=len(routes),
            routes=retained,
            signature=dominant_signature,
            relevant_class_lines=relevant_class_lines,
            denominator_proven=denominator_proven,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeResourceClassRouteDominanceProjection",
    "ExtremeResourceClassRouteDominanceProjectionService",
]
