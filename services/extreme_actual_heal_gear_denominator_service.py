from __future__ import annotations

"""Count the canonical ordinary-set denominator used by Extreme MOST Actual Heal.

This service does not broaden gear search and does not change scoring. It makes the
existing fail-closed ordinary five-piece admission rule countable by assigning every
canonical gear set exactly one H1 disposition.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from minmax.gear_set_repository import GearSetRepository
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class ExtremeActualHealGearDisposition(str, Enum):
    ACCEPTED = "accepted"
    UNRESOLVED = "unresolved"
    NO_FIVE_PIECE_SHAPE = "no_five_piece_shape"
    REVIEWED_NONPOSITIVE = "reviewed_nonpositive"


@dataclass(frozen=True)
class ExtremeActualHealGearDenominatorRow:
    set_id: int
    set_name: str
    category: str | None
    maximum_useful_piece_count: int
    disposition: ExtremeActualHealGearDisposition
    positive_objectives: tuple[str, ...] = ()
    unresolved_objectives: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeActualHealGearDenominatorReport:
    rows: tuple[ExtremeActualHealGearDenominatorRow, ...]
    accepted_candidate_names: tuple[str, ...]
    candidate_pool_matches_denominator: bool

    @property
    def denominator_count(self) -> int:
        return len(self.rows)

    def count(self, disposition: ExtremeActualHealGearDisposition) -> int:
        return sum(1 for row in self.rows if row.disposition is disposition)

    @property
    def disposition_total(self) -> int:
        return sum(self.count(disposition) for disposition in ExtremeActualHealGearDisposition)

    @property
    def denominator_proven(self) -> bool:
        return (
            self.denominator_count > 0
            and self.disposition_total == self.denominator_count
            and self.candidate_pool_matches_denominator
        )


class ExtremeActualHealGearDenominatorService:
    """Disposition every canonical set under the existing H1 ordinary-set rules."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: GearSetRepository | None = None,
    ) -> None:
        if repository is None:
            if database_path is None:
                raise ValueError("database_path is required when repository is not supplied")
            repository = GearSetRepository(database_path)
        self.repository = repository
        self.candidate_service = ExtremeActualHealGearSetCandidateService.__new__(
            ExtremeActualHealGearSetCandidateService
        )
        self.candidate_service.repository = repository

    def build(self) -> ExtremeActualHealGearDenominatorReport:
        objectives = tuple(self.candidate_service.OBJECTIVES)
        rows_by_objective = {
            objective: ExtremeGearSetObjectiveService.candidates_for_objective(
                self.repository,
                objective,
            )
            for objective in objectives
        }
        objective_by_set = {
            objective: {int(row.set_id): row for row in rows}
            for objective, rows in rows_by_objective.items()
        }

        result: list[ExtremeActualHealGearDenominatorRow] = []
        accepted_names: list[str] = []
        for gear_set in self.repository.list_sets():
            set_id = int(gear_set.id)
            useful = ExtremeGearSetObjectiveService._maximum_useful_piece_count(
                self.repository,
                gear_set,
            )
            objective_rows = tuple(
                objective_by_set[objective][set_id]
                for objective in objectives
                if set_id in objective_by_set[objective]
            )

            unresolved_objectives: list[str] = []
            blockers: list[str] = []
            positive_objectives: list[str] = []
            for row in objective_rows:
                review = self.candidate_service._h1_review(row)
                if not review.h1_mechanic_complete:
                    unresolved_objectives.append(str(row.objective_key))
                    blockers.extend(review.remaining_blockers)
                elif self.candidate_service._h1_positive(row):
                    positive_objectives.append(str(row.objective_key))

            if useful < 5:
                disposition = ExtremeActualHealGearDisposition.NO_FIVE_PIECE_SHAPE
            elif unresolved_objectives:
                disposition = ExtremeActualHealGearDisposition.UNRESOLVED
            elif positive_objectives:
                disposition = ExtremeActualHealGearDisposition.ACCEPTED
                accepted_names.append(str(gear_set.name))
            else:
                disposition = ExtremeActualHealGearDisposition.REVIEWED_NONPOSITIVE

            result.append(
                ExtremeActualHealGearDenominatorRow(
                    set_id=set_id,
                    set_name=str(gear_set.name),
                    category=gear_set.category,
                    maximum_useful_piece_count=int(useful),
                    disposition=disposition,
                    positive_objectives=tuple(dict.fromkeys(positive_objectives)),
                    unresolved_objectives=tuple(dict.fromkeys(unresolved_objectives)),
                    blockers=tuple(dict.fromkeys(str(value) for value in blockers if str(value).strip())),
                )
            )

        result.sort(key=lambda row: (row.set_name.casefold(), row.set_id))
        candidate_names = self.candidate_service.candidate_set_names(per_objective=None)
        accepted_by_disposition = tuple(
            row.set_name
            for row in result
            if row.disposition is ExtremeActualHealGearDisposition.ACCEPTED
        )
        return ExtremeActualHealGearDenominatorReport(
            rows=tuple(result),
            accepted_candidate_names=tuple(candidate_names),
            candidate_pool_matches_denominator=(
                set(name.casefold() for name in candidate_names)
                == set(name.casefold() for name in accepted_by_disposition)
            ),
        )


__all__ = [
    "ExtremeActualHealGearDenominatorReport",
    "ExtremeActualHealGearDenominatorRow",
    "ExtremeActualHealGearDenominatorService",
    "ExtremeActualHealGearDisposition",
]
