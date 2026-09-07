from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from minmax.character_build.character_class import CharacterClass
from services.class_mastery_classification_service import ClassMasteryBoundary
from services.class_mastery_extreme_effect_service import (
    ClassMasteryExtremeContribution,
    ClassMasteryExtremeEffectService,
)
from services.class_mastery_repository import ClassMasteryPassive, ClassMasteryRepository


_BOUNDARY_RANK = {
    ClassMasteryBoundary.STANDING_SELF_CONTAINED: 0,
    ClassMasteryBoundary.SELF_ACHIEVABLE_CONDITIONAL: 1,
    ClassMasteryBoundary.COMBAT_STATE_DEPENDENT: 2,
    ClassMasteryBoundary.TARGET_STATE_DEPENDENT: 3,
    ClassMasteryBoundary.GROUP_ONLY_OR_NON_SELF: 4,
    ClassMasteryBoundary.NON_SHEET_OR_OTHER: 5,
    ClassMasteryBoundary.UNRESOLVED: 6,
}


@dataclass(frozen=True)
class ExtremeClassMasteryPairCandidate:
    base_class: CharacterClass
    objective_key: str
    passive_names: tuple[str, ...]
    flat: float
    percent: float
    additive_ratio: float
    boundary: ClassMasteryBoundary
    conditions: tuple[str, ...]
    projected_delta: float | None

    @property
    def label(self) -> str:
        names = " + ".join(self.passive_names) if self.passive_names else "No Class Mastery"
        return f"{self.base_class.value}: {names}"


class ExtremeClassMasteryPairService:
    """Enumerate and score legal pure-class Class Mastery selections.

    ESO allows a pure-class character to select up to two Class Mastery passives.
    This service only combines reviewed Class Mastery contributions. It does not
    score subclass skill lines and therefore cannot declare pure class globally
    superior to a subclass route by itself.

    Percent contributions need a caller-supplied reference value to become a
    projected delta. Flat contributions and additive-ratio contributions can be
    compared directly in the objective's own units. This keeps the service from
    inventing a baseline simply to make unlike contribution types sortable.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.repository = ClassMasteryRepository(database_path)

    @staticmethod
    def _objective_contribution(
        passive: ClassMasteryPassive,
        objective_key: str,
        *,
        higher_max_resource: float | None,
    ) -> ClassMasteryExtremeContribution | None:
        for row in ClassMasteryExtremeEffectService.contributions(
            passive,
            higher_max_resource=higher_max_resource,
        ):
            if row.objective_key == objective_key:
                return row
        return None

    @staticmethod
    def _worst_boundary(
        rows: tuple[ClassMasteryExtremeContribution, ...],
    ) -> ClassMasteryBoundary:
        if not rows:
            return ClassMasteryBoundary.STANDING_SELF_CONTAINED
        return max(rows, key=lambda row: _BOUNDARY_RANK[row.boundary]).boundary

    @staticmethod
    def _projected_delta(
        *,
        flat: float,
        percent: float,
        additive_ratio: float,
        reference_value: float | None,
    ) -> float | None:
        if percent and reference_value is None:
            return None
        reference = 0.0 if reference_value is None else float(reference_value)
        return float(flat) + (reference * float(percent)) + float(additive_ratio)

    def candidates_for_class(
        self,
        base_class: CharacterClass,
        objective_key: str,
        *,
        reference_value: float | None = None,
        higher_max_resource: float | None = None,
        include_empty: bool = False,
    ) -> tuple[ExtremeClassMasteryPairCandidate, ...]:
        passives = self.repository.for_class(base_class.value)
        relevant: list[tuple[ClassMasteryPassive, ClassMasteryExtremeContribution]] = []
        for passive in passives:
            contribution = self._objective_contribution(
                passive,
                objective_key,
                higher_max_resource=higher_max_resource,
            )
            if contribution is not None:
                relevant.append((passive, contribution))

        selections: list[tuple[tuple[ClassMasteryPassive, ClassMasteryExtremeContribution], ...]] = []
        if include_empty:
            selections.append(())
        selections.extend((row,) for row in relevant)
        selections.extend(combinations(relevant, 2))

        candidates: list[ExtremeClassMasteryPairCandidate] = []
        for selection in selections:
            contributions = tuple(row[1] for row in selection)
            flat = sum(row.flat for row in contributions)
            percent = sum(row.percent for row in contributions)
            additive_ratio = sum(row.additive_ratio for row in contributions)
            conditions = tuple(
                dict.fromkeys(row.condition for row in contributions if row.condition)
            )
            candidates.append(
                ExtremeClassMasteryPairCandidate(
                    base_class=base_class,
                    objective_key=objective_key,
                    passive_names=tuple(row[0].name for row in selection),
                    flat=flat,
                    percent=percent,
                    additive_ratio=additive_ratio,
                    boundary=self._worst_boundary(contributions),
                    conditions=conditions,
                    projected_delta=self._projected_delta(
                        flat=flat,
                        percent=percent,
                        additive_ratio=additive_ratio,
                        reference_value=reference_value,
                    ),
                )
            )

        return tuple(
            sorted(
                candidates,
                key=lambda row: (
                    row.projected_delta is None,
                    -(row.projected_delta or 0.0),
                    _BOUNDARY_RANK[row.boundary],
                    tuple(name.casefold() for name in row.passive_names),
                ),
            )
        )

    def best_for_class(
        self,
        base_class: CharacterClass,
        objective_key: str,
        *,
        reference_value: float | None = None,
        higher_max_resource: float | None = None,
    ) -> ExtremeClassMasteryPairCandidate | None:
        rows = self.candidates_for_class(
            base_class,
            objective_key,
            reference_value=reference_value,
            higher_max_resource=higher_max_resource,
        )
        return next((row for row in rows if row.projected_delta is not None), None)

    def best_pure_class_routes(
        self,
        objective_key: str,
        *,
        reference_value: float | None = None,
        higher_max_resource: float | None = None,
    ) -> tuple[ExtremeClassMasteryPairCandidate, ...]:
        rows = []
        for base_class in sorted(CharacterClass, key=lambda item: item.value):
            best = self.best_for_class(
                base_class,
                objective_key,
                reference_value=reference_value,
                higher_max_resource=higher_max_resource,
            )
            if best is not None:
                rows.append(best)
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    -(row.projected_delta or 0.0),
                    _BOUNDARY_RANK[row.boundary],
                    row.base_class.value,
                ),
            )
        )
