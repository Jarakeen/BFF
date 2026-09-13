from __future__ import annotations

"""Prove additive Champion Point loadouts under per-discipline slot limits.

This service owns only structural Champion Bar legality. Candidate mechanics and
numeric ceilings are supplied by authoritative upstream evaluators. Runtime
conditions remain attached to selected candidates but are not treated as proven
merely because the stars fit on the bar.
"""

from dataclasses import dataclass
import math


CHAMPION_POINT_SLOTS_PER_DISCIPLINE = 4


@dataclass(frozen=True)
class ChampionPointLoadoutCandidate:
    name: str
    discipline_index: int | None
    flat_ceiling: float
    condition: str | None = None


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


class ChampionPointLoadoutService:
    """Select the additive top four candidates within each CP discipline."""

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


__all__ = [
    "CHAMPION_POINT_SLOTS_PER_DISCIPLINE",
    "ChampionPointLoadoutCandidate",
    "ChampionPointLoadoutResult",
    "ChampionPointLoadoutService",
]
