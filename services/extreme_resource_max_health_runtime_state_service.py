from __future__ import annotations

"""Proof-reduced runtime witnesses for reviewed Extreme Max Health passives.

This service owns legality/state selection only. It does not perform resource math.
Reviewed Max Health runtime witnesses may stack when ESO legality permits it:

* Expert Summoner's +5% Max Health requires a legal route carrying Daedric Summoning
  and an explicitly active permanent pet.
* Maturation grants Minor Toughness to a healed target after a qualifying Green
  Balance heal. A legal route carrying Green Balance can therefore self-provide the
  named Max Health buff, including on subclass routes that also carry Daedric Summoning.
* Nothing Wasted's +20% Max Health maximum requires pure Necromancer Class Mastery
  and the reviewed 10-stack Corpse Consumption state.

Subclass routes cannot select Class Mastery, so Nothing Wasted remains mutually
exclusive with subclass-only combinations. Maturation and Expert Summoner are not
mutually exclusive and are represented together when the selected route supports
both. Shared named-buff and canonical passive services continue to own the actual
resource arithmetic.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.character_class import CharacterClass
from minmax.combat_effect_semantics import GameUpdate
from minmax.named_combat_buffs import effects_for_buff
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.class_mastery_extreme_effect_service import ClassMasteryExtremeEffectService
from services.class_mastery_repository import ClassMasteryPassive, ClassMasteryRepository
from services.extreme_heal_class_route_service import (
    ExtremeHealClassRoute,
    canonical_class_skill_line_id,
)
from services.extreme_sorcerer_expert_summoner_pet_context_service import (
    ExtremeSorcererExpertSummonerPetContextService,
)


@dataclass(frozen=True)
class ExtremeResourceMaxHealthRuntimeState:
    label: str
    permanent_pet_active: bool = False
    maturation_minor_toughness_active: bool = False
    nothing_wasted_stacks: int = 0
    class_mastery_ability_ids: tuple[int, ...] = ()
    reviewed_percent_bonus: float = 0.0
    conditions: tuple[str, ...] = ()

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.label,
            self.permanent_pet_active,
            self.maturation_minor_toughness_active,
            self.nothing_wasted_stacks,
            self.class_mastery_ability_ids,
            self.reviewed_percent_bonus,
        )


@dataclass(frozen=True)
class ExtremeResourceMaxHealthRuntimeStateCatalog:
    states: tuple[ExtremeResourceMaxHealthRuntimeState, ...]
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()


class ExtremeResourceMaxHealthRuntimeStateService:
    """Return the strongest reviewed legal Max Health runtime witness per route."""

    NOTHING_WASTED = "Nothing Wasted"
    DAEDRIC_SUMMONING = "daedric_summoning"
    GREEN_BALANCE = "green_balance"
    MATURATION_BUFF = "Minor Toughness"
    MAX_NOTHING_WASTED_STACKS = 10

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        mastery_repository: ClassMasteryRepository | None = None,
    ) -> None:
        if database_path is None and mastery_repository is None:
            raise ValueError("database_path or mastery_repository is required")
        self.database_path = Path(database_path) if database_path is not None else None
        self.mastery_repository = mastery_repository or ClassMasteryRepository(
            self.database_path  # type: ignore[arg-type]
        )

    @staticmethod
    def _route_lines(route: ExtremeHealClassRoute) -> frozenset[str]:
        return frozenset(
            canonical_class_skill_line_id(line)
            for line in route.equipped_skill_lines
        )

    @classmethod
    def _maturation_percent(cls) -> float:
        rows = tuple(
            effect
            for effect in effects_for_buff(cls.MATURATION_BUFF, game_update=GameUpdate.U50)
            if effect.stat is StatId.MAX_HEALTH and effect.bucket == "resource_percent"
        )
        if len(rows) != 1 or float(rows[0].value) <= 0.0:
            raise ValueError("Canonical Minor Toughness Max Health effect is unavailable")
        return float(rows[0].value)

    def _nothing_wasted(self) -> tuple[ClassMasteryPassive | None, tuple[str, ...]]:
        rows = tuple(
            row
            for row in self.mastery_repository.for_class(CharacterClass.NECROMANCER.value)
            if row.name.strip().casefold() == self.NOTHING_WASTED.casefold()
        )
        if len(rows) != 1:
            return None, (
                "Canonical Necromancer Class Mastery row is not uniquely resolved: Nothing Wasted",
            )
        passive = rows[0]
        contributions = tuple(
            row
            for row in ClassMasteryExtremeEffectService.contributions(passive)
            if row.objective_key == "max_health"
        )
        if len(contributions) != 1 or contributions[0].percent <= 0.0:
            return None, (
                "Reviewed Max Health contribution is unavailable for Nothing Wasted",
            )
        if passive.base_ability_id <= 0:
            return None, (
                "Canonical Class Mastery ability identity is unavailable for Nothing Wasted",
            )
        return passive, ()

    def build(
        self,
        route: ExtremeHealClassRoute,
    ) -> ExtremeResourceMaxHealthRuntimeStateCatalog:
        lines = self._route_lines(route)
        maturation_active = self.GREEN_BALANCE in lines
        maturation_percent = self._maturation_percent() if maturation_active else 0.0
        maturation_conditions = (
            (
                "Heal yourself with a Green Balance ability so Maturation grants "
                "Minor Toughness during the scored snapshot."
            ),
        ) if maturation_active else ()

        if self.DAEDRIC_SUMMONING in lines:
            expert_percent = ExtremeSorcererExpertSummonerPetContextService.MAX_HEALTH_PERCENT
            label = "Expert Summoner permanent pet"
            if maturation_active:
                label += " + Maturation Minor Toughness"
            state = ExtremeResourceMaxHealthRuntimeState(
                label=label,
                permanent_pet_active=True,
                maturation_minor_toughness_active=maturation_active,
                reviewed_percent_bonus=float(expert_percent) + maturation_percent,
                conditions=("Permanent pet is active.", *maturation_conditions),
            )
            return ExtremeResourceMaxHealthRuntimeStateCatalog(
                states=(state,),
                denominator_proven=True,
            )

        if (
            route.class_mastery_allowed
            and route.base_class is CharacterClass.NECROMANCER
        ):
            passive, unresolved = self._nothing_wasted()
            if passive is None:
                return ExtremeResourceMaxHealthRuntimeStateCatalog(
                    states=(ExtremeResourceMaxHealthRuntimeState(label="No reviewed runtime Max Health bonus"),),
                    denominator_proven=False,
                    unresolved=unresolved,
                )
            contribution = next(
                row
                for row in ClassMasteryExtremeEffectService.contributions(passive)
                if row.objective_key == "max_health"
            )
            state = ExtremeResourceMaxHealthRuntimeState(
                label="Nothing Wasted 10 stacks",
                nothing_wasted_stacks=self.MAX_NOTHING_WASTED_STACKS,
                class_mastery_ability_ids=(int(passive.base_ability_id),),
                reviewed_percent_bonus=float(contribution.percent),
                conditions=(contribution.condition,),
            )
            return ExtremeResourceMaxHealthRuntimeStateCatalog(
                states=(state,),
                denominator_proven=True,
            )

        if maturation_active:
            return ExtremeResourceMaxHealthRuntimeStateCatalog(
                states=(
                    ExtremeResourceMaxHealthRuntimeState(
                        label="Maturation Minor Toughness",
                        maturation_minor_toughness_active=True,
                        reviewed_percent_bonus=maturation_percent,
                        conditions=maturation_conditions,
                    ),
                ),
                denominator_proven=True,
            )

        return ExtremeResourceMaxHealthRuntimeStateCatalog(
            states=(ExtremeResourceMaxHealthRuntimeState(label="No reviewed runtime Max Health bonus"),),
            denominator_proven=True,
        )

    @staticmethod
    def materialize(
        build: PlayerBuild,
        state: ExtremeResourceMaxHealthRuntimeState,
    ) -> PlayerBuild:
        result = PlayerBuild.from_dict(build.to_dict())
        if state.class_mastery_ability_ids:
            result.ClassMasteryAbilityIds = list(state.class_mastery_ability_ids)
        return result
