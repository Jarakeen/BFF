from __future__ import annotations

"""Proof-reduce the U50 potion axis for Extreme max-resource ceilings.

Every canonical formula remains part of the denominator.  A potion may be collapsed
to the no-potion baseline only when every source trait maps through the versioned
potion-trait semantics and none of the resulting named buffs can modify the requested
maximum resource.
"""

from dataclasses import dataclass

from minmax.alchemy_potion_buff_semantics import potion_buff_for_trait
from minmax.named_combat_buffs import effects_for_buff
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.stat_ids import StatId


_OBJECTIVE_STATS = {
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
}


@dataclass(frozen=True)
class ExtremeResourcePotionProjection:
    objective_key: str
    formulas_reviewed: int
    relevant_formulas: tuple[str, ...]
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def objective_irrelevance_proven(self) -> bool:
        return bool(
            self.denominator_proven
            and not self.relevant_formulas
            and not self.unresolved
        )


class ExtremeResourcePotionProjectionService:
    """Prove whether the canonical potion catalogue can alter one max resource."""

    SUPPORTED_OBJECTIVES = frozenset(_OBJECTIVE_STATS)

    def __init__(self, repository: PotionAvailabilityRepository) -> None:
        self.repository = repository

    def build(self, objective_key: str) -> ExtremeResourcePotionProjection:
        key = str(objective_key or "").strip().casefold()
        target = _OBJECTIVE_STATS.get(key)
        if target is None:
            raise KeyError(f"unreviewed Extreme potion projection objective: {objective_key!r}")

        catalog = self.repository.catalog()
        unresolved: list[str] = [str(item) for item in catalog.unresolved if str(item)]
        relevant: list[str] = []

        for formula in catalog.formulas:
            formula_id = str(formula.canonical_id or "").strip()
            traits = tuple(str(value or "").strip() for value in formula.traits if str(value or "").strip())
            if not traits:
                unresolved.append(f"Potion formula has no canonical traits: {formula_id or '<unknown>'}")
                continue

            formula_relevant = False
            for trait in traits:
                buff = potion_buff_for_trait(trait, game_update=self.repository.game_update)
                if not buff:
                    unresolved.append(
                        f"Potion trait has no reviewed named-buff semantics for {self.repository.game_update.value}: {trait}"
                    )
                    continue
                effects = effects_for_buff(buff, game_update=self.repository.game_update)
                if not effects:
                    unresolved.append(
                        f"Potion named buff has no reviewed standing-stat semantics: {buff} ({trait})"
                    )
                    continue
                if any(effect.stat is target for effect in effects):
                    formula_relevant = True
            if formula_relevant:
                relevant.append(formula_id or "+".join(traits))

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        return ExtremeResourcePotionProjection(
            objective_key=key,
            formulas_reviewed=len(catalog.formulas),
            relevant_formulas=tuple(dict.fromkeys(relevant)),
            denominator_proven=bool(catalog.formulas) and not final_unresolved,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeResourcePotionProjection",
    "ExtremeResourcePotionProjectionService",
]
