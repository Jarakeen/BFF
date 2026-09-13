from __future__ import annotations

"""Proof-reduce reviewed armor states for Max Magicka / Max Stamina scoring.

The complete legal armor-weight denominator remains owned by
``ExtremeArmorResourceWeightStateService``.  For Max Magicka and Max Stamina,
that service has already reviewed armor weight and established that the only
max-resource continuation is Undaunted Mettle.  Canonical Undaunted Mettle math
is strictly monotonic in the number of distinct equipped armor types, so the
three-type witness dominates the one- and two-type witnesses while preserving
all joint Divines/Infused + glyph states.

Max Health is intentionally unsupported because Heavy Armor/Juggernaut can
change Max Health and therefore armor composition cannot be collapsed by the
same proof.
"""

from dataclasses import dataclass

from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphState,
    ExtremeArmorResourceWeightTraitGlyphStateCatalog,
)


_SUPPORTED_OBJECTIVES = frozenset({"max_magicka", "max_stamina"})


@dataclass(frozen=True)
class ExtremeMaxResourceArmorScoringFrontier:
    objective_key: str
    source_state_count: int
    states: tuple[ExtremeArmorResourceWeightTraitGlyphState, ...]
    source_weight_state_count: int
    retained_weight_type_count: int
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def reduction_proven(self) -> bool:
        return bool(
            self.denominator_proven
            and self.source_state_count > 0
            and self.states
            and self.retained_weight_type_count == 3
            and not self.unresolved
        )

    @property
    def states_pruned(self) -> int:
        return max(0, self.source_state_count - len(self.states))


class ExtremeMaxResourceArmorScoringFrontierService:
    """Retain only the three-armor-type continuation for Magicka/Stamina."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    @classmethod
    def build(
        cls,
        objective_key: str,
        catalog: ExtremeArmorResourceWeightTraitGlyphStateCatalog,
    ) -> ExtremeMaxResourceArmorScoringFrontier:
        key = str(objective_key or "").strip().casefold()
        if key not in cls.SUPPORTED_OBJECTIVES:
            raise KeyError(
                f"unreviewed Extreme max-resource armor scoring frontier objective: {objective_key!r}"
            )

        unresolved: list[str] = [str(item) for item in catalog.unresolved if str(item)]
        if catalog.objective_key != key:
            unresolved.append(
                "Extreme armor scoring frontier objective mismatch: "
                f"catalog={catalog.objective_key!r}, requested={key!r}"
            )

        source_states = tuple(catalog.states)
        weight_states = tuple(catalog.weight_catalog.states)
        weight_counts = tuple(sorted({int(state.armor_type_count) for state in weight_states}))
        if weight_counts != (1, 2, 3):
            unresolved.append(
                "Armor scoring frontier requires reviewed 1/2/3 distinct armor-type witnesses"
            )
        if not catalog.denominator_proven:
            unresolved.append("Armor scoring frontier requires a proven source denominator")

        retained = tuple(
            sorted(
                (state for state in source_states if int(state.armor_type_count) == 3),
                key=lambda state: state.identity,
            )
        )
        expected_retained = len(catalog.trait_glyph_catalog.states)
        if expected_retained <= 0 or len(retained) != expected_retained:
            unresolved.append(
                "Armor scoring frontier did not preserve one three-type witness per trait/glyph state"
            )

        final_unresolved = tuple(dict.fromkeys(unresolved))
        denominator_proven = bool(
            catalog.denominator_proven
            and weight_counts == (1, 2, 3)
            and expected_retained > 0
            and len(retained) == expected_retained
            and not final_unresolved
        )
        return ExtremeMaxResourceArmorScoringFrontier(
            objective_key=key,
            source_state_count=len(source_states),
            states=retained,
            source_weight_state_count=len(weight_states),
            retained_weight_type_count=3,
            denominator_proven=denominator_proven,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeMaxResourceArmorScoringFrontier",
    "ExtremeMaxResourceArmorScoringFrontierService",
]
