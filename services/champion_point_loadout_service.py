from __future__ import annotations

"""Prove Champion Point loadouts under per-discipline slot limits.

This service owns only structural Champion Bar legality. Candidate mechanics and
numeric ceilings are supplied by authoritative upstream evaluators. Runtime
conditions remain attached to selected candidates but are not treated as proven
merely because the stars fit on the bar.

``build`` remains the additive-objective shortcut used by objectives whose
candidates share one comparable numeric unit. ``enumerate_legal_loadouts`` is the
score-neutral path for mixed-unit objectives such as an actual healing event,
where flat power, percent Healing Done, and Critical Healing must never be ranked
against one another before canonical event evaluation.
"""

from dataclasses import dataclass
from itertools import combinations, product
import math


CHAMPION_POINT_SLOTS_PER_DISCIPLINE = 4


@dataclass(frozen=True)
class ChampionPointLoadoutCandidate:
    name: str
    discipline_index: int | None
    flat_ceiling: float
    condition: str | None = None


@dataclass(frozen=True)
class ChampionPointSlotCandidate:
    """One score-neutral CP option whose legality is discipline/slot based."""

    name: str
    discipline_index: int | None


@dataclass(frozen=True)
class ChampionPointLoadoutResult:
    selected: tuple[ChampionPointLoadoutCandidate, ...] = ()
    excluded: tuple[ChampionPointLoadoutCandidate, ...] = ()
    discipline_slot_counts: tuple[tuple[int, int], ...] = ()
    total_flat_ceiling: float = 0.0
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return not self.unresolved


@dataclass(frozen=True)
class ChampionPointLoadoutEnumerationResult:
    """Every structurally legal full relevant loadout for mixed-unit scoring."""

    loadouts: tuple[tuple[ChampionPointSlotCandidate, ...], ...] = ()
    candidate_count: int = 0
    discipline_candidate_counts: tuple[tuple[int, int], ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return not self.unresolved


class ChampionPointLoadoutService:
    """Own structural Champion Bar legality for additive and mixed-unit search."""

    @staticmethod
    def build(
        candidates: tuple[ChampionPointLoadoutCandidate, ...],
    ) -> ChampionPointLoadoutResult:
        unresolved: list[str] = []
        seen: set[str] = set()
        grouped: dict[int, list[ChampionPointLoadoutCandidate]] = {}

        for candidate in candidates:
            name = str(candidate.name or "").strip()
            identity = name.casefold()
            if not name:
                unresolved.append("Champion Point loadout candidate has no name")
                continue
            if identity in seen:
                unresolved.append(f"duplicate Champion Point loadout candidate: {name}")
                continue
            seen.add(identity)

            discipline = candidate.discipline_index
            if discipline is None:
                unresolved.append(
                    f"{name}: discipline identity is required for Champion Bar legality"
                )
                continue
            if int(discipline) < 0:
                unresolved.append(f"{name}: invalid discipline index {discipline}")
                continue

            ceiling = float(candidate.flat_ceiling)
            if not math.isfinite(ceiling) or ceiling < 0.0:
                unresolved.append(f"{name}: invalid additive ceiling {ceiling!r}")
                continue
            grouped.setdefault(int(discipline), []).append(candidate)

        if unresolved:
            return ChampionPointLoadoutResult(unresolved=tuple(unresolved))

        selected: list[ChampionPointLoadoutCandidate] = []
        excluded: list[ChampionPointLoadoutCandidate] = []
        slot_counts: list[tuple[int, int]] = []
        for discipline, rows in sorted(grouped.items()):
            ranked = sorted(
                rows,
                key=lambda row: (-float(row.flat_ceiling), row.name.casefold()),
            )
            chosen = ranked[:CHAMPION_POINT_SLOTS_PER_DISCIPLINE]
            selected.extend(chosen)
            excluded.extend(ranked[CHAMPION_POINT_SLOTS_PER_DISCIPLINE:])
            slot_counts.append((discipline, len(chosen)))

        return ChampionPointLoadoutResult(
            selected=tuple(selected),
            excluded=tuple(excluded),
            discipline_slot_counts=tuple(slot_counts),
            total_flat_ceiling=sum(float(row.flat_ceiling) for row in selected),
        )

    @staticmethod
    def enumerate_legal_loadouts(
        candidates: tuple[ChampionPointSlotCandidate, ...],
    ) -> ChampionPointLoadoutEnumerationResult:
        """Enumerate legal relevant-star combinations without comparing units.

        For each discipline, every relevant candidate is included when four or
        fewer exist. When more than four relevant candidates exist, every
        four-star combination is emitted. Leaving a relevant slot empty cannot
        improve an objective because selecting a CP star has no intrinsic
        negative effect; unrelated stars may fill any remaining slots later.
        """

        unresolved: list[str] = []
        seen: set[str] = set()
        grouped: dict[int, list[ChampionPointSlotCandidate]] = {}
        for candidate in candidates:
            name = str(candidate.name or "").strip()
            identity = name.casefold()
            if not name:
                unresolved.append("Champion Point slot candidate has no name")
                continue
            if identity in seen:
                unresolved.append(f"duplicate Champion Point slot candidate: {name}")
                continue
            seen.add(identity)

            discipline = candidate.discipline_index
            if discipline is None:
                unresolved.append(
                    f"{name}: discipline identity is required for Champion Bar legality"
                )
                continue
            if int(discipline) < 0:
                unresolved.append(f"{name}: invalid discipline index {discipline}")
                continue
            grouped.setdefault(int(discipline), []).append(
                ChampionPointSlotCandidate(name=name, discipline_index=int(discipline))
            )

        if unresolved:
            return ChampionPointLoadoutEnumerationResult(
                candidate_count=len(candidates),
                unresolved=tuple(unresolved),
            )
        if not grouped:
            return ChampionPointLoadoutEnumerationResult(
                loadouts=((),),
                candidate_count=0,
            )

        per_discipline: list[tuple[tuple[ChampionPointSlotCandidate, ...], ...]] = []
        counts: list[tuple[int, int]] = []
        for discipline, rows in sorted(grouped.items()):
            ordered = tuple(sorted(rows, key=lambda row: row.name.casefold()))
            counts.append((discipline, len(ordered)))
            if len(ordered) <= CHAMPION_POINT_SLOTS_PER_DISCIPLINE:
                per_discipline.append((ordered,))
            else:
                per_discipline.append(
                    tuple(combinations(ordered, CHAMPION_POINT_SLOTS_PER_DISCIPLINE))
                )

        loadouts = tuple(
            tuple(candidate for group in choice for candidate in group)
            for choice in product(*per_discipline)
        )
        return ChampionPointLoadoutEnumerationResult(
            loadouts=loadouts,
            candidate_count=len(candidates),
            discipline_candidate_counts=tuple(counts),
        )


__all__ = [
    "CHAMPION_POINT_SLOTS_PER_DISCIPLINE",
    "ChampionPointLoadoutCandidate",
    "ChampionPointSlotCandidate",
    "ChampionPointLoadoutResult",
    "ChampionPointLoadoutEnumerationResult",
    "ChampionPointLoadoutService",
]
