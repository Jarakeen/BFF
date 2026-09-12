from __future__ import annotations

"""Proof-reduce the U50 potion axis for Extreme max-resource ceilings.

Every canonical formula remains part of the denominator. A formula may be collapsed
to the no-potion baseline only when every source trait is either routed through the
versioned named-buff semantics or explicitly reviewed as irrelevant to maximum
resources for the active patch. New or unreviewed traits fail closed.

The general Alchemy catalog also preserves parser-provenance warnings for malformed
source-table cells. For this narrow max-resource proof, ``non-trait source cells``
are proof-neutral only when the explicit U50 max-resource review covers the complete
canonical U50 Alchemy trait universe. Other catalog unresolved evidence remains a
hard blocker.

Production finite-axis search constructs many evaluator objects around the same
canonical repository. Completed potion irrelevance proofs are therefore cached by
canonical database, patch, and objective; injected test repositories remain local.
"""

from dataclasses import dataclass

from minmax.alchemy_potion_buff_semantics import potion_buff_for_trait
from minmax.combat_effect_semantics import GameUpdate, U50_ALCHEMY_TRAITS
from minmax.named_combat_buffs import effects_for_buff
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.stat_ids import StatId


_OBJECTIVE_STATS = {
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
}

_REVIEWED_U50_MAX_RESOURCE_IRRELEVANT_TRAITS = frozenset(
    {
        "Breach",
        "Cowardice",
        "Defile",
        "Detection",
        "Enervation",
        "Entrapment",
        "Fracture",
        "Heroism",
        "Hindrance",
        "Increase Armor",
        "Increase Spell Power",
        "Increase Spell Resist",
        "Increase Weapon Power",
        "Invisible",
        "Lingering Health",
        "Maim",
        "Protection",
        "Ravage Health",
        "Ravage Magicka",
        "Ravage Stamina",
        "Restore Health",
        "Restore Magicka",
        "Restore Stamina",
        "Speed",
        "Spell Critical",
        "Timidity",
        "Uncertainty",
        "Unstoppable",
        "Vitality",
        "Weapon Critical",
    }
)

_PROOF_NEUTRAL_U50_CATALOG_UNRESOLVED = "non-trait source cells rejected:"


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
    _production_projection_cache: dict[
        tuple[str, str, str], ExtremeResourcePotionProjection
    ] = {}

    def __init__(self, repository: PotionAvailabilityRepository) -> None:
        self.repository = repository

    def _production_cache_key(self, objective_key: str) -> tuple[str, str, str] | None:
        if not isinstance(self.repository, PotionAvailabilityRepository):
            return None
        database_path = str(getattr(self.repository, "database_path", "") or "").strip()
        if not database_path:
            return None
        game_update = getattr(self.repository, "game_update", GameUpdate.U50)
        update_value = str(getattr(game_update, "value", game_update))
        return database_path, update_value, objective_key

    @staticmethod
    def _catalog_unresolved_for_max_resource_proof(
        values: tuple[str, ...],
        *,
        game_update: GameUpdate,
    ) -> tuple[str, ...]:
        complete_u50_trait_review = bool(
            game_update is GameUpdate.U50
            and _REVIEWED_U50_MAX_RESOURCE_IRRELEVANT_TRAITS == U50_ALCHEMY_TRAITS
        )
        unresolved: list[str] = []
        for raw in values:
            message = str(raw or "").strip()
            if not message:
                continue
            if (
                complete_u50_trait_review
                and _PROOF_NEUTRAL_U50_CATALOG_UNRESOLVED in message
            ):
                continue
            unresolved.append(message)
        return tuple(dict.fromkeys(unresolved))

    def build(self, objective_key: str) -> ExtremeResourcePotionProjection:
        key = str(objective_key or "").strip().casefold()
        target = _OBJECTIVE_STATS.get(key)
        if target is None:
            raise KeyError(f"unreviewed Extreme potion projection objective: {objective_key!r}")

        cache_key = self._production_cache_key(key)
        if cache_key is not None:
            cached = self._production_projection_cache.get(cache_key)
            if cached is not None:
                return cached

        catalog = self.repository.catalog()
        game_update = getattr(self.repository, "game_update", GameUpdate.U50)
        unresolved: list[str] = list(
            self._catalog_unresolved_for_max_resource_proof(
                tuple(str(item) for item in catalog.unresolved if str(item)),
                game_update=game_update,
            )
        )
        relevant: list[str] = []

        if game_update is not GameUpdate.U50:
            unresolved.append(
                f"Max-resource potion irrelevance review is not yet closed for {game_update.value}"
            )

        if (
            game_update is GameUpdate.U50
            and _REVIEWED_U50_MAX_RESOURCE_IRRELEVANT_TRAITS != U50_ALCHEMY_TRAITS
        ):
            missing = tuple(
                sorted(
                    U50_ALCHEMY_TRAITS - _REVIEWED_U50_MAX_RESOURCE_IRRELEVANT_TRAITS,
                    key=str.casefold,
                )
            )
            extra = tuple(
                sorted(
                    _REVIEWED_U50_MAX_RESOURCE_IRRELEVANT_TRAITS - U50_ALCHEMY_TRAITS,
                    key=str.casefold,
                )
            )
            unresolved.append(
                "U50 max-resource potion trait review does not match canonical trait universe: "
                f"missing={missing!r}, extra={extra!r}"
            )

        for formula in catalog.formulas:
            formula_id = str(formula.canonical_id or "").strip()
            traits = tuple(
                str(value or "").strip()
                for value in formula.traits
                if str(value or "").strip()
            )
            if not traits:
                unresolved.append(
                    f"Potion formula has no canonical traits: {formula_id or '<unknown>'}"
                )
                continue

            formula_relevant = False
            for trait in traits:
                buff = potion_buff_for_trait(trait, game_update=game_update)
                if buff:
                    effects = effects_for_buff(buff, game_update=game_update)
                    if not effects:
                        unresolved.append(
                            f"Potion named buff has no reviewed standing-stat semantics: {buff} ({trait})"
                        )
                        continue
                    if any(effect.stat is target for effect in effects):
                        formula_relevant = True
                    continue

                if (
                    game_update is GameUpdate.U50
                    and trait in _REVIEWED_U50_MAX_RESOURCE_IRRELEVANT_TRAITS
                ):
                    continue

                unresolved.append(
                    f"Potion trait has no max-resource relevance review for {game_update.value}: {trait}"
                )

            if formula_relevant:
                relevant.append(formula_id or "+".join(traits))

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        result = ExtremeResourcePotionProjection(
            objective_key=key,
            formulas_reviewed=len(catalog.formulas),
            relevant_formulas=tuple(dict.fromkeys(relevant)),
            denominator_proven=bool(catalog.formulas) and not final_unresolved,
            unresolved=final_unresolved,
        )
        if cache_key is not None:
            self._production_projection_cache[cache_key] = result
        return result


__all__ = [
    "ExtremeResourcePotionProjection",
    "ExtremeResourcePotionProjectionService",
]
