from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from minmax.character_build.character_class import CharacterClass
from services.class_mastery_classification_service import ClassMasteryBoundary
from services.extreme_class_configuration_service import ExtremeClassConfigurationService
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService


class ExtremeClassRouteKind(str, Enum):
    PURE_MASTERY = "pure_mastery"
    SUBCLASS = "subclass"


@dataclass(frozen=True)
class ExtremeClassRouteCandidate:
    route_kind: ExtremeClassRouteKind
    base_class: CharacterClass
    objective_key: str
    equipped_skill_lines: tuple[str, ...]
    mastery_names: tuple[str, ...] = ()
    projected_delta: float | None = None
    boundary: ClassMasteryBoundary | None = None
    score_status: str = ""

    @property
    def is_scored(self) -> bool:
        return self.projected_delta is not None


@dataclass(frozen=True)
class ExtremeClassRouteComparison:
    objective_key: str
    routes: tuple[ExtremeClassRouteCandidate, ...]
    best_reviewed_pure_route: ExtremeClassRouteCandidate | None
    unresolved_subclass_count: int

    @property
    def can_declare_global_winner(self) -> bool:
        return self.unresolved_subclass_count == 0


class ExtremeClassRouteComparisonService:
    """Compare reviewed pure-class mastery routes against legal subclass routes.

    Pure-class Class Mastery effects can be scored only where BFF has reviewed
    numeric mechanics. Subclass routes are still enumerated here, but remain
    explicitly unscored until the borrowed skill-line passive/slot effects are
    evaluated for the same objective. That prevents a partially modeled pure
    class from being announced as the global winner by accident.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.mastery_pairs = ExtremeClassMasteryPairService(database_path)

    def compare(
        self,
        objective_key: str,
        *,
        reference_value: float | None = None,
        higher_max_resource: float | None = None,
    ) -> ExtremeClassRouteComparison:
        routes: list[ExtremeClassRouteCandidate] = []

        pure_rows = self.mastery_pairs.best_pure_class_routes(
            objective_key,
            reference_value=reference_value,
            higher_max_resource=higher_max_resource,
        )
        for row in pure_rows:
            pure_config = next(
                candidate
                for candidate in ExtremeClassConfigurationService.candidates_for_base_class(row.base_class)
                if candidate.is_pure_class
            )
            routes.append(
                ExtremeClassRouteCandidate(
                    route_kind=ExtremeClassRouteKind.PURE_MASTERY,
                    base_class=row.base_class,
                    objective_key=objective_key,
                    equipped_skill_lines=pure_config.equipped_skill_lines,
                    mastery_names=row.passive_names,
                    projected_delta=row.projected_delta,
                    boundary=row.boundary,
                    score_status="reviewed_mastery_delta",
                )
            )

        subclass_count = 0
        for config in ExtremeClassConfigurationService.all_candidates():
            if config.is_pure_class:
                continue
            subclass_count += 1
            routes.append(
                ExtremeClassRouteCandidate(
                    route_kind=ExtremeClassRouteKind.SUBCLASS,
                    base_class=config.base_class,
                    objective_key=objective_key,
                    equipped_skill_lines=config.equipped_skill_lines,
                    mastery_names=(),
                    projected_delta=None,
                    boundary=None,
                    score_status="pending_subclass_effect_resolution",
                )
            )

        best_pure = next(
            (
                row
                for row in sorted(
                    (item for item in routes if item.route_kind is ExtremeClassRouteKind.PURE_MASTERY),
                    key=lambda item: (-(item.projected_delta or 0.0), item.base_class.value),
                )
            ),
            None,
        )

        return ExtremeClassRouteComparison(
            objective_key=objective_key,
            routes=tuple(routes),
            best_reviewed_pure_route=best_pure,
            unresolved_subclass_count=subclass_count,
        )
