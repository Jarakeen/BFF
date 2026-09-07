from __future__ import annotations

"""Enumerate deterministic CP160 Gold armor-piece contributions for Extreme Builds.

This service reuses the static armor values and trait constants already owned by
``minmax.item_base_stats``.  It deliberately covers only the armor-piece layer:
base armor plus static armor traits. Armor-weight passives, glyphs, sets,
Mundus/Divines interaction, shields, weapon Defending, and runtime mechanics are
separate source families and must be combined by higher-level Extreme planning.
"""

from dataclasses import dataclass
from math import floor

from minmax.item_base_stats import (
    ARMOR_BASE_CP160_GOLD,
    ARMOR_INVIGORATING_RECOVERY_GOLD,
    ARMOR_NIRNHONED_RESISTANCE_GOLD,
    ARMOR_REINFORCED_PERCENT_GOLD,
)


_ARMOR_WEIGHTS = ("Light", "Medium", "Heavy")
_STATIC_TRAITS = ("None", "Reinforced", "Nirnhoned", "Invigorating")


@dataclass(frozen=True)
class ExtremeArmorPieceObjectiveCandidate:
    objective_key: str
    slot: str
    weight: str
    trait: str
    base_armor: float
    projected_delta: float
    sources: tuple[str, ...]


@dataclass(frozen=True)
class ExtremeArmorGearObjectiveLoadout:
    objective_key: str
    pieces: tuple[ExtremeArmorPieceObjectiveCandidate, ...]
    projected_delta: float

    @property
    def composition_label(self) -> str:
        counts = {weight: 0 for weight in _ARMOR_WEIGHTS}
        for piece in self.pieces:
            counts[piece.weight] += 1
        return f"{counts['Light']}L/{counts['Medium']}M/{counts['Heavy']}H"


class ExtremeArmorGearObjectiveService:
    """Optimize the deterministic armor-piece layer independently by slot."""

    REVIEWED_OBJECTIVES = (
        "physical_resistance",
        "spell_resistance",
        "magicka_recovery",
        "stamina_recovery",
    )

    @classmethod
    def piece_candidate(
        cls,
        objective_key: str,
        *,
        slot: str,
        weight: str,
        trait: str = "None",
    ) -> ExtremeArmorPieceObjectiveCandidate:
        objective = str(objective_key).strip().casefold()
        if objective not in cls.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme armor-gear objective: {objective_key!r}")
        if slot not in ARMOR_BASE_CP160_GOLD:
            raise KeyError(f"unknown armor slot: {slot!r}")
        if weight not in _ARMOR_WEIGHTS:
            raise KeyError(f"unknown armor weight: {weight!r}")
        if trait not in _STATIC_TRAITS:
            raise KeyError(f"unreviewed static armor trait: {trait!r}")

        base = float(ARMOR_BASE_CP160_GOLD[slot][weight])
        delta = 0.0
        sources: list[str] = []

        if objective in {"physical_resistance", "spell_resistance"}:
            delta += base
            sources.append(f"{slot}: {weight} armor base ({base:g})")
            if trait == "Reinforced":
                reinforced = float(floor(base * (1.0 + ARMOR_REINFORCED_PERCENT_GOLD)))
                bonus = reinforced - base
                delta += bonus
                sources.append(f"{slot}: Reinforced (+{bonus:g})")
            elif trait == "Nirnhoned":
                delta += ARMOR_NIRNHONED_RESISTANCE_GOLD
                sources.append(
                    f"{slot}: Nirnhoned (+{ARMOR_NIRNHONED_RESISTANCE_GOLD:g})"
                )
        elif objective in {"magicka_recovery", "stamina_recovery"} and trait == "Invigorating":
            delta += ARMOR_INVIGORATING_RECOVERY_GOLD
            sources.append(
                f"{slot}: Invigorating (+{ARMOR_INVIGORATING_RECOVERY_GOLD:g} recovery)"
            )

        return ExtremeArmorPieceObjectiveCandidate(
            objective_key=objective,
            slot=slot,
            weight=weight,
            trait=trait,
            base_armor=base,
            projected_delta=delta,
            sources=tuple(sources),
        )

    @classmethod
    def candidates_for_slot(
        cls,
        objective_key: str,
        *,
        slot: str,
    ) -> tuple[ExtremeArmorPieceObjectiveCandidate, ...]:
        rows = tuple(
            cls.piece_candidate(
                objective_key,
                slot=slot,
                weight=weight,
                trait=trait,
            )
            for weight in _ARMOR_WEIGHTS
            for trait in _STATIC_TRAITS
        )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    -row.projected_delta,
                    _ARMOR_WEIGHTS.index(row.weight),
                    _STATIC_TRAITS.index(row.trait),
                ),
            )
        )

    @classmethod
    def best_piece_for_slot(
        cls,
        objective_key: str,
        *,
        slot: str,
    ) -> ExtremeArmorPieceObjectiveCandidate:
        return cls.candidates_for_slot(objective_key, slot=slot)[0]

    @classmethod
    def best_loadout_for_objective(
        cls,
        objective_key: str,
    ) -> ExtremeArmorGearObjectiveLoadout:
        pieces = tuple(
            cls.best_piece_for_slot(objective_key, slot=slot)
            for slot in ARMOR_BASE_CP160_GOLD
        )
        return ExtremeArmorGearObjectiveLoadout(
            objective_key=str(objective_key).strip().casefold(),
            pieces=pieces,
            projected_delta=sum(piece.projected_delta for piece in pieces),
        )
