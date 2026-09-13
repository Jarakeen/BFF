from __future__ import annotations

"""Numeric Health Recovery ceilings for already proof-reduced class-route signatures.

This layer is intentionally narrower than whole-record scoring. It scores only
reviewed class-line recovery mechanics and Class Mastery ceilings whose legal
runtime maxima have been independently proven.
"""

from dataclasses import dataclass

from services.class_mastery_extreme_effect_service import (
    ClassMasteryExtremeEffectService,
)
from services.class_mastery_repository import ClassMasteryPassive
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

# U50 canonical Ultimate-cost frontier for a pure Dragonknight. The dedicated
# Booming Voice audit proves that all 46 legal Ultimate choices with canonical
# costs top out at 250 Ultimate (Aggressive Horn / Barrier / Destruction Staff
# family), while the passive grants 5 recovery for every Ultimate spent.
_BOOMING_VOICE_MAX_ULTIMATE_COST = 250.0
_BOOMING_VOICE_RECOVERY_PER_ULTIMATE = 5.0
_BOOMING_VOICE_FLAT_CEILING = (
    _BOOMING_VOICE_MAX_ULTIMATE_COST * _BOOMING_VOICE_RECOVERY_PER_ULTIMATE
)

_MASTERY_IDENTITIES = {
    "sphere_of_influence": ("Sorcerer", "Sphere of Influence"),
    "devout_guardian": ("Templar", "Devout Guardian"),
}


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
    @staticmethod
    def _reviewed_mastery_health_recovery_flat(mastery_key: str | None) -> float | None:
        identity = _MASTERY_IDENTITIES.get(str(mastery_key or ""))
        if identity is None:
            return None
        class_name, passive_name = identity
        passive = ClassMasteryPassive(
            skill_id=0,
            base_ability_id=0,
            name=passive_name,
            class_name=class_name,
            description="",
        )
        rows = tuple(
            row
            for row in ClassMasteryExtremeEffectService.contributions(passive)
            if row.objective_key == "health_recovery"
        )
        if len(rows) != 1:
            return None
        row = rows[0]
        if row.percent or row.additive_ratio:
            return None
        return float(row.flat)

    @classmethod
    def score_signature(
        cls,
        signature: ExtremeHealthRecoveryClassRouteSignature,
        *,
        wellspring_slot_ceiling: int,
    ) -> ExtremeHealthRecoveryRouteCeiling:
        if wellspring_slot_ceiling < 0 or wellspring_slot_ceiling > 6:
            raise ValueError("Wellspring slot ceiling must be between 0 and 6")

        total = 0.0
        slots = 0
        for line in signature.relevant_skill_lines:
            total += _LINE_FLAT.get(line, 0.0)
            if line == "soldier_of_apocrypha":
                slots = int(wellspring_slot_ceiling)
                total += _WELLSPRING_PER_SLOTTED * slots

        if signature.class_mastery == "booming_voice":
            total += _BOOMING_VOICE_FLAT_CEILING
        elif signature.class_mastery:
            mastery_flat = cls._reviewed_mastery_health_recovery_flat(signature.class_mastery)
            if mastery_flat is None:
                return ExtremeHealthRecoveryRouteCeiling(
                    signature=signature,
                    class_flat_ceiling=None,
                    wellspring_slots=slots,
                    unresolved=(
                        f"Class Mastery Health Recovery semantics unavailable for {signature.class_mastery}",
                    ),
                )
            total += mastery_flat

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
