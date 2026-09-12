from __future__ import annotations

"""Build the exact Champion Point continuation required by max-resource Extreme search.

The full CP denominator is reviewed separately. Once that audit proves every star
classified for the requested max resource, this service reduces the legal CP state
to the resource-relevant stars only:

* every relevant non-slottable passive is purchased at max rank;
* up to four relevant slottable stars are selected by reviewed objective delta.

For the current max-resource catalog there is at most one relevant slottable star
per objective, but the four-slot rule is kept explicit so future CP changes fail
closed instead of silently overflowing the Champion Bar.
"""

from dataclasses import dataclass, replace
from pathlib import Path

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.character_progression import CharacterProgression, MAX_SLOTTED_PER_TREE
from models.build_model import ChampionPointEntry, PlayerBuild
from services.extreme_champion_point_objective_service import (
    ExtremeChampionPointObjectiveService,
)
from services.extreme_resource_canonical_static_snapshot_service import (
    ExtremeResourceCanonicalStaticSnapshotService,
)
from services.extreme_resource_champion_point_coverage_audit_service import (
    ExtremeResourceChampionPointCoverageAuditService,
)


@dataclass(frozen=True)
class ExtremeResourceChampionPointState:
    objective_key: str
    non_slottable_allocations: tuple[tuple[str, int, float], ...]
    slottable_allocations: tuple[tuple[str, int, float], ...]
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.objective_key,
            self.non_slottable_allocations,
            self.slottable_allocations,
        )

    @property
    def reviewed_delta(self) -> float:
        return sum(row[2] for row in self.non_slottable_allocations) + sum(
            row[2] for row in self.slottable_allocations
        )


class ExtremeResourceChampionPointStateService:
    """Resolve and materialize the strongest legal max-resource CP state."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: ChampionPointStaticRepository | None = None,
        audit_service: ExtremeResourceChampionPointCoverageAuditService | None = None,
    ) -> None:
        if repository is None and database_path is None:
            raise ValueError("database_path is required when no Champion Point repository is supplied")
        self.repository = (
            repository
            if repository is not None
            else ExtremeResourceCanonicalStaticSnapshotService(database_path).build().champion_point_repository  # type: ignore[arg-type]
        )
        self.audit_service = audit_service or ExtremeResourceChampionPointCoverageAuditService(
            repository=self.repository
        )
        # Champion Point continuation depends only on the objective and canonical
        # CP catalogue, not on gear, armor, class route, bar, food, or runtime
        # candidate state. Cache the complete fail-closed result per objective on
        # each state service; production instances share the snapshot-owned canonical
        # repository for the same immutable database snapshot.
        self._state_cache: dict[str, ExtremeResourceChampionPointState] = {}

    def build(self, objective_key: str) -> ExtremeResourceChampionPointState:
        key = str(objective_key or "").strip().casefold()
        cached = self._state_cache.get(key)
        if cached is not None:
            return cached

        audit = self.audit_service.build(key)
        if not audit.mechanic_complete:
            state = ExtremeResourceChampionPointState(
                objective_key=key,
                non_slottable_allocations=(),
                slottable_allocations=(),
                denominator_proven=False,
                unresolved=tuple(audit.unresolved),
            )
            self._state_cache[key] = state
            return state

        non_slottable: list[tuple[str, int, float]] = []
        slottable: list[tuple[str, int, float]] = []
        for record in (
            *self.repository.non_slottable_records(),
            *self.repository.slottable_records(),
        ):
            candidate = ExtremeChampionPointObjectiveService.candidate_for_record(
                self.repository,
                record,
                key,
            )
            if candidate.reviewed_delta is None or candidate.reviewed_delta <= 0.0:
                continue
            row = (record.name, int(record.max_points), float(candidate.reviewed_delta))
            if record.is_slottable:
                slottable.append(row)
            else:
                non_slottable.append(row)

        slottable.sort(key=lambda row: (-row[2], row[0].casefold()))
        selected = tuple(slottable[:MAX_SLOTTED_PER_TREE])
        overflow = tuple(slottable[MAX_SLOTTED_PER_TREE:])
        unresolved = ()
        if overflow:
            # The current resource effects are additive flat stats, so selecting
            # the top four reviewed deltas is exact. Preserve an explicit guard
            # if that assumption changes under a future objective implementation.
            unresolved = tuple(
                f"additional relevant slottable CP excluded after four-slot limit: {name}"
                for name, _points, _delta in overflow
            )

        state = ExtremeResourceChampionPointState(
            objective_key=key,
            non_slottable_allocations=tuple(
                sorted(non_slottable, key=lambda row: row[0].casefold())
            ),
            slottable_allocations=selected,
            denominator_proven=bool(audit.denominator_proven and not unresolved),
            unresolved=unresolved,
        )
        self._state_cache[key] = state
        return state

    @staticmethod
    def materialize_progression(
        progression: CharacterProgression,
        state: ExtremeResourceChampionPointState,
    ) -> CharacterProgression:
        allocations = dict(progression.passive_cp_points or {})
        for name, points, _delta in state.non_slottable_allocations:
            allocations[name] = int(points)
        return replace(progression, passive_cp_points=allocations)

    @staticmethod
    def materialize_build(
        build: PlayerBuild,
        state: ExtremeResourceChampionPointState,
    ) -> PlayerBuild:
        existing_non_target = []
        selected_names = {name.casefold() for name, _points, _delta in state.slottable_allocations}
        for entry in build.ChampionPoints:
            name = str(entry.Name or "").strip()
            if not name or name.casefold() in selected_names:
                continue
            existing_non_target.append(entry)
        selected = [
            ChampionPointEntry(Name=name, Points=str(points))
            for name, points, _delta in state.slottable_allocations
        ]
        return replace(build, ChampionPoints=[*existing_non_target, *selected])


__all__ = [
    "ExtremeResourceChampionPointState",
    "ExtremeResourceChampionPointStateService",
]
