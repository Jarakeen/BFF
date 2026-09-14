from __future__ import annotations

"""Filter canonical named-set slot eligibility by a required armor weight.

This is a shared physical-legality adapter.  It does not score an objective and it
does not realize a loadout.  Armor slots remain eligible only when canonical
``gear_set_piece.armor_type`` evidence supports the requested weight; jewelry and
weapon eligibility are preserved unchanged.  Consumers can then reuse the ordinary
named-set realization/search machinery without a parallel armor-aware solver.
"""

from dataclasses import dataclass, replace
from pathlib import Path

from services.extreme_named_gear_armor_weight_realization_service import (
    ExtremeNamedGearArmorWeightRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


@dataclass(frozen=True)
class ExtremeArmorWeightFilteredSlotEligibilityResult:
    required_armor_weight: str
    catalog: ExtremeNamedGearSetSlotEligibilityCatalog
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        """Whether this adapter's armor-weight projection is complete.

        Upstream catalog diagnostics remain attached to ``catalog.unresolved`` for
        downstream consumers that own the broader named-gear denominator.  They do
        not make this one transformation unresolved unless armor-weight evidence
        itself is missing or malformed.
        """

        return not self.unresolved


class ExtremeArmorWeightFilteredSlotEligibilityService:
    """Project one slot-eligibility catalog through an armor-weight requirement."""

    @staticmethod
    def build(
        database_path: str | Path,
        eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
        *,
        required_armor_weight: str,
    ) -> ExtremeArmorWeightFilteredSlotEligibilityResult:
        weight = str(required_armor_weight or "").strip().title()
        probe = ExtremeNamedGearArmorWeightRealizationService(database_path)
        if weight not in {"Light", "Medium", "Heavy"}:
            return ExtremeArmorWeightFilteredSlotEligibilityResult(
                required_armor_weight=weight,
                catalog=eligibility,
                unresolved=(f"Unknown required armor weight: {required_armor_weight!r}",),
            )

        armor_weights, unresolved = probe._armor_weight_map(tuple(eligibility.sets))
        if unresolved:
            return ExtremeArmorWeightFilteredSlotEligibilityResult(
                required_armor_weight=weight,
                catalog=eligibility,
                unresolved=tuple(unresolved),
            )

        rows = tuple(
            replace(
                row,
                armor_slots=tuple(
                    slot
                    for slot in row.armor_slots
                    if weight in armor_weights.get((int(row.set_id), slot), frozenset())
                ),
            )
            for row in eligibility.sets
        )
        catalog = ExtremeNamedGearSetSlotEligibilityCatalog(
            sets=rows,
            unresolved=tuple(eligibility.unresolved),
        )
        return ExtremeArmorWeightFilteredSlotEligibilityResult(
            required_armor_weight=weight,
            catalog=catalog,
            unresolved=(),
        )


__all__ = [
    "ExtremeArmorWeightFilteredSlotEligibilityResult",
    "ExtremeArmorWeightFilteredSlotEligibilityService",
]
