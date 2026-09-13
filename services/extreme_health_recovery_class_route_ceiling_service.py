from __future__ import annotations

"""Numeric Health Recovery ceilings for already proof-reduced class-route signatures.

This layer is intentionally narrower than whole-record scoring.  It scores only
reviewed class-line recovery mechanics and refuses to flatten unresolved Class
Mastery runtime formulas into a fake exact value.
"""

from dataclasses import dataclass

from services.extreme_health_recovery_class_route_signature_service import (
    ExtremeHealthRecoveryClassRouteSignature,
    ExtremeHealthRecoveryClassRouteSignatureCatalog,
)


_LINE_FLAT = {
    "draconic_power": 700.0,        # Elder Dragon, maximum missing-health ceiling
    "living_death": 155.0,          # Undead Confederate
    "storm_calling": 141.0,         # Capacitor
}
_WELLSPRING_PER_SLOTTED = 81.0


@dataclass(frozen=True)
class ExtremeHealthRecoveryRouteCeiling:
    signature: ExtremeHealthRecoveryClassRouteSignature
    class_flat_ceiling: float | None
    wellspring_slots: int
    unresolved: tuple[str, ...] = ()

    @property
    def score_complete(self) -> bool:
        return self.class_flat_ceiling is not None and not self.unresolved


@dataclass(frozen=True)
class ExtremeHealthRecoveryRouteCeilingCatalog:
    rows: tuple[ExtremeHealthRecoveryRouteCeiling, ...]

    @property
    def complete_rows(self) -> tuple[ExtremeHealthRecoveryRouteCeiling, ...]:
        return tuple(row for row in self.rows if row.score_complete)

    @property
    def unresolved_rows(self) -> tuple[ExtremeHealthRecoveryRouteCeiling, ...]:
        return tuple(row for row in self.rows if not row.score_complete)

    @property
    def best_complete(self) -> ExtremeHealthRecoveryRouteCeiling | None:
        rows = self.complete_rows
        if not rows:
            return None
        return max(
            rows,
            key=lambda row: (
                float(row.class_flat_ceiling or 0.0),
                row.signature.relevant_skill_lines,
            ),
        )


class ExtremeHealthRecoveryClassRouteCeilingService:
    @classmethod
    def score_signature(
        cls,
        signature: ExtremeHealthRecoveryClassRouteSignature,
        *,
        wellspring_slot_ceiling: int,
    ) -> ExtremeHealthRecoveryRouteCeiling:
        if wellspring_slot_ceiling < 0 or wellspring_slot_ceiling > 6:
            raise ValueError("Wellspring slot ceiling must be between 0 and 6")

        if signature.class_mastery == "booming_voice":
            return ExtremeHealthRecoveryRouteCeiling(
                signature=signature,
                class_flat_ceiling=None,
                wellspring_slots=0,
                unresolved=(
                    "Booming Voice recovery ceiling still requires a proven legal Ultimate-spend bound",
                ),
            )
        if signature.class_mastery == "devout_guardian":
            return ExtremeHealthRecoveryRouteCeiling(
                signature=signature,
                class_flat_ceiling=None,
                wellspring_slots=0,
                unresolved=(
                    "Devout Guardian recovery relevance still requires explicit Class Mastery semantic review",
                ),
            )

        total = 0.0
        slots = 0
        for line in signature.relevant_skill_lines:
            total += _LINE_FLAT.get(line, 0.0)
            if line == "soldier_of_apocrypha":
                slots = int(wellspring_slot_ceiling)
                total += _WELLSPRING_PER_SLOTTED * slots

        if signature.class_mastery == "sphere_of_influence":
            total += 225.0

        return ExtremeHealthRecoveryRouteCeiling(
            signature=signature,
            class_flat_ceiling=total,
            wellspring_slots=slots,
        )

    @classmethod
    def build(
        cls,
        signatures: ExtremeHealthRecoveryClassRouteSignatureCatalog,
        *,
        wellspring_slot_ceiling: int,
    ) -> ExtremeHealthRecoveryRouteCeilingCatalog:
        return ExtremeHealthRecoveryRouteCeilingCatalog(
            rows=tuple(
                cls.score_signature(
                    group.signature,
                    wellspring_slot_ceiling=wellspring_slot_ceiling,
                )
                for group in signatures.groups
            )
        )


__all__ = [
    "ExtremeHealthRecoveryClassRouteCeilingService",
    "ExtremeHealthRecoveryRouteCeiling",
    "ExtremeHealthRecoveryRouteCeilingCatalog",
]
