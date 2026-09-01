from __future__ import annotations

"""Temporal potion-use evidence derived from saved potion availability.

A saved potion only proves availability. This module models what becomes
available *when the potion is explicitly used*: instant resource restores,
timed Alchemy traits, and source-backed named combat buffs. It does not apply
effects to CombatState automatically, does not assume cooldown/uptime, and does
not apply Medicinal Use.
"""

from dataclasses import dataclass
from pathlib import Path

from .alchemy_potion_buff_semantics import potion_buff_for_trait
from .alchemy_potion_tier_repository import AlchemyPotionTierRepository, PotionTierEvidence
from .combat_effect_semantics import GameUpdate, normalize_game_update
from .potion_availability_repository import PotionAvailabilityRepository

_INSTANT_RESTORE_TRAITS = frozenset({"Restore Health", "Restore Magicka", "Restore Stamina"})


@dataclass(frozen=True)
class PotionTraitUse:
    trait: str
    kind: str
    magnitude: float | None
    duration: float | None
    triple_duration: float | None
    tier_name: str
    solvent: str
    level: int


@dataclass(frozen=True)
class PotionBuffGrant:
    source_trait: str
    buff_name: str
    duration: float
    triple_duration: float | None
    tier_name: str


@dataclass(frozen=True)
class PotionUseEvent:
    selected_label: str
    formula_ids: tuple[str, ...] = ()
    traits: tuple[PotionTraitUse, ...] = ()
    buff_grants: tuple[PotionBuffGrant, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.traits) and not self.unresolved

    @property
    def instant_restores(self) -> tuple[PotionTraitUse, ...]:
        return tuple(value for value in self.traits if value.kind == "instant_restore")

    @property
    def timed_traits(self) -> tuple[PotionTraitUse, ...]:
        return tuple(value for value in self.traits if value.kind == "timed_trait")


class PotionUseEventResolver:
    """Resolve one explicit potion-use event from source-backed U50 evidence."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        processed_path: str | Path | None = None,
        game_update: GameUpdate | str = GameUpdate.U50,
    ) -> None:
        kwargs = {}
        if database_path is not None:
            kwargs["database_path"] = database_path
        if processed_path is not None:
            kwargs["processed_path"] = processed_path
        self.game_update = normalize_game_update(game_update)
        self.availability = PotionAvailabilityRepository(game_update=self.game_update, **kwargs)
        self.tiers = AlchemyPotionTierRepository(processed_path) if processed_path is not None else AlchemyPotionTierRepository()

    @staticmethod
    def _trait_use(trait: str, tier: PotionTierEvidence) -> PotionTraitUse:
        is_restore = trait in _INSTANT_RESTORE_TRAITS
        return PotionTraitUse(
            trait=trait,
            kind="instant_restore" if is_restore else "timed_trait",
            magnitude=tier.magnitude if is_restore else None,
            # Timed Alchemy-trait duration remains useful evidence even when the
            # same trait also has an instant restore component. Named-buff grants
            # below consume the ordinary duration explicitly.
            duration=None if is_restore else tier.duration,
            triple_duration=tier.triple_duration,
            tier_name=tier.potion_name,
            solvent=tier.solvent,
            level=tier.level,
        )

    def _buff_grant(self, trait: str, tier: PotionTierEvidence) -> PotionBuffGrant | None:
        buff_name = potion_buff_for_trait(trait, game_update=self.game_update)
        if buff_name is None or tier.duration is None:
            return None
        return PotionBuffGrant(
            source_trait=trait,
            buff_name=buff_name,
            duration=tier.duration,
            triple_duration=tier.triple_duration,
            tier_name=tier.potion_name,
        )

    def resolve(self, selected_label: str) -> PotionUseEvent:
        clean = " ".join(str(selected_label or "").strip().split())
        if not clean:
            return PotionUseEvent(selected_label="")

        if self.game_update is not GameUpdate.U50:
            return PotionUseEvent(
                selected_label=clean,
                unresolved=(
                    f"Potion temporal tier values are not sourced for {self.game_update.value}; U50 evidence is preserved separately",
                ),
            )

        availability = self.availability.resolve(clean)
        if not availability.resolved:
            return PotionUseEvent(
                selected_label=clean,
                formula_ids=tuple(formula.canonical_id for formula in availability.formulas),
                unresolved=availability.unresolved,
            )

        uses: list[PotionTraitUse] = []
        grants: list[PotionBuffGrant] = []
        unresolved: list[str] = []
        for trait in availability.canonical_traits:
            tier = self.tiers.max_tier(trait)
            if tier is None:
                unresolved.append(f"Max potion tier evidence missing for trait: {trait}")
                continue
            uses.append(self._trait_use(trait, tier))
            grant = self._buff_grant(trait, tier)
            if grant is not None:
                grants.append(grant)

        return PotionUseEvent(
            selected_label=clean,
            formula_ids=tuple(formula.canonical_id for formula in availability.formulas),
            traits=tuple(uses),
            buff_grants=tuple(grants),
            unresolved=tuple(unresolved),
        )
