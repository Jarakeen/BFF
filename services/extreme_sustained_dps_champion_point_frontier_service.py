from __future__ import annotations

"""Lazy legal Champion Point loadout frontier for sustained-DPS generated search.

Structural legality remains four slottable stars per discipline. This frontier keeps
all canonical slottable stars in the denominator and indexes the cross-discipline
combination product without materializing it.
"""

from dataclasses import dataclass
from math import comb

from minmax.champion_point_static_repository import (
    ChampionPointRecord,
    ChampionPointStaticRepository,
)
from models.build_model import ChampionPointEntry, PlayerBuild
from services.champion_point_loadout_service import CHAMPION_POINT_SLOTS_PER_DISCIPLINE


@dataclass(frozen=True)
class ExtremeSustainedDPSChampionPointDisciplineAxis:
    discipline_index: int
    star_names: tuple[str, ...]
    selected_count: int
    combination_count: int


@dataclass(frozen=True)
class ExtremeSustainedDPSChampionPointCandidate:
    structural_index: int
    selected_star_names: tuple[str, ...]
    build: PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSChampionPointFrontier:
    disciplines: tuple[ExtremeSustainedDPSChampionPointDisciplineAxis, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.disciplines, tuple):
            raise TypeError("Champion Point frontier disciplines must be a tuple")
        if isinstance(self.candidate_count, bool) or not isinstance(self.candidate_count, int):
            raise TypeError("Champion Point frontier candidate_count must be an integer")
        if self.candidate_count < 0:
            raise ValueError("Champion Point frontier candidate_count cannot be negative")
        if not isinstance(self.denominator_proven, bool):
            raise TypeError("Champion Point frontier denominator_proven must be boolean")
        if not isinstance(self.evidence, tuple):
            raise TypeError("Champion Point frontier evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("Champion Point frontier unresolved must be a tuple")


class ExtremeSustainedDPSChampionPointFrontierService:
    """Index every structurally legal full canonical slottable CP loadout lazily."""

    def __init__(self, repository: ChampionPointStaticRepository | object) -> None:
        self.repository = repository

    @classmethod
    def from_database(cls, database_path) -> "ExtremeSustainedDPSChampionPointFrontierService":
        return cls(ChampionPointStaticRepository(database_path))

    def frontier(self) -> ExtremeSustainedDPSChampionPointFrontier:
        unresolved: list[str] = []
        grouped: dict[int, list[ChampionPointRecord]] = {}
        seen: set[str] = set()

        for record in self.repository.slottable_records():
            name = str(record.name or "").strip()
            key = name.casefold()
            if not name:
                unresolved.append("Canonical slottable Champion Point has no name")
                continue
            if key in seen:
                unresolved.append(f"Duplicate canonical slottable Champion Point: {name}")
                continue
            seen.add(key)
            if record.discipline_index is None or int(record.discipline_index) < 0:
                unresolved.append(f"{name}: Champion Point discipline identity is unavailable")
                continue
            grouped.setdefault(int(record.discipline_index), []).append(record)

        axes: list[ExtremeSustainedDPSChampionPointDisciplineAxis] = []
        count = 1
        for discipline, rows in sorted(grouped.items()):
            names = tuple(sorted((row.name for row in rows), key=str.casefold))
            selected = min(CHAMPION_POINT_SLOTS_PER_DISCIPLINE, len(names))
            combinations = comb(len(names), selected) if selected else 1
            axes.append(
                ExtremeSustainedDPSChampionPointDisciplineAxis(
                    discipline_index=discipline,
                    star_names=names,
                    selected_count=selected,
                    combination_count=combinations,
                )
            )
            count *= combinations

        if not axes:
            unresolved.append("Canonical slottable Champion Point denominator is empty")

        proven = bool(axes and count > 0 and not unresolved)
        return ExtremeSustainedDPSChampionPointFrontier(
            disciplines=tuple(axes),
            candidate_count=count,
            denominator_proven=proven,
            evidence=(
                f"Champion Point disciplines in frontier: {len(axes)}",
                f"Canonical slottable stars reviewed: {sum(len(axis.star_names) for axis in axes)}",
                f"Legal CP loadout denominator: {count}",
                f"Champion Bar slots per discipline: {CHAMPION_POINT_SLOTS_PER_DISCIPLINE}",
                "Dynamic/runtime Champion Point mechanics remain attached to selected identities for later evaluation",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def candidate_at(
        self,
        baseline_build: PlayerBuild,
        index: int,
    ) -> ExtremeSustainedDPSChampionPointCandidate:
        frontier = self.frontier()
        if not frontier.denominator_proven:
            raise ValueError(
                "Champion Point frontier denominator is unresolved: "
                + "; ".join(frontier.unresolved)
            )

        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("Champion Point candidate index must be an integer")
        target = index
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("Champion Point candidate index out of range")

        remainder = target
        selections_reversed: list[tuple[str, ...]] = []
        for axis in reversed(frontier.disciplines):
            local_index = remainder % axis.combination_count
            remainder //= axis.combination_count
            selections_reversed.append(
                self._combination_at(
                    axis.star_names,
                    axis.selected_count,
                    local_index,
                )
            )

        selected_by_axis = tuple(reversed(selections_reversed))
        selected_names = tuple(
            name
            for selection in selected_by_axis
            for name in selection
        )

        build = PlayerBuild.from_dict(baseline_build.to_dict())
        entries: list[ChampionPointEntry] = []
        for name in selected_names:
            record = self.repository.get(name)
            if record is None:
                raise ValueError(f"Canonical Champion Point disappeared during materialization: {name}")
            entries.append(
                ChampionPointEntry(
                    Name=record.name,
                    Points=str(record.max_points),
                )
            )
        entries.sort(key=lambda entry: str(entry.Name or "").casefold())
        build.ChampionPoints = entries

        return ExtremeSustainedDPSChampionPointCandidate(
            structural_index=target,
            selected_star_names=selected_names,
            build=build,
        )

    def page(
        self,
        baseline_build: PlayerBuild,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ExtremeSustainedDPSChampionPointCandidate, ...]:
        frontier = self.frontier()
        if isinstance(offset, bool) or not isinstance(offset, int):
            raise TypeError("Champion Point page offset must be an integer")
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("Champion Point page limit must be an integer")
        start = max(0, offset)
        size = max(0, limit)
        if size == 0 or start >= frontier.candidate_count:
            return ()
        return tuple(
            self.candidate_at(baseline_build, index)
            for index in range(start, min(frontier.candidate_count, start + size))
        )

    @staticmethod
    def _combination_at(
        values: tuple[str, ...],
        choose: int,
        index: int,
    ) -> tuple[str, ...]:
        if isinstance(choose, bool) or not isinstance(choose, int):
            raise TypeError("Champion Point combination choose must be an integer")
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("Champion Point combination index must be an integer")
        n = len(values)
        k = choose
        target = index
        if k < 0 or k > n:
            raise ValueError("Champion Point combination choose is out of range")
        total = comb(n, k)
        if target < 0 or target >= total:
            raise IndexError("Champion Point discipline combination index out of range")
        if k == 0:
            return ()

        result: list[str] = []
        start = 0
        remaining_rank = target
        for remaining_slots in range(k, 0, -1):
            for position in range(start, n):
                tail = comb(n - position - 1, remaining_slots - 1)
                if remaining_rank < tail:
                    result.append(values[position])
                    start = position + 1
                    break
                remaining_rank -= tail
        return tuple(result)


__all__ = [
    "ExtremeSustainedDPSChampionPointCandidate",
    "ExtremeSustainedDPSChampionPointDisciplineAxis",
    "ExtremeSustainedDPSChampionPointFrontier",
    "ExtremeSustainedDPSChampionPointFrontierService",
]
