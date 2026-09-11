from __future__ import annotations

"""Audit canonical Champion Point coverage for Extreme max-resource objectives.

This service owns no Champion Point stat math.  It projects the canonical
``ChampionPointStaticRepository`` through ``ExtremeChampionPointObjectiveService``
and classifies every CP star for one max-resource objective.

The audit deliberately keeps mechanic coverage separate from legal slottable-bar
execution.  A slottable resource star can be fully stat-mapped here while the
four-star Champion Bar optimizer remains a separate search problem.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from services.extreme_champion_point_objective_service import (
    ExtremeChampionPointObjectiveService,
)


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


@dataclass(frozen=True)
class ExtremeResourceChampionPointCoverageAudit:
    objective_key: str
    non_slottable_reviewed: int
    slottable_reviewed: int
    non_slottable_relevant: tuple[str, ...]
    slottable_relevant: tuple[str, ...]
    proven_irrelevant: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def champion_points_reviewed(self) -> int:
        return self.non_slottable_reviewed + self.slottable_reviewed

    @property
    def denominator_proven(self) -> bool:
        classified = (
            len(self.non_slottable_relevant)
            + len(self.slottable_relevant)
            + len(self.proven_irrelevant)
            + len(self.unresolved)
        )
        return self.champion_points_reviewed > 0 and classified == self.champion_points_reviewed

    @property
    def mechanic_complete(self) -> bool:
        """Whether every CP star has reviewed stat semantics for this objective."""
        return self.denominator_proven and not self.unresolved

    @property
    def slottable_search_required(self) -> bool:
        """Whether a legal four-star Champion Bar search can change this objective."""
        return bool(self.slottable_relevant)

    @property
    def projection_complete(self) -> bool:
        """Whether CP can be closed without any further slottable-loadout search."""
        return self.mechanic_complete and not self.slottable_search_required


class ExtremeResourceChampionPointCoverageAuditService:
    """Classify every canonical CP star for one max-resource objective."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: ChampionPointStaticRepository | None = None,
    ) -> None:
        if repository is None and database_path is None:
            raise ValueError("database_path is required when no Champion Point repository is supplied")
        self.repository = repository or ChampionPointStaticRepository(database_path)  # type: ignore[arg-type]

    def build(self, objective_key: str) -> ExtremeResourceChampionPointCoverageAudit:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource Champion Point objective: {objective_key!r}")

        non_slottable = tuple(self.repository.non_slottable_records())
        slottable = tuple(self.repository.slottable_records())

        non_slottable_relevant: list[str] = []
        slottable_relevant: list[str] = []
        irrelevant: list[str] = []
        unresolved: list[str] = []

        for record in (*non_slottable, *slottable):
            candidate = ExtremeChampionPointObjectiveService.candidate_for_record(
                self.repository,
                record,
                key,
            )
            if candidate.reviewed_delta is None:
                detail = "; ".join(candidate.unresolved) or "unresolved Champion Point mechanic"
                unresolved.append(f"{record.name}: {detail}")
                continue
            if candidate.reviewed_delta > 0.0:
                target = slottable_relevant if record.is_slottable else non_slottable_relevant
                target.append(f"{record.name}: +{candidate.reviewed_delta:g}")
                continue
            irrelevant.append(record.name)

        return ExtremeResourceChampionPointCoverageAudit(
            objective_key=key,
            non_slottable_reviewed=len(non_slottable),
            slottable_reviewed=len(slottable),
            non_slottable_relevant=tuple(non_slottable_relevant),
            slottable_relevant=tuple(slottable_relevant),
            proven_irrelevant=tuple(irrelevant),
            unresolved=tuple(unresolved),
        )


__all__ = [
    "ExtremeResourceChampionPointCoverageAudit",
    "ExtremeResourceChampionPointCoverageAuditService",
]
