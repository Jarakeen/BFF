from __future__ import annotations

"""Proof-owned attribute-axis reduction for Extreme max-resource records.

The generic Extreme structural universe correctly enumerates the complete integer
simplex of 64 Health/Magicka/Stamina attribute points.  For the three maximum
resource objectives, however, the canonical primary-resource formula depends on
only the objective's own attribute-point count and uses a strictly positive
per-point coefficient.  The other two allocations do not enter that resource
formula.

This service therefore proves that the complete 2,145-allocation simplex may be
represented by the single legal witness with all 64 points in the requested
resource.  It owns no character-sheet arithmetic beyond importing the canonical
per-point constants used by ``BaseCharacterCalculator``.

The projection is deliberately objective-specific.  Damage, healing, recovery,
and any objective that can depend on highest-resource/highest-attribute selection
must continue to enumerate the full structural attribute universe unless it owns a
separate proof.
"""

from dataclasses import dataclass

from minmax.base_character_state import (
    HEALTH_PER_ATTRIBUTE,
    MAGICKA_PER_ATTRIBUTE,
    STAMINA_PER_ATTRIBUTE,
)
from minmax.character_progression import AttributeAllocation
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService


@dataclass(frozen=True)
class ExtremeResourceAttributeProjection:
    objective_key: str
    allocations: tuple[AttributeAllocation, ...]
    source_allocations_reviewed: int
    target_points: int
    per_point_value: float
    denominator_proven: bool
    scope: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(
            self.denominator_proven
            and self.allocations
            and self.target_points == ExtremeGlobalSearchUniverseService.ATTRIBUTE_POINTS
            and self.per_point_value > 0.0
            and not self.unresolved
        )


class ExtremeResourceAttributeProjectionService:
    """Reduce the full legal attribute simplex to the monotonic target witness."""

    _OBJECTIVES = {
        "max_health": ("health", float(HEALTH_PER_ATTRIBUTE)),
        "max_magicka": ("magicka", float(MAGICKA_PER_ATTRIBUTE)),
        "max_stamina": ("stamina", float(STAMINA_PER_ATTRIBUTE)),
    }

    @staticmethod
    def _identity(allocation: AttributeAllocation) -> tuple[int, int, int]:
        return (
            int(allocation.health),
            int(allocation.magicka),
            int(allocation.stamina),
        )

    @classmethod
    def build(
        cls,
        objective_key: str,
        source_allocations: tuple[AttributeAllocation, ...],
    ) -> ExtremeResourceAttributeProjection:
        key = str(objective_key or "").strip().casefold()
        resolved = cls._OBJECTIVES.get(key)
        if resolved is None:
            raise KeyError(f"unreviewed Extreme resource attribute objective: {objective_key!r}")

        target_name, per_point = resolved
        total = int(ExtremeGlobalSearchUniverseService.ATTRIBUTE_POINTS)
        canonical = ExtremeGlobalSearchUniverseService.attribute_allocations()
        source_ids = tuple(sorted(cls._identity(row) for row in source_allocations))
        canonical_ids = tuple(sorted(cls._identity(row) for row in canonical))

        unresolved: list[str] = []
        if source_ids != canonical_ids:
            unresolved.append(
                "Structural attribute source does not match the complete canonical 64-point simplex"
            )
        if per_point <= 0.0:
            unresolved.append(
                f"Canonical {target_name} per-attribute value is not strictly positive: {per_point}"
            )

        if target_name == "health":
            witness = AttributeAllocation(health=total, magicka=0, stamina=0)
        elif target_name == "magicka":
            witness = AttributeAllocation(health=0, magicka=total, stamina=0)
        else:
            witness = AttributeAllocation(health=0, magicka=0, stamina=total)

        if cls._identity(witness) not in set(source_ids):
            unresolved.append(
                f"Canonical all-{target_name} attribute witness is missing from structural source"
            )

        scope = (
            f"all {len(canonical):,} legal 64-point Health/Magicka/Stamina allocations proof-reduced "
            f"to the monotonic 64-{target_name} witness for {key}",
        )
        return ExtremeResourceAttributeProjection(
            objective_key=key,
            allocations=(witness,) if not unresolved else (),
            source_allocations_reviewed=len(source_allocations),
            target_points=total,
            per_point_value=per_point,
            denominator_proven=not unresolved,
            scope=scope,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeResourceAttributeProjection",
    "ExtremeResourceAttributeProjectionService",
]
