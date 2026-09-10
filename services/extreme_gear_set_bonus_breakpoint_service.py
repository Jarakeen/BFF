from __future__ import annotations

"""Canonical set-bonus breakpoint evidence for Extreme gear search.

A named set only changes *set-bonus* mechanics when its equipped count reaches a
canonical ``gear_set_bonus.piece_count`` threshold.  Counts between thresholds
consume slots without activating a new set bonus, so they are dominated for the
set-effect search itself and must not be expanded as distinct named-set states.

This service does not claim that the underlying items, traits, glyphs, or weapon
choices are irrelevant.  Those are separate gear axes.  It only proves which
piece counts are mechanically distinct for the named set-bonus layer.
"""

from dataclasses import dataclass

from minmax.gear_set_repository import GearSetRepository


@dataclass(frozen=True)
class ExtremeGearSetBonusBreakpoints:
    set_id: int
    name: str
    max_equip_count: int
    bonus_counts: tuple[int, ...]
    rejected_bonus_counts: tuple[int, ...] = ()

    @property
    def has_set_bonus(self) -> bool:
        return bool(self.bonus_counts)


@dataclass(frozen=True)
class ExtremeGearSetBonusBreakpointCatalog:
    sets: tuple[ExtremeGearSetBonusBreakpoints, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return bool(self.sets) and not self.unresolved

    def by_set_id(self, set_id: int) -> ExtremeGearSetBonusBreakpoints | None:
        target = int(set_id)
        return next((row for row in self.sets if row.set_id == target), None)

    @property
    def mechanically_relevant_sets(self) -> tuple[ExtremeGearSetBonusBreakpoints, ...]:
        return tuple(row for row in self.sets if row.has_set_bonus)


class ExtremeGearSetBonusBreakpointService:
    """Read the finite piece-count thresholds at which each named set changes state."""

    def __init__(self, repository: GearSetRepository) -> None:
        self.repository = repository

    def build(self) -> ExtremeGearSetBonusBreakpointCatalog:
        rows: list[ExtremeGearSetBonusBreakpoints] = []
        unresolved: list[str] = []

        for gear_set in self.repository.list_sets():
            set_id = int(gear_set.id)
            name = str(gear_set.name or "").strip()
            try:
                maximum = int(gear_set.max_equip_count or 0)
            except (TypeError, ValueError):
                maximum = 0

            if not name:
                unresolved.append(f"Gear set {set_id} has no canonical name")
                continue
            if maximum <= 0:
                unresolved.append(f"Gear set {name} has no positive canonical max_equip_count")
                rows.append(
                    ExtremeGearSetBonusBreakpoints(
                        set_id=set_id,
                        name=name,
                        max_equip_count=maximum,
                        bonus_counts=(),
                    )
                )
                continue

            valid: set[int] = set()
            rejected: set[int] = set()
            for bonus in self.repository.get_bonuses(set_id):
                try:
                    count = int(bonus.piece_count)
                except (TypeError, ValueError):
                    unresolved.append(
                        f"Gear set {name} has a non-integer canonical bonus piece_count"
                    )
                    continue
                if count <= 0 or count > maximum:
                    rejected.add(count)
                    unresolved.append(
                        f"Gear set {name} has bonus piece_count {count} outside canonical equip range 1..{maximum}"
                    )
                    continue
                valid.add(count)

            rows.append(
                ExtremeGearSetBonusBreakpoints(
                    set_id=set_id,
                    name=name,
                    max_equip_count=maximum,
                    bonus_counts=tuple(sorted(valid)),
                    rejected_bonus_counts=tuple(sorted(rejected)),
                )
            )

        rows.sort(key=lambda row: (row.name.casefold(), row.name, row.set_id))
        return ExtremeGearSetBonusBreakpointCatalog(
            sets=tuple(rows),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )
