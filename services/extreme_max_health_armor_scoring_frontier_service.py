from __future__ import annotations

"""Proof-reduce Max Health armor states after preserving the full weight denominator.

The source weight catalog keeps every distinct ``(armor type count, Heavy pieces)``
Max Health signature.  Canonical reviewed armor passives then provide a monotonic
comparison for this objective:

* Undaunted Mettle: +2% Max Health per distinct armor type, and
* Juggernaut: +2% Max Health per Heavy piece.

Both feed the same additive Max Health percentage stage.  For a fixed trait/glyph
state, any weight signature with a lower combined reviewed percentage is dominated.
The legal maximum is +16%, reached by 7H, 6H/1 other, and 5H/1L/1M.  All three legal
witness families are retained rather than selecting one arbitrarily.
"""

from dataclasses import dataclass

from minmax.passive_math import (
    heavy_armor_juggernaut_max_health_percent,
    undaunted_mettle_resource_percent,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphState,
    ExtremeArmorResourceWeightTraitGlyphStateCatalog,
)


@dataclass(frozen=True)
class ExtremeMaxHealthArmorScoringFrontier:
    source_state_count: int
    states: tuple[ExtremeArmorResourceWeightTraitGlyphState, ...]
    source_weight_signature_count: int
    retained_weight_signatures: tuple[tuple[int, int], ...]
    best_reviewed_percent: float
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def reduction_proven(self) -> bool:
        return bool(
            self.denominator_proven
            and self.source_state_count > 0
            and self.states
            and self.retained_weight_signatures
            and not self.unresolved
        )

    @property
    def states_pruned(self) -> int:
        return max(0, self.source_state_count - len(self.states))


class ExtremeMaxHealthArmorScoringFrontierService:
    OBJECTIVE = "max_health"

    @staticmethod
    def _reviewed_percent(state) -> float:
        return float(
            undaunted_mettle_resource_percent(state.armor_type_count)
            + heavy_armor_juggernaut_max_health_percent(state.heavy_pieces)
        )

    @classmethod
    def build(
        cls,
        catalog: ExtremeArmorResourceWeightTraitGlyphStateCatalog,
    ) -> ExtremeMaxHealthArmorScoringFrontier:
        unresolved: list[str] = [str(item) for item in catalog.unresolved if str(item)]
        if catalog.objective_key != cls.OBJECTIVE:
            unresolved.append(
                "Max Health armor scoring frontier objective mismatch: "
                f"catalog={catalog.objective_key!r}"
            )
        if not catalog.denominator_proven:
            unresolved.append("Max Health armor scoring frontier requires a proven source denominator")

        weight_states = tuple(catalog.weight_catalog.states)
        percentages = {
            state.max_health_signature: cls._reviewed_percent(state)
            for state in weight_states
        }
        best_percent = max(percentages.values(), default=0.0)
        retained_signatures = tuple(
            sorted(
                signature
                for signature, value in percentages.items()
                if abs(float(value) - float(best_percent)) <= 1e-12
            )
        )
        expected_signatures = ((1, 7), (2, 6), (3, 5))
        if retained_signatures != expected_signatures:
            unresolved.append(
                "Reviewed Max Health armor passive frontier changed: "
                f"expected={expected_signatures!r}, retained={retained_signatures!r}"
            )

        retained_set = set(retained_signatures)
        states = tuple(
            sorted(
                (
                    state
                    for state in catalog.states
                    if state.weight_state.max_health_signature in retained_set
                ),
                key=lambda state: state.identity,
            )
        )
        expected_states = len(retained_signatures) * len(catalog.trait_glyph_catalog.states)
        if expected_states <= 0 or len(states) != expected_states:
            unresolved.append(
                "Max Health armor scoring frontier did not preserve each dominant weight "
                "signature for every trait/glyph state"
            )

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        denominator_proven = bool(
            catalog.denominator_proven
            and retained_signatures == expected_signatures
            and expected_states > 0
            and len(states) == expected_states
            and not final_unresolved
        )
        return ExtremeMaxHealthArmorScoringFrontier(
            source_state_count=len(catalog.states),
            states=states,
            source_weight_signature_count=len(weight_states),
            retained_weight_signatures=retained_signatures,
            best_reviewed_percent=float(best_percent),
            denominator_proven=denominator_proven,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeMaxHealthArmorScoringFrontier",
    "ExtremeMaxHealthArmorScoringFrontierService",
]
