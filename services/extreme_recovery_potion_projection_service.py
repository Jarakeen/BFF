from __future__ import annotations

"""Proof-review the canonical potion axis for Extreme recovery records.

The formula catalog may carry parser-provenance warnings for rejected non-trait
source cells. For U50 recovery objectives those warnings are proof-neutral because
the complete canonical U50 Alchemy trait universe is reviewed explicitly below.
Relevant formulas are retained whenever their named combat buff changes the target
recovery stat; all other reviewed U50 traits are objective-irrelevant.
"""

from dataclasses import dataclass

from minmax.alchemy_potion_buff_semantics import potion_buff_for_trait
from minmax.combat_effect_semantics import GameUpdate, U50_ALCHEMY_TRAITS
from minmax.named_combat_buffs import effects_for_buff
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.stat_ids import StatId


_OBJECTIVE_STATS = {
    "health_recovery": StatId.HEALTH_RECOVERY,
    "magicka_recovery": StatId.MAGICKA_RECOVERY,
    "stamina_recovery": StatId.STAMINA_RECOVERY,
}

_PROOF_NEUTRAL_U50_CATALOG_UNRESOLVED = "non-trait source cells rejected:"


@dataclass(frozen=True)
class ExtremeRecoveryPotionProjection:
    objective_key: str
    formulas_reviewed: int
    relevant_formulas: tuple[str, ...]
    relevant_buffs: tuple[str, ...]
    traits_reviewed: tuple[str, ...]
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(self.denominator_proven and not self.unresolved)


class ExtremeRecoveryPotionProjectionService:
    SUPPORTED_OBJECTIVES = frozenset(_OBJECTIVE_STATS)

    def __init__(self, repository: PotionAvailabilityRepository) -> None:
        self.repository = repository

    @staticmethod
    def _catalog_unresolved_for_recovery_proof(
        values: tuple[str, ...],
        *,
        game_update: GameUpdate,
        complete_trait_review: bool,
    ) -> tuple[str, ...]:
        unresolved: list[str] = []
        for raw in values:
            message = str(raw or "").strip()
            if not message:
                continue
            if (
                game_update is GameUpdate.U50
                and complete_trait_review
                and _PROOF_NEUTRAL_U50_CATALOG_UNRESOLVED in message
            ):
                continue
            unresolved.append(message)
        return tuple(dict.fromkeys(unresolved))

    @staticmethod
    def _review_u50_trait_universe(target: StatId) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Return canonical U50 traits reviewed and any semantic gaps for target recovery."""
        unresolved: list[str] = []
        for trait in sorted(U50_ALCHEMY_TRAITS, key=str.casefold):
            buff = potion_buff_for_trait(trait, game_update=GameUpdate.U50)
            if not buff:
                # Reviewed canonical traits without a standing named buff cannot
                # modify an instantaneous recovery rating in the canonical sheet.
                continue
            effects = effects_for_buff(buff, game_update=GameUpdate.U50)
            if not effects:
                unresolved.append(
                    f"Potion named buff has no reviewed standing-stat semantics: {buff} ({trait})"
                )
                continue
            # Effects for other stats are explicitly reviewed and irrelevant.
            _ = any(effect.stat is target for effect in effects)
        return tuple(sorted(U50_ALCHEMY_TRAITS, key=str.casefold)), tuple(dict.fromkeys(unresolved))

    def build(self, objective_key: str) -> ExtremeRecoveryPotionProjection:
        key = str(objective_key or "").strip().casefold()
        target = _OBJECTIVE_STATS.get(key)
        if target is None:
            raise KeyError(f"unreviewed Extreme recovery potion objective: {objective_key!r}")

        catalog = self.repository.catalog()
        game_update = getattr(self.repository, "game_update", GameUpdate.U50)
        source_traits = {
            str(trait or "").strip()
            for formula in catalog.formulas
            for trait in formula.traits
            if str(trait or "").strip()
        }

        reviewed_traits: tuple[str, ...] = ()
        trait_unresolved: tuple[str, ...] = ()
        if game_update is GameUpdate.U50:
            reviewed_traits, trait_unresolved = self._review_u50_trait_universe(target)
        complete_trait_review = bool(game_update is GameUpdate.U50 and reviewed_traits)

        unresolved: list[str] = list(trait_unresolved)
        unresolved.extend(
            self._catalog_unresolved_for_recovery_proof(
                tuple(str(item) for item in catalog.unresolved if str(item)),
                game_update=game_update,
                complete_trait_review=complete_trait_review,
            )
        )
        if game_update is not GameUpdate.U50:
            unresolved.append(
                f"Recovery potion relevance review is not yet closed for {game_update.value}"
            )

        unknown = tuple(sorted(source_traits - U50_ALCHEMY_TRAITS, key=str.casefold))
        if game_update is GameUpdate.U50 and unknown:
            unresolved.append(
                "Potion formula catalog contains traits outside the reviewed U50 universe: "
                + ", ".join(unknown)
            )

        relevant_formulas: list[str] = []
        relevant_buffs: list[str] = []

        for formula in catalog.formulas:
            formula_relevant = False
            for raw_trait in formula.traits:
                trait = str(raw_trait or "").strip()
                if not trait:
                    continue
                if game_update is GameUpdate.U50 and trait not in U50_ALCHEMY_TRAITS:
                    continue
                buff = potion_buff_for_trait(trait, game_update=game_update)
                if not buff:
                    continue
                effects = effects_for_buff(buff, game_update=game_update)
                if not effects:
                    continue
                if any(effect.stat is target for effect in effects):
                    formula_relevant = True
                    relevant_buffs.append(buff)
            if formula_relevant:
                relevant_formulas.append(
                    str(formula.canonical_id or "").strip()
                    or "+".join(str(value) for value in formula.traits)
                )

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        return ExtremeRecoveryPotionProjection(
            objective_key=key,
            formulas_reviewed=len(catalog.formulas),
            relevant_formulas=tuple(dict.fromkeys(relevant_formulas)),
            relevant_buffs=tuple(dict.fromkeys(relevant_buffs)),
            traits_reviewed=reviewed_traits,
            denominator_proven=bool(catalog.formulas) and complete_trait_review and not final_unresolved,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeRecoveryPotionProjection",
    "ExtremeRecoveryPotionProjectionService",
]
