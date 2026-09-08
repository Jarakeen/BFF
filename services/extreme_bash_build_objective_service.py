from __future__ import annotations

"""Compose reviewed build-owned Bash sources for the Extreme/MOST Bash objective."""

from dataclasses import dataclass, replace

from .extreme_bash_champion_point_service import ExtremeBashChampionPointResult
from .extreme_bash_jewelry_service import ExtremeBashJewelryResult
from .extreme_bash_objective_service import (
    ExtremeBashDamageInputs,
    ExtremeBashLegalityContext,
    ExtremeBashObjectiveResult,
    ExtremeBashObjectiveService,
)


@dataclass(frozen=True)
class ExtremeBashBuildObjectiveResult:
    objective: ExtremeBashObjectiveResult
    source_blockers: tuple[str, ...] = ()

    @property
    def reviewed_value(self) -> float:
        return self.objective.reviewed_value

    @property
    def mechanic_complete(self) -> bool:
        return self.objective.mechanic_complete and not self.source_blockers


class ExtremeBashBuildObjectiveService:
    """Feed canonical CP and jewelry evidence into the existing Bash formula."""

    @classmethod
    def evaluate_damage(
        cls,
        inputs: ExtremeBashDamageInputs,
        *,
        legality: ExtremeBashLegalityContext | None = None,
        champion_point: ExtremeBashChampionPointResult | None = None,
        jewelry: ExtremeBashJewelryResult | None = None,
    ) -> ExtremeBashBuildObjectiveResult:
        source_blockers: list[str] = []
        resolved_inputs = inputs

        if champion_point is not None:
            if inputs.cp_bash_damage is not None:
                raise ValueError(
                    "cp_bash_damage was supplied directly and through Champion Point evidence"
                )
            if champion_point.reviewed_formula_value is not None:
                resolved_inputs = replace(
                    resolved_inputs,
                    cp_bash_damage=float(champion_point.reviewed_formula_value),
                )
            source_blockers.extend(
                f"Champion Point {champion_point.name}: {problem}"
                for problem in champion_point.unresolved
            )

        if jewelry is not None:
            if inputs.item_extra_bash_damage is not None:
                raise ValueError(
                    "item_extra_bash_damage was supplied directly and through jewelry evidence"
                )
            resolved_inputs = replace(
                resolved_inputs,
                item_extra_bash_damage=float(
                    jewelry.reviewed_item_extra_bash_damage
                ),
            )
            source_blockers.extend(
                f"Jewelry: {problem}" for problem in jewelry.unresolved
            )

        objective = ExtremeBashObjectiveService.evaluate_damage(
            resolved_inputs,
            legality=legality,
        )
        return ExtremeBashBuildObjectiveResult(
            objective=objective,
            source_blockers=tuple(source_blockers),
        )
