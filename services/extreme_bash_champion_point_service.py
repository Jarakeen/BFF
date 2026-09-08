from __future__ import annotations

"""Resolve canonical Bash-specific Champion Point rows for Extreme/MOST Bashy.

The generic Champion Point static repository deliberately leaves Bash mechanics
unmapped because ordinary character-sheet/block pipelines do not own them. This
adapter reads the same canonical records and projects only the pieces whose
formula semantics are reviewed for the Extreme Bash objective.

Important boundary: Bashing Brutality is a flat CP.BashDamage term in the
canonical Bash damage equation and can be projected directly. Savage Defense is
canonical evidence for a flat Stamina reduction, while the inherited UESP Bash
cost equation currently exposes CP.BashCost as a multiplier. Until that semantic
bridge is reviewed, the flat reduction is retained as evidence and an explicit
blocker instead of being converted into a guessed percentage.
"""

import re
from dataclasses import dataclass

from minmax.champion_point_static_repository import (
    ChampionPointRecord,
    ChampionPointStaticRepository,
)

_VALUE = r"([0-9]+(?:\.[0-9]+)?)"


@dataclass(frozen=True)
class ExtremeBashChampionPointResult:
    name: str
    objective_key: str
    stages: int
    reviewed_formula_value: float | None
    canonical_flat_value: float | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return self.reviewed_formula_value is not None and not self.unresolved


class ExtremeBashChampionPointService:
    BASHING_BRUTALITY = "Bashing Brutality"
    SAVAGE_DEFENSE = "Savage Defense"

    @staticmethod
    def _stages(record: ChampionPointRecord, points: int) -> int:
        allocated = max(0, min(int(points), record.max_points or int(points)))
        thresholds = tuple(value for value in record.jump_points if value > 0)
        if thresholds:
            return sum(1 for value in thresholds if allocated >= value)
        return allocated

    @classmethod
    def resolve_damage(
        cls,
        repository: ChampionPointStaticRepository,
        *,
        points: int | None = None,
    ) -> ExtremeBashChampionPointResult:
        record = repository.get(cls.BASHING_BRUTALITY)
        if record is None:
            return ExtremeBashChampionPointResult(
                name=cls.BASHING_BRUTALITY,
                objective_key="bash_damage",
                stages=0,
                reviewed_formula_value=None,
                unresolved=("Champion Point not found: Bashing Brutality",),
            )

        allocated = record.max_points if points is None else int(points)
        stages = cls._stages(record, allocated)
        first_line = record.description.splitlines()[0].strip()
        match = re.match(
            rf"^Increases your Bash damage by {_VALUE} per stage\.?$",
            first_line,
            flags=re.IGNORECASE,
        )
        if not match:
            return ExtremeBashChampionPointResult(
                name=record.name,
                objective_key="bash_damage",
                stages=stages,
                reviewed_formula_value=None,
                unresolved=(
                    f"unrecognized Bashing Brutality tooltip: {first_line}",
                ),
            )

        value = float(match.group(1)) * stages
        return ExtremeBashChampionPointResult(
            name=record.name,
            objective_key="bash_damage",
            stages=stages,
            reviewed_formula_value=value,
            canonical_flat_value=value,
        )

    @classmethod
    def resolve_cost(
        cls,
        repository: ChampionPointStaticRepository,
        *,
        points: int | None = None,
    ) -> ExtremeBashChampionPointResult:
        record = repository.get(cls.SAVAGE_DEFENSE)
        if record is None:
            return ExtremeBashChampionPointResult(
                name=cls.SAVAGE_DEFENSE,
                objective_key="bash_cost",
                stages=0,
                reviewed_formula_value=None,
                unresolved=("Champion Point not found: Savage Defense",),
            )

        allocated = record.max_points if points is None else int(points)
        stages = cls._stages(record, allocated)
        first_line = record.description.splitlines()[0].strip()
        match = re.match(
            rf"^Reduces the cost of Bash by {_VALUE} Stamina per stage\.?$",
            first_line,
            flags=re.IGNORECASE,
        )
        if not match:
            return ExtremeBashChampionPointResult(
                name=record.name,
                objective_key="bash_cost",
                stages=stages,
                reviewed_formula_value=None,
                unresolved=(f"unrecognized Savage Defense tooltip: {first_line}",),
            )

        flat_reduction = float(match.group(1)) * stages
        return ExtremeBashChampionPointResult(
            name=record.name,
            objective_key="bash_cost",
            stages=stages,
            reviewed_formula_value=None,
            canonical_flat_value=-flat_reduction,
            unresolved=(
                "Savage Defense is a flat Stamina Bash-cost reduction, but the "
                "canonical Bash formula currently exposes CP.BashCost as a "
                "multiplier; conversion requires reviewed formula semantics",
            ),
        )
