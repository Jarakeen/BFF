from __future__ import annotations

"""Jointly optimize reviewed armor-piece, armor-passive, and Mundus layers.

This service closes the most important Divines boundary for the current Extreme
objectives. It searches legal seven-piece CP160 Gold armor weight/trait choices,
adds reviewed armor-weight passive contributions, applies the resulting Divines
multiplier to the canonical Mundus repository, and ranks the combined layer.

It still does not claim a whole-character global maximum. Shields, weapon traits,
sets, glyphs, race, CP, active skills, contextual passives, consumables, and
runtime/group/encounter effects remain separate source families.
"""

from dataclasses import dataclass
from math import floor

from minmax.item_base_stats import (
    ARMOR_BASE_CP160_GOLD,
    ARMOR_INVIGORATING_RECOVERY_GOLD,
    ARMOR_NIRNHONED_RESISTANCE_GOLD,
    ARMOR_REINFORCED_PERCENT_GOLD,
)
from minmax.mundus_repository import MundusRepository
from services.extreme_armor_weight_objective_service import (
    ExtremeArmorWeightObjectiveService,
)
from services.extreme_divines_mundus_objective_service import (
    ExtremeDivinesMundusObjectiveService,
)


_WEIGHTS = ("Light", "Medium", "Heavy")
_TRAITS = ("None", "Divines", "Reinforced", "Nirnhoned", "Invigorating")


@dataclass(frozen=True)
class ExtremeArmorMundusPieceChoice:
    slot: str
    weight: str
    trait: str
    direct_delta: float


@dataclass(frozen=True)
class ExtremeArmorMundusJointCandidate:
    objective_key: str
    pieces: tuple[ExtremeArmorMundusPieceChoice, ...]
    mundus_name: str
    armor_direct_delta: float
    armor_passive_delta: float
    mundus_delta: float
    total_delta: float
    divines_multiplier: float

    @property
    def divines_count(self) -> int:
        return sum(1 for piece in self.pieces if piece.trait == "Divines")

    @property
    def composition_label(self) -> str:
        counts = {weight: 0 for weight in _WEIGHTS}
        for piece in self.pieces:
            counts[piece.weight] += 1
        return f"{counts['Light']}L/{counts['Medium']}M/{counts['Heavy']}H"


@dataclass(frozen=True)
class _PartialState:
    pieces: tuple[ExtremeArmorMundusPieceChoice, ...]
    armor_direct_delta: float


class ExtremeArmorMundusJointObjectiveService:
    REVIEWED_OBJECTIVES = ExtremeArmorWeightObjectiveService.REVIEWED_OBJECTIVES

    @staticmethod
    def _direct_piece_delta(
        objective_key: str,
        *,
        slot: str,
        weight: str,
        trait: str,
    ) -> float:
        objective = objective_key.strip().casefold()
        base = float(ARMOR_BASE_CP160_GOLD[slot][weight])

        if objective in {"physical_resistance", "spell_resistance"}:
            value = base
            if trait == "Reinforced":
                value = float(floor(base * (1.0 + ARMOR_REINFORCED_PERCENT_GOLD)))
            elif trait == "Nirnhoned":
                value += ARMOR_NIRNHONED_RESISTANCE_GOLD
            return value

        if objective in {"magicka_recovery", "stamina_recovery"}:
            return (
                float(ARMOR_INVIGORATING_RECOVERY_GOLD)
                if trait == "Invigorating"
                else 0.0
            )

        return 0.0

    @classmethod
    def _states_after_armor(cls, objective_key: str) -> tuple[_PartialState, ...]:
        # Dynamic programming keeps only the strongest direct-gear solution for
        # each final (Light, Medium, Heavy, Divines) count state. Armor-passive
        # and Mundus contributions depend only on those counts, so discarded
        # lower direct-score paths can never become optimal later.
        states: dict[tuple[int, int, int, int], _PartialState] = {
            (0, 0, 0, 0): _PartialState((), 0.0)
        }

        for slot in ARMOR_BASE_CP160_GOLD:
            next_states: dict[tuple[int, int, int, int], _PartialState] = {}
            for (light, medium, heavy, divines), state in states.items():
                for weight in _WEIGHTS:
                    for trait in _TRAITS:
                        counts = {
                            "Light": light,
                            "Medium": medium,
                            "Heavy": heavy,
                        }
                        counts[weight] += 1
                        new_divines = divines + int(trait == "Divines")
                        key = (
                            counts["Light"],
                            counts["Medium"],
                            counts["Heavy"],
                            new_divines,
                        )
                        delta = cls._direct_piece_delta(
                            objective_key,
                            slot=slot,
                            weight=weight,
                            trait=trait,
                        )
                        candidate = _PartialState(
                            pieces=state.pieces
                            + (
                                ExtremeArmorMundusPieceChoice(
                                    slot=slot,
                                    weight=weight,
                                    trait=trait,
                                    direct_delta=delta,
                                ),
                            ),
                            armor_direct_delta=state.armor_direct_delta + delta,
                        )
                        incumbent = next_states.get(key)
                        if incumbent is None or candidate.armor_direct_delta > incumbent.armor_direct_delta:
                            next_states[key] = candidate
            states = next_states

        return tuple(states.values())

    @classmethod
    def candidates_for_objective(
        cls,
        repository: MundusRepository,
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> tuple[ExtremeArmorMundusJointCandidate, ...]:
        objective = objective_key.strip().casefold()
        if objective not in cls.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme armor/Mundus objective: {objective_key!r}")

        rows: list[ExtremeArmorMundusJointCandidate] = []
        for state in cls._states_after_armor(objective):
            light = sum(1 for piece in state.pieces if piece.weight == "Light")
            medium = sum(1 for piece in state.pieces if piece.weight == "Medium")
            heavy = sum(1 for piece in state.pieces if piece.weight == "Heavy")
            divines = sum(1 for piece in state.pieces if piece.trait == "Divines")

            armor_passive = ExtremeArmorWeightObjectiveService.candidate_for_composition(
                objective,
                light_pieces=light,
                medium_pieces=medium,
                heavy_pieces=heavy,
                reference_value=reference_value,
            )
            if armor_passive.projected_delta is None:
                continue

            mundus = ExtremeDivinesMundusObjectiveService.best_mundus_for_configuration(
                repository,
                objective,
                armor_divines_count=divines,
                shield_divines=False,
            )
            if mundus is None or mundus.projected_delta is None:
                continue

            total = (
                state.armor_direct_delta
                + float(armor_passive.projected_delta)
                + float(mundus.projected_delta)
            )
            rows.append(
                ExtremeArmorMundusJointCandidate(
                    objective_key=objective,
                    pieces=state.pieces,
                    mundus_name=mundus.mundus.mundus_name,
                    armor_direct_delta=state.armor_direct_delta,
                    armor_passive_delta=float(armor_passive.projected_delta),
                    mundus_delta=float(mundus.projected_delta),
                    total_delta=total,
                    divines_multiplier=mundus.configuration.multiplier,
                )
            )

        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    -row.total_delta,
                    -row.divines_count,
                    row.composition_label,
                    tuple((piece.slot, piece.weight, piece.trait) for piece in row.pieces),
                ),
            )
        )

    @classmethod
    def best_for_objective(
        cls,
        repository: MundusRepository,
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> ExtremeArmorMundusJointCandidate | None:
        rows = cls.candidates_for_objective(
            repository,
            objective_key,
            reference_value=reference_value,
        )
        return rows[0] if rows else None
