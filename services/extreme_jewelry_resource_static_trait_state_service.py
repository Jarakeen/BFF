from __future__ import annotations

"""Proof-safe static jewelry-trait states for Extreme max-resource records.

This service owns only the reviewed CP160 Gold *static* jewelry traits already
resolved by ``JewelryTraitRepository``. Glyph-dependent Infused is deliberately
left to the jewelry glyph layer. No ESO stat arithmetic is duplicated here: trait
effects are read from the canonical repository, projected onto one requested max
resource, and lower flat-resource loadouts are safely dominated because later
resource percentage multipliers apply to the completed resource pool.
"""

from dataclasses import dataclass
from itertools import product
from pathlib import Path

from minmax.gear_stat_inputs import STATIC_JEWELRY_TRAITS
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


_SLOTS = ("Necklace", "Ring1", "Ring2")
_OBJECTIVE_STATS = {
    "max_health": StatId.MAX_HEALTH,
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
}
_DISPLAY_NAMES = {
    "arcane": "Arcane",
    "healthy": "Healthy",
    "robust": "Robust",
    "triune": "Triune",
    "protective": "Protective",
}


@dataclass(frozen=True)
class ExtremeJewelryResourceStaticTraitChoice:
    trait: str
    direct_delta: float


@dataclass(frozen=True)
class ExtremeJewelryResourceStaticTraitState:
    objective_key: str
    traits: tuple[tuple[str, str], ...]
    direct_delta: float

    @property
    def identity(self) -> tuple[tuple[str, str], ...]:
        return self.traits


@dataclass(frozen=True)
class ExtremeJewelryResourceStaticTraitStateCatalog:
    objective_key: str
    states: tuple[ExtremeJewelryResourceStaticTraitState, ...]
    traits_reviewed: tuple[str, ...]
    relevant_traits: tuple[str, ...]
    raw_loadouts_reviewed: int
    objective_relevant_loadouts_considered: int
    dominated_loadouts_pruned: int
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return bool(self.states and self.traits_reviewed and not self.unresolved)


class ExtremeJewelryResourceStaticTraitStateService:
    """Reduce CP160 Gold static jewelry traits to the strongest resource witness."""

    SUPPORTED_OBJECTIVES = tuple(_OBJECTIVE_STATS)

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: JewelryTraitRepository | None = None,
    ) -> None:
        if repository is None and database_path is None:
            raise ValueError("database_path is required when no jewelry trait repository is supplied")
        self.repository = repository or JewelryTraitRepository(database_path)  # type: ignore[arg-type]

    def build(self, objective_key: str) -> ExtremeJewelryResourceStaticTraitStateCatalog:
        key = str(objective_key or "").strip().casefold()
        stat = _OBJECTIVE_STATS.get(key)
        if stat is None:
            raise KeyError(f"unreviewed Extreme jewelry resource trait objective: {objective_key!r}")

        reviewed = tuple(sorted(STATIC_JEWELRY_TRAITS))
        unresolved: list[str] = []
        choices: list[ExtremeJewelryResourceStaticTraitChoice] = [
            ExtremeJewelryResourceStaticTraitChoice("", 0.0)
        ]
        relevant: list[str] = []

        for trait_key in reviewed:
            effects = self.repository.get_static_effects(
                trait_key,
                quality="Gold",
                level="CP160",
            )
            if not effects:
                unresolved.append(
                    f"Canonical CP160 Gold jewelry trait effects unavailable: {trait_key}"
                )
                continue
            delta = sum(
                float(effect.value)
                for effect in effects
                if effect.stat is stat
            )
            if delta <= 0.0:
                continue
            name = _DISPLAY_NAMES.get(trait_key, trait_key.title())
            choices.append(ExtremeJewelryResourceStaticTraitChoice(name, delta))
            relevant.append(name)

        relevant_choices = tuple(choices)
        best_traits: tuple[tuple[str, str], ...] | None = None
        best_delta: float | None = None
        relevant_loadouts = 0
        for values in product(relevant_choices, repeat=len(_SLOTS)):
            relevant_loadouts += 1
            traits = tuple((slot, choice.trait) for slot, choice in zip(_SLOTS, values))
            delta = sum(choice.direct_delta for choice in values)
            if (
                best_delta is None
                or delta > best_delta + 1e-9
                or (abs(delta - best_delta) <= 1e-9 and (best_traits is None or traits < best_traits))
            ):
                best_delta = delta
                best_traits = traits

        states: tuple[ExtremeJewelryResourceStaticTraitState, ...] = ()
        if best_traits is not None and best_delta is not None:
            states = (
                ExtremeJewelryResourceStaticTraitState(
                    objective_key=key,
                    traits=best_traits,
                    direct_delta=float(best_delta),
                ),
            )
        else:
            unresolved.append(f"No static jewelry trait state was produced for {key}")

        raw_loadouts = (1 + len(reviewed)) ** len(_SLOTS)
        return ExtremeJewelryResourceStaticTraitStateCatalog(
            objective_key=key,
            states=states,
            traits_reviewed=tuple(_DISPLAY_NAMES.get(name, name.title()) for name in reviewed),
            relevant_traits=tuple(relevant),
            raw_loadouts_reviewed=raw_loadouts,
            objective_relevant_loadouts_considered=relevant_loadouts,
            dominated_loadouts_pruned=max(0, relevant_loadouts - len(states)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def materialize(
        build: PlayerBuild,
        state: ExtremeJewelryResourceStaticTraitState,
    ) -> PlayerBuild:
        candidate = PlayerBuild.from_dict(build.to_dict())
        seen: set[str] = set()
        for slot_name, trait in state.traits:
            if slot_name not in _SLOTS:
                raise ValueError(f"unknown Extreme jewelry slot: {slot_name!r}")
            if slot_name in seen:
                raise ValueError(f"duplicate Extreme jewelry slot: {slot_name!r}")
            seen.add(slot_name)
            slot = getattr(candidate, slot_name)
            slot.Trait = trait
            slot.Quality = "Gold"
            slot.Level = "CP160"

        if seen != set(_SLOTS):
            missing = ", ".join(sorted(set(_SLOTS) - seen))
            raise ValueError(f"Extreme jewelry trait state does not cover all jewelry slots: {missing}")
        return candidate
